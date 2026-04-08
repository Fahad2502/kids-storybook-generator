# Research Paper Context — Kids Story Generator
# Use this as a prompt for any AI to help write your research paper

---

## PROJECT OVERVIEW

**Title:** Kids Story Generator — An AI-Powered Personalized Children's Story Generation System with Multi-Modal Output

**Degree:** BE in Artificial Intelligence & Data Science

**Year:** 2025

**One-line summary:** A full-stack web application that uses large language models, fine-tuned GPT-2, and AI image generation to create personalized, illustrated children's picture books with text-to-speech narration.

---

## PROBLEM STATEMENT

Traditional children's books are static, generic, and not personalized. Parents cannot easily create stories featuring their child's name, age, and interests. Existing AI tools (ChatGPT, etc.) can generate text but do not provide:
- Age-appropriate language calibration
- Consistent character illustration across pages
- Integrated text-to-speech narration
- A complete end-to-end picture book experience
- Domain-specific fine-tuned models for children's content

---

## SYSTEM ARCHITECTURE

### Frontend
- Pure HTML5, CSS3, Vanilla JavaScript (Single Page Application)
- Book-flip UI with CSS 3D transforms simulating a real picture book
- Web Speech API for text-to-speech with voice selection, speed control
- Toast notification system, skeleton loaders, fade transitions
- Responsive design with dark theme

### Backend
- FastAPI (Python) REST API
- SQLite (local development) / PostgreSQL (production)
- JWT-based authentication (python-jose, passlib/bcrypt)
- Cloudinary for permanent image storage
- Environment-based configuration (.env)

### Deployment
- GitHub for version control
- Koyeb for cloud hosting
- PostgreSQL cloud database
- Cloudinary CDN for images

---

## AI/ML COMPONENTS

### 1. Story Generation (Production)
- **Model:** Llama 3.3 70B via Groq API
- **Approach:** Two-step generation
  - Step 1: Generate rich prose story using a structured 5-beat narrative prompt
  - Step 2: Format prose into JSON pages using a formatter model (Llama 3.1 8B)
- **Narrative Structure:** Setup → Wrong Choice → Consequence → Realization → Earned Resolution (inspired by classic fables like the Woodcutter and the Golden Axe)
- **Story Type Inference:** System detects story type (mystery, adventure, funny, spooky, friendship, fantasy) from theme and user description using keyword matching
- **Multi-character support:** Comma-separated names (e.g., "Ali, Sara") are parsed into two separate characters
- **Age adaptation:** Vocabulary complexity adapts to target age (2-12 years)
- **Custom themes:** When theme is not in known list, AI generates freely without scenario seed

### 2. Fine-tuned GPT-2 (Research Component)
- **Base model:** GPT-2 Small (117M parameters)
- **Dataset:** TinyStories (roneneldan/TinyStories) — 2.1 million children's stories
- **Training:** 50,000 samples, 2 epochs, Google Colab T4 GPU, fp16 precision
- **Framework:** HuggingFace Transformers, Trainer API
- **Results:**
  - Base GPT-2 perplexity: 10.44
  - Fine-tuned GPT-2 perplexity: 3.68
  - Improvement: 2.8x better on children's story domain
- **Qualitative finding:** Base GPT-2 generates adult/random content; fine-tuned model stays child-appropriate with simple vocabulary and story structure
- **Purpose:** Research contribution demonstrating domain-specific fine-tuning improves children's content generation; informs the decision to use a larger model for production

### 3. Image Generation
- **Primary:** Infip.pro API (FLUX.1 model) — 1000 free images/day, ~2-5 seconds
- **Fallback 1:** HuggingFace Gradio spaces (multimodalart/FLUX.1-merged) — free, ~30-45s
- **Fallback 2:** HuggingFace Inference API — free monthly credits
- **Scene extraction:** Llama 3.1 8B extracts a 40-word visual scene description per page
- **Character consistency:** A single character description (hair, eyes, skin, outfit) is generated once per story and passed to every image generation call
- **Caching:** Generated image URLs stored in database — same page never regenerated twice
- **Storage:** All images uploaded to Cloudinary for permanent CDN storage

### 4. Readability Evaluation
- **Metric:** Flesch-Kincaid Grade Level and Reading Ease Score
- **Library:** textstat (Python)
- **Results across 5 test stories:**
  - Average FK Grade Level: 4.0 (target: ~4-5 for ages 6-10)
  - Average Reading Ease: 84.7 (70-80 = easy, 80+ = very easy)
  - Age-Appropriate: 100% of stories matched target age group
  - Grade level increases with age: age 6 → grade 1.9, age 10 → grade 6.2

---

## KEY FEATURES

1. **Personalized story generation** — name, age, gender, theme, length, extra details
2. **6 built-in themes** — Adventure, Fantasy, Space, Ocean, Animals, Friendship
3. **Custom themes** — user can type any theme (pirates, dinosaurs, ghost story, etc.)
4. **Two-character stories** — enter "Ali, Sara" to get a story with two characters
5. **Picture book UI** — hardcover book with page-flip animations, left page = illustration, right page = text
6. **Text-to-speech** — Web Speech API with voice accent selection, speed control, auto-read mode
7. **Gallery** — search, filter by theme, sort by date, story count, favorites, ratings, day streak
8. **User authentication** — JWT-based register/login with bcrypt password hashing, full registration form (first name, last name, email, username, password with strength indicator)
9. **Image caching** — DB-level cache prevents regenerating same image twice
10. **Permanent image storage** — Cloudinary CDN

---

## DATABASE SCHEMA

```sql
users (
    id, username, email, first_name, last_name, password (hashed), date
)

stories (
    id, name, theme, full_text (JSON), is_favorite, date, rating, user_id
)

story_images (
    story_id, page_num, image_url (Cloudinary URL)
)
```

---

## API ENDPOINTS

- POST /register — create account (validates email, username format, password strength)
- POST /login — authenticate, returns JWT token
- POST /generate-story — generate AI story (name, age, theme, gender, length, extra_details)
- POST /generate-image — generate page illustration (with DB cache check)
- GET /stories — list all stories with pagination
- GET /stories/{id} — get single story
- DELETE /stories/{id} — delete story
- POST /stories/{id}/rate — rate story 1-5 stars
- POST /stories/{id}/favorite — toggle favorite
- GET /favorites — get favorited stories
- GET /stats — total stories, favorites, themes breakdown
- GET /story-image/{story_id}/{page} — serve cached image

---

## EVALUATION RESULTS

### Model Comparison Table
| Metric | Base GPT-2 | Fine-tuned GPT-2 | Groq Llama 3.3 70B |
|--------|-----------|-----------------|-------------------|
| Perplexity | 10.44 | 3.68 | N/A (API) |
| Child-safe content | No | Yes | Yes |
| Story structure | None | Basic | Full 5-beat arc |
| Generation time | 2s | 2s | 8-12s |
| Parameters | 117M | 117M (fine-tuned) | 70B |

### Readability Evaluation
| Story | Target Age | FK Grade | Reading Ease | Age-Appropriate |
|-------|-----------|----------|-------------|----------------|
| Ali and the Forbidden Cave | 6 | 1.9 | 97.7 | YES |
| Sara and the Baby Bird | 7 | 3.1 | 92.1 | YES |
| Omar and the Magic Lamp | 9 | 4.5 | 81.4 | YES |
| Zara and the Coral Reef | 8 | 4.4 | 82.0 | YES |
| Hamza and the Shooting Star | 10 | 6.2 | 70.3 | YES |
| **Average** | **8** | **4.0** | **84.7** | **100%** |

---

## TECHNOLOGY STACK

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | HTML5, CSS3, Vanilla JS | Single page application |
| Backend | FastAPI (Python) | REST API server |
| LLM | Groq API — Llama 3.3 70B | Story generation |
| Fine-tuning | HuggingFace Transformers | GPT-2 domain adaptation |
| Dataset | TinyStories (HuggingFace) | 2.1M children's stories |
| Image Gen | Infip.pro (FLUX.1) | Page illustrations |
| Image Storage | Cloudinary | Permanent CDN storage |
| Database | SQLite / PostgreSQL | Story and user storage |
| Auth | JWT + bcrypt | User authentication |
| TTS | Web Speech API | Story narration |
| Deployment | Koyeb + GitHub | Cloud hosting |
| Evaluation | textstat (Flesch-Kincaid) | Readability metrics |

---

## LIMITATIONS

1. Fine-tuned GPT-2 (117M params) produces basic stories — insufficient for production quality; larger models needed
2. No user isolation yet — all stories visible to all users (user_id column added but filtering not implemented)
3. Image generation relies on third-party free APIs with rate limits
4. No formal human evaluation study — readability metrics are automated only
5. Google/GitHub OAuth not yet implemented — username/password only

---

## FUTURE WORK

1. Fine-tune TinyLlama 1.1B or Mistral 7B for better quality with trainable hardware
2. Human evaluation study — parents and children rating stories on engagement and age-appropriateness
3. Google/GitHub OAuth integration
4. User-specific story libraries (filter by user_id)
5. Story continuation feature ("What happens next?" button)
6. Quiz after story for educational engagement
7. PDF/print export for physical books
8. Multi-language support

---

## HOW TO USE THIS CONTEXT

Paste this entire document into any AI (Claude, ChatGPT, Gemini) followed by your request. Examples:

- "Using the above context, write the Abstract section of my research paper in IEEE format"
- "Write the Literature Review section comparing our approach to existing work"
- "Write the Methodology section explaining our two-step story generation approach"
- "Write the Results and Discussion section using our evaluation data"
- "Write the Conclusion section"
- "Generate a list of 15 relevant references for this paper"
