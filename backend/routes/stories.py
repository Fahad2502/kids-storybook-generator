"""
Story and favorites CRUD routes.
"""

import json

from fastapi import APIRouter, HTTPException

from backend.config import USE_FREE_MODE
from backend.database import get_conn
from backend.models import StoryRequest, StoryResponse
from backend.story_service import generate_ai_story, generate_free_story

router = APIRouter()


def _parse_story_text(text_data: str) -> dict | str:
    """Attempt to parse stored story JSON. Returns raw value on failure."""
    try:
        return json.loads(text_data) if text_data else {}
    except (json.JSONDecodeError, TypeError):
        return text_data


def _build_preview(data: dict, name: str) -> str:
    first_page = (data.get("pages") or [None])[0]
    if isinstance(first_page, dict):
        return first_page.get("text", "")[:100] + "..."
    return str(first_page or "")[:100] + "..."


@router.post("/generate-story", response_model=StoryResponse)
async def generate_story(request: StoryRequest):
    if USE_FREE_MODE:
        return await generate_free_story(request)
    return await generate_ai_story(request)


@router.get("/stories")
async def get_stories():
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, theme, full_text, date, is_favorite, rating "
                "FROM stories ORDER BY date DESC"
            )
            stories = []
            for story_id, name, theme, text_data, date, is_fav, rating in cursor.fetchall():
                data = _parse_story_text(text_data)
                if isinstance(data, dict):
                    stories.append({
                        "id": story_id,
                        "name": name,
                        "theme": theme,
                        "title": data.get("title", f"Story for {name}"),
                        "date": date,
                        "is_favorite": is_fav == 1,
                        "rating": rating,
                        "preview": _build_preview(data, name),
                        "customCoverNumber": data.get("customCoverNumber"),
                        "isCustomTheme": data.get("isCustomTheme", False),
                    })
                else:
                    stories.append({
                        "id": story_id,
                        "name": name,
                        "theme": theme,
                        "title": f"Story for {name}",
                        "date": date,
                        "is_favorite": is_fav == 1,
                        "rating": rating,
                        "preview": str(data)[:100] + "..." if data else "",
                    })
        finally:
            conn.close()
        return {"stories": stories}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching stories: {exc}")


@router.get("/stories/{story_id}")
async def get_story(story_id: int):
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT full_text, is_favorite, rating FROM stories WHERE id = ?",
                (story_id,),
            )
            result = cursor.fetchone()
        finally:
            conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="Story not found")

        try:
            parsed = json.loads(result[0])
            if not isinstance(parsed, dict):
                raise ValueError("unexpected type")
            story_data = parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            story_data = {
                "title": f"Story #{story_id}",
                "pages": [{"page_number": 1, "text": str(result[0]), "image_prompt": "A story illustration"}],
            }

        story_data["is_favorite"] = result[1] == 1
        story_data["story_id"] = story_id
        story_data["rating"] = result[2]
        return story_data

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching story: {exc}")


@router.post("/stories/{story_id}/favorite")
async def toggle_favorite(story_id: int):
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT is_favorite FROM stories WHERE id = ?", (story_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Story not found")
            new_status = 0 if result[0] == 1 else 1
            cursor.execute(
                "UPDATE stories SET is_favorite = ? WHERE id = ?",
                (new_status, story_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "is_favorite": new_status == 1}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error toggling favorite: {exc}")


@router.get("/favorites")
async def get_favorites():
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, theme, full_text, date FROM stories "
                "WHERE is_favorite = 1 ORDER BY date DESC"
            )
            favorites = []
            for story_id, name, theme, text_data, date in cursor.fetchall():
                data = _parse_story_text(text_data)
                if isinstance(data, dict):
                    favorites.append({
                        "id": story_id,
                        "name": name,
                        "theme": theme,
                        "title": data.get("title", f"Story for {name}"),
                        "dateAdded": date,
                        "customCoverNumber": data.get("customCoverNumber"),
                        "isCustomTheme": data.get("isCustomTheme", False),
                    })
                else:
                    favorites.append({
                        "id": story_id,
                        "name": name,
                        "theme": theme,
                        "title": f"Story for {name}",
                        "dateAdded": date,
                    })
        finally:
            conn.close()
        return {"favorites": favorites}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching favorites: {exc}")


@router.delete("/stories/{story_id}")
async def delete_story(story_id: int):
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Story not found")
            cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "message": "Story deleted successfully", "story_id": story_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error deleting story: {exc}")


@router.post("/stories/{story_id}/update")
async def update_story_cover(story_id: int, data: dict):
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT full_text FROM stories WHERE id = ?", (story_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Story not found")
            story_data = json.loads(result[0])
            story_data["customCoverNumber"] = data.get("customCoverNumber")
            story_data["isCustomTheme"] = data.get("isCustomTheme", False)
            cursor.execute(
                "UPDATE stories SET full_text = ? WHERE id = ?",
                (json.dumps(story_data), story_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error updating story: {exc}")


@router.post("/stories/{story_id}/rate")
async def rate_story(story_id: int, data: dict):
    try:
        rating = int(data.get("rating", 0))
        if not 1 <= rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Story not found")
            cursor.execute("UPDATE stories SET rating = ? WHERE id = ?", (rating, story_id))
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "rating": rating}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
