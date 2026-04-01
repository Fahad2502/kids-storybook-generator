"""
story_service.py -- Free-template and Groq AI story generation logic
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
        "{name} catches the biggest fish ever seen but notices it is wearing a tiny crown -- it is the king of the sea.",
    ],
}


def _apply_pronouns(text: str, gender: str) -> str:
    pronouns = _PRONOUN_MAP.get(gender, {})
    for src, dst in pronouns.items():
        text = text.replace(f" {src} ", f" {dst} ")
        text = text.replace(f" {src.capitalize()} ", f" {dst.capitalize()} ")
    return text


async def generate_free_story(request: StoryRequest) -> dict:
    """Build a story from local templates -- zero API calls."""
    try:
        print(f"FREE story: name={request.name}, age={request.age}, theme={request.theme}")
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
        lesson_text = f"{lesson['title'].format(name=request.name)}\n\n" + "\n\n".join(lesson["points"])
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
        print(f"FREE story saved: {title} (ID: {story_id})")
        return {**story_data, "story_id": story_id,
                "char_desc": f"{request.age}-year-old child named {request.name}"}

    except Exception as e:
        print(f"FREE story error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {e}")


async def generate_ai_story(request: StoryRequest) -> dict:
    """Generate a story via Groq LLM; falls back to free templates on quota errors."""
    try:
        print(f"AI story: name={request.name}, age={request.age}, theme={request.theme}")
        page_count = _LENGTH_MAP.get((request.length or "medium").lower(), 5)
        gender     = (request.gender or "boy").lower()
        pronoun_str = {
            "boy":  "he/him/his",
            "girl": "she/her/her",
            "both": "they/them/their (two main characters, one boy and one girl)",
        }.get(gender, "they/them/their")

        lesson_num = page_count + 1
        extra = f"\nExtra details to include: {request.extra_details}" if request.extra_details else ""

        # Handle multiple names (e.g. "Ali, Sara" = two characters)
        names = [n.strip() for n in request.name.split(",")]
        if len(names) >= 2 and gender == "both":
            char_intro = f"two friends named {names[0]} (boy) and {names[1]} (girl)"
        elif len(names) >= 2:
            char_intro = f"{names[0]} and {names[1]}"
        else:
            char_intro = request.name

        # Infer story type from theme and extra details — not random
        theme_lower = request.theme.lower()
        extra_lower = (request.extra_details or "").lower()
        combined = theme_lower + " " + extra_lower

        if any(w in combined for w in ["ghost", "spooky", "scary", "haunted", "vampire", "witch", "demon", "horror", "mystery", "strange", "weird"]):
            story_type_instruction = "A spooky but age-appropriate story — mysterious atmosphere, a ghost or strange creature, tension that resolves safely."
        elif any(w in combined for w in ["funny", "silly", "laugh", "joke", "humor", "comic", "crazy", "ridiculous"]):
            story_type_instruction = "A lighthearted, funny story — full of humor, silly situations, and a warm happy ending. Make the reader smile and laugh."
        elif any(w in combined for w in ["friend", "friendship", "together", "team", "partner", "buddy", "trust", "loyalty"]):
            story_type_instruction = "A story about friendship — characters face a challenge together, trust is tested, and loyalty wins in the end."
        elif any(w in combined for w in ["pirate", "treasure", "adventure", "explore", "quest", "journey", "discover", "map", "cave", "forest", "mountain"]):
            story_type_instruction = "A classic adventure — the characters go on a journey, face real danger, and must be brave to succeed."
        elif any(w in combined for w in ["magic", "wizard", "dragon", "fairy", "enchant", "spell", "fantasy", "kingdom", "princess", "prince"]):
            story_type_instruction = "A magical fantasy story — a world of wonder, a magical problem to solve, and a hero who uses courage and kindness."
        elif any(w in combined for w in ["space", "alien", "planet", "rocket", "star", "galaxy", "astronaut", "robot"]):
            story_type_instruction = "A sci-fi adventure — exploring the unknown, encountering something unexpected in space, and using intelligence to solve problems."
        elif any(w in combined for w in ["animal", "pet", "dog", "cat", "bird", "rabbit", "lion", "tiger", "elephant", "fish"]):
            story_type_instruction = "A heartwarming animal story — a bond between a child and an animal, a problem they solve together, and a lesson about kindness."
        elif any(w in combined for w in ["ocean", "sea", "underwater", "mermaid", "fish", "whale", "coral", "beach"]):
            story_type_instruction = "An underwater adventure — exploring the ocean, meeting sea creatures, and discovering something magical beneath the waves."
        else:
            # Default: let the theme drive the story naturally
            story_type_instruction = f"A creative story that fully embraces the '{request.theme}' theme. Make it engaging, surprising, and memorable for a {request.age}-year-old."

        print(f"Story type inferred from theme '{request.theme}': {story_type_instruction[:60]}")

        # Known themes use a concrete scenario seed.
        # Custom themes skip the seed so the AI uses the theme freely.
        theme_key = request.theme.lower()
        is_custom = theme_key not in _SCENARIOS

        if is_custom:
            scenario_line = (
                f"THEME: {request.theme}\n"
                f"Build a creative, specific story around this theme. "
                f"Do NOT default to a forest adventure. "
                f"The setting, characters, and conflict must all fit the theme '{request.theme}' naturally.\n"
            )
            print(f"Custom theme: {request.theme}")
        else:
            scenario = random.choice(_SCENARIOS[theme_key]).format(name=names[0])
            scenario_line = f"SCENARIO (use this exact situation, do not change it):\n{scenario}\n"
            print(f"Scenario: {scenario}")

        story_prompt = (
            f"Write a children's story for a {request.age}-year-old. Main character(s): {char_intro} ({pronoun_str} pronouns).\n\n"
            f"STORY TYPE: {story_type_instruction}\n\n"
            f"{scenario_line}"
            f"{extra}\n\n"
            f"WRITING STYLE:\n"
            f"- Include at least 3 lines of DIALOGUE (characters speaking to each other in quotes)\n"
            f"- Use SENSORY DETAILS: what the characters smell, hear, feel, see\n"
            f"- Show emotions through body language: hands trembled, stomach dropped\n"
            f"- The moral (if any) must come from the EVENTS, never state it directly\n"
            f"- Simple words for age {request.age}, but real emotions and real stakes\n"
            f"- Length: {page_count * 5} to {page_count * 7} sentences\n\n"
            f"Write ONLY the story. No title, no labels, no JSON."
        )

        story_text = None
        last_error = None
        for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                print(f"Step 1 - story prose via {model_name}")
                chat = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": story_prompt}],
                    temperature=0.9,
                    max_tokens=2048,
                )
                story_text = chat.choices[0].message.content.strip()
                print(f"Prose generated ({len(story_text)} chars)")
                break
            except Exception as err:
                last_error = err
                print(f"Step 1 {model_name} failed: {str(err)[:100]}")

        if story_text is None:
            raise last_error

        page_slots = "".join([
            f'    {{"page_number": {i}, "text": "PASTE_PAGE_{i}_TEXT_HERE", "image_prompt": "visual scene for page {i}"}},\n'
            for i in range(1, page_count + 1)
        ])
        system_msg = (
            "You are a JSON formatter. Your ONLY job is to split a story into pages and output JSON. "
            "You must COPY the story text word-for-word into the pages. "
            "Do NOT rewrite, summarize, or change any words. "
            "Do NOT add new sentences. Only split and copy. "
            "For emotion: pick ONE emoji from the allowed list that matches the mood of that page."
        )
        format_prompt = (
            f"Split the story below into exactly {page_count} pages, then add a lesson page {lesson_num}.\n\n"
            f"STORY TO SPLIT:\n---\n{story_text}\n---\n\n"
            f"OUTPUT this exact JSON structure with the story text copied in:\n"
            + '{\n'
            + '  "title": "create a short title from the story",\n'
            + '  "pages": [\n'
            + page_slots
            + f'    {{"page_number": {lesson_num}, "text": "What {char_intro} Learned\\n\\n🌟 [lesson from story]\\n\\n💫 [lesson from story]\\n\\n✨ [lesson from story]\\n\\n❤️ [warm closing]", "image_prompt": "warm closing scene", "emotion": "🌟"}}\n'
            + '  ]\n'
            + '}\n\n'
            + "Copy the story text exactly. Split at paragraph breaks. Return ONLY the JSON."
        )

        response = None
        for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                print(f"Step 2 - JSON format via {model_name}")
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
                print(f"JSON formatted")
                break
            except Exception as err:
                last_error = err
                print(f"Step 2 {model_name} failed: {str(err)[:100]}")

        if response is None:
            raise last_error

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
            raise ValueError("Invalid story structure from AI")

        story_data["theme"] = request.theme

        char_desc = f"{request.age}-year-old child"
        try:
            desc = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": (
                    f"Write a SHORT physical description of {names[0]} for an illustrator. "
                    f"Include: age (~{request.age} years old), hair color/style, eye color, skin tone, one specific outfit. "
                    "Max 25 words. Descriptive phrases only, no sentences.\n\n"
                    f"Story title: {story_data['title']}\n"
                    f"First page: {story_data['pages'][0]['text'][:200]}"
                )}],
                temperature=0.3,
                max_tokens=50,
            )
            char_desc = desc.choices[0].message.content.strip()
            print(f"Char desc: {char_desc}")
        except Exception as e:
            print(f"Char desc failed: {e}")

        story_data["char_desc"] = char_desc
        story_id = save_story(request.name, request.theme, story_data)
        print(f"AI story saved: {story_data['title']} (ID: {story_id})")
        return {**story_data, "story_id": story_id}

    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        print(f"AI story error: {err}")
        if any(x in err for x in ["429", "rate_limit", "quota"]):
            print("Quota hit -- falling back to FREE templates")
            return await generate_free_story(request)
        raise HTTPException(status_code=500, detail=f"Error generating story: {err}")