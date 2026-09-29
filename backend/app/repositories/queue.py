from datetime import timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select, update

from app.core.errors import LeaseLost
from app.models.entities import ACTIVE, Transcription, now


class SqlJobQueue:
    """Atomic compare-and-set claims. No database-specific queue primitives."""

    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    def claim(self):
        moment = now()
        expired = and_(Transcription.status.in_(ACTIVE), Transcription.lease_until < moment)
        eligible = or_(Transcription.status == "QUEUED", expired)
        with self.database.sessions.begin() as db:
            db.execute(
                update(Transcription)
                .where(expired, Transcription.attempts >= self.settings.job_max_attempts)
                .values(
                    status="FAILED",
                    error_message="O processamento foi interrompido repetidamente. Envie o áudio novamente.",
                    processing_finished_at=moment,
                    lease_token=None,
                    lease_until=None,
                )
            )
            ids = db.scalars(
                select(Transcription.id)
                .where(eligible, Transcription.attempts < self.settings.job_max_attempts)
                .order_by(Transcription.created_at)
                .limit(10)
            ).all()
            for job_id in ids:
                token = str(uuid4())
                changed = db.execute(
                    update(Transcription)
                    .where(
                        Transcription.id == job_id,
                        eligible,
                        Transcription.attempts < self.settings.job_max_attempts,
                    )
                    .values(
                        status="PREPROCESSING",
                        lease_token=token,
                        lease_until=moment + timedelta(seconds=self.settings.job_lease_seconds),
                        attempts=Transcription.attempts + 1,
                        processing_started_at=moment,
                        error_message=None,
                    )
                )
                if changed.rowcount == 1:
                    return job_id, token
        return None

    def heartbeat(self, job_id, token):
        with self.database.sessions.begin() as db:
            result = db.execute(
                update(Transcription)
                .where(
                    Transcription.id == job_id,
                    Transcription.lease_token == token,
                    Transcription.status.in_(ACTIVE),
                )
                .values(lease_until=now() + timedelta(seconds=self.settings.job_lease_seconds))
            )
            return result.rowcount == 1

    def stage(self, job_id, token, status):
        with self.database.sessions.begin() as db:
            result = db.execute(
                update(Transcription)
                .where(
                    Transcription.id == job_id,
                    Transcription.lease_token == token,
                    Transcription.status.in_(ACTIVE),
                )
                .values(status=status, updated_at=now())
            )
            if result.rowcount != 1:
                raise LeaseLost()

    def fail(self, job_id, token, message):
        with self.database.sessions.begin() as db:
            db.execute(
                update(Transcription)
                .where(Transcription.id == job_id, Transcription.lease_token == token)
                .values(
                    status="FAILED",
                    error_message=message,
                    processing_finished_at=now(),
                    lease_token=None,
                    lease_until=None,
                )
            )
