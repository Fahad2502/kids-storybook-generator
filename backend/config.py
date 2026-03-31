"""
config.py — environment variables, shared paths, Groq client
All other modules import from here. Never import dotenv elsewhere.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Story mode ────────────────────────────────────────────────────────────────
USE_FREE_MODE: bool = os.getenv("USE_FREE_MODE", "true").lower() == "true"
GROQ_API_KEY:  str  = os.getenv("GROQ_API_KEY", "")

groq_client = None

if not USE_FREE_MODE:
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not found — falling back to FREE mode.")
        USE_FREE_MODE = True
    else:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)

# ── Image mode ────────────────────────────────────────────────────────────────
# Set IMAGE_MODE in .env: infip | gradio | inference
IMAGE_MODE: str = os.getenv("IMAGE_MODE", "infip").lower()

HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
INFIP_API_KEY:       str = os.getenv("INFIP_API_KEY", "")

# Multiple Gradio spaces — rotated in order, falls back to next if one fails
# Note: free spaces have GPU quotas that reset hourly — rotation helps spread load
GRADIO_SPACES: list = [
    "multimodalart/FLUX.1-merged",        # confirmed working
    "black-forest-labs/FLUX.1-schnell",   # official BFL schnell (quota resets hourly)
    "black-forest-labs/FLUX.1-dev",       # official BFL dev (quota resets hourly)
    "evalstate/flux1_schnell",            # community mirror
]

# ── Storage ───────────────────────────────────────────────────────────────────
DATABASE_PATH: str  = "stories.db"
IMAGES_DIR:    Path = Path("frontend/img/generated")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
