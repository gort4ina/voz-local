from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.core.errors import ApplicationError
from app.models.entities import Transcription
from app.services.storage import sanitize_filename


class UploadService:
    def __init__(self, database, storage, audio, settings):
        self.database, self.storage, self.audio, self.settings = database, storage, audio, settings

    async def create(self, upload, language, options):
        filename = sanitize_filename(upload.filename or "")
        extension = self.audio.validate_headers(filename, upload.content_type)
        job_id = str(uuid4())
        directory = self.storage.directory(job_id)
        directory.mkdir(mode=0o700)
        key = f"{job_id}/original{extension}"
        path = self.storage.resolve(key)
        size = 0
        try:
            with path.open("xb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_audio_size_mb * 1024 * 1024:
                        raise ApplicationError("O arquivo excede o limite de tamanho.", 413)
                    output.write(chunk)
            if size == 0:
                raise ApplicationError("O arquivo está vazio.", 422)
            duration, mime = await run_in_threadpool(self.audio.inspect, path, extension)
            with self.database.sessions.begin() as db:
                job = Transcription(
                    id=job_id,
                    original_filename=filename,
                    audio_path=key,
                    status="UPLOADED",
                    language=language,
                    duration=duration,
                    size_bytes=size,
                    mime_type=mime,
                    options=options.model_dump(exclude_none=True),
                )
                db.add(job)
                db.flush()
                job.status = "QUEUED"
            return {"id": job_id, "status": "QUEUED", "progress": None, "progress_basis": "stage"}
        except BaseException:
            self.storage.delete(job_id)
            raise
        finally:
            await upload.close()
