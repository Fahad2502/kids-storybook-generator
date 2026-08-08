"""
FastAPI application entry point.

Local:      python -X utf8 app.py
Production: uvicorn app:app --host 0.0.0.0 --port $PORT --workers 4
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import USE_FREE_MODE, IMAGE_MODE
from backend.database import init_database
from backend.routes import misc, stories, images, auth as auth_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    story_mode = "template" if USE_FREE_MODE else "groq/llama-3.3-70b"
    port = os.getenv("PORT", "8025")
    print(f"Kids Story Generator running on http://localhost:{port}")
    print(f"Story mode: {story_mode} | Image mode: {IMAGE_MODE}")
    yield


app = FastAPI(title="Kids Story Generator", version="3.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOWED_ORIGINS == "*" else ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js",  StaticFiles(directory="frontend/js"),  name="js")
app.mount("/img", StaticFiles(directory="frontend/img"), name="img")

app.include_router(misc.router)
app.include_router(stories.router)
app.include_router(images.router)
app.include_router(auth_routes.router)


if __name__ == "__main__":
    import uvicorn
    sys.stdout.reconfigure(encoding="utf-8")
    port = int(os.getenv("PORT", "8025"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
        workers=1,
    )
