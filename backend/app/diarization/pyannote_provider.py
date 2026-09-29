import gc
import os
from pathlib import Path

from app.core.device import resolve_device
from app.core.errors import ApplicationError
from app.schemas.domain import Turn


class PyannoteProvider:
    def __init__(self, settings):
        self.settings = settings

    def validate_configuration(self):
        model = self.settings.diarization_model
        local = Path(model).is_dir()
        if not local and model != "pyannote/speaker-diarization-community-1":
            raise ApplicationError(
                "Use Community-1 ou um diretório local. Providers remotos não são permitidos nesta implementação."
            )
        if not local and not self.settings.huggingface_token.get_secret_value():
            raise ApplicationError(
                "Configure HUGGINGFACE_TOKEN e aceite os termos do modelo Community-1 no Hugging Face."
            )

    def diarize(self, audio_path, options):
        self.validate_configuration()
        os.environ["HF_HOME"] = str(self.settings.hf_home.resolve())
        # Must precede import: prevent opt-in analytics, including duration/participant metrics.
        os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        token = self.settings.huggingface_token.get_secret_value()
        model = self.settings.diarization_model
        if not token and not Path(model).is_dir():
            raise ApplicationError(
                "Configure HUGGINGFACE_TOKEN e aceite os termos do modelo Community-1 no Hugging Face."
            )
        import torch
        from pyannote.audio import Pipeline

        pipeline = Pipeline.from_pretrained(model, token=token or None)
        if pipeline is None:
            raise ApplicationError(
                "Não foi possível carregar a diarização. Verifique o token e o acesso ao modelo."
            )
        device = resolve_device(self.settings.diarization_device)
        pipeline.to(torch.device(device))
        kwargs = options.model_dump(exclude_none=True)
        if "number_of_speakers" in kwargs:
            kwargs["num_speakers"] = kwargs.pop("number_of_speakers")
        try:
            output = pipeline(audio_path, **kwargs)
            # Regular annotation preserves overlap; exclusive output deliberately not used.
            return [
                Turn(turn.start, turn.end, speaker)
                for turn, _, speaker in output.speaker_diarization.itertracks(yield_label=True)
            ]
        finally:
            del pipeline
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()
