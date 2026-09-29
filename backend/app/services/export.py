import html
import json

from app.core.errors import ApplicationError
from app.repositories.transcriptions import TranscriptionRepository


def timestamp(seconds, separator="."):
    milliseconds = max(0, round(seconds * 1000))
    total, ms = divmod(milliseconds, 1000)
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{ms:03d}"


def subtitle_text(value):
    # Prevent injected cue boundaries/tags while retaining user text as literal subtitle content.
    return html.escape(" ".join(value.split()), quote=False)


class ExportService:
    def __init__(self, results):
        self.results = results

    def export(self, job_id, fmt):
        data = self.results.get(job_id)
        if data["status"] != "COMPLETED":
            raise ApplicationError("A transcrição ainda não foi concluída.", 409)
        names = {s["id"]: s["display_name"] for s in data["speakers"]}
        if fmt == "json":
            with self.results.database.sessions() as db:
                job = TranscriptionRepository(db).get(job_id, complete=False)
                data["raw_words"], data["diarization_turns"] = job.raw_words, job.diarization_turns
            data["document"] = self.results.get_transcript_document(job_id).model_dump()
            return json.dumps(data, ensure_ascii=False, indent=2), "application/json"
        blocks = []
        for index, s in enumerate(data["segments"], 1):
            name = names[s["speaker_id"]]
            if fmt == "txt":
                blocks.append(
                    f"[{timestamp(s['start'])} - {timestamp(s['end'])}] {name}:\n{s['text']}"
                )
            else:
                separator = "," if fmt == "srt" else "."
                blocks.append(
                    f"{index}\n{timestamp(s['start'], separator)} --> {timestamp(s['end'], separator)}\n{subtitle_text(name)}: {subtitle_text(s['text'])}"
                )
        text = "\n\n".join(blocks) + "\n"
        if fmt == "vtt":
            text = "WEBVTT\n\n" + text
        return text, "text/vtt" if fmt == "vtt" else "text/plain"
