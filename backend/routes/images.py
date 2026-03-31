"""
routes/images.py — Image generation and serving endpoints
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import IMAGES_DIR
from backend.image_service import generate_image as _generate_image

router = APIRouter()


@router.get("/story-image/{story_id}/{page}")
async def serve_story_image(story_id: int, page: int):
    """Serve a cached story page image from disk."""
    for ext in ("webp", "png", "jpg"):
        path = IMAGES_DIR / f"{story_id}_page_{page}.{ext}"
        if path.exists():
            return FileResponse(str(path), media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="Image not found")


@router.post("/generate-image")
async def generate_image(data: dict):
    """Generate an image for a story page (with disk cache + character consistency)."""
    return await _generate_image(data)
