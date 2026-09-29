import io
import math
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(
            b"".join(
                struct.pack("<h", int(3000 * math.sin(i / 16000 * 440 * 2 * math.pi)))
                for i in range(48000)
            )
        )
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path}/test.db",
        upload_dir=tmp_path / "uploads",
        max_audio_size_mb=1,
        max_audio_duration_seconds=120,
        _env_file=None,
    )
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def uploaded(client, wav_bytes):
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("conversa.wav", wav_bytes, "audio/wav")},
        data={"language": "pt", "number_of_speakers": "2"},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]
