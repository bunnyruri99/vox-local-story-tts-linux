from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

ProviderKind = Literal["capcut", "local"]


class ProviderError(RuntimeError):
    """Raised when a TTS provider cannot complete a request."""


@dataclass(frozen=True)
class AudioResult:
    data: bytes
    content_type: str
    source_url: str


@dataclass(frozen=True)
class VoiceProfile:
    provider: ProviderKind
    provider_label: str
    name: str
    voice_type: str
    resource_id: str
    language: str
    header_value: str


@dataclass(frozen=True)
class ProviderCandidate:
    kind: ProviderKind
    profile: VoiceProfile
    available: bool
    issue: str


@dataclass(frozen=True)
class SynthesisResult:
    audio: AudioResult
    profile: VoiceProfile
    fallback_from: str | None = None


class TTSProvider(Protocol):
    def synthesize(self, text: str, rate: float) -> AudioResult:
        ...
