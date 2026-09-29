import logging
import os
import signal
import threading
from time import monotonic

from app.audio.processing import AudioProcessingService
from app.core.config import get_settings
from app.core.database import Database
from app.core.logging import configure_logging
from app.diarization.pyannote_provider import PyannoteProvider
from app.repositories.queue import SqlJobQueue
from app.services.results import ResultService
from app.services.storage import LocalAudioStorage
from app.services.transcription import TranscriptionService
from app.transcription.whisper_provider import FasterWhisperProvider


def main():
    os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    configure_logging()
    settings = get_settings()
    os.environ["HF_HOME"] = str(settings.hf_home.resolve())
    database = Database(settings.database_url)
    database.initialize()
    storage = LocalAudioStorage(settings.upload_dir)
    queue = SqlJobQueue(database, settings)
    service = TranscriptionService(
        database,
        storage,
        AudioProcessingService(settings),
        FasterWhisperProvider(settings),
        PyannoteProvider(settings),
        queue,
        engine_metadata={
            "transcription_provider": "faster-whisper",
            "whisper_model": settings.whisper_model,
            "whisper_device_config": settings.whisper_device,
            "whisper_compute_type_config": settings.whisper_compute_type,
            "diarization_provider": "pyannote.audio",
            "diarization_model": settings.diarization_model,
            "diarization_device_config": settings.diarization_device,
        },
    )
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    last_purge = 0
    while not stop.is_set():
        if monotonic() - last_purge > 3600:
            ResultService(database, storage).purge_expired(settings.retention_days)
            last_purge = monotonic()
        claim = queue.claim()
        if not claim:
            stop.wait(1)
            continue
        job_id, token = claim
        heartbeat_stop = threading.Event()

        def heartbeat():
            while not heartbeat_stop.wait(settings.job_lease_seconds / 3):
                try:
                    if not queue.heartbeat(job_id, token):
                        return
                except Exception:
                    logging.getLogger(__name__).warning(
                        "heartbeat_failed", extra={"job_id": job_id}
                    )

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        logging.getLogger(__name__).info("job_started", extra={"job_id": job_id})
        try:
            service.process(job_id, token)
        finally:
            heartbeat_stop.set()
            thread.join(timeout=5)
    database.engine.dispose()


if __name__ == "__main__":
    main()
