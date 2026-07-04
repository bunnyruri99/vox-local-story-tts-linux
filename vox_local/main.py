from __future__ import annotations

import re
import secrets
import unicodedata
import hashlib
import base64
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import requests
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from vox_local import __version__
from vox_local.cache import AudioCache
from vox_local.config import Settings
from vox_local.models import (
    HistoryItem,
    LocalVoiceInfo,
    PreparedChunk,
    TTSBatchItem,
    TTSBatchRequest,
    TTSBatchResponse,
    TTSRequest,
    TextPrepareRequest,
    TextPrepareResponse,
    VoiceInfo,
)
from vox_local.providers.base import ProviderCandidate, ProviderError
from vox_local.providers.manager import ProviderManager
from vox_local.providers.windows_sapi import WindowsSapiProvider


SESSION_COOKIE = "vox_session"
OAUTH_STATE_COOKIE = "vox_oauth_state"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _extension_from_content_type(content_type: str) -> str:
    return {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/aac": "aac",
        "audio/flac": "flac",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
    }.get(content_type, "bin")


def _safe_download_name(value: str, fallback: str) -> str:
    candidate = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", value.strip())
    candidate = candidate.strip(" .")[:100]
    return candidate or fallback


def _require_api_key(settings: Settings, x_api_key: str | None) -> str | None:
    if not settings.api_key_required:
        return None
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key không hợp lệ hoặc đang thiếu.")

    if settings.local_api_key and secrets.compare_digest(x_api_key, settings.local_api_key):
        return "default"

    for label, key in settings.local_api_keys.items():
        if secrets.compare_digest(x_api_key, key):
            return label

    if settings.local_api_key_hashes:
        provided_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
        for label, key_hash in settings.local_api_key_hashes.items():
            if secrets.compare_digest(provided_hash, key_hash.strip().lower()):
                return label

    raise HTTPException(status_code=401, detail="X-API-Key không hợp lệ hoặc đang thiếu.")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _session_secret(settings: Settings, runtime_secret: str) -> str:
    return settings.web_session_secret or settings.local_api_key or runtime_secret


def _sign_payload(payload: dict[str, Any], secret: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = _b64encode(raw)
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def _verify_payload(token: str | None, secret: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, signature = token.split(".", 1)
    expected = _b64encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _create_session(settings: Settings, runtime_secret: str, user: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user.get("sub") or user.get("email") or user.get("label") or "user"),
        "label": str(user.get("label") or user.get("email") or "user"),
        "provider": str(user.get("provider") or "api_key"),
        "email": str(user.get("email") or ""),
        "name": str(user.get("name") or ""),
        "iat": now,
        "exp": now + settings.web_session_hours * 3600,
    }
    return _sign_payload(payload, _session_secret(settings, runtime_secret))


def _read_session(settings: Settings, request: Request) -> dict[str, Any] | None:
    runtime_secret = request.app.state.web_session_secret
    return _verify_payload(request.cookies.get(SESSION_COOKIE), _session_secret(settings, runtime_secret))


def _set_session_cookie(settings: Settings, response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.web_session_hours * 3600,
        httponly=True,
        secure=settings.web_auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")


def _login_redirect(next_url: str = "/") -> RedirectResponse:
    safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
    return RedirectResponse(f"/login?next={quote(safe_next, safe='/?=&')}", status_code=303)


def _require_web_session(settings: Settings, request: Request) -> dict[str, Any] | RedirectResponse | None:
    if not settings.web_auth_enabled:
        return None
    session = _read_session(settings, request)
    if session:
        return session
    next_url = request.url.path
    if request.url.query:
        next_url += f"?{request.url.query}"
    return _login_redirect(next_url)


def _require_request_auth(settings: Settings, request: Request, x_api_key: str | None) -> str | None:
    if not settings.api_key_required and not settings.web_auth_enabled:
        return None

    key_error: HTTPException | None = None
    if x_api_key and settings.api_key_required:
        try:
            return _require_api_key(settings, x_api_key)
        except HTTPException as exc:
            key_error = exc

    if settings.web_auth_enabled:
        session = _read_session(settings, request)
        if session:
            return str(session.get("label") or session.get("sub") or "web")

    if settings.api_key_required:
        if key_error:
            raise key_error
        return _require_api_key(settings, x_api_key)

    raise HTTPException(status_code=401, detail="Bạn cần đăng nhập web UI trước khi gọi API này.")


def _google_email_allowed(settings: Settings, email: str) -> bool:
    normalized = email.strip().lower()
    domain = normalized.rsplit("@", 1)[-1] if "@" in normalized else ""
    if settings.google_allowed_emails and normalized in settings.google_allowed_emails:
        return True
    if settings.google_allowed_domains and domain in settings.google_allowed_domains:
        return True
    return False


def _metadata_headers(metadata: dict[str, Any], cache_status: str = "HIT") -> dict[str, str]:
    fallback_from = str(metadata.get("fallback_from") or "")
    return {
        "X-TTS-Provider": str(metadata.get("provider", "")),
        "X-TTS-Provider-Label": quote(str(metadata.get("provider_label", "")), safe=" -_.:/|"),
        "X-TTS-Voice": str(metadata.get("voice_header", "")),
        "X-TTS-Voice-Name": quote(str(metadata.get("voice", "")), safe=" -_.:/|"),
        "X-TTS-Voice-Type": str(metadata.get("voice_type", "")),
        "X-TTS-Rate": f"{float(metadata.get('rate', 1.0)):.2f}",
        "X-TTS-Cache": cache_status,
        "X-TTS-Cache-Id": str(metadata.get("id", "")),
        "X-TTS-Fallback": "true" if fallback_from else "",
        "Cache-Control": "no-store",
    }


EMOTION_TAG_GROUPS: list[dict[str, Any]] = [
    {"label": "Bình thường", "aliases": ["bình thường", "binh thuong"], "rate_multiplier": 1.0, "pause_after": 0.25},
    {"label": "Căng thẳng", "aliases": ["căng thẳng", "cang thang"], "rate_multiplier": 0.96, "pause_after": 0.45},
    {"label": "Buồn", "aliases": ["buồn", "buon"], "rate_multiplier": 0.9, "pause_after": 0.55},
    {"label": "Phẫn nộ", "aliases": ["phẫn nộ", "phan no"], "rate_multiplier": 1.08, "pause_after": 0.25},
    {"label": "Thì thầm", "aliases": ["thì thầm", "thi tham"], "rate_multiplier": 0.86, "pause_after": 0.65},
    {"label": "Cao trào", "aliases": ["cao trào", "cao trao"], "rate_multiplier": 1.06, "pause_after": 0.2},
    {"label": "Bí ẩn", "aliases": ["bí ẩn", "bi an"], "rate_multiplier": 0.88, "pause_after": 0.7},
    {"label": "Chậm lại", "aliases": ["chậm lại", "cham lai"], "rate_multiplier": 0.82, "pause_after": 0.75},
    {"label": "Nhấn mạnh", "aliases": ["nhấn mạnh", "nhan manh"], "rate_multiplier": 0.9, "pause_after": 0.65},
]

EMOTION_TAGS = {
    alias: group
    for group in EMOTION_TAG_GROUPS
    for alias in group["aliases"]
}


def _normalize_tag(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", normalized.replace("đ", "d"))


EMOTION_TAGS.update(
    {
        _normalize_tag(alias): group
        for group in EMOTION_TAG_GROUPS
        for alias in group["aliases"]
    }
)


def _read_emotion_tag(text: str) -> dict[str, Any] | None:
    match = re.match(r"^\[([^\]]+)\]\s*", text.strip())
    if not match:
        return None
    raw_tag = match.group(1).strip().lower()
    emotion = EMOTION_TAGS.get(raw_tag) or EMOTION_TAGS.get(_normalize_tag(raw_tag))
    if not emotion:
        return None
    return {"marker": match.group(0), "tag": f"[{match.group(1).strip()}]", "emotion": emotion}


def _detect_emotion_tag(text: str) -> tuple[str, dict[str, Any] | None, str | None]:
    trimmed = text.strip()
    detected = _read_emotion_tag(trimmed)
    if not detected:
        return trimmed, None, None
    return trimmed[len(detected["marker"]):].strip(), detected["emotion"], detected["tag"]


def _emotion_rate(base_rate: float, emotion: dict[str, Any] | None) -> float:
    multiplier = float(emotion["rate_multiplier"]) if emotion else 1.0
    return max(0.5, min(2.0, float(base_rate) * multiplier))


def _clean_text_for_chunks(value: str) -> str:
    lines = [
        re.sub(r"[\t ]+", " ", line).strip()
        for line in value.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    return "\n\n".join(line for line in lines if line).strip()


def _split_emotion_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        value = "\n".join(current).strip()
        if value:
            blocks.append(value)
        current = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            if current:
                current.append("")
            continue
        if _read_emotion_tag(line) and any(item.strip() for item in current):
            flush()
        current.append(raw_line)
    flush()
    return blocks or [text.strip()]


def _split_long_text(text: str, max_length: int) -> list[str]:
    clean = _clean_text_for_chunks(text)
    if not clean:
        return []
    chunks: list[str] = []

    def push_chunk(value: str) -> None:
        trimmed = re.sub(r"\s+", " ", value).strip()
        if trimmed:
            chunks.append(trimmed)

    def with_tag(value: str, tag_prefix: str) -> str:
        return f"{tag_prefix} {value}" if tag_prefix else value

    def push_tagged_chunk(value: str, tag_prefix: str) -> None:
        push_chunk(with_tag(value, tag_prefix))

    def prefixed_length(value: str, tag_prefix: str) -> int:
        return len(with_tag(value, tag_prefix))

    def split_paragraph(paragraph: str, tag_prefix: str = "") -> None:
        body_max_length = max(120, max_length - (len(tag_prefix) + 1 if tag_prefix else 0))
        sentences = re.findall(r"[^.!?。！？…]+[.!?。！？…]*|.+", re.sub(r"\s+", " ", paragraph)) or [paragraph]
        current = ""
        for raw_sentence in sentences:
            sentence = raw_sentence.strip()
            if not sentence:
                continue
            proposed = f"{current} {sentence}".strip()
            if len(proposed) <= body_max_length:
                current = proposed
                continue
            if current:
                push_tagged_chunk(current, tag_prefix)
            if len(sentence) <= body_max_length:
                current = sentence
            else:
                for start in range(0, len(sentence), body_max_length):
                    push_tagged_chunk(sentence[start:start + body_max_length], tag_prefix)
                current = ""
        if current:
            push_tagged_chunk(current, tag_prefix)

    for block in _split_emotion_blocks(clean):
        body, emotion, tag = _detect_emotion_tag(block)
        tag_prefix = tag if emotion else ""
        if not body:
            continue
        current = ""

        def flush_current() -> None:
            nonlocal current
            if current:
                push_tagged_chunk(current, tag_prefix)
            current = ""

        for paragraph in [item.strip() for item in re.split(r"\n{2,}", body) if item.strip()]:
            proposed = f"{current}\n\n{paragraph}".strip()
            if prefixed_length(proposed, tag_prefix) <= max_length:
                current = proposed
            else:
                flush_current()
                if prefixed_length(paragraph, tag_prefix) <= max_length:
                    current = paragraph
                else:
                    split_paragraph(paragraph, tag_prefix)
        flush_current()
    return chunks


def _prepare_tts_chunks(text: str, base_rate: float, chunk_size: int, max_text_length: int) -> list[PreparedChunk]:
    effective_chunk_size = min(max_text_length, max(100, chunk_size))
    prepared: list[PreparedChunk] = []
    for index, chunk in enumerate(_split_long_text(text, effective_chunk_size), start=1):
        body, emotion, tag = _detect_emotion_tag(chunk)
        body = body or chunk
        prepared.append(
            PreparedChunk(
                index=index,
                text=body,
                char_count=len(body),
                rate=round(_emotion_rate(base_rate, emotion), 2),
                emotion_tag=tag,
                emotion_label=str(emotion["label"]) if emotion else "Bình thường",
                pause_after=float(emotion["pause_after"]) if emotion else 0.25,
            )
        )
    return prepared


def _emotion_tag_catalog() -> list[dict[str, Any]]:
    return [
        {
            "label": str(group["label"]),
            "aliases": list(group["aliases"]),
            "rate_multiplier": float(group["rate_multiplier"]),
            "pause_after": float(group["pause_after"]),
            "syntax": f"[{group['aliases'][0]}] Nội dung cần đọc",
        }
        for group in EMOTION_TAG_GROUPS
    ]


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    cache = AudioCache(active_settings)
    manager = ProviderManager(active_settings)

    app = FastAPI(
        title="Vox Local Story TTS",
        version=__version__,
        description="Local-first story TTS workspace with CapCut CLI and offline fallback providers.",
    )
    app.state.settings = active_settings
    app.state.cache = cache
    app.state.provider_manager = manager
    app.state.web_session_secret = secrets.token_urlsafe(32)
    app.mount("/assets", StaticFiles(directory=active_settings.static_dir), name="assets")

    def generate_or_load(text: str, rate: float, capcut_profile=None) -> tuple[Path, dict[str, Any], bool]:
        try:
            candidates = manager.candidates()
        except ProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if not candidates:
            raise HTTPException(
                status_code=503,
                detail="Không có provider TTS khả dụng. Hãy chạy setup-capcut-k07vn.ps1 hoặc bật local Windows TTS.",
            )

        # Prefer cached audio from the highest-priority available provider.
        for candidate in candidates:
            active_candidate = candidate
            if capcut_profile and candidate.kind == "capcut":
                active_candidate = ProviderCandidate(candidate.kind, capcut_profile, candidate.available, candidate.issue)
            key = cache.cache_id(text, rate, active_candidate.profile)
            cached = cache.find(key)
            if cached:
                path, metadata = cached
                return path, metadata, True

        errors: list[str] = []
        for candidate in candidates:
            active_candidate = candidate
            if capcut_profile and candidate.kind == "capcut":
                active_candidate = ProviderCandidate(candidate.kind, capcut_profile, candidate.available, candidate.issue)
            key = cache.cache_id(text, rate, active_candidate.profile)
            lock = cache.lock_for(key)
            with lock:
                cached = cache.find(key)
                if cached:
                    path, metadata = cached
                    return path, metadata, True

                try:
                    result = manager.synthesize(active_candidate, text=text, rate=rate)
                except ProviderError as exc:
                    errors.append(f"{active_candidate.profile.provider_label}: {exc}")
                    continue

                audio = result.audio
                extension = _extension_from_content_type(audio.content_type)
                profile = result.profile
                fallback_from = " | ".join(errors)
                metadata = {
                    "provider": profile.provider,
                    "provider_label": profile.provider_label,
                    "voice": profile.name,
                    "voice_header": profile.header_value,
                    "voice_type": profile.voice_type,
                    "resource_id": profile.resource_id,
                    "language": profile.language,
                    "rate": rate,
                    "text": text,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "provider_url": audio.source_url,
                    "fallback_from": fallback_from,
                }
                return cache.write(key, audio.data, audio.content_type, extension, metadata) + (False,)

        raise HTTPException(
            status_code=502,
            detail="Không provider nào tạo được audio. " + " ; ".join(errors),
        )

    @app.get("/", include_in_schema=False)
    def web_ui(request: Request):
        web_auth = _require_web_session(active_settings, request)
        if isinstance(web_auth, RedirectResponse):
            return web_auth
        return FileResponse(active_settings.static_dir / "index.html", media_type="text/html")

    @app.get("/api", include_in_schema=False)
    def api_guide(request: Request):
        web_auth = _require_web_session(active_settings, request)
        if isinstance(web_auth, RedirectResponse):
            return web_auth
        return FileResponse(active_settings.static_dir / "api.html", media_type="text/html")

    @app.get("/login", include_in_schema=False)
    def login_page(request: Request):
        if not active_settings.web_auth_enabled:
            return RedirectResponse("/", status_code=303)
        if _read_session(active_settings, request):
            next_url = request.query_params.get("next") or "/"
            return RedirectResponse(next_url if next_url.startswith("/") else "/", status_code=303)
        return FileResponse(active_settings.static_dir / "login.html", media_type="text/html")

    @app.get("/auth/config")
    def auth_config(request: Request) -> dict:
        next_url = request.query_params.get("next") or "/"
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/"
        session = _read_session(active_settings, request)
        return {
            "enabled": active_settings.web_auth_enabled,
            "authenticated": bool(session),
            "user": session or None,
            "session_hours": active_settings.web_session_hours,
            "providers": {
                "api_key": active_settings.web_auth_enabled and active_settings.web_auth_api_key_enabled,
                "google": active_settings.web_auth_enabled and active_settings.google_oauth_configured,
            },
            "google_configured": active_settings.google_oauth_configured,
            "google_start_url": f"/auth/google/start?next={quote(next_url, safe='/?=&')}",
            "next": next_url,
        }

    @app.post("/auth/login")
    async def auth_login(request: Request):
        if not active_settings.web_auth_enabled or not active_settings.web_auth_api_key_enabled:
            raise HTTPException(status_code=404, detail="Web login bằng API key chưa được bật.")
        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Body JSON không hợp lệ.") from exc
        api_key = str(payload.get("api_key") or "").strip()
        next_url = str(payload.get("next") or "/")
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/"
        label = _require_api_key(active_settings, api_key)
        token = _create_session(
            active_settings,
            request.app.state.web_session_secret,
            {"provider": "api_key", "label": label or "api_key", "sub": f"api_key:{label or 'default'}"},
        )
        response = JSONResponse({"authenticated": True, "next": next_url, "user": {"provider": "api_key", "label": label}})
        _set_session_cookie(active_settings, response, token)
        return response

    @app.post("/auth/logout")
    def auth_logout():
        response = JSONResponse({"authenticated": False})
        _clear_session_cookie(response)
        return response

    @app.get("/auth/me")
    def auth_me(request: Request) -> dict:
        session = _read_session(active_settings, request)
        return {
            "web_auth_enabled": active_settings.web_auth_enabled,
            "authenticated": bool(session),
            "user": session or None,
        }

    @app.get("/auth/google/start")
    def google_start(request: Request):
        if not active_settings.google_oauth_configured:
            raise HTTPException(
                status_code=503,
                detail="Google OAuth chưa được cấu hình đủ client id/secret và allowlist email/domain.",
            )
        next_url = request.query_params.get("next") or "/"
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/"
        state_value = secrets.token_urlsafe(24)
        state_token = _sign_payload(
            {"state": state_value, "next": next_url, "exp": int(time.time()) + 600},
            _session_secret(active_settings, request.app.state.web_session_secret),
        )
        redirect_uri = active_settings.google_oauth_redirect_uri or str(request.url_for("google_callback"))
        query = urlencode(
            {
                "client_id": active_settings.google_oauth_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state_value,
                "prompt": "select_account",
            }
        )
        response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}", status_code=303)
        response.set_cookie(
            OAUTH_STATE_COOKIE,
            state_token,
            max_age=600,
            httponly=True,
            secure=active_settings.web_auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    @app.get("/auth/google/callback", name="google_callback")
    def google_callback(request: Request):
        if not active_settings.google_oauth_configured:
            raise HTTPException(status_code=503, detail="Google OAuth chưa được cấu hình.")
        if request.query_params.get("error"):
            detail = request.query_params.get("error_description") or request.query_params.get("error")
            raise HTTPException(status_code=400, detail=f"Google OAuth lỗi: {detail}")
        code = request.query_params.get("code")
        state_value = request.query_params.get("state")
        state_payload = _verify_payload(
            request.cookies.get(OAUTH_STATE_COOKIE),
            _session_secret(active_settings, request.app.state.web_session_secret),
        )
        if not code or not state_value or not state_payload or state_payload.get("state") != state_value:
            raise HTTPException(status_code=400, detail="Google OAuth state không hợp lệ hoặc đã hết hạn.")

        redirect_uri = active_settings.google_oauth_redirect_uri or str(request.url_for("google_callback"))
        try:
            token_response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": active_settings.google_oauth_client_id,
                    "client_secret": active_settings.google_oauth_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=20,
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            user_response = requests.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
                timeout=20,
            )
            user_response.raise_for_status()
            user = user_response.json()
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"Không xác thực được với Google: {exc}") from exc

        email = str(user.get("email") or "").lower()
        if user.get("email_verified") is not True:
            raise HTTPException(status_code=403, detail="Google email chưa được verified.")
        if not _google_email_allowed(active_settings, email):
            raise HTTPException(status_code=403, detail="Email Google này chưa nằm trong allowlist của server.")

        token = _create_session(
            active_settings,
            request.app.state.web_session_secret,
            {
                "provider": "google",
                "sub": f"google:{user.get('sub')}",
                "email": email,
                "name": user.get("name") or email,
                "label": email,
            },
        )
        next_url = str(state_payload.get("next") or "/")
        response = RedirectResponse(next_url if next_url.startswith("/") else "/", status_code=303)
        _set_session_cookie(active_settings, response, token)
        response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
        return response

    @app.get("/health")
    def health_route() -> dict:
        current = manager.health()
        return {
            **current,
            "cache_dir": str(active_settings.cache_dir),
            "api_key_required": active_settings.api_key_required,
            "max_text_length": active_settings.max_text_length,
            "version": __version__,
        }

    @app.get("/v1/extension/capabilities")
    def extension_capabilities() -> dict:
        current_health = health_route()
        return {
            "name": "Vox Local Story TTS API",
            "version": __version__,
            "base_url": f"http://{active_settings.host}:{active_settings.port}",
            "docs": {
                "human": "/api",
                "swagger": "/docs",
                "openapi": "/openapi.json",
            },
            "auth": {
                "api_key_required": active_settings.api_key_required,
                "header": "X-API-Key",
                "note": "Nếu LOCAL_API_KEY, LOCAL_API_KEYS và LOCAL_API_KEY_HASHES đều rỗng trong .env thì không cần header này.",
                "supported_env": ["LOCAL_API_KEY", "LOCAL_API_KEYS", "LOCAL_API_KEY_HASHES"],
                "web_auth_enabled": active_settings.web_auth_enabled,
                "web_auth_providers": list(active_settings.web_auth_providers),
                "google_oauth_configured": active_settings.google_oauth_configured,
            },
            "limits": {
                "max_text_length": active_settings.max_text_length,
                "rate_min": 0.5,
                "rate_max": 2.0,
                "recommended_chunk_size": min(3200, active_settings.max_text_length),
                "batch_max_chunks": 100,
            },
            "server": {
                "status": current_health.get("status"),
                "provider": current_health.get("provider"),
                "provider_label": current_health.get("provider_label"),
                "provider_order": current_health.get("provider_order", []),
                "network_tts_enabled": current_health.get("network_tts_enabled", False),
                "fallback_to_local": current_health.get("fallback_to_local", False),
            },
            "extension_flow": [
                "GET /health để kiểm tra server và giới hạn text.",
                "GET /v1/voices để hiển thị danh sách giọng.",
                "POST /v1/text/prepare để chia text thành block và áp emotion tag.",
                "POST /v1/tts để tạo một file audio binary hoặc POST /v1/tts/batch để tạo nhiều block và nhận link cache.",
                "GET /v1/cache/{cache_id}?filename=... để tải lại audio đã tạo.",
            ],
            "endpoints": [
                {"method": "GET", "path": "/health", "auth": False, "purpose": "Trạng thái server, provider, cache, giới hạn text."},
                {"method": "GET", "path": "/api/ui/config", "auth": False, "purpose": "Cấu hình tối thiểu cho web UI."},
                {"method": "GET", "path": "/v1/extension/capabilities", "auth": False, "purpose": "Metadata chi tiết cho extension tự cấu hình."},
                {"method": "GET", "path": "/v1/auth/check", "auth": True, "purpose": "Kiểm tra API key và trả label key."},
                {"method": "GET", "path": "/auth/me", "auth": False, "purpose": "Kiểm tra session web UI hiện tại."},
                {"method": "GET", "path": "/v1/emotion-tags", "auth": False, "purpose": "Danh sách emotion tag và hệ số tốc độ/pause."},
                {"method": "GET", "path": "/v1/voices", "auth": False, "purpose": "Danh sách voice CapCut/local mà extension có thể chọn."},
                {"method": "GET", "path": "/v1/providers", "auth": True, "purpose": "Chi tiết provider đang khả dụng."},
                {"method": "POST", "path": "/v1/text/prepare", "auth": True, "purpose": "Chuẩn hóa, chia block, bỏ emotion tag, tính rate/pause."},
                {"method": "POST", "path": "/v1/tts", "auth": True, "purpose": "Tạo một audio và trả binary."},
                {"method": "POST", "path": "/v1/tts/batch", "auth": True, "purpose": "Tạo nhiều audio block và trả JSON link cache."},
                {"method": "GET", "path": "/v1/history?limit=12", "auth": True, "purpose": "Lịch sử audio cache."},
                {"method": "GET", "path": "/v1/cache/{cache_id}", "auth": True, "purpose": "Tải audio cache."},
                {"method": "DELETE", "path": "/v1/cache/{cache_id}", "auth": True, "purpose": "Xóa một audio cache."},
                {"method": "DELETE", "path": "/v1/cache", "auth": True, "purpose": "Clear toàn bộ cache audio."},
            ],
            "tts_response_headers": {
                "X-TTS-Provider": "Provider thực tế đã tạo audio.",
                "X-TTS-Provider-Label": "Tên provider hiển thị, URL-encoded.",
                "X-TTS-Voice-Name": "Tên voice hiển thị, URL-encoded.",
                "X-TTS-Voice-Type": "Mã voice_type đã dùng.",
                "X-TTS-Rate": "Tốc độ đọc sau khi áp emotion tag.",
                "X-TTS-Cache": "HIT hoặc MISS.",
                "X-TTS-Cache-Id": "ID cache để gọi /v1/cache/{id}.",
                "X-TTS-Fallback": "true nếu provider chính lỗi và server dùng fallback.",
            },
            "emotion_tags": _emotion_tag_catalog(),
        }

    @app.get("/v1/emotion-tags")
    def emotion_tags() -> dict:
        return {"items": _emotion_tag_catalog()}

    @app.get("/v1/auth/check")
    def auth_check(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
        label = _require_request_auth(active_settings, request, x_api_key)
        return {
            "authenticated": True,
            "api_key_required": active_settings.api_key_required,
            "key_label": label or "public",
        }

    @app.get("/api/ui/config")
    def ui_config(request: Request) -> dict:
        current_health = health_route()
        provider_label = current_health.get("provider_label") or "Provider local"
        session = _read_session(active_settings, request)
        return {
            "voice": current_health["voice"],
            "provider": current_health.get("provider", "unknown"),
            "provider_label": provider_label,
            "provider_order": current_health.get("provider_order", []),
            "network_tts_enabled": current_health.get("network_tts_enabled", False),
            "fallback_to_local": current_health.get("fallback_to_local", False),
            "api_key_required": current_health["api_key_required"],
            "web_auth_enabled": active_settings.web_auth_enabled,
            "browser_session_authenticated": bool(session),
            "browser_user": session,
            "max_text_length": active_settings.max_text_length,
            "server_status": current_health["status"],
            "client_configured": current_health["client_configured"],
            "client_exists": current_health["client_exists"],
        }

    @app.get("/v1/providers")
    def providers(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
        _require_request_auth(active_settings, request, x_api_key)
        return manager.health()

    @app.get("/v1/voices", response_model=list[VoiceInfo])
    def voices() -> list[VoiceInfo]:
        profiles = manager.voice_profiles()
        return [
            VoiceInfo(
                name=profile.name,
                voice_type=profile.voice_type,
                resource_id=profile.resource_id,
                language=profile.language,
                provider=profile.provider,
                provider_label=profile.provider_label,
            )
            for profile in profiles
        ]

    @app.get("/v1/local-voices", response_model=list[LocalVoiceInfo])
    def local_voices(request: Request, x_api_key: str | None = Header(default=None)) -> list[LocalVoiceInfo]:
        _require_request_auth(active_settings, request, x_api_key)
        try:
            voices_available = WindowsSapiProvider.list_voices(active_settings.local_tts_powershell)
        except ProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return [
            LocalVoiceInfo(
                name=voice.name,
                culture=voice.culture,
                gender=voice.gender,
                age=voice.age,
                description=voice.description,
            )
            for voice in voices_available
        ]

    @app.post("/v1/text/prepare", response_model=TextPrepareResponse)
    def prepare_text(
        prepare_request: TextPrepareRequest,
        request: Request,
        x_api_key: str | None = Header(default=None),
    ) -> TextPrepareResponse:
        _require_request_auth(active_settings, request, x_api_key)
        chunk_size = min(active_settings.max_text_length, prepare_request.chunk_size or active_settings.max_text_length)
        chunks = _prepare_tts_chunks(prepare_request.text, prepare_request.rate, chunk_size, active_settings.max_text_length)
        return TextPrepareResponse(
            total_chunks=len(chunks),
            total_chars=sum(item.char_count for item in chunks),
            max_text_length=active_settings.max_text_length,
            chunk_size=chunk_size,
            base_rate=prepare_request.rate,
            chunks=chunks,
        )

    @app.post("/v1/tts")
    def tts(tts_request: TTSRequest, request: Request, x_api_key: str | None = Header(default=None)):
        _require_request_auth(active_settings, request, x_api_key)
        if len(tts_request.text) > active_settings.max_text_length:
            raise HTTPException(
                status_code=422,
                detail=f"text không được vượt quá {active_settings.max_text_length} ký tự.",
            )
        text = _normalize_text(tts_request.text)
        if not text:
            raise HTTPException(status_code=422, detail="text không được để trống.")

        capcut_profile = None
        if tts_request.voice_type or tts_request.resource_id:
            try:
                capcut_profile = manager.resolve_capcut_profile(
                    tts_request.voice_type,
                    tts_request.resource_id,
                    tts_request.voice_name,
                )
            except ProviderError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        path, metadata, was_cached = generate_or_load(text, tts_request.rate, capcut_profile)
        prefix = "co_gai_hoat_ngon" if metadata.get("provider") == "capcut" else "local_tts"
        default_name = f"{prefix}_{metadata['id'][:12]}.{path.suffix.lstrip('.')}"
        safe_name = _safe_download_name(tts_request.filename or default_name, default_name)
        if not safe_name.lower().endswith(path.suffix.lower()):
            safe_name += path.suffix

        return FileResponse(
            path,
            media_type=metadata["content_type"],
            filename=safe_name,
            headers=_metadata_headers(metadata, "HIT" if was_cached else "MISS"),
        )

    @app.post("/v1/tts/batch", response_model=TTSBatchResponse)
    def tts_batch(
        batch_request: TTSBatchRequest,
        request: Request,
        x_api_key: str | None = Header(default=None),
    ) -> TTSBatchResponse:
        _require_request_auth(active_settings, request, x_api_key)
        chunk_size = min(active_settings.max_text_length, batch_request.chunk_size or active_settings.max_text_length)
        chunks = _prepare_tts_chunks(batch_request.text, batch_request.rate, chunk_size, active_settings.max_text_length)
        if not chunks:
            raise HTTPException(status_code=422, detail="text không được để trống.")
        if len(chunks) > 100:
            raise HTTPException(status_code=422, detail="Batch tối đa 100 block. Hãy giảm nội dung hoặc tăng chunk_size.")

        capcut_profile = None
        if batch_request.voice_type or batch_request.resource_id:
            try:
                capcut_profile = manager.resolve_capcut_profile(
                    batch_request.voice_type,
                    batch_request.resource_id,
                    batch_request.voice_name,
                )
            except ProviderError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        prefix = _safe_download_name(batch_request.filename_prefix or "story", "story")
        items: list[TTSBatchItem] = []
        for chunk in chunks:
            if len(chunk.text) > active_settings.max_text_length:
                raise HTTPException(
                    status_code=422,
                    detail=f"Block {chunk.index} vượt quá {active_settings.max_text_length} ký tự.",
                )
            path, metadata, was_cached = generate_or_load(chunk.text, chunk.rate, capcut_profile)
            extension = path.suffix.lstrip(".") or "audio"
            filename = f"{prefix}_part_{chunk.index:03d}.{extension}" if len(chunks) > 1 else f"{prefix}.{extension}"
            cache_id = str(metadata.get("id", ""))
            items.append(
                TTSBatchItem(
                    index=chunk.index,
                    filename=filename,
                    cache_id=cache_id,
                    download_url=f"/v1/cache/{cache_id}?filename={quote(filename)}",
                    content_type=str(metadata.get("content_type", "audio/mpeg")),
                    extension=extension,
                    cache="HIT" if was_cached else "MISS",
                    provider=str(metadata.get("provider", "")),
                    provider_label=str(metadata.get("provider_label", "")),
                    voice=str(metadata.get("voice", "")),
                    voice_type=str(metadata.get("voice_type", "")),
                    rate=chunk.rate,
                    char_count=chunk.char_count,
                    emotion_label=chunk.emotion_label,
                )
            )
        return TTSBatchResponse(total=len(items), items=items)

    @app.get("/v1/history", response_model=list[HistoryItem])
    def history(
        request: Request,
        limit: int = Query(default=12, ge=1, le=100),
        x_api_key: str | None = Header(default=None),
    ) -> list[HistoryItem]:
        _require_request_auth(active_settings, request, x_api_key)
        return cache.history(limit)

    @app.get("/v1/cache/{cache_id}")
    def get_cached(
        cache_id: str,
        request: Request,
        filename: str | None = Query(default=None, max_length=100),
        x_api_key: str | None = Header(default=None),
    ):
        _require_request_auth(active_settings, request, x_api_key)
        if len(cache_id) != 64 or any(char not in "0123456789abcdef" for char in cache_id.lower()):
            raise HTTPException(status_code=422, detail="cache_id không hợp lệ.")
        cached = cache.find(cache_id)
        if not cached:
            raise HTTPException(status_code=404, detail="Không tìm thấy audio cache.")
        path, metadata = cached
        default_name = str(metadata.get("file") or path.name)
        safe_name = _safe_download_name(filename or default_name, default_name)
        if not safe_name.lower().endswith(path.suffix.lower()):
            safe_name += path.suffix
        return FileResponse(
            path,
            media_type=metadata["content_type"],
            filename=safe_name,
            headers=_metadata_headers(metadata, "HIT"),
        )

    @app.delete("/v1/cache")
    def clear_cache(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
        _require_request_auth(active_settings, request, x_api_key)
        return {"cleared": True, **cache.clear()}

    @app.delete("/v1/cache/{cache_id}")
    def delete_cached(cache_id: str, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
        _require_request_auth(active_settings, request, x_api_key)
        if not cache.delete(cache_id):
            raise HTTPException(status_code=404, detail="Không tìm thấy audio cache.")
        return {"deleted": cache_id}

    return app


settings = Settings.from_env()
app = create_app(settings)


def health() -> dict:
    return app.state.provider_manager.health()
