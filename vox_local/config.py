from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _secret_map_env(name: str) -> dict[str, str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    output: dict[str, str] = {}
    for index, item in enumerate(raw.replace("\n", ",").replace(";", ",").split(","), start=1):
        value = item.strip()
        if not value:
            continue
        if ":" in value:
            label, secret = value.split(":", 1)
        else:
            label, secret = f"key_{index}", value
        label = label.strip() or f"key_{index}"
        secret = secret.strip()
        if secret:
            output[label] = secret
    return output


def _list_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return ()
    return tuple(
        item.strip()
        for item in raw.replace("\n", ",").replace(";", ",").split(",")
        if item.strip()
    )


@dataclass(frozen=True)
class Settings:
    project_dir: Path
    static_dir: Path
    cache_dir: Path
    local_api_key: str
    local_api_keys: dict[str, str]
    local_api_key_hashes: dict[str, str]
    tts_provider: str
    allow_network_tts: bool
    fallback_to_local: bool
    capcut_client_path: str
    capcut_python: str
    capcut_device_json: str | None
    local_tts_voice: str | None
    local_tts_display_name: str | None
    local_tts_powershell: str
    local_tts_volume: int
    timeout_seconds: int
    poll_seconds: float
    max_text_length: int
    host: str
    port: int
    web_auth_enabled: bool
    web_auth_providers: tuple[str, ...]
    web_session_secret: str
    web_session_hours: int
    web_auth_cookie_secure: bool
    google_oauth_client_id: str
    google_oauth_client_secret: str
    google_oauth_redirect_uri: str
    google_allowed_emails: tuple[str, ...]
    google_allowed_domains: tuple[str, ...]

    @property
    def api_key_required(self) -> bool:
        return bool(self.local_api_key or self.local_api_keys or self.local_api_key_hashes)

    @property
    def web_auth_api_key_enabled(self) -> bool:
        return "api_key" in self.web_auth_providers

    @property
    def web_auth_google_enabled(self) -> bool:
        return "google" in self.web_auth_providers

    @property
    def google_oauth_configured(self) -> bool:
        return bool(
            self.web_auth_google_enabled
            and self.google_oauth_client_id
            and self.google_oauth_client_secret
            and (self.google_allowed_emails or self.google_allowed_domains)
        )

    @classmethod
    def from_env(cls, project_dir: Path | None = None) -> "Settings":
        load_dotenv()
        root = project_dir or Path(__file__).resolve().parents[1]
        cache_dir = Path(os.getenv("CACHE_DIR", "./audio_cache")).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = root / cache_dir
        cache_dir = cache_dir.resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)

        provider = os.getenv("TTS_PROVIDER", "auto").strip().lower() or "auto"
        web_auth_providers = tuple(
            provider_name.strip().lower().replace("-", "_")
            for provider_name in _list_env("WEB_AUTH_PROVIDERS")
        ) or ("api_key",)
        return cls(
            project_dir=root,
            static_dir=root / "static",
            cache_dir=cache_dir,
            local_api_key=os.getenv("LOCAL_API_KEY", "").strip(),
            local_api_keys=_secret_map_env("LOCAL_API_KEYS"),
            local_api_key_hashes=_secret_map_env("LOCAL_API_KEY_HASHES"),
            tts_provider=provider,
            allow_network_tts=_bool_env("ALLOW_NETWORK_TTS", True),
            fallback_to_local=_bool_env("TTS_FALLBACK_TO_LOCAL", True),
            capcut_client_path=os.getenv("CAPCUT_CLIENT_PATH", "").strip(),
            capcut_python=os.getenv("CAPCUT_PYTHON", "python").strip() or "python",
            capcut_device_json=os.getenv("CAPCUT_DEVICE_JSON", "").strip() or None,
            local_tts_voice=os.getenv("LOCAL_TTS_VOICE", "").strip() or None,
            local_tts_display_name=os.getenv("LOCAL_TTS_DISPLAY_NAME", "").strip() or None,
            local_tts_powershell=os.getenv("LOCAL_TTS_POWERSHELL", "powershell.exe").strip()
            or "powershell.exe",
            local_tts_volume=max(0, min(100, _int_env("LOCAL_TTS_VOLUME", 100))),
            timeout_seconds=max(10, _int_env("TTS_TIMEOUT_SECONDS", 180)),
            poll_seconds=max(0.5, _float_env("TTS_POLL_SECONDS", 2.0)),
            max_text_length=max(100, _int_env("MAX_TEXT_LENGTH", 3800)),
            host=os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=max(1, min(65535, _int_env("PORT", 8010))),
            web_auth_enabled=_bool_env("WEB_AUTH_ENABLED", False),
            web_auth_providers=web_auth_providers,
            web_session_secret=os.getenv("WEB_SESSION_SECRET", "").strip(),
            web_session_hours=max(1, min(24 * 30, _int_env("WEB_SESSION_HOURS", 24))),
            web_auth_cookie_secure=_bool_env("WEB_AUTH_COOKIE_SECURE", False),
            google_oauth_client_id=(
                os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
                or os.getenv("GOOGLE_CLIENT_ID", "").strip()
            ),
            google_oauth_client_secret=(
                os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
                or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
            ),
            google_oauth_redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip(),
            google_allowed_emails=tuple(email.lower() for email in _list_env("GOOGLE_ALLOWED_EMAILS")),
            google_allowed_domains=tuple(domain.lower().lstrip("@") for domain in _list_env("GOOGLE_ALLOWED_DOMAINS")),
        )
