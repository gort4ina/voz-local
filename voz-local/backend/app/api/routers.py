from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.core.errors import ApplicationError
from app.schemas.domain import ExportFormat, SpeakerEdit, SpeakerOptions
from app.services.export import ExportService

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "processing": "local",
        "max_audio_size_mb": request.app.state.settings.max_audio_size_mb,
        "max_audio_duration_seconds": request.app.state.settings.max_audio_duration_seconds,
    }


@router.post("/transcriptions", status_code=202)
async def create(
    request: Request,
    audio: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
    number_of_speakers: Annotated[int | None, Form()] = None,
    min_speakers: Annotated[int | None, Form()] = None,
    max_speakers: Annotated[int | None, Form()] = None,
):
    language = language or request.app.state.settings.default_language
    if language not in {"auto", "pt", "en", "es", "fr", "de", "it"}:
        raise ApplicationError("Idioma não suportado pela interface.", 422)
    try:
        options = SpeakerOptions(
            number_of_speakers=number_of_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    except ValidationError:
        raise ApplicationError(
            "Quantidade de falantes inválida. Use exato ou mínimo/máximo, entre 1 e 32.", 422
        ) from None
    return await request.app.state.upload.create(audio, language, options)


@router.get("/transcriptions")
def list_transcriptions(
    request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
):
    return request.app.state.results.list(limit, offset)


@router.get("/transcriptions/{job_id}/status")
def status(job_id: UUID, request: Request):
    return request.app.state.results.status(str(job_id))


@router.get("/transcriptions/{job_id}")
def result(job_id: UUID, request: Request):
    return request.app.state.results.get(str(job_id))


@router.get("/transcriptions/{job_id}/segments")
def segments(job_id: UUID, request: Request):
    return request.app.state.results.get(str(job_id))["segments"]


@router.patch("/transcriptions/{job_id}/speakers/{speaker_id}")
def rename(job_id: UUID, speaker_id: UUID, body: SpeakerEdit, request: Request):
    return request.app.state.results.rename_speaker(
        str(job_id), str(speaker_id), body.display_name
    )


@router.delete("/transcriptions/{job_id}", status_code=204)
def delete(job_id: UUID, request: Request):
    request.app.state.results.delete(str(job_id))
    return Response(status_code=204)


@router.delete("/transcriptions/{job_id}/audio", status_code=204)
def delete_audio(job_id: UUID, request: Request):
    request.app.state.results.delete(str(job_id), audio_only=True)
    return Response(status_code=204)


@router.get("/transcriptions/{job_id}/audio")
def audio(job_id: UUID, request: Request):
    path, mime, filename = request.app.state.results.audio_file(str(job_id))
    return FileResponse(
        path,
        media_type=mime,
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/transcriptions/{job_id}/export")
def export(job_id: UUID, request: Request, format: ExportFormat = "txt"):
    content, mime = ExportService(request.app.state.results).export(str(job_id), format)
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="transcricao-{job_id}.{format}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/transcriptions/{job_id}/document")
def document(job_id: UUID, request: Request):
    return request.app.state.results.get_transcript_document(str(job_id))
