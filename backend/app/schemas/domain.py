from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, model_validator


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    word: str
    confidence: float | None = None


@dataclass(frozen=True)
class Turn:
    start: float
    end: float
    speaker: str


@dataclass
class AlignedSegment:
    start: float
    end: float
    text: str
    speaker: str
    confidence: float | None = None
    words: list[dict] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    overlap: bool = False
    needs_review: bool = False


class SpeakerOptions(BaseModel):
    number_of_speakers: int | None = Field(default=None, ge=1, le=32)
    min_speakers: int | None = Field(default=None, ge=1, le=32)
    max_speakers: int | None = Field(default=None, ge=1, le=32)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.number_of_speakers is not None and (
            self.min_speakers is not None or self.max_speakers is not None
        ):
            raise ValueError("Informe o número exato OU os limites de falantes.")
        if self.min_speakers and self.max_speakers and self.min_speakers > self.max_speakers:
            raise ValueError("O mínimo de falantes não pode exceder o máximo.")
        return self


class SpeakerEdit(BaseModel):
    display_name: str = Field(min_length=1, max_length=100, pattern=r"^\S(?:[^\r\n]*\S)?$")


class DocumentSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class TranscriptDocument(BaseModel):
    transcription_id: str
    language: str
    duration: float
    participants: list[str]
    segments: list[DocumentSegment]


ExportFormat = Literal["txt", "json", "srt", "vtt"]
