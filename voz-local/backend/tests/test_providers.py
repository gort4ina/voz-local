import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.core.errors import ApplicationError
from app.diarization.pyannote_provider import PyannoteProvider
from app.schemas.domain import SpeakerOptions
from app.transcription.whisper_provider import FasterWhisperProvider


def test_faster_whisper_adapter_preserves_words_and_uses_vad(monkeypatch):
    model = Mock()
    model.transcribe.return_value = (
        [
            SimpleNamespace(
                words=[SimpleNamespace(start=1.1, end=1.7, word=" olá", probability=0.8)],
                text=" olá",
            )
        ],
        SimpleNamespace(language="pt"),
    )
    constructor = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=constructor))
    monkeypatch.setitem(
        sys.modules, "ctranslate2", SimpleNamespace(get_supported_compute_types=lambda _: {"int8"})
    )
    monkeypatch.setattr("app.transcription.whisper_provider.resolve_device", lambda _: "cpu")
    words, language = FasterWhisperProvider(Settings(_env_file=None)).transcribe(
        "audio.wav", "auto"
    )
    assert words[0].start == 1.1 and words[0].confidence == 0.8 and language == "pt"
    assert model.transcribe.call_args.kwargs["word_timestamps"]
    assert model.transcribe.call_args.kwargs["vad_filter"]
    assert model.transcribe.call_args.kwargs["language"] is None


def test_pyannote_missing_credentials_fails_before_model_import():
    with pytest.raises(ApplicationError, match="HUGGINGFACE_TOKEN"):
        PyannoteProvider(Settings(huggingface_token="", _env_file=None)).diarize(
            "audio.wav", SpeakerOptions()
        )


def test_pyannote_api_mapping_regular_overlap_and_local_call(monkeypatch):
    annotation = Mock()
    annotation.itertracks.return_value = [
        (SimpleNamespace(start=0, end=2), "_", "A"),
        (SimpleNamespace(start=1, end=3), "_", "B"),
    ]
    pipeline = Mock(return_value=SimpleNamespace(speaker_diarization=annotation))
    loader = Mock(return_value=pipeline)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(device=lambda d: d))
    monkeypatch.setitem(sys.modules, "pyannote", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "pyannote.audio",
        SimpleNamespace(Pipeline=SimpleNamespace(from_pretrained=loader)),
    )
    monkeypatch.setattr("app.diarization.pyannote_provider.resolve_device", lambda _: "cpu")
    result = PyannoteProvider(
        Settings(huggingface_token="fake-test-token", _env_file=None)
    ).diarize("audio.wav", SpeakerOptions(number_of_speakers=2))
    assert result[0].end > result[1].start
    assert pipeline.call_args.kwargs == {"num_speakers": 2}
    assert loader.call_args.kwargs == {"token": "fake-test-token"}


def test_remote_pyannote_pipeline_is_rejected():
    settings = Settings(
        diarization_model="pyannote/speaker-diarization-precision-2",
        huggingface_token="fake-test-token",
        _env_file=None,
    )
    with pytest.raises(ApplicationError, match="remotos"):
        PyannoteProvider(settings).validate_configuration()
