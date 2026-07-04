from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

import requests

from vox_local.providers.base import AudioResult, ProviderError, VoiceProfile

VOICE_NAME = "Cô Gái Hoạt Ngôn"
VOICE_TYPE = "BV074_streaming"
RESOURCE_ID = "7102355709945188865"

CAPCUT_PROFILE = VoiceProfile(
    provider="capcut",
    provider_label="CapCut API qua K07VN/capcut-tts-api",
    name=VOICE_NAME,
    voice_type=VOICE_TYPE,
    resource_id=RESOURCE_ID,
    language="vi-VN",
    header_value="co-gai-hoat-ngon",
)


def _capcut_ssml_rate(rate: float) -> str:
    multiplier = max(0.5, min(2.0, float(rate)))
    percent = multiplier * 100
    if abs(percent - round(percent)) < 0.001:
        return f"{int(round(percent))}%"
    return f"{percent:.2f}".rstrip("0").rstrip(".") + "%"


def _audio_extension(content_type: str) -> str:
    return {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/aac": "aac",
        "audio/flac": "flac",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
    }.get(content_type.split(";", 1)[0].strip().lower(), "mp3")


def _ffmpeg_executable() -> str:
    configured = os.getenv("FFMPEG_BINARY", "").strip() or os.getenv("VOX_FFMPEG_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return str(candidate)
        found = shutil.which(configured)
        if found:
            return found

    found = shutil.which("ffmpeg")
    if found:
        return found

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise ProviderError(
            "Chỉnh tốc độ CapCut cần ffmpeg. Hãy chạy .\\vox.bat install để cài imageio-ffmpeg."
        ) from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def _atempo_filter(rate: float) -> str:
    factor = max(0.5, min(2.0, float(rate)))
    return f"atempo={factor:.6g}"


def _adjust_audio_speed(audio: AudioResult, rate: float) -> AudioResult:
    factor = max(0.5, min(2.0, float(rate)))
    if abs(factor - 1.0) < 0.001:
        return audio

    extension = _audio_extension(audio.content_type)
    with tempfile.TemporaryDirectory(prefix="vox-capcut-speed-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        input_path = temp_dir / f"input.{extension}"
        output_path = temp_dir / f"output.{extension}"
        input_path.write_bytes(audio.data)

        command = [
            _ffmpeg_executable(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-filter:a",
            _atempo_filter(factor),
            "-vn",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("Chỉnh tốc độ audio CapCut vượt quá thời gian chờ.") from exc
        except OSError as exc:
            raise ProviderError(f"Không thể chạy ffmpeg để chỉnh tốc độ: {exc}") from exc

        if completed.returncode != 0:
            output = ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-1200:]
            raise ProviderError(f"ffmpeg chỉnh tốc độ thất bại. Output: {output}")
        if not output_path.is_file() or output_path.stat().st_size < 512:
            raise ProviderError("ffmpeg không tạo được audio đã chỉnh tốc độ.")

        return AudioResult(
            data=output_path.read_bytes(),
            content_type=audio.content_type,
            source_url=f"{audio.source_url}#speed={factor:.2f}",
        )


def _header_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "capcut-voice"


def load_capcut_voice_profiles(client_path: str | None) -> list[VoiceProfile]:
    """Load CapCut voice profiles from K07VN/capcut-tts-api Voice.json."""
    voice_json = None
    if client_path:
        candidate = Path(client_path).expanduser().resolve().with_name("Voice.json")
        if candidate.is_file():
            voice_json = candidate
    if not voice_json:
        return [CAPCUT_PROFILE]

    try:
        raw = json.loads(voice_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [CAPCUT_PROFILE]
    if not isinstance(raw, list):
        return [CAPCUT_PROFILE]

    profiles: list[VoiceProfile] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        voice_type = str(item.get("voice_type") or "").strip()
        resource_id = str(item.get("resource_id") or "").strip()
        name = str(item.get("display_name") or voice_type).strip()
        language = str(item.get("lang") or item.get("lan") or "vi-VN").strip()
        if not voice_type or not resource_id:
            continue
        key = (voice_type, resource_id)
        if key in seen:
            continue
        seen.add(key)
        profiles.append(
            VoiceProfile(
                provider="capcut",
                provider_label="CapCut API qua K07VN/capcut-tts-api",
                name=name,
                voice_type=voice_type,
                resource_id=resource_id,
                language=language,
                header_value=_header_slug(voice_type),
            )
        )

    if not profiles:
        return [CAPCUT_PROFILE]
    profiles.sort(key=lambda profile: 0 if profile.voice_type == VOICE_TYPE and profile.resource_id == RESOURCE_ID else 1)
    return profiles


def _walk(value: Any) -> Iterable[Any]:
    """Yield all nested values and decode embedded JSON strings when possible."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate[:1] in {"{", "["}:
            try:
                yield from _walk(json.loads(candidate))
            except (json.JSONDecodeError, TypeError):
                pass


def _last_json_object(stdout: str) -> dict[str, Any]:
    """Extract the largest JSON object emitted by a CLI that prints status lines."""
    decoder = json.JSONDecoder()
    best: Any = None
    best_size = -1
    for index, char in enumerate(stdout):
        if char not in "{[":
            continue
        try:
            parsed, consumed = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and consumed > best_size:
            best = parsed
            best_size = consumed
    if not isinstance(best, dict):
        raise ProviderError(
            "Client không trả về JSON hợp lệ. Output rút gọn: " + stdout[-800:]
        )
    return best


def _find_task(payload: dict[str, Any]) -> tuple[str, str, str]:
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        task_id = node.get("id") or node.get("task_id") or node.get("taskId")
        token = node.get("token") or node.get("task_token") or node.get("taskToken")
        if task_id and token:
            status = str(node.get("status") or "queueing")
            return str(task_id), str(token), status
    raise ProviderError("Không tìm thấy id/token TTS trong phản hồi của client.")


def _find_audio_url(payload: dict[str, Any]) -> str | None:
    preferred_keys = {
        "audio_url",
        "audiourl",
        "audio",
        "url",
        "file_url",
        "fileurl",
        "download_url",
        "downloadurl",
        "voice_url",
        "voiceurl",
    }
    candidates: list[tuple[int, str]] = []
    url_pattern = re.compile(r"^https?://", re.IGNORECASE)

    def visit(value: Any, key_hint: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, str(key).lower())
        elif isinstance(value, list):
            for child in value:
                visit(child, key_hint)
        elif isinstance(value, str):
            raw = value.strip()
            if raw[:1] in {"{", "["}:
                try:
                    visit(json.loads(raw), key_hint)
                    return
                except json.JSONDecodeError:
                    pass
            if url_pattern.match(raw):
                score = 0
                lowered = raw.lower()
                if key_hint.replace("_", "") in preferred_keys:
                    score += 10
                if any(ext in lowered for ext in (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")):
                    score += 5
                if "audio" in lowered or "tts" in lowered:
                    score += 2
                candidates.append((score, raw))

    visit(payload)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _task_status(payload: dict[str, Any]) -> str:
    statuses: list[str] = []
    for node in _walk(payload):
        if isinstance(node, dict):
            value = node.get("status") or node.get("state") or node.get("task_status")
            if value is not None:
                statuses.append(str(value).strip().lower())
    return statuses[0] if statuses else ""


def _provider_error(payload: dict[str, Any]) -> str | None:
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        code = node.get("code") or node.get("error_code") or node.get("ret")
        message = node.get("message") or node.get("error") or node.get("msg") or node.get("errmsg")
        if code not in (None, 0, "0", "success", "ok") and message:
            return f"{code}: {message}"
    return None


class CapCutCliProvider:
    """Runs a K07VN/capcut-tts-api compatible CLI and downloads generated audio."""

    def __init__(
        self,
        client_path: str,
        python_executable: str | None = None,
        device_json: str | None = None,
        voice_profile: VoiceProfile | None = None,
        timeout_seconds: int = 180,
        poll_seconds: float = 2.0,
    ) -> None:
        self.client_path = Path(client_path).expanduser().resolve()
        self.python_executable = python_executable or sys.executable
        self.device_json = Path(device_json).expanduser().resolve() if device_json else None
        self.voice_profile = voice_profile or CAPCUT_PROFILE
        self.timeout_seconds = max(10, int(timeout_seconds))
        self.poll_seconds = max(0.5, float(poll_seconds))

        if not self.client_path.is_file():
            raise ProviderError(
                "Không thấy CAPCUT_CLIENT_PATH. Hãy chạy setup-capcut-k07vn.ps1 hoặc trỏ tới client tương thích."
            )
        if self.device_json and not self.device_json.is_file():
            raise ProviderError("CAPCUT_DEVICE_JSON được cấu hình nhưng file không tồn tại.")

    def _run(self, arguments: list[str]) -> dict[str, Any]:
        command = [self.python_executable, str(self.client_path), *arguments]
        if self.device_json:
            command.extend(["--device-json", str(self.device_json)])
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("Client TTS vượt quá thời gian chờ 90 giây.") from exc
        except OSError as exc:
            raise ProviderError(f"Không thể chạy client TTS: {exc}") from exc

        output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        if completed.returncode != 0:
            raise ProviderError(
                f"Client TTS thoát với mã {completed.returncode}. Output: {output[-1200:]}"
            )
        payload = _last_json_object(output)
        error = _provider_error(payload)
        if error:
            raise ProviderError(f"CapCut client báo lỗi: {error}")
        return payload

    def synthesize(self, text: str, rate: float) -> AudioResult:
        created = self._run(
            [
                "tts-new",
                "--text",
                text,
                "--voice",
                self.voice_profile.voice_type,
                "--resource-id",
                self.voice_profile.resource_id,
                "--rate",
                _capcut_ssml_rate(rate),
            ]
        )
        task_id, token, _ = _find_task(created)
        deadline = time.monotonic() + self.timeout_seconds
        last_payload = created

        while time.monotonic() < deadline:
            queried = self._run(["tts-query", "--task-id", task_id, "--token", token])
            last_payload = queried
            url = _find_audio_url(queried)
            if url:
                return _adjust_audio_speed(self._download_audio(url), rate)

            status = _task_status(queried)
            if status in {"failed", "failure", "error", "cancelled", "canceled"}:
                raise ProviderError(f"TTS thất bại, trạng thái: {status}. Chi tiết: {queried}")
            time.sleep(self.poll_seconds)

        raise ProviderError(
            "TTS chưa hoàn thành trước khi hết thời gian chờ. "
            f"Task id: {task_id}; phản hồi cuối: {last_payload}"
        )

    @staticmethod
    def _download_audio(url: str) -> AudioResult:
        try:
            response = requests.get(url, timeout=90)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Không tải được audio kết quả: {exc}") from exc

        data = response.content
        if len(data) < 512:
            raise ProviderError("Audio tải về quá nhỏ; task có thể chưa xong hoặc URL đã hết hạn.")

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        if not content_type.startswith("audio/"):
            if data.startswith(b"RIFF"):
                content_type = "audio/wav"
            elif data[:3] == b"ID3" or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
                content_type = "audio/mpeg"
            else:
                content_type = "application/octet-stream"
        return AudioResult(data=data, content_type=content_type, source_url=url)
