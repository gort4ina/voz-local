"""Import/runtime smoke check without downloading gated or large models."""
import os
from importlib.metadata import version

os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from torchcodec.decoders import AudioDecoder

for name in ("torch", "torchaudio", "torchcodec", "faster-whisper", "pyannote.audio"):
    print(f"{name}: {version(name)}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print("Imports concluídos. Isso não valida a qualidade da transcrição nem o acesso ao modelo de diarização.")
