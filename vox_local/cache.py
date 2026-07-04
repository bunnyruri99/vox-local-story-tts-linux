from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from vox_local.config import Settings
from vox_local.models import HistoryItem
from vox_local.providers.base import VoiceProfile


class AudioCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache_dir = settings.cache_dir
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def cache_id(self, text: str, rate: float, profile: VoiceProfile) -> str:
        provider_cache_version = "capcut-rate-postprocess-v1" if profile.provider == "capcut" else "default"
        raw = (
            f"{provider_cache_version}|{profile.provider}|{profile.voice_type}|{profile.resource_id}|"
            f"{rate:.2f}|{text}"
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def lock_for(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def metadata_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def find(self, key: str) -> tuple[Path, dict[str, Any]] | None:
        metadata_path = self.metadata_path(key)
        if not metadata_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            audio_path = self.cache_dir / metadata["file"]
            if audio_path.is_file() and audio_path.stat().st_size >= 512:
                return audio_path, metadata
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def write(
        self,
        key: str,
        data: bytes,
        content_type: str,
        extension: str,
        metadata: dict[str, Any],
    ) -> tuple[Path, dict[str, Any]]:
        filename = f"{key}.{extension}"
        target = self.cache_dir / filename
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(data)
        temporary.replace(target)

        saved = {
            "id": key,
            "file": filename,
            "content_type": content_type,
            **metadata,
        }
        self.metadata_path(key).write_text(
            json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return target, saved

    def history(self, limit: int) -> list[HistoryItem]:
        records: list[tuple[datetime, HistoryItem]] = []
        for metadata_path in self.cache_dir.glob("*.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                item_id = str(metadata["id"])
                file_name = str(metadata["file"])
                audio_path = self.cache_dir / file_name
                created_at = str(metadata["created_at"])
                parsed_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                text = str(metadata.get("text", ""))
                if not audio_path.is_file() or audio_path.stat().st_size < 512:
                    continue
                records.append(
                    (
                        parsed_time,
                        HistoryItem(
                            id=item_id,
                            created_at=created_at,
                            rate=float(metadata.get("rate", 1.0)),
                            text_preview=(text[:150] + "...") if len(text) > 150 else text,
                            char_count=len(text),
                            extension=audio_path.suffix.lstrip(".") or "audio",
                            content_type=str(metadata.get("content_type", "audio/mpeg")),
                            provider=str(metadata.get("provider", "unknown")),
                            provider_label=str(metadata.get("provider_label", "")),
                            voice=str(metadata.get("voice", "")),
                        ),
                    )
                )
            except (OSError, ValueError, KeyError, TypeError):
                continue
        records.sort(key=lambda record: record[0], reverse=True)
        return [item for _, item in records[:limit]]

    def delete(self, key: str) -> bool:
        cached = self.find(key)
        if not cached:
            return False
        path, _ = cached
        path.unlink(missing_ok=True)
        self.metadata_path(key).unlink(missing_ok=True)
        return True

    def clear(self) -> dict[str, int]:
        cache_suffixes = {".json", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".bin", ".part"}
        deleted_files = 0
        deleted_metadata = 0
        for path in self.cache_dir.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in cache_suffixes:
                continue
            try:
                path.unlink()
            except OSError:
                continue
            deleted_files += 1
            if path.suffix.lower() == ".json":
                deleted_metadata += 1
        return {"deleted_files": deleted_files, "deleted_metadata": deleted_metadata}
