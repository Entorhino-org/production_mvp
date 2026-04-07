"""
Entorhino — FastAPI application entry point.
Sets up middleware, mounts static files, registers all API routers.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine, Base

# Import all models so they are registered with SQLAlchemy
from app.models import *  # noqa: F401, F403

# Import all API routers
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.admin import router as admin_router
from app.api.topics import router as topics_router
from app.api.tests import router as tests_router
from app.api.attendance import router as attendance_router
from app.api.announcements import router as announcements_router
from app.api.feedback import router as feedback_router
from app.api.alerts import router as alerts_router
from app.api.homework import router as homework_router
from app.api.analytics import router as analytics_router
from app.api.websocket import router as ws_router
from app.api.voice_interview import router as voice_router
from app.api.push import router as push_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure upload directories exist
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR, "topics").mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR, "homework").mkdir(parents=True, exist_ok=True)

    # Initialize Redis
    from app.core.redis import init_redis, close_redis
    await init_redis()

    yield

    await close_redis()
    await engine.dispose()


# ── Create FastAPI app ────────────────────────────────────────

app = FastAPI(
    title="Entorhino",
    description="AI-driven educational platform for student performance monitoring",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Validation error handler (clean 422 messages) ────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        # Extract the first human-readable message
        msg = errors[0].get("msg", "Validation error")
        # Remove "Value error, " prefix that Pydantic adds
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        return JSONResponse(status_code=422, content={"detail": msg})
    return JSONResponse(status_code=422, content={"detail": "Validation error"})

# ── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & templates ─────────────────────────────────

static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

uploads_dir = Path(__file__).parent.parent / settings.UPLOAD_DIR
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# ── Frontend Static Assets (Vite) ───────────────────────────
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount assets folder for JS/CSS/Images
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# ── Register all API routers ─────────────────────────────────

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(topics_router)
app.include_router(tests_router)
app.include_router(attendance_router)
app.include_router(announcements_router)
app.include_router(feedback_router)
app.include_router(alerts_router)
app.include_router(homework_router)
app.include_router(analytics_router)
app.include_router(ws_router)
app.include_router(voice_router)
app.include_router(push_router)


# ── Frontend handlers (Serve React SPA) ──────────────────────

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_frontend(request: Request, full_path: str):
    """
    Catch-all route:
    1. If the path exists in dist (like favicon.svg), serve it.
    2. Otherwise, serve index.html for React Router to handle.
    """
    # Skip API routes so they don't get swallowed by the catch-all
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "API route not found"})

    # Check for direct files in dist (e.g. favicon.svg, icons.svg)
    file_path = frontend_dist / full_path
    if file_path.is_file():
        return FileResponse(file_path)

    # All other paths serve the main index.html (SPA logic)
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    return HTMLResponse("Frontend build not found. Run 'npm run build' in the frontend folder.", status_code=404)


# ── Health check ──────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": "Entorhino", "version": "1.0.0"}
