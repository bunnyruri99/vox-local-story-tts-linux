from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from vox_local.providers.base import AudioResult, ProviderError, VoiceProfile


@dataclass(frozen=True)
class LocalVoice:
    name: str
    culture: str
    gender: str
    age: str
    description: str


def local_profile(voice_name: str | None, display_name: str | None) -> VoiceProfile:
    return VoiceProfile(
        provider="local",
        provider_label="Local offline (Windows SAPI)",
        name=display_name or voice_name or "Giọng đọc Windows offline",
        voice_type="windows_sapi",
        resource_id=voice_name or "default",
        language="local",
        header_value="local-windows-sapi",
    )


_SAPI_SCRIPT = r"""
param(
  [Parameter(Mandatory=$true)][string]$TextPath,
  [Parameter(Mandatory=$true)][string]$OutPath,
  [string]$VoiceName = "",
  [int]$Rate = 0,
  [int]$Volume = 100
)

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $synth.Rate = [Math]::Max(-10, [Math]::Min(10, $Rate))
  $synth.Volume = [Math]::Max(0, [Math]::Min(100, $Volume))
  if ($VoiceName -and $VoiceName.Trim().Length -gt 0) {
    try {
      $synth.SelectVoice($VoiceName)
    } catch {
      $available = ($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }) -join ', '
      throw "Local voice '$VoiceName' is not installed. Installed voices: $available"
    }
  }
  $text = Get-Content -LiteralPath $TextPath -Raw -Encoding UTF8
  $synth.SetOutputToWaveFile($OutPath)
  $synth.Speak($text)
} finally {
  if ($synth) {
    $synth.Dispose()
  }
}
"""


_SAPI_LIST_SCRIPT = r"""
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  @($synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
    [pscustomobject]@{
      name = $_.VoiceInfo.Name
      culture = $_.VoiceInfo.Culture.Name
      gender = $_.VoiceInfo.Gender.ToString()
      age = $_.VoiceInfo.Age.ToString()
      description = $_.VoiceInfo.Description
    }
  }) | ConvertTo-Json -Depth 3
} finally {
  if ($synth) {
    $synth.Dispose()
  }
}
"""


class WindowsSapiProvider:
    """Offline TTS provider backed by Windows' built-in Speech API."""

    def __init__(
        self,
        voice_name: str | None = None,
        powershell_executable: str = "powershell.exe",
        timeout_seconds: int = 180,
        volume: int = 100,
    ) -> None:
        self.voice_name = voice_name.strip() if voice_name else None
        self.powershell_executable = powershell_executable.strip() or "powershell.exe"
        self.timeout_seconds = max(10, int(timeout_seconds))
        self.volume = max(0, min(100, int(volume)))

        if not sys.platform.startswith("win"):
            raise ProviderError("Local Windows TTS chỉ chạy trên Windows.")
        if not self._command_available(self.powershell_executable):
            raise ProviderError(
                f"Không tìm thấy PowerShell executable: {self.powershell_executable}"
            )

    @staticmethod
    def _command_available(command: str) -> bool:
        candidate = Path(command).expanduser()
        if candidate.is_file():
            return True
        return shutil.which(command) is not None

    @staticmethod
    def is_available(powershell_executable: str = "powershell.exe") -> bool:
        return sys.platform.startswith("win") and WindowsSapiProvider._command_available(
            powershell_executable
        )

    @staticmethod
    def list_voices(
        powershell_executable: str = "powershell.exe",
        timeout_seconds: int = 20,
    ) -> list[LocalVoice]:
        if not WindowsSapiProvider.is_available(powershell_executable):
            return []
        command = [
            powershell_executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _SAPI_LIST_SCRIPT,
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(5, int(timeout_seconds)),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderError(f"Không thể liệt kê voice local: {exc}") from exc

        output = (completed.stdout or "").strip()
        if completed.returncode != 0:
            detail = ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-1200:]
            raise ProviderError(f"Không thể liệt kê voice local. Output: {detail}")
        if not output:
            return []
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"PowerShell trả về danh sách voice không hợp lệ: {output}") from exc
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return []
        voices: list[LocalVoice] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            voices.append(
                LocalVoice(
                    name=str(item.get("name") or ""),
                    culture=str(item.get("culture") or ""),
                    gender=str(item.get("gender") or ""),
                    age=str(item.get("age") or ""),
                    description=str(item.get("description") or ""),
                )
            )
        return voices

    @staticmethod
    def _sapi_rate(rate: float) -> int:
        return max(-10, min(10, int(round((float(rate) - 1.0) * 10))))

    def synthesize(self, text: str, rate: float) -> AudioResult:
        with tempfile.TemporaryDirectory(prefix="vox-local-tts-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            text_path = temp_dir / "input.txt"
            output_path = temp_dir / "output.wav"
            script_path = temp_dir / "speak.ps1"
            text_path.write_text(text, encoding="utf-8")
            script_path.write_text(_SAPI_SCRIPT, encoding="utf-8-sig")

            command = [
                self.powershell_executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-TextPath",
                str(text_path),
                "-OutPath",
                str(output_path),
                "-Rate",
                str(self._sapi_rate(rate)),
                "-Volume",
                str(self.volume),
            ]
            if self.voice_name:
                command.extend(["-VoiceName", self.voice_name])

            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderError("Local Windows TTS vượt quá thời gian chờ.") from exc
            except OSError as exc:
                raise ProviderError(f"Không thể chạy Local Windows TTS: {exc}") from exc

            if completed.returncode != 0:
                output = ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-1200:]
                raise ProviderError(f"Local Windows TTS lỗi. Output: {output}")
            if not output_path.is_file():
                raise ProviderError("Local Windows TTS không tạo được file WAV.")

            data = output_path.read_bytes()
            if len(data) < 128 or not data.startswith(b"RIFF"):
                raise ProviderError("File WAV local không hợp lệ hoặc quá nhỏ.")
            return AudioResult(
                data=data,
                content_type="audio/wav",
                source_url="local:windows-sapi",
            )
