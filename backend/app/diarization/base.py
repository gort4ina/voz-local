from typing import Protocol

from app.schemas.domain import SpeakerOptions, Turn


class DiarizationProvider(Protocol):
    def validate_configuration(self) -> None:
        """Validate local credentials/model selection before starting a long job."""
        ...

    def diarize(self, audio_path: str, options: SpeakerOptions) -> list[Turn]:
        """Return all speaker turns, including overlapping turns."""
        ...
