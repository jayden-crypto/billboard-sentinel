
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .routers import reports, registry, review, stats
app = FastAPI(title="Billboard Sentinel - Complete", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
# Serve uploaded images
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
app.mount("/api/uploads", StaticFiles(directory=uploads_dir), name="uploads")
init_db()
app.include_router(reports.router, prefix="/api")
app.include_router(registry.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
@app.get("/health")
def health(): return {"ok": True}
