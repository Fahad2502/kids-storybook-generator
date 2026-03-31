# Kids Story Generator

An AI-powered children's story generator that creates personalized picture books with illustrations and text-to-speech narration.

## What It Does

- Generates unique children's stories using **Llama 3.3 70B** (via Groq API) with a real narrative arc — setup, wrong choice, consequence, realization, resolution
- Creates per-page illustrations using **FLUX.1** image models
- Reads stories aloud with **Web Speech API** TTS with voice/speed controls
- Saves stories to a gallery with search, filter, favorites, and ratings
- Supports 6 built-in themes + custom themes with extra story details

## AI/DS Contribution

- Fine-tuned **GPT-2** on 50,000 children's stories from the TinyStories dataset
- Achieved perplexity of **3.68** vs base GPT-2's **10.44** — a **2.8x improvement**
- Evaluated story readability using Flesch-Kincaid metrics — **100% age-appropriate** across test stories
- Two-model architecture: fine-tuned GPT-2 for research, Llama 3.3 70B for production

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| LLM | Groq API — Llama 3.3 70B |
| Image Generation | infip.pro (FLUX) + Cloudinary storage |
| Database | SQLite (local) / PostgreSQL (production) |
| Frontend | Vanilla HTML/CSS/JS |
| TTS | Web Speech API |
| Fine-tuning | HuggingFace Transformers + TinyStories dataset |

## Project Structure

```
kids-story-generator/
├── app.py                    # FastAPI entry point
├── backend/
│   ├── config.py             # Environment variables
│   ├── database.py           # SQLite/PostgreSQL support
│   ├── story_service.py      # Story generation logic
│   ├── image_service.py      # Image generation + Cloudinary
│   ├── models.py             # Pydantic models
│   ├── templates.py          # Free-mode story templates
│   └── routes/               # API endpoints
├── frontend/
│   ├── index.html            # Single page app
│   ├── css/style.css
│   └── js/script.js
├── tinystories-gpt2-final/   # Fine-tuned GPT-2 model
├── demo_our_model.py         # GPT-2 demo script
├── evaluate_stories.py       # Readability evaluation
└── seed_gallery.py           # Gallery population script
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in your API keys in .env

# Run locally
start.bat          # Windows
# or
python app.py
```

Open `http://localhost:8025`

## Environment Variables

```
GROQ_API_KEY          # Groq API key for story generation
USE_FREE_MODE         # true = templates, false = AI stories
IMAGE_MODE            # infip | gradio | inference
INFIP_API_KEY         # infip.pro API key (1000 free/day)
HUGGINGFACE_API_KEY   # HuggingFace token
CLOUDINARY_CLOUD_NAME # Cloudinary for permanent image storage
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
DATABASE_URL          # PostgreSQL URL (production only)
```

## Research Results

| Metric | Base GPT-2 | Fine-tuned GPT-2 |
|--------|-----------|-----------------|
| Perplexity | 10.44 | 3.68 |
| Improvement | — | 2.8x better |
| Child-safe content | No | Yes |
| Story structure | None | Basic arc |

| Story | Target Age | FK Grade | Reading Ease | Age-Appropriate |
|-------|-----------|----------|-------------|----------------|
| Ali and the Forbidden Cave | 6 | 1.9 | 97.7 | YES |
| Sara and the Baby Bird | 7 | 3.1 | 92.1 | YES |
| Omar and the Magic Lamp | 9 | 4.5 | 81.4 | YES |
| Zara and the Coral Reef | 8 | 4.4 | 82.0 | YES |
| Hamza and the Shooting Star | 10 | 6.2 | 70.3 | YES |

## Final Year Project

BE — Artificial Intelligence & Data Science, 2025
