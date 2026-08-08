"""
Story generation service.

Two generation paths:
  generate_free_story - builds stories from local templates, no API calls required.
  generate_ai_story   - uses Groq LLaMA 3.3 70B via a two-step pipeline
                        (prose generation, then JSON formatting).
                        Falls back to templates on quota errors.
"""

import json
import random

from fastapi import HTTPException

from backend.config import USE_FREE_MODE, groq_client
from backend.database import save_story
from backend.models import StoryRequest, StoryPage
from backend.templates import STORY_TEMPLATES

_PRONOUN_MAP = {
    "boy":  {"they": "he",  "them": "him", "their": "his",  "they've": "he's",  "they're": "he's"},
    "girl": {"they": "she", "them": "her", "their": "her",  "they've": "she's", "they're": "she's"},
    "both": {},
}

_LENGTH_MAP = {"short": 3, "medium": 5, "long": 8}

_SCENARIOS = {
    "adventure": [
        "{name} finds a mysterious old map and follows it alone, ignoring a warning from an elder.",
        "{name} wants to be first to reach the top of the forbidden hill. A friend says it is too risky.",
        "{name} discovers a hidden cave and goes inside despite a sign that says Do Not Enter.",
        "{name} finds a wounded animal deep in the forest and must choose between helping it or making it home before dark.",
    ],
    "fantasy": [
        "{name} finds a magic lamp. The genie says one wish only. {name} almost wishes for something selfish.",
        "A witch offers {name} a shortcut through the enchanted forest. It seems too good to be true.",
        "{name} steals a single golden apple from the magic tree, not knowing the tree will wither without it.",
        "A dragon offers {name} great power in exchange for one small secret. But the secret belongs to a friend.",
    ],
    "friendship": [
        "{name}'s best friend makes a mistake and everyone is laughing. {name} must choose: join the laughter or stand up.",
        "{name} wants to win a competition so badly that they consider cheating when no one is watching.",
        "A new kid arrives and {name} ignores them to stay with the popular group. Then something happens that changes everything.",
        "{name} accidentally breaks something precious belonging to a friend and must decide whether to tell the truth.",
    ],
    "animals": [
        "{name} finds an injured bird and wants to keep it as a pet forever, even though it wants to fly free.",
        "{name} takes a baby rabbit from the forest to show friends, not realizing the mother is desperately searching.",
        "A clever fox tricks {name} into giving away food meant for a hungry family of deer.",
        "{name} discovers a bird's nest and wants to take one egg to hatch at home, ignoring the mother bird's cries.",
    ],
    "space": [
        "{name} is on a space mission and finds a glowing alien egg. The crew says leave it. {name} secretly takes it.",
        "{name} discovers a shortcut through an asteroid field. The captain says no. {name} goes anyway.",
        "An alien offers {name} a powerful weapon to defeat enemies. But using it would destroy a planet.",
        "{name} finds a distress signal from a distant planet but the mission rules say do not deviate from the route.",
    ],
    "ocean": [
        "{name} finds a mermaid's pearl on the beach. A crab warns it belongs to the sea queen and must be returned.",
        "{name} wants to swim to the forbidden coral reef despite the old fisherman's warning about the current.",
        "A sea creature offers {name} the ability to breathe underwater forever but {name} must never return to land.",
        "{name} catches the biggest fish ever seen but notices it is wearing a tiny crown — it is the king of the sea.",
    ],
}

_THEME_KEYWORDS = {
    "spooky": ["ghost", "spooky", "scary", "haunted", "vampire", "witch", "demon", "horror", "mystery", "strange", "weird"],
    "funny":  ["funny", "silly", "laugh", "joke", "humor", "comic", "crazy", "ridiculous"],
    "friendship": ["friend", "friendship", "together", "team", "partner", "buddy", "trust", "loyalty"],
    "adventure":  ["pirate", "treasure", "adventure", "explore", "quest", "journey", "discover", "map", "cave", "forest", "mountain"],
    "fantasy":    ["magic", "wizard", "dragon", "fairy", "enchant", "spell", "fantasy", "kingdom", "princess", "prince"],
    "space":      ["space", "alien", "planet", "rocket", "star", "galaxy", "astronaut", "robot"],
    "animals":    ["animal", "pet", "dog", "cat", "bird", "rabbit", "lion", "tiger", "elephant", "fish"],
    "ocean":      ["ocean", "sea", "underwater", "mermaid", "fish", "whale", "coral", "beach"],
}

_STORY_TYPE_INSTRUCTIONS = {
    "spooky":     "A spooky but age-appropriate story — mysterious atmosphere, a ghost or strange creature, tension that resolves safely.",
    "funny":      "A lighthearted, funny story — full of humor, silly situations, and a warm happy ending. Make the reader smile and laugh.",
    "friendship": "A story about friendship — characters face a challenge together, trust is tested, and loyalty wins in the end.",
    "adventure":  "A classic adventure — the characters go on a journey, face real danger, and must be brave to succeed.",
    "fantasy":    "A magical fantasy story — a world of wonder, a magical problem to solve, and a hero who uses courage and kindness.",
    "space":      "A sci-fi adventure — exploring the unknown, encountering something unexpected in space, and using intelligence to solve problems.",
    "animals":    "A heartwarming animal story — a bond between a child and an animal, a problem they solve together, and a lesson about kindness.",
    "ocean":      "An underwater adventure — exploring the ocean, meeting sea creatures, and discovering something magical beneath the waves.",
}


def _apply_pronouns(text: str, gender: str) -> str:
    pronouns = _PRONOUN_MAP.get(gender, {})
    for src, dst in pronouns.items():
        text = text.replace(f" {src} ", f" {dst} ")
        text = text.replace(f" {src.capitalize()} ", f" {dst.capitalize()} ")
    return text


def _infer_story_type(theme: str, extra: str) -> str:
    """Determine story type from theme and extra details by keyword matching."""
    combined = (theme + " " + extra).lower()
    for story_type, keywords in _THEME_KEYWORDS.items():
        if any(word in combined for word in keywords):
            return story_type
    return None


async def generate_free_story(request: StoryRequest) -> dict:
    """Build a story from local templates without any API calls."""
    try:
        print(f"Template story: name={request.name}, age={request.age}, theme={request.theme}")
        theme = request.theme.lower()
        if theme not in STORY_TEMPLATES:
            theme = "adventure"

        template   = STORY_TEMPLATES[theme]
        title      = random.choice(template["titles"]).format(name=request.name)
        page_count = _LENGTH_MAP.get((request.length or "medium").lower(), 5)
        gender     = (request.gender or "boy").lower()

        pages = []
        for i, raw in enumerate(template["pages"][:page_count], 1):
            text = _apply_pronouns(raw.format(name=request.name, age=request.age), gender)
            first_sentence = text.split(".")[0].strip()
            pages.append(StoryPage(
                page_number=i,
                text=text,
                image_prompt=(
                    f"{first_sentence}. {request.name} is the main character, "
                    f"{theme} theme, children's storybook scene"
                ),
            ))

        lesson = template["lesson"]
        lesson_text = (
            f"{lesson['title'].format(name=request.name)}\n\n"
            + "\n\n".join(lesson["points"])
        )
        pages.append(StoryPage(
            page_number=len(pages) + 1,
            text=lesson_text,
            image_prompt=f"A warm educational illustration showing {request.name} reflecting on their journey",
        ))

        story_data = {
            "title": title,
            "theme": request.theme,
            "pages": [p.dict() for p in pages],
        }
        story_id = save_story(request.name, request.theme, story_data)
        print(f"Template story saved: {title} (ID: {story_id})")
        return {
            **story_data,
            "story_id": story_id,
            "char_desc": f"{request.age}-year-old child named {request.name}",
        }

    except Exception as exc:
        print(f"Template story error: {exc}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {exc}")


async def generate_ai_story(request: StoryRequest) -> dict:
    """
    Generate a story via Groq LLaMA 3.3 70B.

    Step 1: Generate raw story prose.
    Step 2: Format the prose into structured JSON pages.
    Step 3: Generate a character description for image consistency.

    Falls back to template generation on rate limit or quota errors.
    """
    try:
        print(f"AI story: name={request.name}, age={request.age}, theme={request.theme}")

        page_count = _LENGTH_MAP.get((request.length or "medium").lower(), 5)
        gender     = (request.gender or "boy").lower()
        pronoun_str = {
            "boy":  "he/him/his",
            "girl": "she/her/her",
            "both": "they/them/their (two main characters, one boy and one girl)",
        }.get(gender, "they/them/their")

        names = [n.strip() for n in request.name.split(",")]
        if len(names) >= 2 and gender == "both":
            char_intro = f"two friends named {names[0]} (boy) and {names[1]} (girl)"
        elif len(names) >= 2:
            char_intro = f"{names[0]} and {names[1]}"
        else:
            char_intro = request.name

        extra = request.extra_details or ""
        story_type = _infer_story_type(request.theme, extra)

        if story_type:
            story_type_instruction = _STORY_TYPE_INSTRUCTIONS[story_type]
        else:
            story_type_instruction = (
                f"A creative story that fully embraces the '{request.theme}' theme. "
                f"Make it engaging, surprising, and memorable for a {request.age}-year-old."
            )

        print(f"Story type: {story_type_instruction[:70]}")

        is_custom = request.theme.lower() not in _SCENARIOS

        if is_custom:
            scenario_line = (
                f"THEME: {request.theme}\n"
                f"Build a creative, specific story around this theme. "
                f"Do NOT default to a forest adventure. "
                f"The setting, characters, and conflict must fit the theme '{request.theme}' naturally.\n"
            )
            print(f"Custom theme detected: {request.theme}")
        else:
            scenario = random.choice(_SCENARIOS[request.theme.lower()]).format(name=names[0])
            scenario_line = f"SCENARIO (use this exact situation, do not change it):\n{scenario}\n"
            print(f"Scenario: {scenario}")

        extra_line = f"\nExtra details to include: {extra}" if extra else ""

        story_prompt = (
            f"Write a children's story for a {request.age}-year-old. "
            f"Main character(s): {char_intro} ({pronoun_str} pronouns).\n\n"
            f"STORY TYPE: {story_type_instruction}\n\n"
            f"{scenario_line}"
            f"{extra_line}\n\n"
            f"WRITING STYLE:\n"
            f"- Include at least 3 lines of DIALOGUE (characters speaking in quotes)\n"
            f"- Use SENSORY DETAILS: what the characters smell, hear, feel, see\n"
            f"- Show emotions through body language: hands trembled, stomach dropped\n"
            f"- The moral must come from the EVENTS, never stated directly\n"
            f"- Simple words for age {request.age}, but real emotions and real stakes\n"
            f"- Length: {page_count * 5} to {page_count * 7} sentences\n\n"
            f"Write ONLY the story. No title, no labels, no JSON."
        )

        # Step 1 — prose generation
        story_text = None
        last_error = None
        for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                print(f"Step 1: prose via {model_name}")
                chat = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": story_prompt}],
                    temperature=0.9,
                    max_tokens=2048,
                )
                story_text = chat.choices[0].message.content.strip()
                print(f"Prose generated ({len(story_text)} chars)")
                break
            except Exception as exc:
                last_error = exc
                print(f"Step 1 {model_name} failed: {str(exc)[:100]}")

        if story_text is None:
            raise last_error

        # Step 2 — JSON formatting
        lesson_page_num = page_count + 1
        page_slots = "".join([
            f'    {{"page_number": {i}, "text": "PASTE_PAGE_{i}_TEXT_HERE", "image_prompt": "visual scene for page {i}"}},\n'
            for i in range(1, page_count + 1)
        ])
        system_msg = (
            "You are a JSON formatter. Split a story into pages. "
            "COPY the story text exactly. Do NOT rewrite anything. "
            "Return ONLY valid JSON. No markdown, no extra text."
        )
        format_prompt = (
            f"Split the story below into exactly {page_count} pages, "
            f"then add a lesson page {lesson_page_num}.\n\n"
            f"STORY:\n---\n{story_text}\n---\n\n"
            f"Return ONLY this JSON (no markdown, no extra text):\n"
            + "{\n"
            + '  "title": "short title from the story",\n'
            + '  "pages": [\n'
            + page_slots
            + f'    {{"page_number": {lesson_page_num}, "text": "What {char_intro} Learned. [4 lessons from the story]", "image_prompt": "warm closing scene"}}\n'
            + "  ]\n"
            + "}"
        )

        response = None
        for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                print(f"Step 2: JSON format via {model_name}")
                chat = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": format_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=3000,
                )
                response = chat.choices[0].message.content
                print("JSON formatted")
                break
            except Exception as exc:
                last_error = exc
                print(f"Step 2 {model_name} failed: {str(exc)[:100]}")

        if response is None:
            raise last_error

        # Clean the JSON response
        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end:
            text = text[start:end]

        story_data = json.loads(text)
        if not isinstance(story_data, dict) or "title" not in story_data or "pages" not in story_data:
            raise ValueError("Unexpected story structure from LLM")

        story_data["theme"] = request.theme

        # Step 3 — character description for image consistency
        char_desc = f"{request.age}-year-old child"
        try:
            desc_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Write a SHORT physical description of {names[0]} for an illustrator. "
                        f"Include: age (~{request.age} years old), hair color/style, eye color, skin tone, one specific outfit. "
                        "Max 25 words. Descriptive phrases only, no sentences.\n\n"
                        f"Story title: {story_data['title']}\n"
                        f"First page: {story_data['pages'][0]['text'][:200]}"
                    ),
                }],
                temperature=0.3,
                max_tokens=50,
            )
            char_desc = desc_response.choices[0].message.content.strip()
            print(f"Character description: {char_desc}")
        except Exception as exc:
            print(f"Character description failed: {exc}")

        story_data["char_desc"] = char_desc
        story_id = save_story(request.name, request.theme, story_data)
        print(f"AI story saved: {story_data['title']} (ID: {story_id})")
        return {**story_data, "story_id": story_id}

    except HTTPException:
        raise
    except Exception as exc:
        err = str(exc)
        print(f"AI story error: {err}")
        if any(code in err for code in ["429", "rate_limit", "quota"]):
            print("Rate limit hit — falling back to template generation")
            return await generate_free_story(request)
        raise HTTPException(status_code=500, detail=f"Error generating story: {err}")
