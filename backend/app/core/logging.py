import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Only explicitly allowed metadata; never exception strings, names or transcript content.
        return json.dumps(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                **{
                    key: getattr(record, key)
                    for key in ("job_id", "stage", "duration_seconds", "error_type")
                    if hasattr(record, key)
                },
            }
        )


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in ("httpx", "httpcore", "huggingface_hub", "faster_whisper", "pyannote"):
        logging.getLogger(name).setLevel(logging.ERROR)
