from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.core.config import settings, DATABASE_URL, get_settings
from app.db.session import engine, Base
from app.api import learners, sessions, insights, progress, health, levels


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run migrations (skip in test mode)
    settings = get_settings()
    if settings.env != "test":
        from alembic.config import Config
        from alembic import command
        from app.db.session import get_migration_engine

        try:
            alembic_cfg = Config("backend/alembic.ini")
            migration_engine = get_migration_engine()
            alembic_cfg.attributes["connection"] = migration_engine.connect()
            command.upgrade(alembic_cfg, "head")
        except Exception as e:
            print(f"Migration warning: {e}")

    yield
    # Shutdown
    engine.dispose()


app = FastAPI(
    title="MisconceptionMap API",
    description="Educational diagnostic API for algebra misconceptions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [o.strip() for o in settings.allowed_origins.split(",")]
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
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:;"
    return response


# API routes
app.include_router(health.router, prefix="/api")
app.include_router(learners.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(levels.router, prefix="/api")

# Serve static files (built frontend)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes are handled above, this catches all other routes for SPA fallback
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not built"}

else:
    @app.get("/")
    async def root():
        return {"message": "MisconceptionMap API", "docs": "/api/docs"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)