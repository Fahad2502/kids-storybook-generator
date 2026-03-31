"""
image_service.py — Image generation backends:
  gradio     — free HF spaces, rotates through multiple if one fails (default)
  together   — Together AI free tier, FLUX.1-schnell (3 months free, needs TOGETHER_API_KEY)
  inference  — HuggingFace Inference API (monthly credits)
"""
import asyncio
import base64
import hashlib
import httpx
from pathlib import Path
from fastapi import HTTPException

from backend.config import (
    USE_FREE_MODE, groq_client,
    IMAGE_MODE, HUGGINGFACE_API_KEY, INFIP_API_KEY,
    IMAGES_DIR, GRADIO_SPACES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _story_seed(story_id) -> int | None:
    if story_id is None:
        return None
    return int(hashlib.md5(str(story_id).encode()).hexdigest()[:8], 16) % 2_147_483_647


def _build_prompt(scene: str, char_name: str, char_desc: str) -> str:
    char_part = ""
    if char_name and char_desc:
        char_part = f"The main character {char_name} looks like this in every scene: {char_desc}. "
    elif char_name:
        char_part = f"The main character is a child named {char_name}. "
    return (
        f"children's picture book illustration: {char_part}{scene}. "
        "Soft watercolor and gouache style, warm pastel colors, "
        "expressive friendly characters, detailed whimsical background, "
        "storybook art, high quality, vibrant, no text, no words, no letters"
    )


async def _extract_scene(page_text: str) -> str:
    """Use Groq (cheap 8b model) to pull a tight visual scene from page text."""
    try:
        if not USE_FREE_MODE and groq_client:
            resp = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": (
                    "Read this children's story page and write ONE visual scene description "
                    "(max 40 words) for an illustrator. Describe exactly what is visible: "
                    "characters, their actions, the setting, key objects. No narration, just visuals.\n\n"
                    f"Page text:\n{page_text}"
                )}],
                temperature=0.4,
                max_tokens=80,
            )
            scene = resp.choices[0].message.content.strip()
            print(f"🎨 Scene prompt: {scene}")
            return scene
    except Exception as e:
        print(f"⚠️ Scene extract failed: {e}")
    return ". ".join(page_text.replace("\n", " ").split(". ")[:2])




async def _generate_gradio(prompt: str) -> tuple[str, str]:
    """
    Rotate through multiple free HuggingFace Gradio spaces.
    Tries each in order — stops immediately on quota errors (no point retrying).
    """
    from gradio_client import Client as GradioClient

    # Errors that mean "quota hit" — no point trying other spaces right now
    QUOTA_PHRASES = ["gpu quota", "exceeded your gpu", "quota", "rate limit", "too many requests"]

    last_error = None
    for space in GRADIO_SPACES:
        try:
            print(f"🤗 Trying Gradio space: {space}")

            def _call(sp=space):
                gc = GradioClient(sp)
                try:
                    result, _ = gc.predict(
                        prompt=prompt, randomize_seed=True,
                        width=1024, height=1024, num_inference_steps=4,
                        api_name="/infer",
                    )
                except Exception:
                    result = gc.predict(prompt, api_name="/infer")
                    if isinstance(result, (list, tuple)):
                        result = result[0]
                return result

            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _call),
                timeout=60,
            )

            raw = None
            img_ext = "jpg"
            if isinstance(result, dict):
                url  = result.get("url")
                path = result.get("path")
                if url and url.startswith("data:"):
                    raw = base64.b64decode(url.split(",", 1)[1])
                elif url:
                    async with httpx.AsyncClient(timeout=30) as hc:
                        raw = (await hc.get(url)).content
                elif path:
                    raw = Path(path).read_bytes()
                    img_ext = Path(path).suffix.lstrip(".") or "jpg"
            elif isinstance(result, (list, tuple)):
                file_path = result[0]
                raw = Path(file_path).read_bytes()
                img_ext = Path(file_path).suffix.lstrip(".") or "jpg"
            elif isinstance(result, str):
                raw = Path(result).read_bytes()
                img_ext = Path(result).suffix.lstrip(".") or "jpg"

            if not raw or len(raw) < 1000:
                raise ValueError("Empty image returned")

            print(f"✅ Gradio success via {space}")
            return base64.b64encode(raw).decode("utf-8"), img_ext

        except Exception as e:
            last_error = e
            err_str = str(e).lower()

            # If it's a quota/rate-limit error, no point trying other spaces
            if any(phrase in err_str for phrase in QUOTA_PHRASES):
                print(f"⛔ Gradio quota hit on {space} — all spaces likely rate-limited. Stopping.")
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Gradio GPU quota exceeded on all spaces. "
                        f"Quotas reset hourly — try again in ~1 hour, "
                        f"or switch IMAGE_MODE to 'together' or 'inference' in .env"
                    )
                )

            print(f"⚠️ Gradio space {space} failed: {str(e)[:80]} — trying next...")
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All Gradio spaces failed. Last error: {str(last_error)[:150]}"
    )


async def _generate_inference(prompt: str) -> tuple[str, str]:
    """HuggingFace Inference API — uses monthly free credits."""
    if not HUGGINGFACE_API_KEY:
        raise HTTPException(status_code=500, detail="HUGGINGFACE_API_KEY not set in .env")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
            headers={"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"},
            json={"inputs": prompt},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502,
                                detail=f"HF Inference error {r.status_code}: {r.text[:200]}")
    print("✅ HF Inference success")
    return base64.b64encode(r.content).decode("utf-8"), "jpg"


async def _generate_infip(prompt: str) -> tuple[str, str]:
    """
    Ghostbot/infip.pro -- free tier: 1000 images/day, 30 req/min.
    Returns (image_url, "url") so we don't need to download/store the image.
    """
    if not INFIP_API_KEY:
        raise HTTPException(status_code=500,
                            detail="INFIP_API_KEY not set in .env -- get free key at infip.pro")
    print("Infip request (img3)...")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.infip.pro/v1/images/generations",
            headers={"Authorization": f"Bearer {INFIP_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "img3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "url",
            },
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502,
                                detail=f"Infip error {r.status_code}: {r.text[:200]}")
        data = r.json()
        img_url = data["data"][0]["url"]

    print(f"Infip success: {img_url}")
    return img_url, "url"




# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_image(data: dict) -> dict:
    """
    1. Check disk cache (local only).
    2. Extract visual scene via Groq.
    3. Call selected backend.
    4. Save to disk if local, return URL if production.
    """
    page_text = data.get("text", "")
    story_id  = data.get("story_id")
    page_num  = data.get("page_num", 0)
    char_name = data.get("char_name", "")
    char_desc = data.get("char_desc", "")

    if not page_text:
        raise HTTPException(status_code=400, detail="No text provided")

    # 1. Disk cache (only works locally)
    if story_id and page_num and IMAGES_DIR.exists():
        for ext in ("webp", "png", "jpg"):
            cached = IMAGES_DIR / f"{story_id}_page_{page_num}.{ext}"
            if cached.exists():
                img_b64 = base64.b64encode(cached.read_bytes()).decode("utf-8")
                print(f"Cache hit: story {story_id} page {page_num}")
                return {"image": f"data:image/{ext};base64,{img_b64}",
                        "scene_prompt": "cached", "cached": True}

    # 2. Scene + prompt
    scene  = await _extract_scene(page_text)
    prompt = _build_prompt(scene, char_name, char_desc)
    seed   = _story_seed(story_id)

    print(f"Image mode: {IMAGE_MODE}")

    # 3. Generate
    if IMAGE_MODE == "infip":
        result, result_type = await _generate_infip(prompt)
    elif IMAGE_MODE == "gradio":
        result, result_type = await _generate_gradio(prompt)
    elif IMAGE_MODE == "inference":
        result, result_type = await _generate_inference(prompt)
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown IMAGE_MODE '{IMAGE_MODE}'. Use: infip, gradio, or inference"
        )

    # 4. If result is a URL (infip), return it directly — no disk needed
    if result_type == "url":
        return {"image": result, "scene_prompt": scene,
                "backend": IMAGE_MODE, "cached": False}

    # 5. If result is base64, save to disk locally
    img_b64 = result
    img_ext = result_type
    try:
        if story_id and page_num:
            save_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{img_ext}"
            save_path.write_bytes(base64.b64decode(img_b64))
            print(f"Saved: {save_path}")
    except Exception as e:
        print(f"Disk save skipped: {e}")

    return {"image": f"data:image/{img_ext};base64,{img_b64}",
            "scene_prompt": scene, "backend": IMAGE_MODE, "cached": False}
