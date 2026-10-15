from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings, DATABASE_URL, get_settings
from app.db.session import engine, Base
from app.api import learners, sessions, insights, progress, health, levels


# Application lifespan: run database migrations on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = get_settings()

    if app_settings.env != "test":
        try:
            from alembic.config import Config
            from alembic import command

            # Docker: /app/alembic.ini
            # Local: backend/alembic.ini
            ini_path = (
                "alembic.ini"
                if Path("alembic.ini").exists()
                else "backend/alembic.ini"
            )

            alembic_cfg = Config(ini_path)
            command.upgrade(alembic_cfg, "head")

        except Exception as e:
            print(f"Migration warning: {e}")

    yield

    engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="MisconceptionMap API",
    description="Educational diagnostic API for algebra misconceptions",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS configuration
allowed_origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "img-src 'self' data:;"
    )

    return response


# API routes
app.include_router(health.router, prefix="/api")
app.include_router(learners.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(levels.router, prefix="/api")


# Serve static files (built frontend)
# Docker: /app/static
# Local: frontend/dist
_candidates = [
    Path("/app/static"),
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "static",
]

frontend_dist = next(
    (path for path in _candidates if path.exists()),
    None,
)

if frontend_dist is not None:
    assets_dir = frontend_dist / "assets"

    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="assets",
        )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_file = frontend_dist / "index.html"

        if index_file.exists():
            return FileResponse(str(index_file))

        return {"error": "Frontend index missing"}

else:

    @app.get("/")
    async def root():
        return {
            "message": "MisconceptionMap API",
            "docs": "/api/docs",
        }


# Run application directly
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
    )
