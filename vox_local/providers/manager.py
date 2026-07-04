from __future__ import annotations

from pathlib import Path

from vox_local.config import Settings
from vox_local.providers.base import (
    ProviderCandidate,
    ProviderError,
    ProviderKind,
    SynthesisResult,
    TTSProvider,
    VoiceProfile,
)
from vox_local.providers.capcut_cli import CAPCUT_PROFILE, CapCutCliProvider, load_capcut_voice_profiles
from vox_local.providers.windows_sapi import WindowsSapiProvider, local_profile


class ProviderManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def local_profile(self) -> VoiceProfile:
        return local_profile(self.settings.local_tts_voice, self.settings.local_tts_display_name)

    @property
    def capcut_profile(self) -> VoiceProfile:
        return self.capcut_profiles()[0]

    def capcut_profiles(self) -> list[VoiceProfile]:
        return load_capcut_voice_profiles(self.settings.capcut_client_path)

    def voice_profiles(self) -> list[VoiceProfile]:
        profiles: list[VoiceProfile] = []
        requested = self.settings.tts_provider.replace("-", "_")
        if requested in {"", "auto", "capcut", "capcut_cli"}:
            profiles.extend(self.capcut_profiles())
        if requested in {"", "auto", "local", "offline", "sapi", "windows_sapi"} or self.settings.fallback_to_local:
            profiles.append(self.local_profile)
        return profiles

    def resolve_capcut_profile(
        self,
        voice_type: str | None,
        resource_id: str | None,
        voice_name: str | None = None,
    ) -> VoiceProfile:
        if not voice_type and not resource_id:
            return self.capcut_profile
        for profile in self.capcut_profiles():
            voice_match = not voice_type or profile.voice_type == voice_type
            resource_match = not resource_id or profile.resource_id == resource_id
            if voice_match and resource_match:
                return profile
        if voice_type and resource_id:
            return VoiceProfile(
                provider="capcut",
                provider_label="CapCut API qua K07VN/capcut-tts-api",
                name=voice_name or voice_type,
                voice_type=voice_type,
                resource_id=resource_id,
                language="vi-VN",
                header_value="custom-capcut-voice",
            )
        raise ProviderError("Voice CapCut không hợp lệ hoặc thiếu resource_id.")

    def capcut_available(self) -> bool:
        return bool(
            self.settings.allow_network_tts
            and self.settings.capcut_client_path
            and Path(self.settings.capcut_client_path).expanduser().is_file()
        )

    def local_available(self) -> bool:
        return WindowsSapiProvider.is_available(self.settings.local_tts_powershell)

    def _capcut_candidate(self) -> ProviderCandidate:
        if not self.settings.allow_network_tts:
            issue = "ALLOW_NETWORK_TTS=false"
        elif not self.settings.capcut_client_path:
            issue = "Chưa cấu hình CAPCUT_CLIENT_PATH"
        elif not Path(self.settings.capcut_client_path).expanduser().is_file():
            issue = "CAPCUT_CLIENT_PATH không tồn tại"
        else:
            issue = ""
        return ProviderCandidate(
            kind="capcut",
            profile=self.capcut_profile,
            available=not issue,
            issue=issue,
        )

    def _local_candidate(self) -> ProviderCandidate:
        available = self.local_available()
        return ProviderCandidate(
            kind="local",
            profile=self.local_profile,
            available=available,
            issue="" if available else "Windows SAPI không khả dụng",
        )

    def candidates(self) -> list[ProviderCandidate]:
        requested = self.settings.tts_provider.replace("-", "_")
        if requested in {"", "auto"}:
            candidates = [self._capcut_candidate(), self._local_candidate()]
            return [candidate for candidate in candidates if candidate.available]
        if requested in {"capcut", "capcut_cli"}:
            candidates = [self._capcut_candidate()]
            if self.settings.fallback_to_local:
                candidates.append(self._local_candidate())
            return candidates
        if requested in {"local", "offline", "sapi", "windows_sapi"}:
            return [self._local_candidate()]
        raise ProviderError("TTS_PROVIDER phải là auto, local hoặc capcut.")

    def provider_for(self, kind: ProviderKind, profile: VoiceProfile | None = None) -> TTSProvider:
        if kind == "capcut":
            return CapCutCliProvider(
                client_path=self.settings.capcut_client_path,
                python_executable=self.settings.capcut_python,
                device_json=self.settings.capcut_device_json,
                voice_profile=profile or self.capcut_profile,
                timeout_seconds=self.settings.timeout_seconds,
                poll_seconds=self.settings.poll_seconds,
            )
        return WindowsSapiProvider(
            voice_name=self.settings.local_tts_voice,
            powershell_executable=self.settings.local_tts_powershell,
            timeout_seconds=self.settings.timeout_seconds,
            volume=self.settings.local_tts_volume,
        )

    def synthesize(self, candidate: ProviderCandidate, text: str, rate: float) -> SynthesisResult:
        if not candidate.available:
            raise ProviderError(candidate.issue or f"{candidate.kind} không khả dụng")
        provider = self.provider_for(candidate.kind, candidate.profile)
        return SynthesisResult(audio=provider.synthesize(text=text, rate=rate), profile=candidate.profile)

    def health(self) -> dict:
        try:
            candidates = self.candidates()
            provider_error = ""
        except ProviderError as exc:
            candidates = []
            provider_error = str(exc)

        capcut_candidate = self._capcut_candidate()
        local_candidate = self._local_candidate()
        primary = candidates[0].profile if candidates else self.local_profile
        return {
            "status": "ok" if any(candidate.available for candidate in candidates) else "needs_configuration",
            "provider": self.settings.tts_provider,
            "provider_error": provider_error,
            "provider_label": " -> ".join(candidate.profile.provider_label for candidate in candidates),
            "provider_order": [candidate.kind for candidate in candidates],
            "voice": primary.name,
            "voice_type": primary.voice_type,
            "resource_id": primary.resource_id,
            "client_configured": capcut_candidate.available or local_candidate.available,
            "client_exists": capcut_candidate.available or local_candidate.available,
            "capcut_client_configured": bool(self.settings.capcut_client_path),
            "capcut_client_exists": bool(
                self.settings.capcut_client_path
                and Path(self.settings.capcut_client_path).expanduser().is_file()
            ),
            "network_tts_enabled": self.settings.allow_network_tts,
            "fallback_to_local": self.settings.fallback_to_local,
            "local_tts_available": local_candidate.available,
            "local_tts_voice": self.settings.local_tts_voice or "",
            "providers": [
                {
                    "provider": candidate.kind,
                    "provider_label": candidate.profile.provider_label,
                    "voice": candidate.profile.name,
                    "voice_type": candidate.profile.voice_type,
                    "resource_id": candidate.profile.resource_id,
                    "available": candidate.available,
                    "issue": candidate.issue,
                }
                for candidate in [capcut_candidate, local_candidate]
            ],
        }
