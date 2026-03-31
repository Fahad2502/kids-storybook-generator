# Code Walkthrough & Security Review
Read this before your viva. Understand every section.

---

## How the App Works — Big Picture

```
Browser (frontend) → FastAPI server (backend) → Groq API (stories) + Infip API (images)
                                              → SQLite database (storage)
                                              → Cloudinary (image storage)
```

User fills form → JS sends POST to /generate-story → backend calls Groq → story saved to DB → returned to browser → browser displays book → user clicks generate images → JS sends POST to /generate-image per page → backend calls Infip → image uploaded to Cloudinary → URL saved to DB → returned to browser

---

## File by File

### app.py — Entry Point
- Creates the FastAPI app
- Registers all routes (misc, stories, images)
- Mounts static files (CSS, JS, images)
- Calls init_database() on startup
- Runs uvicorn server on port 8025 (or $PORT env var for production)

**Security note:** CORS is set to allow all origins ("*") — fine for development, but in production you should restrict this to your actual domain.

---

### backend/config.py — Environment Variables
- Loads .env file using python-dotenv
- Exports all API keys and settings as Python variables
- Every other module imports from here — never from .env directly

**Security note:** API keys are in .env which is gitignored. Good. But if someone gets access to your server, they can read config.py values in memory. This is acceptable for a student project.

---

### backend/database.py — Database Layer
- Supports both SQLite (local) and PostgreSQL (production)
- Detects which to use based on DATABASE_URL environment variable
- Functions: init_database(), save_story(), save_image_url(), get_image_url()

**Security note:** Uses parameterized queries (?, %s) everywhere — this prevents SQL injection attacks. Good practice.

**Potential issue:** No connection pooling. Each request opens and closes a new DB connection. Fine for low traffic, but would be slow under heavy load.

---

### backend/models.py — Data Models
- StoryRequest: validates incoming story generation requests
- StoryPage: represents one page of a story
- StoryResponse: the response format

Pydantic automatically validates types — if someone sends age="hello" it gets rejected automatically.

---

### backend/story_service.py — Story Generation
Two functions:
1. generate_free_story() — uses local templates, no API calls, instant
2. generate_ai_story() — two-step process:
   - Step 1: Sends prompt to Groq (llama-3.3-70b) → gets raw story prose
   - Step 2: Sends prose to Groq (llama-3.1-8b) → formats into JSON pages
   - Step 3: Gets character description for image consistency

The prompt uses a 5-beat narrative arc: Setup → Wrong Choice → Consequence → Realization → Resolution

For custom themes: skips the scenario seed, tells AI to build around the theme freely
For known themes (adventure, fantasy, etc.): picks a random scenario seed from _SCENARIOS dict

**Security note:** The extra_details field (user input) goes directly into the AI prompt. A malicious user could try prompt injection — telling the AI to ignore instructions. The Groq model's safety filters handle most cases, but this is a known limitation.

---

### backend/image_service.py — Image Generation
Flow:
1. Check DB cache — if image already generated for this story+page, return it instantly
2. Check local disk cache — for older stories
3. Extract visual scene from page text using Groq 8B model
4. Build image prompt with character description for consistency
5. Call selected backend (infip/gradio/inference)
6. Upload result to Cloudinary for permanent storage
7. Save Cloudinary URL to database
8. Return URL to browser

Three backends:
- infip: POST to api.infip.pro, returns URL, 1000/day free
- gradio: connects to HuggingFace spaces, slower, quota resets hourly
- inference: HuggingFace Inference API, free monthly credits

**Security note:** No validation on image content — we trust the AI not to generate inappropriate images. Infip has its own content filters.

---

### backend/routes/stories.py — Story CRUD Endpoints
- GET /stories — returns all stories with pagination
- GET /stories/{id} — returns one story
- DELETE /stories/{id} — deletes a story
- POST /stories/{id}/rate — saves rating (1-5)
- POST /stories/{id}/favorite — toggles favorite
- GET /favorites — returns favorited stories

**Security note:** No authentication — anyone who knows the story ID can delete it. This is the biggest security gap. Adding login/auth would fix this.

---

### backend/routes/misc.py — Utility Endpoints
- GET / — serves index.html
- GET /api — health check
- GET /stats — story count, favorites count, themes breakdown
- GET /groq-quota — checks Groq API status

---

### backend/routes/images.py — Image Endpoints
- GET /story-image/{story_id}/{page} — serves cached image from disk (legacy)
- POST /generate-image — main image generation endpoint

---

### frontend/js/script.js — All Frontend Logic (~2600 lines)
Key functions to know:
- handleStoryGeneration() — form submit, calls /generate-story
- displayStoryInView() — renders the book UI
- loadRecentStories() — fetches and displays gallery
- generatePageImage() — calls /generate-image per page
- showToast() — notification system
- selectTheme() — theme card selection
- selectAge() — age button selection
- toggleReadAloud() — TTS controls

**Known issues:**
- All styles are inline — makes the code hard to maintain
- No proper state management — uses global variables
- Console.log statements everywhere — should be removed for production

---

## Security Issues Summary

| Issue | Severity | Fix |
|-------|----------|-----|
| No user authentication | High | Add login/registration |
| Anyone can delete any story | High | Auth + ownership check |
| CORS allows all origins | Medium | Restrict to your domain in production |
| User input goes into AI prompt | Low | Groq filters handle it |
| API keys in .env on server | Low | Use secret manager in production |
| No rate limiting on endpoints | Medium | Add slowapi rate limiter |
| Console.log in production JS | Low | Remove before final deploy |

---

## Questions to Be Ready For

**"How does your narrative arc work?"**
The prompt tells the AI to write exactly 5 beats: Setup (introduce world and problem), Wrong Choice (character makes bad decision), Consequence (things go wrong), Realization (character understands their mistake), Earned Resolution (right choice leads to meaningful reward). This is inspired by classic fable structure.

**"What happens if Groq API is down?"**
The app falls back to USE_FREE_MODE=true which uses local pre-written templates. No API needed.

**"How do you ensure image consistency across pages?"**
We generate a character description once per story using the 8B model (hair color, eye color, outfit, skin tone — max 25 words). This description is passed to every image generation call so the same character appears on every page.

**"What database do you use and why?"**
SQLite locally because it requires zero setup — just a file. PostgreSQL in production because SQLite doesn't handle concurrent writes well. The code detects which to use based on the DATABASE_URL environment variable.

**"How does the caching work?"**
Two levels: DB cache (story_images table stores Cloudinary URLs — checked first on every request) and disk cache (local files in frontend/img/generated — fallback for older stories). Once an image is generated it's never regenerated, saving API quota.
