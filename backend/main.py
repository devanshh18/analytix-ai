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

# ─── Routers ─────────────────────────────────────────
app.include_router(upload_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(export_router)


# ─── Root ────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "app": "Analytix AI",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
