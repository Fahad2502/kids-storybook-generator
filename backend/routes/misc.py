"""
Miscellaneous routes — health check, stats, Groq quota.
"""

import httpx
from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.config import GROQ_API_KEY, IMAGE_MODE, USE_FREE_MODE, groq_client
from backend.database import get_conn

router = APIRouter()


@router.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")


@router.get("/api")
async def api_root():
    mode = "template" if USE_FREE_MODE else "groq/llama-3.3-70b"
    return {"status": "ok", "story_mode": mode, "image_mode": IMAGE_MODE}


@router.get("/stats")
async def get_stats():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stories")
        total_stories = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stories WHERE is_favorite = 1")
        total_favorites = cursor.fetchone()[0]
    finally:
        conn.close()
    return {"total_stories": total_stories, "total_favorites": total_favorites}


@router.get("/groq-quota")
async def check_groq_quota():
    """Check remaining Groq API quota via a minimal single-token request."""
    if USE_FREE_MODE or not groq_client:
        return {"mode": "template", "message": "Groq API is not active"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )
        headers = dict(response.headers)
        return {
            "status": response.status_code,
            "requests_limit": headers.get("x-ratelimit-limit-requests"),
            "requests_remaining": headers.get("x-ratelimit-remaining-requests"),
            "requests_reset": headers.get("x-ratelimit-reset-requests"),
            "tokens_limit": headers.get("x-ratelimit-limit-tokens"),
            "tokens_remaining": headers.get("x-ratelimit-remaining-tokens"),
            "tokens_reset": headers.get("x-ratelimit-reset-tokens"),
            "message": "API key valid" if response.status_code == 200 else f"Status: {response.status_code}",
        }
    except Exception as exc:
        return {"error": str(exc)}
