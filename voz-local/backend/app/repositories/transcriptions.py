from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.models.entities import Transcription


class TranscriptionRepository:
    def __init__(self, session):
        self.session = session

    def get(self, job_id, complete=True):
        query = select(Transcription).where(Transcription.id == job_id)
        if complete:
            query = query.options(
                selectinload(Transcription.speakers), selectinload(Transcription.segments)
            )
        job = self.session.scalar(query)
        if job is None:
            raise ApplicationError("Transcrição não encontrada.", 404)
        return job

    def list(self, limit=50, offset=0):
        return self.session.scalars(
            select(Transcription)
            .order_by(Transcription.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
