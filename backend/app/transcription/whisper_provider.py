import gc
import os

from app.core.device import resolve_device
from app.core.errors import ApplicationError
from app.schemas.domain import Word


class FasterWhisperProvider:
    def __init__(self, settings):
        self.settings = settings

    def transcribe(self, audio_path, language):
        os.environ["HF_HOME"] = str(self.settings.hf_home.resolve())
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        import ctranslate2
        from faster_whisper import WhisperModel

        device = resolve_device(self.settings.whisper_device)
        compute = self.settings.whisper_compute_type
        if compute == "auto":
            compute = "int8" if device == "cpu" else "int8_float16"
        if compute not in ctranslate2.get_supported_compute_types(device):
            raise ApplicationError(
                f"O tipo de cálculo {compute} não é suportado no dispositivo {device}."
            )
        model = WhisperModel(self.settings.whisper_model, device=device, compute_type=compute)
        try:
            segments, info = model.transcribe(
                audio_path,
                language=None if language == "auto" else language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
            )
            words = []
            for segment in segments:
                if segment.words:
                    words.extend(Word(w.start, w.end, w.word, w.probability) for w in segment.words)
                elif segment.text.strip():
                    # A provider may lack word alignment; preserve its real segment interval.
                    words.append(Word(segment.start, segment.end, segment.text, None))
            return words, info.language
        finally:
            del model
            gc.collect()
