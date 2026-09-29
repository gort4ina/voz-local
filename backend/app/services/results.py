from datetime import timedelta

from sqlalchemy import select, update

from app.core.errors import ApplicationError
from app.models.entities import ACTIVE, TERMINAL, Speaker, Transcription, now
from app.repositories.transcriptions import TranscriptionRepository
from app.schemas.domain import DocumentSegment, TranscriptDocument

STAGES = [
    "UPLOADED",
    "QUEUED",
    "PREPROCESSING",
    "TRANSCRIBING",
    "DIARIZING",
    "ALIGNING",
    "COMPLETED",
]


def utc_iso(value):
    return value.isoformat() + "Z" if value else None


def status_dto(job):
    return {
        "id": job.id,
        "status": job.status,
        "progress": 100 if job.status == "COMPLETED" else None,
        "progress_basis": "stage",
        "stage_index": STAGES.index(job.status) if job.status in STAGES else None,
        "error_message": job.error_message,
        "attempts": job.attempts,
        "updated_at": utc_iso(job.updated_at),
    }


def summary_dto(job):
    return {
        **status_dto(job),
        "original_filename": job.original_filename,
        "language": job.language,
        "duration": job.duration,
        "size_bytes": job.size_bytes,
        "mime_type": job.mime_type,
        "audio_available": job.audio_path is not None,
        "created_at": utc_iso(job.created_at),
    }


def segment_dto(s):
    return {
        "id": s.id,
        "speaker_id": s.speaker_id,
        "start": s.start_time,
        "end": s.end_time,
        "duration": s.end_time - s.start_time,
        "text": s.text,
        "original_text": s.original_text,
        "confidence": s.confidence,
        "sequence": s.sequence,
        "words": s.words,
        "candidate_labels": s.candidate_labels,
        "overlap": s.overlap,
        "needs_review": s.needs_review,
        "edited_at": utc_iso(s.edited_at),
    }


def result_dto(job):
    return {
        **summary_dto(job),
        "processing_started_at": utc_iso(job.processing_started_at),
        "processing_finished_at": utc_iso(job.processing_finished_at),
        "metadata": job.technical_metadata,
        "speakers": [
            {"id": s.id, "internal_label": s.internal_label, "display_name": s.display_name}
            for s in job.speakers
        ],
        "segments": [segment_dto(s) for s in job.segments],
    }


class ResultService:
    def __init__(self, database, storage):
        self.database, self.storage = database, storage

    def get(self, job_id):
        with self.database.sessions() as db:
            return result_dto(TranscriptionRepository(db).get(job_id))

    def status(self, job_id):
        with self.database.sessions() as db:
            return status_dto(TranscriptionRepository(db).get(job_id, complete=False))

    def list(self, limit, offset):
        with self.database.sessions() as db:
            return [summary_dto(t) for t in TranscriptionRepository(db).list(limit, offset)]

    def rename_speaker(self, job_id, speaker_id, display_name):
        with self.database.sessions.begin() as db:
            job = TranscriptionRepository(db).get(job_id, complete=False)
            if job.status != "COMPLETED":
                raise ApplicationError("Aguarde a conclusão para editar a transcrição.", 409)
            entity = db.scalar(
                select(Speaker).where(Speaker.id == speaker_id, Speaker.transcription_id == job_id)
            )
            if entity is None:
                raise ApplicationError("Item não encontrado nesta transcrição.", 404)
            entity.display_name = display_name
            job.updated_at = now()
        return self.get(job_id)

    def delete(self, job_id, audio_only=False):
        with self.database.sessions.begin() as db:
            # Lock/check together so a worker cannot claim a queued job during deletion.
            changed = db.execute(
                update(Transcription)
                .where(Transcription.id == job_id, Transcription.status.not_in(ACTIVE))
                .values(updated_at=now())
            )
            if changed.rowcount != 1:
                TranscriptionRepository(db).get(job_id, complete=False)
                raise ApplicationError(
                    "Aguarde o processamento terminar para excluir este arquivo.", 409
                )
            job = TranscriptionRepository(db).get(job_id)
            if audio_only and job.status not in TERMINAL:
                raise ApplicationError("O áudio é necessário para processar este job.", 409)
            self.storage.delete(job_id)
            if audio_only:
                job.audio_path = None
            else:
                job.segments.clear()
                db.flush()
                job.speakers.clear()
                db.flush()
                db.delete(job)

    def audio_file(self, job_id):
        with self.database.sessions() as db:
            job = TranscriptionRepository(db).get(job_id, complete=False)
            if not job.audio_path:
                raise ApplicationError("O áudio foi excluído.", 410)
            path = self.storage.resolve(job.audio_path)
            if not path.is_file():
                raise ApplicationError("O áudio não está mais disponível.", 410)
            return path, job.mime_type, job.original_filename

    def get_transcript_document(self, transcription_id):
        data = self.get(transcription_id)
        if data["status"] != "COMPLETED":
            raise ApplicationError("A transcrição ainda não foi concluída.", 409)
        names = {s["id"]: s["display_name"] for s in data["speakers"]}
        return TranscriptDocument(
            transcription_id=transcription_id,
            language=data["language"],
            duration=data["duration"],
            participants=list(names.values()),
            segments=[
                DocumentSegment(
                    speaker=names[s["speaker_id"]], start=s["start"], end=s["end"], text=s["text"]
                )
                for s in data["segments"]
            ],
        )

    def purge_expired(self, days):
        if days <= 0:
            return 0
        with self.database.sessions() as db:
            ids = db.scalars(
                select(Transcription.id).where(
                    Transcription.status.in_(TERMINAL),
                    Transcription.created_at < now() - timedelta(days=days),
                )
            ).all()
        for job_id in ids:
            self.delete(job_id)
        return len(ids)
