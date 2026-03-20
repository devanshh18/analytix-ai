"""
Analytix AI — FastAPI Application Entry Point.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.upload import router as upload_router
from routes.dashboard import router as dashboard_router
from routes.chat import router as chat_router
from routes.export import router as export_router

# ─── App Configuration ───────────────────────────────
app = FastAPI(
    title="Analytix AI",
    description="AI-Powered Data Analytics Platform — Upload datasets, auto-generate dashboards, extract insights, and chat with your data.",
    version=os.getenv("APP_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# ─── Routers ─────────────────────────────────────────
app.include_router(upload_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(export_router)


# ─── Frontend Serving (Production) ──────────────────────
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    # Mount the /assets directory explicitly
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow API, docs, and openapi.json to pass through
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Endpoint not found")
            
        # Check if the exact file exists (e.g., vite.svg, favicon.ico)
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
            
        # Fallback to index.html for React Router
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": "Analytix AI API Server",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "status": "running locally without built frontend",
            "docs": "/docs",
        }


@app.get("/health")
async def health():
    return {"status": "healthy"}
