import json
import math
import subprocess
from pathlib import Path

import magic

from app.core.errors import ApplicationError

FORMATS = {
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".wav": {"audio/wav", "audio/x-wav", "audio/vnd.wave", "audio/wave"},
    ".m4a": {"audio/mp4", "video/mp4", "audio/x-m4a", "audio/m4a"},
    ".ogg": {"audio/ogg", "video/ogg", "application/ogg"},
    ".webm": {"audio/webm", "video/webm", "video/x-matroska", "audio/x-matroska"},
    ".mp4": {"video/mp4", "audio/mp4"},
}


class AudioProcessingService:
    def __init__(self, settings):
        self.settings = settings

    def validate_headers(self, filename, mime):
        extension = Path(filename).suffix.lower()
        if extension not in FORMATS:
            raise ApplicationError("Formato não aceito. Use MP3, WAV, M4A, OGG, WebM ou MP4.", 415)
        # Generic/absent browser MIME is tolerated only with magic + ffprobe validation later.
        if mime and mime.split(";")[0].lower() not in FORMATS[extension] | {
            "application/octet-stream"
        }:
            raise ApplicationError(
                "O tipo MIME informado não corresponde ao formato do arquivo.", 415
            )
        return extension

    def inspect(self, path, extension):
        actual_mime = magic.from_file(str(path), mime=True)
        if actual_mime not in FORMATS[extension]:
            raise ApplicationError("O conteúdo do arquivo não corresponde a um áudio aceito.", 415)
        try:
            process = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            data = json.loads(process.stdout)
            audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
            duration = float(data.get("format", {}).get("duration", 0))
            if not audio_streams or not math.isfinite(duration) or duration <= 0:
                raise ValueError("Missing audio/duration")
        except (subprocess.SubprocessError, ValueError, KeyError):
            raise ApplicationError(
                "Áudio inválido, corrompido ou sem duração identificável.", 422
            ) from None
        if duration > self.settings.max_audio_duration_seconds:
            raise ApplicationError("A duração do áudio excede o limite configurado.", 413)
        return duration, actual_mime

    def normalize(self, source, destination):
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-xerror",
                    "-y",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    "-t",
                    str(self.settings.max_audio_duration_seconds + 1),
                    str(destination),
                ],
                capture_output=True,
                check=True,
                timeout=3600,
            )
            # Revalidate decoded duration: forged container duration must not bypass the limit.
            duration, _ = self.inspect(destination, ".wav")
            return duration
        except subprocess.SubprocessError:
            raise ApplicationError(
                "Falha ao decodificar o áudio. O arquivo pode estar corrompido.", 422
            ) from None
