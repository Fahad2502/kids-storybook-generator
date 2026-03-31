"""
routes/misc.py — Health check, stats, and Groq quota endpoints
"""
import httpx
from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.config import USE_FREE_MODE, GROQ_API_KEY, IMAGE_MODE, groq_client
from backend.database import get_conn

router = APIRouter()


@router.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")


@router.get("/api")
async def api_root():
    mode = "FREE (No API costs)" if USE_FREE_MODE else "AI-Powered (Groq llama-3.3-70b)"
    return {"message": "Kids Story Generator API is running!", "mode": mode, "image_mode": IMAGE_MODE}


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
    """Check remaining Groq API quota by making a minimal 1-token call."""
    if USE_FREE_MODE or not groq_client:
        return {"mode": "FREE", "message": "Groq API not active (USE_FREE_MODE=true)"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile",
                      "messages": [{"role": "user", "content": "hi"}],
                      "max_tokens": 1},
            )
        h = dict(r.headers)
        return {
            "status":             r.status_code,
            "requests_limit":     h.get("x-ratelimit-limit-requests"),
            "requests_remaining": h.get("x-ratelimit-remaining-requests"),
            "requests_reset":     h.get("x-ratelimit-reset-requests"),
            "tokens_limit":       h.get("x-ratelimit-limit-tokens"),
            "tokens_remaining":   h.get("x-ratelimit-remaining-tokens"),
            "tokens_reset":       h.get("x-ratelimit-reset-tokens"),
            "message": "API key valid" if r.status_code == 200 else f"Status: {r.status_code}",
        }
    except Exception as e:
        return {"error": str(e)}
