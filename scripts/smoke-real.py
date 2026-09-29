"""Explicit real-model smoke test: use a short, non-sensitive conversation.

Run from the project root with the backend environment installed:
  python scripts/smoke-real.py /absolute/path/conversation.wav
The script performs actual upload, worker processing, persistence and export locally.
No fake providers are enabled. Needs HUGGINGFACE_TOKEN and accepted model terms.
"""
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.audio.processing import AudioProcessingService
from app.core.config import Settings
from app.diarization.pyannote_provider import PyannoteProvider
from app.main import create_app
from app.repositories.queue import SqlJobQueue
from app.services.transcription import TranscriptionService
from app.transcription.whisper_provider import FasterWhisperProvider

if len(sys.argv) != 2:
    raise SystemExit("Uso: python scripts/smoke-real.py caminho-do-audio")
os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
settings = Settings(database_url="sqlite:///./data/smoke.db", upload_dir=Path("./data/smoke-uploads"))
path = Path(sys.argv[1]).resolve()
app = create_app(settings)
with TestClient(app) as client:
    with path.open("rb") as source:
        response = client.post("/api/transcriptions", files={"audio": (path.name, source, "application/octet-stream")}, data={"language": "pt", "number_of_speakers": 2})
    response.raise_for_status()
    job_id = response.json()["id"]
    queue = SqlJobQueue(app.state.database, settings)
    claim = queue.claim()
    if claim is None or claim[0] != job_id:
        raise SystemExit("Há outro job pendente no banco de smoke; finalize-o antes de repetir.")
    service = TranscriptionService(app.state.database, app.state.storage, AudioProcessingService(settings), FasterWhisperProvider(settings), PyannoteProvider(settings), queue)
    start = time.monotonic()
    service.process(*claim)
    result = client.get(f"/api/transcriptions/{job_id}").json()
    print({"status": result["status"], "speakers": len(result["speakers"]), "segments": len(result["segments"]), "seconds": round(time.monotonic() - start, 2)})
    if result["status"] != "COMPLETED":
        raise SystemExit(result["error_message"])
    output = Path("./data/smoke-result.json")
    output.write_bytes(client.get(f"/api/transcriptions/{job_id}/export?format=json").content)
    print(f"Resultado: {output}. Confira manualmente a atribuição dos falantes.")
