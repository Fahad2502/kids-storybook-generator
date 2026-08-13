"""
Image generation service.

Supported backends (configured via IMAGE_MODE in .env):
  infip     - infip.pro, up to 1000 free images/day, ~2-5s per image (default)
  gradio    - HuggingFace Gradio Spaces, free with hourly GPU quota
  inference - HuggingFace Inference API, free monthly credits

Generated images are uploaded to Cloudinary for permanent storage.
"""

import asyncio
import base64
import hashlib
import httpx
from pathlib import Path

from fastapi import HTTPException

from backend.config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    GRADIO_SPACES,
    HUGGINGFACE_API_KEY,
    IMAGE_MODE,
    IMAGES_DIR,
    INFIP_API_KEY,
    USE_FREE_MODE,
    groq_client,
)
from backend.database import get_image_url, save_image_url

if CLOUDINARY_CLOUD_NAME:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )
    print(f"Cloudinary configured: {CLOUDINARY_CLOUD_NAME}")


def _story_seed(story_id) -> int | None:
    if story_id is None:
        return None
    return int(hashlib.md5(str(story_id).encode()).hexdigest()[:8], 16) % 2_147_483_647


def _build_prompt(scene: str, char_name: str, char_desc: str) -> str:
    if char_name and char_desc:
        character_clause = f"The main character {char_name} looks like this: {char_desc}. "
    elif char_name:
        character_clause = f"The main character is a child named {char_name}. "
    else:
        character_clause = ""

    return (
        f"children's picture book illustration: {character_clause}{scene}. "
        "Soft watercolor and gouache style, warm pastel colors, "
        "expressive friendly characters, detailed whimsical background, "
        "storybook art, high quality, vibrant, no text, no words, no letters"
    )


async def _extract_scene(page_text: str) -> str:
    """Use Groq to extract a concise visual description from page text."""
    try:
        if not USE_FREE_MODE and groq_client:
            response = groq_client.chat.completions.create(
                model="gpt-oss-20b",
                messages=[{
                    "role": "user",
                    "content": (
                        "Read this children's story page and write ONE visual scene description "
                        "(max 40 words) for an illustrator. Describe exactly what is visible: "
                        "characters, their actions, the setting, key objects. No narration, just visuals.\n\n"
                        f"Page text:\n{page_text}"
                    ),
                }],
                temperature=0.4,
                max_tokens=80,
            )
            scene = response.choices[0].message.content.strip()
            print(f"Scene extracted: {scene}")
            return scene
    except Exception as exc:
        print(f"Scene extraction failed: {exc}")

    return ". ".join(page_text.replace("\n", " ").split(". ")[:2])


async def _upload_to_cloudinary(image_source: str, story_id, page_num: int) -> str:
    """Upload an image URL or base64 data URI to Cloudinary. Returns the permanent URL."""
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
            ),
        )
        url = result["secure_url"]
        print(f"Cloudinary upload: {url}")
        return url
    except Exception as exc:
        print(f"Cloudinary upload failed, using original source: {exc}")
        return image_source


async def _generate_infip(prompt: str) -> tuple[str, str]:
    """
    Generate via infip.pro.
    Returns (url, 'url'). Retries once on timeout then falls back to HF Inference.
    """
    if not INFIP_API_KEY:
        raise HTTPException(status_code=500, detail="INFIP_API_KEY is not set")

    for attempt in range(2):
        try:
            print(f"infip request (attempt {attempt + 1})")
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    "https://api.infip.pro/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {INFIP_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"model": "img3", "prompt": prompt, "n": 1, "size": "1024x1024", "response_format": "url"},
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=f"infip error {response.status_code}: {response.text[:200]}",
                    )
                img_url = response.json()["data"][0]["url"]
            print("infip success")
            return img_url, "url"
        except httpx.ReadTimeout:
            print(f"infip timeout on attempt {attempt + 1}")
            if attempt == 1:
                print("infip failed twice — falling back to HuggingFace Inference")
                return await _generate_inference(prompt)
        except HTTPException:
            raise


async def _generate_gradio(prompt: str) -> tuple[str, str]:
    """
    Generate via HuggingFace Gradio Spaces.
    Rotates through GRADIO_SPACES and raises 429 on quota exhaustion.
    """
    from gradio_client import Client as GradioClient

    QUOTA_PHRASES = ["gpu quota", "exceeded your gpu", "quota", "rate limit", "too many requests"]
    last_error = None

    for space in GRADIO_SPACES:
        try:
            print(f"Gradio: trying {space}")

            def _call(sp=space):
                gc = GradioClient(sp)
                try:
                    result, _ = gc.predict(
                        prompt=prompt,
                        randomize_seed=True,
                        width=1024,
                        height=1024,
                        num_inference_steps=4,
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
                raw = Path(result[0]).read_bytes()
                img_ext = Path(result[0]).suffix.lstrip(".") or "jpg"
            elif isinstance(result, str):
                raw = Path(result).read_bytes()
                img_ext = Path(result).suffix.lstrip(".") or "jpg"

            if not raw or len(raw) < 1000:
                raise ValueError("Empty or invalid image returned")

            print(f"Gradio success via {space}")
            return base64.b64encode(raw).decode("utf-8"), img_ext

        except Exception as exc:
            last_error = exc
            if any(phrase in str(exc).lower() for phrase in QUOTA_PHRASES):
                print(f"Gradio quota exceeded on {space} — stopping rotation")
                raise HTTPException(
                    status_code=429,
                    detail="Gradio GPU quota exceeded. Try again in ~1 hour.",
                )
            print(f"Gradio {space} failed: {str(exc)[:80]} — trying next space")

    raise HTTPException(
        status_code=502,
        detail=f"All Gradio spaces failed. Last error: {str(last_error)[:150]}",
    )


async def _generate_inference(prompt: str) -> tuple[str, str]:
    """Generate via HuggingFace Inference API (free monthly credits)."""
    if not HUGGINGFACE_API_KEY:
        raise HTTPException(status_code=500, detail="HUGGINGFACE_API_KEY is not set")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            headers={"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"},
            json={"inputs": prompt},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"HuggingFace Inference error {response.status_code}: {response.text[:200]}",
            )

    print("HuggingFace Inference success")
    return base64.b64encode(response.content).decode("utf-8"), "jpg"


async def generate_image(data: dict) -> dict:
    """
    Generate or retrieve a cached illustration for a story page.

    Pipeline:
      1. Check database cache (story_id + page_num key).
      2. Check local disk cache (fallback for older stories).
      3. Extract a visual scene description via Groq.
      4. Generate an image using the configured backend.
      5. Upload to Cloudinary and persist the URL to the database.
    """
    page_text = data.get("text", "")
    story_id  = data.get("story_id")
    page_num  = data.get("page_num", 0)
    char_name = data.get("char_name", "")
    char_desc = data.get("char_desc", "")

    if not page_text:
        raise HTTPException(status_code=400, detail="No page text provided")

    # 1. Database cache
    if story_id and page_num:
        cached_url = get_image_url(story_id, page_num)
        if cached_url:
            print(f"DB cache hit: story {story_id} page {page_num}")
            return {"image": cached_url, "scene_prompt": "cached", "cached": True}

    # 2. Local disk cache
    if story_id and page_num and IMAGES_DIR.exists():
        for ext in ("webp", "png", "jpg"):
            cached_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{ext}"
            if cached_path.exists():
                img_b64 = base64.b64encode(cached_path.read_bytes()).decode("utf-8")
                print(f"Disk cache hit: story {story_id} page {page_num}")
                return {"image": f"data:image/{ext};base64,{img_b64}", "scene_prompt": "cached", "cached": True}

    # 3. Build image prompt
    scene  = await _extract_scene(page_text)
    prompt = _build_prompt(scene, char_name, char_desc)

    print(f"Generating image via: {IMAGE_MODE}")

    # 4. Generate
    if IMAGE_MODE == "infip":
        result, result_type = await _generate_infip(prompt)
    elif IMAGE_MODE == "gradio":
        result, result_type = await _generate_gradio(prompt)
    elif IMAGE_MODE == "inference":
        result, result_type = await _generate_inference(prompt)
    else:
        raise HTTPException(status_code=500, detail=f"Unknown IMAGE_MODE: '{IMAGE_MODE}'")

    # 5. Upload to Cloudinary and persist
    if result_type == "url":
        permanent_url = await _upload_to_cloudinary(result, story_id, page_num)
        if story_id and page_num:
            save_image_url(story_id, page_num, permanent_url)
        return {"image": permanent_url, "scene_prompt": scene, "backend": IMAGE_MODE, "cached": False}

    # Base64 result
    img_b64  = result
    img_ext  = result_type
    data_uri = f"data:image/{img_ext};base64,{img_b64}"

    permanent_url = await _upload_to_cloudinary(data_uri, story_id, page_num)
    if permanent_url != data_uri:
        if story_id and page_num:
            save_image_url(story_id, page_num, permanent_url)
        return {"image": permanent_url, "scene_prompt": scene, "backend": IMAGE_MODE, "cached": False}

    # Cloudinary not configured — save to local disk
    try:
        if story_id and page_num:
            save_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{img_ext}"
            save_path.write_bytes(base64.b64decode(img_b64))
            print(f"Saved locally: {save_path}")
    except Exception as exc:
        print(f"Local save failed: {exc}")

    return {"image": data_uri, "scene_prompt": scene, "backend": IMAGE_MODE, "cached": False}
