from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.middleware import BodySizeLimitMiddleware
from app.api.routers import router
from app.audio.processing import AudioProcessingService
from app.core.config import get_settings
from app.core.database import Database
from app.core.errors import ApplicationError
from app.services.results import ResultService
from app.services.storage import LocalAudioStorage
from app.services.upload import UploadService


def create_app(settings=None):
    settings = settings or get_settings()
    database = Database(settings.database_url)
    storage = LocalAudioStorage(settings.upload_dir)

    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        yield
        database.engine.dispose()

    app = FastAPI(title="Voz Local", version="1.0.0", lifespan=lifespan)
    app.state.settings, app.state.database, app.state.storage = settings, database, storage
    app.state.results = ResultService(database, storage)
    app.state.upload = UploadService(database, storage, AudioProcessingService(settings), settings)
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=settings.max_audio_size_mb * 1024 * 1024 + 1024 * 1024
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
        allow_credentials=False,
    )

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {
                "detail": "Campos inválidos. Confira o arquivo, os identificadores e as opções informadas."
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            {"detail": "Falha interna. Tente novamente e consulte o administrador local."},
            status_code=500,
        )

    @app.middleware("http")
    async def private_response(request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method in {"POST", "PATCH", "DELETE"}
            and origin
            and origin not in settings.cors_origins
        ):
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # --- INTEGRATION FOR EXE / PoC ---
    # Servir arquivos estáticos do Angular
    frontend_path = os.path.join(os.getcwd(), "frontend", "dist", "voz-local", "browser")
    if os.path.exists(frontend_path):
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")

        @app.get("/{full_path:path}")
        async def serve_frontend(request: Request, full_path: str):
            # Se a requisição começar com /api, ela já foi tratada pelo router
            if full_path.startswith("api"):
                return

            # Tenta servir o arquivo estático
            file_path = os.path.join(frontend_path, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)

            # Para qualquer outra rota, serve o index.html (Angular SPA)
            return FileResponse(os.path.join(frontend_path, "index.html"))
    # --------------------------------

    app.include_router(router)
    return app


app = create_app()
