import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.audio.processing import AudioProcessingService
from app.core.errors import ApplicationError
from app.models.entities import Transcription, now
from app.repositories.queue import SqlJobQueue
from app.schemas.domain import SpeakerOptions, Turn, Word
from app.services.export import timestamp
from app.services.transcription import TranscriptionService


def complete(client, job_id, asr=None, diar=None):
    state = client.app.state
    queue = SqlJobQueue(state.database, state.settings)
    claim = queue.claim()
    assert claim and claim[0] == job_id
    transcription = asr or Mock()
    if asr is None:
        transcription.transcribe.return_value = (
            [Word(0.1, 0.8, "Olá.", 0.9), Word(1.2, 1.9, " Tudo bem?", 0.8)],
            "pt",
        )
    diarization = diar or Mock()
    if diar is None:
        diarization.diarize.return_value = [Turn(0, 1, "SPEAKER_00"), Turn(1, 2.5, "SPEAKER_01")]
    service = TranscriptionService(
        state.database,
        state.storage,
        AudioProcessingService(state.settings),
        transcription,
        diarization,
        queue,
    )
    service.process(*claim)
    return client.get(f"/api/transcriptions/{job_id}").json()


def test_upload_job_and_stream_audio(client, uploaded, wav_bytes):
    data = client.get(f"/api/transcriptions/{uploaded}").json()
    assert data["status"] == "QUEUED" and data["duration"] == 3
    assert data["progress"] is None
    assert data["original_filename"] == "conversa.wav"
    audio = client.get(f"/api/transcriptions/{uploaded}/audio")
    assert audio.content == wav_bytes and audio.headers["cache-control"] == "no-store"
    part = client.get(f"/api/transcriptions/{uploaded}/audio", headers={"Range": "bytes=0-9"})
    assert part.status_code == 206 and part.content == wav_bytes[:10]


@pytest.mark.parametrize(
    "filename,mime,body,status",
    [
        ("a.exe", "audio/wav", b"x", 415),
        ("a.wav", "text/plain", b"x", 415),
        ("a.wav", "audio/wav", b"not audio", 415),
        ("a.wav", "audio/wav", b"", 422),
        ("a.wav", "audio/wav", b"x" * (1024 * 1024 + 1), 413),
    ],
)
def test_upload_validation(client, filename, mime, body, status):
    response = client.post("/api/transcriptions", files={"audio": (filename, body, mime)})
    assert response.status_code == status
    assert not list(client.app.state.storage.root.iterdir())


def test_entire_multipart_body_limit(client):
    response = client.post(
        "/api/transcriptions",
        content=b"x" * (3 * 1024 * 1024),
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert response.status_code == 413


def test_duration_limit(client, wav_bytes):
    client.app.state.settings.max_audio_duration_seconds = 1
    response = client.post(
        "/api/transcriptions", files={"audio": ("a.wav", wav_bytes, "audio/wav")}
    )
    assert response.status_code == 413
    assert not list(client.app.state.storage.root.iterdir())


def test_filename_is_metadata_only(client, wav_bytes):
    response = client.post(
        "/api/transcriptions", files={"audio": ("../../evil.wav", wav_bytes, "audio/wav")}
    )
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert client.get(f"/api/transcriptions/{job_id}").json()["original_filename"] == "evil.wav"
    assert list(client.app.state.storage.root.iterdir())[0].name == job_id
    with pytest.raises(ValueError):
        client.app.state.storage.resolve("../../etc/passwd")


@pytest.mark.parametrize(
    "options",
    [
        {"number_of_speakers": "0"},
        {"min_speakers": "3", "max_speakers": "2"},
        {"number_of_speakers": "2", "max_speakers": "3"},
        {"language": "xx"},
        {"number_of_speakers": "2.5"},
    ],
)
def test_invalid_options(client, wav_bytes, options):
    assert (
        client.post(
            "/api/transcriptions", files={"audio": ("a.wav", wav_bytes, "audio/wav")}, data=options
        ).status_code
        == 422
    )


def test_complete_rename_export_document_delete(client, uploaded):
    data = complete(client, uploaded)
    assert data["status"] == "COMPLETED" and data["progress"] == 100
    assert len(data["speakers"]) == 2 and len(data["segments"]) == 2
    assert data["metadata"]["diarization_duration_seconds"] >= 0
    speaker, segment = data["speakers"][0], data["segments"][0]
    response = client.patch(
        f"/api/transcriptions/{uploaded}/speakers/{speaker['id']}",
        json={"display_name": "Psicólogo"},
    )
    assert response.status_code == 200
    assert (
        client.patch(
            f"/api/transcriptions/{uploaded}/segments/{segment['id']}", json={"text": "Olá, como vai?"}
        ).status_code
        == 404
    )
    for fmt in ["txt", "json", "srt", "vtt"]:
        export = client.get(f"/api/transcriptions/{uploaded}/export?format={fmt}")
        assert (
            export.status_code == 200
            and "Psicólogo" in export.text
            and "Olá." in export.text
        )
        if fmt == "json":
            result = export.json()
            assert len(result["raw_words"]) == 2 and len(result["diarization_turns"]) == 2
        if fmt == "vtt":
            assert export.text.startswith("WEBVTT\n\n")
    document = client.get(f"/api/transcriptions/{uploaded}/document").json()
    assert document["segments"][0]["speaker"] == "Psicólogo"
    assert client.get(f"/api/transcriptions/{uploaded}/segments").status_code == 200
    assert client.delete(f"/api/transcriptions/{uploaded}/audio").status_code == 204
    assert client.get(f"/api/transcriptions/{uploaded}/audio").status_code == 410
    assert client.get(f"/api/transcriptions/{uploaded}/export").status_code == 200
    assert client.delete(f"/api/transcriptions/{uploaded}").status_code == 204
    assert client.get(f"/api/transcriptions/{uploaded}").status_code == 404
    assert not list(client.app.state.storage.root.iterdir())


def test_no_access_to_other_job_entities(client, uploaded):
    data = complete(client, uploaded)
    assert (
        client.patch(
            f"/api/transcriptions/{uploaded}/speakers/{uuid4()}", json={"display_name": "Teste"}
        ).status_code
        == 404
    )


def test_safe_errors_and_normalized_cleanup(client, uploaded):
    asr = Mock()
    asr.transcribe.side_effect = RuntimeError("SECRET_CONTENT_DO_NOT_LOG")
    data = complete(client, uploaded, asr=asr)
    assert data["status"] == "FAILED"
    assert "SECRET_CONTENT" not in json.dumps(data)
    assert not list(client.app.state.storage.directory(uploaded).glob("normalized-*"))


def test_missing_token_is_actionable_failure(client, uploaded):
    diar = Mock()
    diar.diarize.side_effect = ApplicationError("Configure HUGGINGFACE_TOKEN.")
    data = complete(client, uploaded, diar=diar)
    assert data["status"] == "FAILED" and "HUGGINGFACE_TOKEN" in data["error_message"]


def test_active_job_cannot_be_deleted_or_edited(client, uploaded):
    state = client.app.state
    queue = SqlJobQueue(state.database, state.settings)
    queue.claim()
    assert client.delete(f"/api/transcriptions/{uploaded}").status_code == 409
    assert client.get(f"/api/transcriptions/{uploaded}/export").status_code == 409
    assert (
        client.patch(
            f"/api/transcriptions/{uploaded}/speakers/{uuid4()}", json={"display_name": "x"}
        ).status_code
        == 409
    )


def test_only_one_worker_claims_a_job(client, uploaded):
    queue = SqlJobQueue(client.app.state.database, client.app.state.settings)
    with ThreadPoolExecutor(max_workers=4) as executor:
        claims = list(executor.map(lambda _: queue.claim(), range(4)))
    assert len([claim for claim in claims if claim]) == 1


def test_lease_recovery_and_old_owner_cannot_publish(client, uploaded):
    state = client.app.state
    queue = SqlJobQueue(state.database, state.settings)
    first = queue.claim()
    assert first and queue.heartbeat(*first)
    with state.database.sessions.begin() as db:
        db.execute(
            update(Transcription)
            .where(Transcription.id == uploaded)
            .values(lease_until=now() - timedelta(seconds=1))
        )
    second = queue.claim()
    assert second and first[1] != second[1]
    assert not queue.heartbeat(*first)
    queue.fail(*first, "stale worker")
    assert client.get(f"/api/transcriptions/{uploaded}/status").json()["status"] == "PREPROCESSING"


def test_persistent_jobs_survive_api_recreation(client, uploaded):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(client.app.state.settings)) as second:
        assert second.get(f"/api/transcriptions/{uploaded}/status").json()["status"] == "QUEUED"


def test_retention_only_removes_expired_terminal_jobs(client, uploaded):
    complete(client, uploaded)
    with client.app.state.database.sessions.begin() as db:
        job = db.scalar(select(Transcription).where(Transcription.id == uploaded))
        job.created_at = now() - timedelta(days=40)
    assert client.app.state.results.purge_expired(0) == 0
    assert client.app.state.results.purge_expired(30) == 1
    assert client.get(f"/api/transcriptions/{uploaded}").status_code == 404


def test_timestamp_millisecond_carry_and_long_audio():
    assert timestamp(59.9999, ",") == "00:01:00,000"
    assert timestamp(7200.1) == "02:00:00.100"


def test_speaker_options_valid_bounds():
    assert SpeakerOptions(min_speakers=1, max_speakers=3).max_speakers == 3


def test_unknown_origin_cannot_enqueue_local_audio(client, wav_bytes):
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("a.wav", wav_bytes, "audio/wav")},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403
    assert client.get("/api/transcriptions").json() == []


def test_streamed_body_without_content_length_is_limited(client):
    def chunks():
        yield b'--boundary\r\nContent-Disposition: form-data; name="audio"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'
        for _ in range(4):
            yield b"a" * (1024 * 1024)
        yield b"\r\n--boundary--\r\n"

    response = client.post(
        "/api/transcriptions",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=boundary"},
    )
    assert response.status_code == 413
    assert client.get("/api/transcriptions").json() == []


def test_exhausted_interrupted_job_fails_explicitly(client, uploaded):
    state = client.app.state
    queue = SqlJobQueue(state.database, state.settings)
    queue.claim()
    with state.database.sessions.begin() as db:
        db.execute(
            update(Transcription)
            .where(Transcription.id == uploaded)
            .values(
                lease_until=now() - timedelta(seconds=1), attempts=state.settings.job_max_attempts
            )
        )
    assert queue.claim() is None
    result = client.get(f"/api/transcriptions/{uploaded}/status").json()
    assert result["status"] == "FAILED" and result["error_message"]
