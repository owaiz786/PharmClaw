"""
PharmaClaw — AI-Driven Pharmacy Inventory Management
FastAPI app entry point.

Run: uvicorn main:app --reload --port 8000
"""

import os
import sys

# Ensure app directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env from project root or app directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from db.models import init_db
from db.seed import seed
from api.routes import router

app = FastAPI(
    title="PharmaClaw — Pharmacy Inventory API",
    description="AI-driven pharmacy inventory management built on OpenClaw",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    seed()
    print("✅ PharmaClaw ready at http://localhost:8000")


# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# API routes under /api
app.include_router(router, prefix="/api")


# Serve the SPA index for all other routes
@app.get("/")
@app.get("/{path:path}")
def spa(path: str = ""):
    index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(index)
