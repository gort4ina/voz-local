from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now():
    # UTC-naive is intentional: identical comparisons on SQLite and PostgreSQL.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


ACTIVE = ("PREPROCESSING", "TRANSCRIBING", "DIARIZING", "ALIGNING")
TERMINAL = ("COMPLETED", "FAILED")


class Transcription(Base):
    __tablename__ = "transcriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    original_filename: Mapped[str] = mapped_column(String(255))
    audio_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    language: Mapped[str] = mapped_column(String(20), default="pt")
    duration: Mapped[float] = mapped_column(Float)
    size_bytes: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    technical_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_words: Mapped[list] = mapped_column(JSON, default=list)
    diarization_turns: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    speakers: Mapped[list["Speaker"]] = relationship(
        cascade="all, delete-orphan", order_by="Speaker.internal_label"
    )
    segments: Mapped[list["TranscriptionSegment"]] = relationship(
        cascade="all, delete-orphan", order_by="TranscriptionSegment.sequence"
    )
    __table_args__ = (Index("ix_queue_lease", "status", "lease_until", "created_at"),)


class Speaker(Base):
    __tablename__ = "speakers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    transcription_id: Mapped[str] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="CASCADE"), index=True
    )
    internal_label: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(100))


class TranscriptionSegment(Base):
    __tablename__ = "segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    transcription_id: Mapped[str] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="CASCADE"), index=True
    )
    speaker_id: Mapped[str] = mapped_column(ForeignKey("speakers.id", ondelete="CASCADE"))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    original_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    words: Mapped[list] = mapped_column(JSON, default=list)
    candidate_labels: Mapped[list] = mapped_column(JSON, default=list)
    overlap: Mapped[bool] = mapped_column(default=False)
    needs_review: Mapped[bool] = mapped_column(default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
