from typing import Protocol

from app.schemas.domain import Word


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: str, language: str) -> tuple[list[Word], str]:
        """Return timestamped words and the detected/selected language."""
        ...
