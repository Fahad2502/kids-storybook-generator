"""
Central configuration module.

Loads environment variables and initialises shared clients.
All other modules should import from here — do not call load_dotenv elsewhere.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Story generation
USE_FREE_MODE: bool = os.getenv("USE_FREE_MODE", "true").lower() == "true"
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

groq_client = None

if not USE_FREE_MODE:
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not set — falling back to template mode.")
        USE_FREE_MODE = True
    else:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)

# Image generation
# Accepted values: infip | gradio | inference
IMAGE_MODE: str = os.getenv("IMAGE_MODE", "infip").lower()

HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
INFIP_API_KEY: str = os.getenv("INFIP_API_KEY", "")

# Cloudinary — permanent image storage
CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

# HuggingFace Gradio spaces, tried in order with fallback to the next on failure.
# Free spaces have hourly GPU quotas; rotation spreads the load.
GRADIO_SPACES: list = [
    "multimodalart/FLUX.1-merged",
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/FLUX.1-dev",
    "evalstate/flux1_schnell",
]

# Storage
DATABASE_PATH: str = "stories.db"
IMAGES_DIR: Path = Path("frontend/img/generated")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
