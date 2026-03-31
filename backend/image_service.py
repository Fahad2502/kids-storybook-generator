"""
image_service.py -- Image generation backends:
  infip     -- Ghostbot/infip.pro, 1000 free/day, fast 2-5s (default)
  gradio    -- HuggingFace Spaces, free, slower
  inference -- HuggingFace Inference API, free monthly credits
Images are uploaded to Cloudinary for permanent storage.
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
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
    IMAGES_DIR, GRADIO_SPACES,
)
from backend.database import save_image_url, get_image_url

# Configure Cloudinary if credentials are set
if CLOUDINARY_CLOUD_NAME:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )
    print(f"Cloudinary configured: {CLOUDINARY_CLOUD_NAME}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _story_seed(story_id) -> int | None:
    if story_id is None:
        return None
    return int(hashlib.md5(str(story_id).encode()).hexdigest()[:8], 16) % 2_147_483_647


def _build_prompt(scene: str, char_name: str, char_desc: str) -> str:
    char_part = ""
    if char_name and char_desc:
        char_part = f"The main character {char_name} looks like this: {char_desc}. "
    elif char_name:
        char_part = f"The main character is a child named {char_name}. "
    return (
        f"children's picture book illustration: {char_part}{scene}. "
        "Soft watercolor and gouache style, warm pastel colors, "
        "expressive friendly characters, detailed whimsical background, "
        "storybook art, high quality, vibrant, no text, no words, no letters"
    )


async def _extract_scene(page_text: str) -> str:
    """Use Groq to pull a tight visual scene from page text."""
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
            print(f"Scene: {scene}")
            return scene
    except Exception as e:
        print(f"Scene extract failed: {e}")
    return ". ".join(page_text.replace("\n", " ").split(". ")[:2])


# ── Cloudinary upload ─────────────────────────────────────────────────────────

async def _upload_to_cloudinary(image_source: str, story_id, page_num: int) -> str:
    """Upload image URL or base64 to Cloudinary. Returns permanent URL."""
    if not CLOUDINARY_CLOUD_NAME:
        return image_source
    try:
        import cloudinary.uploader
        public_id = f"kids_story/{story_id}_page_{page_num}"
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cloudinary.uploader.upload(
                image_source,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            )
        )
        url = result["secure_url"]
        print(f"Cloudinary: {url}")
        return url
    except Exception as e:
        print(f"Cloudinary upload failed, using original: {e}")
        return image_source


# ── Backends ──────────────────────────────────────────────────────────────────

async def _generate_infip(prompt: str) -> tuple[str, str]:
    """Ghostbot/infip.pro -- 1000 free images/day, fast 2-5s."""
    if not INFIP_API_KEY:
        raise HTTPException(status_code=500,
                            detail="INFIP_API_KEY not set in .env")
    print("Infip request...")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.infip.pro/v1/images/generations",
            headers={"Authorization": f"Bearer {INFIP_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "img3", "prompt": prompt, "n": 1,
                  "size": "1024x1024", "response_format": "url"},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502,
                                detail=f"Infip error {r.status_code}: {r.text[:200]}")
        img_url = r.json()["data"][0]["url"]
    print(f"Infip success")
    return img_url, "url"


async def _generate_gradio(prompt: str) -> tuple[str, str]:
    """Rotate through HuggingFace Gradio spaces."""
    from gradio_client import Client as GradioClient

    QUOTA_PHRASES = ["gpu quota", "exceeded your gpu", "quota", "rate limit", "too many requests"]
    last_error = None

    for space in GRADIO_SPACES:
        try:
            print(f"Gradio: {space}")

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
                url = result.get("url")
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

            print(f"Gradio success via {space}")
            return base64.b64encode(raw).decode("utf-8"), img_ext

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if any(phrase in err_str for phrase in QUOTA_PHRASES):
                print(f"Gradio quota hit on {space} -- stopping.")
                raise HTTPException(status_code=429,
                                    detail="Gradio GPU quota exceeded. Try again in ~1 hour.")
            print(f"Gradio {space} failed: {str(e)[:80]} -- trying next...")
            continue

    raise HTTPException(status_code=502,
                        detail=f"All Gradio spaces failed. Last: {str(last_error)[:150]}")


async def _generate_inference(prompt: str) -> tuple[str, str]:
    """HuggingFace Inference API -- free monthly credits."""
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
    print("HF Inference success")
    return base64.b64encode(r.content).decode("utf-8"), "jpg"


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_image(data: dict) -> dict:
    """
    1. Check disk cache (local only).
    2. Extract visual scene via Groq.
    3. Generate image via selected backend.
    4. Upload to Cloudinary for permanent storage.
    """
    page_text = data.get("text", "")
    story_id  = data.get("story_id")
    page_num  = data.get("page_num", 0)
    char_name = data.get("char_name", "")
    char_desc = data.get("char_desc", "")

    if not page_text:
        raise HTTPException(status_code=400, detail="No text provided")

    # 1. Check DB cache first (works both locally and on production)
    if story_id and page_num:
        cached_url = get_image_url(story_id, page_num)
        if cached_url:
            print(f"DB cache hit: story {story_id} page {page_num}")
            return {"image": cached_url, "scene_prompt": "cached", "cached": True}

    # 2. Check local disk cache (fallback for older stories)
    if story_id and page_num and IMAGES_DIR.exists():
        for ext in ("webp", "png", "jpg"):
            cached = IMAGES_DIR / f"{story_id}_page_{page_num}.{ext}"
            if cached.exists():
                img_b64 = base64.b64encode(cached.read_bytes()).decode("utf-8")
                print(f"Disk cache hit: story {story_id} page {page_num}")
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
        raise HTTPException(status_code=500,
                            detail=f"Unknown IMAGE_MODE '{IMAGE_MODE}'")

    # 4. Upload to Cloudinary for permanent storage, then save URL to DB
    if result_type == "url":
        permanent = await _upload_to_cloudinary(result, story_id, page_num)
        if story_id and page_num:
            save_image_url(story_id, page_num, permanent)
        return {"image": permanent, "scene_prompt": scene,
                "backend": IMAGE_MODE, "cached": False}
    else:
        img_b64 = result
        img_ext = result_type
        data_uri = f"data:image/{img_ext};base64,{img_b64}"
        permanent = await _upload_to_cloudinary(data_uri, story_id, page_num)
        if permanent != data_uri:
            if story_id and page_num:
                save_image_url(story_id, page_num, permanent)
            return {"image": permanent, "scene_prompt": scene,
                    "backend": IMAGE_MODE, "cached": False}
        # No Cloudinary -- save locally
        try:
            if story_id and page_num:
                save_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{img_ext}"
                save_path.write_bytes(base64.b64decode(img_b64))
                print(f"Saved locally: {save_path}")
        except Exception as e:
            print(f"Local save failed: {e}")
        return {"image": data_uri, "scene_prompt": scene,
                "backend": IMAGE_MODE, "cached": False}
