from __future__ import annotations

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    filename: str | None = Field(default=None, max_length=100)
    voice_type: str | None = Field(default=None, max_length=120)
    resource_id: str | None = Field(default=None, max_length=80)
    voice_name: str | None = Field(default=None, max_length=120)


class TextPrepareRequest(BaseModel):
    text: str = Field(..., min_length=1)
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    chunk_size: int | None = Field(default=None, ge=100, le=10000)


class PreparedChunk(BaseModel):
    index: int
    text: str
    char_count: int
    rate: float
    emotion_tag: str | None
    emotion_label: str
    pause_after: float


class TextPrepareResponse(BaseModel):
    total_chunks: int
    total_chars: int
    max_text_length: int
    chunk_size: int
    base_rate: float
    chunks: list[PreparedChunk]


class TTSBatchRequest(TextPrepareRequest):
    filename_prefix: str | None = Field(default=None, max_length=90)
    voice_type: str | None = Field(default=None, max_length=120)
    resource_id: str | None = Field(default=None, max_length=80)
    voice_name: str | None = Field(default=None, max_length=120)


class TTSBatchItem(BaseModel):
    index: int
    filename: str
    cache_id: str
    download_url: str
    content_type: str
    extension: str
    cache: str
    provider: str
    provider_label: str
    voice: str
    voice_type: str
    rate: float
    char_count: int
    emotion_label: str


class TTSBatchResponse(BaseModel):
    total: int
    items: list[TTSBatchItem]


class VoiceInfo(BaseModel):
    name: str
    voice_type: str
    resource_id: str
    language: str
    provider: str
    provider_label: str


class LocalVoiceInfo(BaseModel):
    name: str
    culture: str
    gender: str
    age: str
    description: str


class HistoryItem(BaseModel):
    id: str
    created_at: str
    rate: float
    text_preview: str
    char_count: int
    extension: str
    content_type: str
    provider: str
    provider_label: str
    voice: str
