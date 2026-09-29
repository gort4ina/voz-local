import logging
from dataclasses import asdict
from time import monotonic

from sqlalchemy import update

from app.core.errors import ApplicationError, LeaseLost
from app.models.entities import Speaker, Transcription, TranscriptionSegment, now, uid
from app.repositories.transcriptions import TranscriptionRepository
from app.schemas.domain import SpeakerOptions
from app.services.alignment import SegmentAlignmentService
from app.services.merge import SegmentMergeService

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(
        self,
        database,
        storage,
        audio,
        transcription_provider,
        diarization_provider,
        queue,
        engine_metadata=None,
    ):
        self.engine_metadata = engine_metadata or {}
        self.database, self.storage, self.audio = database, storage, audio
        self.transcription_provider, self.diarization_provider = (
            transcription_provider,
            diarization_provider,
        )
        self.queue = queue
        self.alignment, self.merge = SegmentAlignmentService(), SegmentMergeService()

    def process(self, job_id, token):
        started = monotonic()
        normalized = self.storage.directory(job_id) / f"normalized-{token}.wav"

        def stage(value):
            self.queue.stage(job_id, token, value)
            logger.info("job_stage", extra={"job_id": job_id, "stage": value})

        try:
            with self.database.sessions() as db:
                job = TranscriptionRepository(db).get(job_id, complete=False)
                path, language, options = (
                    job.audio_path,
                    job.language,
                    SpeakerOptions(**job.options),
                )
            self.diarization_provider.validate_configuration()
            stage("PREPROCESSING")
            duration = self.audio.normalize(self.storage.resolve(path), normalized)
            prep_time = monotonic() - started
            stage("TRANSCRIBING")
            point = monotonic()
            words, detected_language = self.transcription_provider.transcribe(
                str(normalized), language
            )
            asr_time = monotonic() - point
            stage("DIARIZING")
            point = monotonic()
            turns = self.diarization_provider.diarize(str(normalized), options)
            diar_time = monotonic() - point
            stage("ALIGNING")
            point = monotonic()
            segments = self.merge.merge(self.alignment.align(words, turns), turns)
            if not segments:
                raise ApplicationError(
                    "Nenhuma fala foi reconhecida. Confira se o áudio contém fala audível."
                )
            # Preserve speakers detected only in overlap or without an ASR word.
            labels = list(dict.fromkeys([s.speaker for s in segments] + [t.speaker for t in turns]))
            metrics = {
                "audio_duration_seconds": duration,
                "processing_duration_seconds": monotonic() - started,
                "preprocessing_duration_seconds": prep_time,
                "transcription_duration_seconds": asr_time,
                "diarization_duration_seconds": diar_time,
                "alignment_duration_seconds": monotonic() - point,
                "segments": len(segments),
                "speakers": len([x for x in labels if x != "UNKNOWN"]),
                "confidence_kind": "mean_word_probability_not_calibrated",
                "timestamp_source": "faster-whisper_word_alignment",
                "overlap_policy": "preserve_turns_flag_ambiguous_words",
                "pipeline_version": "1.0.0",
                "engines": self.engine_metadata,
            }
            with self.database.sessions.begin() as db:
                # Acquire a write lock and guard ownership in the same transaction as result insertion.
                owned = db.execute(
                    update(Transcription)
                    .where(
                        Transcription.id == job_id,
                        Transcription.lease_token == token,
                        Transcription.status == "ALIGNING",
                    )
                    .values(updated_at=now())
                )
                if owned.rowcount != 1:
                    raise LeaseLost()
                job = TranscriptionRepository(db).get(job_id)
                job.segments.clear()
                db.flush()
                job.speakers.clear()
                db.flush()
                speakers, number = {}, 0
                for label in labels:
                    if label != "UNKNOWN":
                        number += 1
                    speaker = Speaker(
                        id=uid(),
                        internal_label=label,
                        display_name=f"Falante {number}"
                        if label != "UNKNOWN"
                        else "Falante não identificado",
                    )
                    job.speakers.append(speaker)
                    speakers[label] = speaker.id
                db.flush()
                for sequence, s in enumerate(segments):
                    job.segments.append(
                        TranscriptionSegment(
                            speaker_id=speakers[s.speaker],
                            start_time=s.start,
                            end_time=s.end,
                            text=s.text,
                            original_text=s.text,
                            confidence=s.confidence,
                            sequence=sequence,
                            words=s.words,
                            candidate_labels=s.candidates,
                            overlap=s.overlap,
                            needs_review=s.needs_review,
                        )
                    )
                job.duration, job.language, job.status = duration, detected_language, "COMPLETED"
                job.technical_metadata = metrics
                job.raw_words, job.diarization_turns = (
                    [asdict(w) for w in words],
                    [asdict(t) for t in turns],
                )
                job.processing_finished_at, job.lease_token, job.lease_until = now(), None, None
            logger.info(
                "job_completed", extra={"job_id": job_id, "duration_seconds": monotonic() - started}
            )
        except LeaseLost:
            logger.warning("job_lease_lost", extra={"job_id": job_id})
        except Exception as exc:
            message = (
                exc.message
                if isinstance(exc, ApplicationError)
                else "Falha no processamento local. Verifique memória disponível, dependências, download dos modelos e acesso ao Hugging Face."
            )
            self.queue.fail(job_id, token, message)
            logger.error("job_failed", extra={"job_id": job_id, "error_type": type(exc).__name__})
        finally:
            normalized.unlink(missing_ok=True)
