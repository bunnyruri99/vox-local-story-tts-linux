"""Compatibility imports for older scripts.

New code lives under vox_local.providers.
"""

from vox_local.providers.base import AudioResult, ProviderError
from vox_local.providers.capcut_cli import (
    RESOURCE_ID,
    VOICE_NAME,
    VOICE_TYPE,
    CapCutCliProvider,
)
from vox_local.providers.windows_sapi import LocalVoice, WindowsSapiProvider

__all__ = [
    "AudioResult",
    "ProviderError",
    "RESOURCE_ID",
    "VOICE_NAME",
    "VOICE_TYPE",
    "CapCutCliProvider",
    "LocalVoice",
    "WindowsSapiProvider",
]
