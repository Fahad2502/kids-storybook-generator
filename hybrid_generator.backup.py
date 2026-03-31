import os
import sqlite3
import json
import random
import httpx
import base64
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURATION - SWITCH BETWEEN FREE AND API
# ============================================
USE_FREE_MODE = os.getenv("USE_FREE_MODE", "true").lower() == "true"
# Set to "false" in .env to use Gemini API for production

if not USE_FREE_MODE:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("⚠️ WARNING: GROQ_API_KEY not found. Falling back to FREE mode.")
        USE_FREE_MODE = True
    else:
        groq_client = Groq(api_key=GROQ_API_KEY)

# Image generation via HuggingFace FLUX.1-schnell
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_IMAGE_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
USE_IMAGE_GEN = bool(HF_API_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="Kids Story Generator API - HYBRID MODE",
    version="2.0.0",
    description="Switch between FREE templates and AI-powered stories"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8025",
        "http://127.0.0.1:8025",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:*",
        "http://127.0.0.1:*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Database setup
DATABASE_PATH = "stories.db"

# Generated images storage
IMAGES_DIR = Path("img/generated")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def init_database():
    """Initialize the database and create tables if they don't exist"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        cursor.execute("""
            CREATE TABLE stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                theme TEXT NOT NULL,
                full_text TEXT NOT NULL,
                is_favorite INTEGER DEFAULT 0,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created new stories table")
    else:
        cursor.execute("PRAGMA table_info(stories)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'full_text' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN full_text TEXT")
            print("✅ Added full_text column to existing stories table")
            cursor.execute("UPDATE stories SET full_text = '{}' WHERE full_text IS NULL")
        
        if 'is_favorite' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN is_favorite INTEGER DEFAULT 0")
            print("✅ Added is_favorite column to existing stories table")

        if 'rating' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN rating INTEGER DEFAULT NULL")
            print("✅ Added rating column to existing stories table")

    conn.commit()
    conn.close()

# Pydantic models
class StoryRequest(BaseModel):
    name: str
    age: int
    theme: str
    length: Optional[str] = "medium"   # short=3, medium=5, long=8
    gender: Optional[str] = "neutral"  # boy, girl, neutral

class StoryPage(BaseModel):
    page_number: int
    text: str
    image_prompt: Optional[str] = ""

class StoryResponse(BaseModel):
    title: str
    theme: str
    pages: List[StoryPage]
    story_id: Optional[int] = None
    
    class Config:
        extra = "allow"  # Allow extra fields like story_id

# FREE STORY TEMPLATES
STORY_TEMPLATES = {
    "adventure": {
        "titles": [
            "{name}'s Great Adventure",
            "The Amazing Journey of {name}",
            "{name} and the Hidden Treasure",
            "{name}'s Mountain Quest"
        ],
        "pages": [
            "Once upon a time, in a cozy little town, there lived a brave {age}-year-old named {name}. {name} had always dreamed of going on a real adventure, just like the heroes in their favorite books.\n\nOne sunny morning, while playing in the backyard, {name} noticed something unusual. The old oak tree seemed to be glowing with a soft, golden light.\n\nCurious and excited, {name} walked closer to investigate. Hidden in a hollow of the tree trunk was an ancient, rolled-up map covered in mysterious symbols.\n\n{name}'s heart raced with excitement. This was it - the beginning of a real adventure!",
            
            "The map showed a path leading deep into the enchanted forest beyond the town. {name} packed a small backpack with snacks, water, and their favorite lucky charm.\n\nAs {name} entered the forest, the trees seemed to whisper words of encouragement. Birds chirped cheerful melodies, as if they were cheering {name} on.\n\nSuddenly, a wise old owl landed on a branch nearby. 'Hello, young adventurer,' the owl hooted. 'I've been expecting you. The forest has many secrets to share.'\n\n{name} couldn't believe it - the owl was talking! This adventure was already more magical than {name} had ever imagined.",
            
            "Following the map's directions, {name} came to a wide, rushing river. The water sparkled in the sunlight, but there was no bridge to cross.\n\n{name} sat down to think. Giving up wasn't an option - true adventurers always find a way. Looking around, {name} spotted some fallen logs and strong vines nearby.\n\nWith determination and clever thinking, {name} began tying the logs together with the vines. It took time and effort, but slowly a sturdy raft began to take shape.\n\nA friendly beaver swam by and offered to help. Together, they created a safe way to cross the river. {name} learned that asking for help is a sign of wisdom, not weakness.",
            
            "On the other side of the river, the map led to a beautiful clearing filled with wildflowers. In the center stood an ancient stone chest.\n\n{name}'s hands trembled with excitement as they opened the chest. But instead of gold or jewels, inside were colorful friendship bracelets and a note.\n\nThe note read: 'The greatest treasure is the friends you make and the courage you discover along the way.' {name} smiled, understanding the true meaning.\n\nAll the forest animals gathered around - the owl, the beaver, rabbits, and deer. They had all been part of the adventure, helping {name} along the journey.",
            
            "As the sun began to set, {name} said goodbye to all the new friends. The owl gave {name} a special feather to remember the adventure.\n\n{name} walked back home, feeling taller and braver than before. The backpack was filled with friendship bracelets instead of treasure, but {name} felt richer than ever.\n\nMom and Dad were waiting at home with warm hugs. {name} excitedly shared stories of the magical day and the wonderful friends made along the way.\n\nThat night, {name} placed the owl feather on the bedside table and smiled. This was just the first of many adventures to come."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "🌟 True courage means trying new things even when you're a little scared",
                "🤝 The best treasures in life are the friends we make along the way",
                "💡 Using your brain to solve problems is just as important as being strong",
                "❤️ Asking for help from others shows wisdom and creates stronger friendships"
            ]
        }
    },
    "fantasy": {
        "titles": [
            "{name} and the Magic Kingdom",
            "The Enchanted World of {name}",
            "{name}'s Magical Powers",
            "{name} and the Friendly Dragon"
        ],
        "pages": [
            "{name}, a curious {age}-year-old, was exploring the attic when they found a dusty old trunk. Inside was a beautiful glowing crystal that pulsed with rainbow colors.\n\nThe moment {name} touched the crystal, the whole room filled with sparkling light. The walls seemed to melt away, revealing a magnificent magical kingdom.\n\nTowering castles made of crystal reached toward the clouds. Friendly unicorns grazed in meadows of flowers that sang gentle melodies.\n\n{name} stood in wonder, realizing that magic was real and this incredible adventure was just beginning.",
            
            "A kind wizard with a long silver beard approached {name} with a warm smile. 'Welcome, young one,' he said. 'We've been waiting for someone with a pure heart like yours.'\n\nThe wizard explained that {name} had a special gift - the ability to see and use magic that others couldn't. This gift came from having a kind and imaginative heart.\n\n{name} met Sparkle, a gentle dragon with scales that shimmered like opals. Sparkle became {name}'s guide and friend in this magical world.\n\nTogether, they began learning simple spells - making flowers bloom, creating tiny rainbows, and helping lost creatures find their way home.",
            
            "One day, dark storm clouds began covering the magical kingdom. The flowers stopped singing, and the unicorns looked worried.\n\nThe wizard told {name} that the kingdom needed help. Only someone with true magic in their heart could bring back the light and joy.\n\n{name} felt nervous but remembered all the lessons learned. With Sparkle by their side, {name} climbed to the highest tower of the crystal castle.\n\nTaking a deep breath, {name} focused on all the happy memories and kind thoughts. The crystal began to glow brighter and brighter in {name}'s hands.",
            
            "A brilliant beam of rainbow light shot from the crystal into the dark clouds. Slowly, the darkness began to fade away, replaced by warm sunshine.\n\nThe flowers started singing again, even more beautifully than before. All the magical creatures cheered and celebrated {name}'s bravery.\n\nThe wizard smiled proudly. 'You see, {name}, the real magic was inside you all along. It's your kindness, courage, and belief in yourself.'\n\n{name} understood now that magic isn't just about spells and crystals - it's about having a good heart and helping others.",
            
            "When it was time to go home, {name} felt sad to leave but knew this wasn't goodbye forever. The wizard gave {name} a small crystal to keep.\n\n'Whenever you need to remember the magic within you, just hold this crystal,' the wizard said. 'And remember, you can return anytime you believe.'\n\nSparkle nuzzled {name} gently, promising they would always be friends. {name} hugged the dragon's warm neck, feeling grateful for this amazing adventure.\n\nBack in the attic, {name} held the crystal tight and smiled. Magic was real, and it lived in every kind act and brave choice."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "✨ Real magic comes from having a kind heart and believing in yourself",
                "🐉 True friends support you and help you discover your special gifts",
                "🌈 When you help others, you make the whole world a brighter place",
                "💫 The most powerful magic is the love and kindness you share with others"
            ]
        }
    },
    "friendship": {
        "titles": [
            "{name} and the New Friend",
            "The Friendship Adventure of {name}",
            "{name} Learns About Kindness",
            "{name}'s Circle of Friends"
        ],
        "pages": [
            "It was {name}'s first day back at school after summer vacation. The {age}-year-old walked into the classroom excited to see old friends.\n\nBut {name} noticed someone new - a quiet student sitting alone in the corner, looking down at their desk. The new student seemed nervous and a little sad.\n\nWhile everyone else was busy chatting with their friends, {name} remembered how it felt to be new. It can be scary and lonely.\n\n{name} made a decision. Instead of rushing to sit with old friends, {name} walked over to the new student with a warm smile.",
            
            "'Hi! I'm {name},' they said cheerfully. 'Would you like to sit with me at lunch today? I can show you around the school.'\n\nThe new student looked up with surprised, hopeful eyes. 'Really? That would be amazing. I'm Alex, and I just moved here. I don't know anyone yet.'\n\nAt lunch, {name} shared their favorite sandwich and told Alex all about the school, the teachers, and the fun activities. Alex started to smile and relax.\n\nThey discovered they both loved the same books, the same games, and even had the same favorite color. It felt like they had known each other forever.",
            
            "During recess, {name} invited Alex to play with the other kids. At first, Alex was shy, but {name} stayed close and made sure Alex felt included.\n\nThey played tag, swung on the swings, and laughed together. {name} introduced Alex to all their friends, and soon everyone was having fun together.\n\nBut then something not-so-nice happened. A couple of kids started making fun of Alex's new backpack, saying it looked different and weird.\n\n{name} saw Alex's face fall and knew this was a moment that mattered. True friends stand up for each other, even when it's hard.",
            
            "'{name} stepped forward bravely. 'I think Alex's backpack is really cool and unique. Being different makes us special, not weird.'\n\nThe other kids looked surprised. {name} continued, 'How would you feel if someone made fun of something you liked? We should be kind to everyone.'\n\nThe kids who had been mean looked down, feeling a bit ashamed. One of them apologized to Alex, and soon everyone was being friendly again.\n\nAlex smiled at {name} with grateful eyes. 'Thank you for being such a good friend. You made me feel like I belong here.'",
            
            "From that day forward, {name} and Alex became best friends. They did homework together, played together, and shared all their secrets.\n\n{name} learned that being a good friend means more than just having fun together. It means listening when someone is sad, standing up for what's right, and always being kind.\n\nAlex taught {name} new games from their old town, and {name} showed Alex all the best spots in the neighborhood. They made each other's lives brighter and happier.\n\nAs they walked home together that afternoon, both {name} and Alex knew they had found something truly special - a friendship that would last forever."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "🤗 A simple act of kindness can change someone's whole day",
                "💪 Standing up for your friends, even when it's hard, shows true courage",
                "🌟 Everyone deserves to feel included and valued for who they are",
                "❤️ The best friendships are built on kindness, loyalty, and understanding"
            ]
        }
    },
    "animals": {
        "titles": [
            "{name} and the Forest Friends",
            "The Animal Adventure of {name}",
            "{name}'s Pet Rescue Mission",
            "{name} and the Talking Animals"
        ],
        "pages": [
            "{name}, an animal-loving {age}-year-old, woke up one morning to discover something incredible. They could understand what animals were saying!\n\nA little bird chirped outside the window, and {name} heard it clearly: 'Good morning! The sunrise is beautiful today!' {name} gasped in amazement.\n\nRunning outside, {name} found the family dog, Max, wagging his tail. 'Finally, you can hear me!' Max barked happily. 'I've been trying to tell you jokes for years!'\n\n{name} laughed with joy. This was the most amazing gift ever - being able to talk with animal friends!",
            
            "Later that day, a worried rabbit hopped up to {name} in the backyard. 'Please help me,' the rabbit said with tears in her eyes. 'My family is lost in the big forest.'\n\n{name}'s heart filled with concern. 'Don't worry, I'll help you find them,' {name} promised. 'We'll search together until we bring your family home safely.'\n\nThe rabbit, whose name was Rosie, explained that her family had gone looking for food but hadn't returned. They might be scared and alone.\n\n{name} knew this was important. Animals are part of our world too, and they deserve our help and protection.",
            
            "{name} gathered a team of animal friends to help with the rescue. A wise old owl named Oliver agreed to search from the sky with his sharp eyes.\n\nA strong, gentle bear named Bruno offered to move heavy branches and logs that might be blocking paths. A quick squirrel named Sammy volunteered to check all the tree hollows.\n\nTogether, this amazing team entered the forest. {name} felt proud to be working with such wonderful animal friends, each using their special abilities.\n\nThey followed tiny paw prints in the soft dirt, listened for soft rabbit calls, and checked every burrow and hiding spot they could find.",
            
            "After hours of searching, Oliver hooted from above. 'I see them! They're trapped in a small cave behind some fallen rocks!'\n\nEveryone rushed to the spot. Bruno used his strength to carefully move the rocks while {name} called out encouraging words to the scared rabbit family.\n\nFinally, the opening was clear. Rosie's family hopped out, tired but safe. The reunion was beautiful - all the rabbits hugged and cried happy tears.\n\nRosie turned to {name} with grateful eyes. 'Thank you for caring about us. You're a true friend to all animals.'",
            
            "As the sun set, all the forest animals gathered around {name}. They wanted to thank this special human who had shown such kindness and respect.\n\nOliver the owl spoke wisely: '{name}, you have a gift not just to hear us, but to truly care about us. That makes you very special indeed.'\n\n{name} realized that caring for animals and nature wasn't just fun - it was an important responsibility. Every creature, big or small, deserves kindness and protection.\n\nWalking home that evening, {name} made a promise to always be a voice for animals and to protect the natural world. It was a purpose worth living for."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "🐾 All animals deserve our kindness, respect, and protection",
                "🌳 Taking care of nature and wildlife is everyone's responsibility",
                "🤝 Working together as a team makes us stronger and helps us achieve great things",
                "💚 When we help animals and nature, we make the whole world a better place"
            ]
        }
    },
    "space": {
        "titles": [
            "{name}'s Space Adventure",
            "Captain {name} and the Star Quest",
            "{name} Visits the Moon",
            "{name} and the Friendly Aliens"
        ],
        "pages": [
            "{name}, a {age}-year-old who loved everything about space, spent every night gazing at the stars through a telescope. The universe seemed so vast and full of mysteries.\n\nOne day, {name} decided to build a rocket ship in the backyard using cardboard boxes, aluminum foil, and lots of imagination. It looked amazing!\n\n{name} climbed inside the cardboard rocket, closed their eyes, and imagined blasting off into space. Suddenly, the rocket began to shake and rumble.\n\nTo {name}'s absolute amazement, the cardboard rocket actually lifted off the ground! The power of imagination and dreams had made it real!",
            
            "The rocket soared higher and higher, past the clouds, past the atmosphere, and into the starry darkness of space. {name} looked out the window in wonder.\n\nPlanets of every color floated by - red Mars, giant Jupiter with its swirling storms, and beautiful Saturn with its glittering rings.\n\n{name} spotted a colorful planet that wasn't on any map. It had purple mountains, orange rivers, and cities that sparkled like diamonds.\n\nDeciding to explore, {name} carefully landed the rocket on this mysterious new world. The adventure was just beginning!",
            
            "As {name} stepped out of the rocket, a group of friendly alien children came running over. They had big curious eyes and skin that shimmered with different colors.\n\n'Welcome to Planet Harmony!' they said in a musical language that {name} could somehow understand. 'We love meeting new friends from other worlds!'\n\nThe alien children showed {name} their incredible crystal cities that floated in the air. They played games that were surprisingly similar to Earth games - tag, hide and seek, and catch.\n\n{name} realized that even though they looked different, kids everywhere in the universe loved to play, laugh, and make friends.",
            
            "The alien children taught {name} how to float and bounce in the planet's low gravity. They soared through the air together, giggling and doing flips.\n\n{name} shared stories about Earth - about oceans, forests, animals, and all the wonderful things back home. The alien children listened with fascination.\n\nIn return, they showed {name} their amazing technology - books that came to life with holograms, food that grew instantly from seeds, and music that you could see as colorful lights.\n\n{name} learned that every planet and every culture has something special and beautiful to share with others.",
            
            "As it was time to go home, the alien children gave {name} a special gift - a small crystal that glowed with the light of their planet's three suns.\n\n'This will help you remember that friendship exists throughout the entire universe,' they said. 'Distance doesn't matter when hearts are connected.'\n\n{name} hugged each new friend goodbye and promised to visit again someday. The rocket lifted off, and {name} waved until the colorful planet was just a tiny dot.\n\nFlying back to Earth, {name} looked at the crystal and smiled. The universe was full of friends waiting to be discovered, and every star held the possibility of new adventures."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "🌟 The power of imagination and dreams can take you anywhere you want to go",
                "👽 Even though people may look different, we all share the same feelings and desires for friendship",
                "🚀 Being curious and open to new experiences leads to amazing discoveries",
                "💫 Friendship has no boundaries - it exists everywhere in the universe"
            ]
        }
    },
    "ocean": {
        "titles": [
            "{name} and the Ocean Adventure",
            "The Underwater World of {name}",
            "{name} Meets the Mermaids",
            "{name}'s Deep Sea Discovery"
        ],
        "pages": [
            "{name}, a {age}-year-old who loved the ocean, was walking along the beach one morning when something caught their eye. A beautiful seashell was glowing with a soft blue light.\n\nPicking up the shell, {name} heard a gentle voice whisper: 'Hold me close and make a wish to explore the ocean depths.' It sounded like the voice of the sea itself.\n\n{name} closed their eyes and wished with all their heart to see the underwater world. Suddenly, the shell glowed brighter and brighter.\n\nWhen {name} opened their eyes, they were standing underwater, breathing easily as if they had gills! The magical seashell had granted the wish!",
            
            "The underwater world was more beautiful than {name} had ever imagined. Coral reefs in every color of the rainbow stretched as far as the eye could see.\n\nSchools of tropical fish swam by in perfect formation, their scales glittering like jewels. Sea turtles glided gracefully through the water, and seahorses danced among the seaweed.\n\nSuddenly, a friendly dolphin swam up to {name} with a playful smile. 'Hello! I'm Splash! Would you like a tour of our underwater kingdom?'\n\n{name} grabbed onto Splash's fin, and together they zoomed through the water, exploring caves, shipwrecks, and hidden grottos filled with treasure.",
            
            "As they swam deeper, {name} and Splash discovered a coral city where mermaids and mermen lived in harmony with all sea creatures.\n\nThe mer-people welcomed {name} warmly and showed them their beautiful gardens of sea flowers and their schools where young mer-children learned about ocean life.\n\nBut then {name} noticed something sad - a gentle sea turtle named Shelly was tangled in old fishing nets and plastic trash. She couldn't swim freely and looked very upset.\n\n{name}'s heart ached seeing Shelly in trouble. 'We have to help her!' {name} said to Splash. 'No creature should suffer because of pollution.'",
            
            "Working carefully and gently, {name} and Splash untangled the nets from Shelly's flippers. It took patience and teamwork, but finally, Shelly was free!\n\nShelly swam in happy circles, thanking {name} over and over. 'You saved me! Not many humans care about us sea creatures like you do.'\n\nThe mer-people gathered around {name} and explained how pollution from land was hurting their ocean home. Plastic, trash, and chemicals were making many sea animals sick.\n\n{name} felt determined to make a difference. 'I promise to help protect the ocean. I'll tell everyone how important it is to keep our seas clean.'",
            
            "As the magical seashell began to glow again, {name} knew it was time to return to land. Splash and all the new ocean friends gathered to say goodbye.\n\n'Remember,' Splash said, 'the ocean needs guardians like you. Every piece of trash you pick up, every person you teach about ocean protection, makes a real difference.'\n\nThe mer-people gave {name} a special pearl necklace. 'Wear this to remember us and your promise to protect our home,' they said with grateful smiles.\n\nBack on the beach, {name} held the glowing seashell and the pearl necklace close. From that day on, {name} became a true ocean guardian, teaching others and working to keep the seas clean and beautiful for all marine life."
        ],
        "lesson": {
            "title": "What {name} Learned",
            "points": [
                "🌊 The ocean is home to amazing creatures that need our protection and care",
                "♻️ Keeping our environment clean helps all living things thrive and stay healthy",
                "🐢 Every small action we take to help nature makes a big difference",
                "💙 We are all connected to nature, and it's our responsibility to be good guardians of the Earth"
            ]
        }
    }
}

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    mode = "FREE TEMPLATE MODE" if USE_FREE_MODE else "GROQ AI MODE (llama-3.3-70b)"
    print(f"\n{'='*60}")
    print(f"🚀 HYBRID Kids Story Generator Started")
    print(f"📊 Current Mode: {mode}")
    print(f"💡 To switch modes, set USE_FREE_MODE in .env file")
    print(f"{'='*60}\n")

# Mount static files
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/img", StaticFiles(directory="img"), name="img")

@app.get("/")
async def serve_index():
    """Serve the main HTML file"""
    return FileResponse("index.html")

@app.get("/api")
async def api_root():
    mode = "FREE (No API costs)" if USE_FREE_MODE else "AI-Powered (Gemini API)"
    return {
        "message": "HYBRID Kids Story Generator API is running!",
        "mode": mode,
        "cost": "FREE" if USE_FREE_MODE else "Uses API credits"
    }

@app.post("/generate-story", response_model=StoryResponse)
async def generate_story(request: StoryRequest):
    """Generate a story - uses FREE templates or Gemini AI based on configuration"""
    
    if USE_FREE_MODE:
        return await generate_free_story(request)
    else:
        return await generate_ai_story(request)

async def generate_free_story(request: StoryRequest):
    """Generate a FREE story using local templates"""
    try:
        print(f"📝 FREE Story generation: name={request.name}, age={request.age}, theme={request.theme}")
        
        theme = request.theme.lower()
        if theme not in STORY_TEMPLATES:
            theme = "adventure"
        
        template = STORY_TEMPLATES[theme]
        title = random.choice(template["titles"]).format(name=request.name)

        # Determine page count from length
        length_map = {"short": 3, "medium": 5, "long": 8}
        page_count = length_map.get((request.length or "medium").lower(), 5)

        # Gender pronoun substitution
        gender = (request.gender or "neutral").lower()
        pronoun_map = {
            "boy":     {"they": "he",  "them": "him",  "their": "his",  "they've": "he's",  "they're": "he's"},
            "girl":    {"they": "she", "them": "her",  "their": "her",  "they've": "she's", "they're": "she's"},
            "neutral": {},
            "both":    {},
        }
        pronouns = pronoun_map.get(gender, {})

        def apply_pronouns(text):
            for src, dst in pronouns.items():
                text = text.replace(f" {src} ", f" {dst} ")
                text = text.replace(f" {src.capitalize()} ", f" {dst.capitalize()} ")
            return text

        pages = []
        template_pages = template["pages"]
        # Trim or pad to page_count
        selected_pages = template_pages[:page_count]
        for i, page_text in enumerate(selected_pages, 1):
            formatted_text = apply_pronouns(page_text.format(name=request.name, age=request.age))
            # Extract first sentence as scene basis for a specific image prompt
            first_sentence = formatted_text.split('.')[0].strip()
            image_prompt = (
                f"{first_sentence}. "
                f"{request.name} is the main character, {theme} theme, "
                f"children's storybook scene"
            )
            pages.append(StoryPage(page_number=i, text=formatted_text, image_prompt=image_prompt))
        
        # Add lesson page
        lesson = template["lesson"]
        lesson_text = f"{lesson['title'].format(name=request.name)}\n\n" + "\n\n".join(lesson["points"])
        pages.append(StoryPage(
            page_number=len(pages) + 1,
            text=lesson_text,
            image_prompt=f"A warm, educational illustration showing {request.name} reflecting on their journey"
        ))
        story_data = {
            "title": title,
            "theme": request.theme,
            "pages": [{"page_number": p.page_number, "text": p.text, "image_prompt": p.image_prompt} for p in pages]
        }
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        full_text = json.dumps(story_data, default=str)
        cursor.execute(
            "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
            (request.name, request.theme, full_text, datetime.now())
        )
        story_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Return dict with story_id
        result = {
            "title": title,
            "theme": request.theme,
            "pages": story_data["pages"],
            "story_id": story_id,
            "char_desc": f"{request.age}-year-old child named {request.name}"
        }
        
        print(f"✅ FREE story generated: {title} (ID: {story_id})")
        return result
        
    except Exception as e:
        print(f"❌ Error generating FREE story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {str(e)}")

async def generate_ai_story(request: StoryRequest):
    """Generate an AI-powered story using Gemini"""
    try:
        print(f"📝 AI Story generation: name={request.name}, age={request.age}, theme={request.theme}")
        
        # Determine page count
        length_map = {"short": 3, "medium": 5, "long": 8}
        page_count = length_map.get((request.length or "medium").lower(), 5)
        story_pages = page_count  # story pages (lesson page added separately)

        # Gender pronouns
        gender = (request.gender or "neutral").lower()
        pronoun_str = {"boy": "he/him/his", "girl": "she/her/her", "neutral": "they/them/their", "both": "they/them/their (two main characters, one boy and one girl)"}.get(gender, "they/them/their")

        # Build page instructions dynamically
        page_instructions = ""
        for p in range(1, story_pages + 1):
            page_instructions += f'            {{{{"page_number": {p}, "text": "2-3 short paragraphs for page {p}.", "image_prompt": "Colorful scene"}}}},\n'
        lesson_num = story_pages + 1

        prompt = f"""
        Create an educational children's picture book story for a {request.age}-year-old named {request.name} with theme: {request.theme}.
        Use pronouns: {pronoun_str} for {request.name}.
        
        CRITICAL: Return ONLY valid JSON, no markdown, no extra text.
        
        {{
            "title": "Story Title Here",
            "pages": [
                {chr(10).join([f'{{"page_number": {p}, "text": "2-3 short paragraphs (3-4 sentences each) for page {p} of the story about {request.name}. Use pronouns {pronoun_str}.", "image_prompt": "Detailed scene description of exactly what is happening on this page: who is there, what they are doing, where they are, key objects visible. Be specific and visual."}},' for p in range(1, story_pages + 1)])}
                {{"page_number": {lesson_num}, "text": "What {request.name} Learned\\n\\n🌟 First lesson\\n\\n💫 Second lesson\\n\\n✨ Third lesson\\n\\n❤️ Fourth lesson", "image_prompt": "{request.name} smiling and surrounded by symbols of what they learned in the story, warm glowing background"}}
            ]
        }}
        
        REQUIREMENTS:
        - Exactly {story_pages + 1} pages ({story_pages} story + 1 lesson)
        - Each story page: 2-3 SHORT paragraphs, 3-4 sentences each
        - Use {pronoun_str} pronouns for {request.name} consistently
        - Age-appropriate for {request.age} years old
        - Educational values: kindness, courage, friendship, problem-solving
        - image_prompt: must describe the SPECIFIC scene on that page in detail (characters, action, setting, objects) — NOT generic
        - Return ONLY the JSON
        """
        
        model = groq_client.chat.completions
        
        # Try models in order of preference
        response = None
        last_error = None
        for model_name in ['llama-3.3-70b-versatile', 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant']:
            try:
                print(f"🤖 Trying model: {model_name}")
                chat_response = model.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=4096
                )
                response = chat_response.choices[0].message.content
                print(f"✅ Success with model: {model_name}")
                break
            except Exception as model_err:
                last_error = model_err
                print(f"⚠️ Model {model_name} failed: {str(model_err)[:100]}")
                continue
        
        if response is None:
            raise last_error
        
        if not response:
            raise HTTPException(status_code=500, detail="Empty response from AI")
        
        # Parse JSON response
        response_text = response.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            response_text = response_text[start_idx:end_idx]
        
        story_data = json.loads(response_text)
        
        if not isinstance(story_data, dict) or "title" not in story_data or "pages" not in story_data:
            raise HTTPException(status_code=500, detail="Invalid story structure from AI")
        
        # Add theme to story data
        story_data["theme"] = request.theme

        # ── Generate a fixed character description for visual consistency ────────
        # This description is injected into every page's image prompt so the
        # protagonist looks the same across all illustrations
        char_desc = ""
        try:
            desc_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Based on this children's story, write a SHORT physical description of the main character {request.name} "
                        f"for an illustrator. Include: age (child, ~{request.age} years old), hair color and style, eye color, "
                        f"skin tone, and ONE specific outfit they wear. Max 25 words. No sentences, just descriptive phrases.\n\n"
                        f"Story title: {story_data['title']}\n"
                        f"First page: {story_data['pages'][0]['text'][:200]}"
                    )
                }],
                temperature=0.3,
                max_tokens=50
            )
            char_desc = desc_response.choices[0].message.content.strip()
            story_data["char_desc"] = char_desc
            print(f"👤 Character description: {char_desc}")
        except Exception as e:
            print(f"⚠️ Could not generate char description: {e}")
            # Fallback: basic description from name + age + gender
            char_desc = f"{request.age}-year-old child"
            story_data["char_desc"] = char_desc

        # Validate structure
        story_response = StoryResponse(
            title=story_data["title"],
            theme=story_data["theme"],
            pages=[StoryPage(**page) for page in story_data["pages"]],
            story_id=None
        )
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        full_text = json.dumps(story_data)
        cursor.execute(
            "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
            (request.name, request.theme, full_text, datetime.now())
        )
        story_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Return dict with story_id
        result = {
            "title": story_data["title"],
            "theme": story_data["theme"],
            "pages": story_data["pages"],
            "story_id": story_id,
            "char_desc": story_data.get("char_desc", "")
        }
        
        print(f"✅ AI story generated: {story_data['title']} (ID: {story_id})")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating AI story: {error_msg}")
        # If quota/API error, fall back to free templates automatically
        if "429" in error_msg or "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
            print("⚠️ API quota/error - falling back to FREE template mode")
            return await generate_free_story(request)
        raise HTTPException(status_code=500, detail=f"Error generating story: {error_msg}")

@app.get("/stories")
async def get_recent_stories():
    """Get recent stories from the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # First check what columns exist in the table
        cursor.execute("PRAGMA table_info(stories)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📊 Database columns: {columns}")
        
        # Build query based on available columns
        if 'theme' in columns:
            cursor.execute(
                "SELECT id, name, theme, full_text, date, is_favorite, rating FROM stories ORDER BY date DESC"
            )
        else:
            # Fallback for old database without theme column
            cursor.execute(
                "SELECT id, name, full_text, date FROM stories ORDER BY date DESC"
            )
        
        stories = []
        for row in cursor.fetchall():
            try:
                if 'theme' in columns:
                    story_id, name, theme, text_data, date, is_fav, rating = row
                else:
                    story_id, name, text_data, date = row
                    theme = "adventure"
                    is_fav = 0
                    rating = None
                
                if text_data:
                    # Try to parse as JSON first
                    try:
                        story_data = json.loads(text_data)
                        # Check if it's a dict (new format) or string (old format)
                        if isinstance(story_data, dict):
                            stories.append({
                                "id": story_id,
                                "name": name,
                                "theme": theme,
                                "title": story_data.get("title", "Untitled Story"),
                                "date": date,
                                "is_favorite": is_fav == 1,
                                "rating": rating,
                                "preview": story_data.get("pages", [{}])[0].get("text", "")[:100] + "..." if story_data.get("pages") else "",
                                "customCoverNumber": story_data.get("customCoverNumber"),
                                "isCustomTheme": story_data.get("isCustomTheme", False)
                            })
                        else:
                            # Old format - story_data is a string
                            stories.append({
                                "id": story_id,
                                "name": name,
                                "theme": theme,
                                "title": f"Story for {name}",
                                "date": date,
                                "is_favorite": is_fav == 1,
                                "rating": rating,
                                "preview": str(story_data)[:100] + "..."
                            })
                    except (json.JSONDecodeError, TypeError):
                        # If JSON parsing fails, treat as plain text
                        stories.append({
                            "id": story_id,
                            "name": name,
                            "theme": theme,
                            "title": f"Story for {name}",
                            "date": date,
                            "preview": str(text_data)[:100] + "..."
                        })
            except Exception as e:
                print(f"⚠️ Error processing story {story_id}: {e}")
                continue
        
        conn.close()
        print(f"✅ Returning {len(stories)} stories")
        return {"stories": stories}
        
    except Exception as e:
        print(f"❌ Error fetching stories: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching stories: {str(e)}")

@app.get("/stories/{story_id}")
async def get_story(story_id: int):
    """Get a specific story by ID"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT full_text, is_favorite, rating FROM stories WHERE id = ?", (story_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Story not found")
        
        try:
            parsed = json.loads(result[0])
            if not isinstance(parsed, dict):
                raise ValueError("Not a dict")
            story_data = parsed
            story_data["is_favorite"] = result[1] == 1
            story_data["story_id"] = story_id
            story_data["rating"] = result[2]
        except (json.JSONDecodeError, TypeError, ValueError):
            story_data = {
                "title": f"Story #{story_id}",
                "pages": [{"page_number": 1, "text": str(result[0]), "image_prompt": "A story illustration"}],
                "is_favorite": result[1] == 1,
                "rating": result[2],
                "story_id": story_id
            }
        
        conn.close()
        return story_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching story: {str(e)}")

@app.post("/stories/{story_id}/favorite")
async def toggle_favorite(story_id: int):
    """Toggle favorite status for a story"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get current favorite status
        cursor.execute("SELECT is_favorite FROM stories WHERE id = ?", (story_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Toggle the favorite status
        new_status = 0 if result[0] == 1 else 1
        cursor.execute("UPDATE stories SET is_favorite = ? WHERE id = ?", (new_status, story_id))
        conn.commit()
        conn.close()
        
        print(f"✅ Story {story_id} favorite status: {new_status == 1}")
        return {"success": True, "is_favorite": new_status == 1}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling favorite: {str(e)}")

@app.get("/favorites")
async def get_favorites():
    """Get all favorite stories"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, name, theme, full_text, date FROM stories WHERE is_favorite = 1 ORDER BY date DESC"
        )
        
        favorites = []
        for row in cursor.fetchall():
            story_id, name, theme, text_data, date = row
            try:
                if text_data:
                    try:
                        story_data = json.loads(text_data)
                        if isinstance(story_data, dict):
                            favorites.append({
                                "id": story_id,
                                "name": name,
                                "theme": theme,
                                "title": story_data.get("title", "Untitled Story"),
                                "dateAdded": date,
                                "customCoverNumber": story_data.get("customCoverNumber"),
                                "isCustomTheme": story_data.get("isCustomTheme", False)
                            })
                        else:
                            favorites.append({
                                "id": story_id,
                                "name": name,
                                "theme": theme,
                                "title": f"Story for {name}",
                                "dateAdded": date
                            })
                    except (json.JSONDecodeError, TypeError):
                        favorites.append({
                            "id": story_id,
                            "name": name,
                            "theme": theme,
                            "title": f"Story for {name}",
                            "dateAdded": date
                        })
            except Exception as e:
                print(f"⚠️ Error processing favorite {story_id}: {e}")
                continue
        
        conn.close()
        print(f"✅ Returning {len(favorites)} favorite stories")
        return {"favorites": favorites}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching favorites: {str(e)}")

@app.delete("/stories/{story_id}")
async def delete_story(story_id: int):
    """Delete a story from the database (also removes from favorites if favorited)"""
    try:
        print(f"🗑️ Attempting to delete story ID: {story_id}")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if story exists
        cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            print(f"❌ Story {story_id} not found")
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Delete the story (this will automatically remove it from favorites too since it's the same table)
        cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Story {story_id} deleted successfully (rows affected: {rows_affected})")
        return {"success": True, "message": "Story deleted successfully", "story_id": story_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting story {story_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting story: {str(e)}")

@app.post("/stories/{story_id}/update")
async def update_story_cover(story_id: int, data: dict):
    """Update story with custom cover number"""
    try:
        print(f"🔄 Updating story {story_id} with cover data: {data}")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get current story
        cursor.execute("SELECT full_text FROM stories WHERE id = ?", (story_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Parse and update story data
        story_data = json.loads(result[0])
        story_data["customCoverNumber"] = data.get("customCoverNumber")
        story_data["isCustomTheme"] = data.get("isCustomTheme", False)
        
        # Save back to database
        cursor.execute(
            "UPDATE stories SET full_text = ? WHERE id = ?",
            (json.dumps(story_data), story_id)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Story {story_id} updated with cover number {data.get('customCoverNumber')}")
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating story: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating story: {str(e)}")


@app.get("/story-image/{story_id}/{page}")
async def serve_story_image(story_id: int, page: int):
    """Serve a saved story page image from disk"""
    for ext in ("webp", "png", "jpg"):
        path = IMAGES_DIR / f"{story_id}_page_{page}.{ext}"
        if path.exists():
            return FileResponse(str(path), media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="Image not found")


@app.post("/generate-image")
async def generate_image(data: dict):
    """
    Generate illustration for a story page.

    Features:
    - Checks disk cache first — if image already saved, returns it instantly (no API call)
    - Consistent character: same seed per story_id so protagonist looks the same on every page
    - Fallback chain: replicate → gradio → HF inference (automatic, tries each if previous fails)

    Pipeline: page text → Groq extracts 40-word visual scene → image model → saved to disk
    """
    page_text  = data.get("text", "")
    story_id   = data.get("story_id")       # used for cache key + consistent seed
    page_num   = data.get("page_num", 0)    # used for cache key
    char_name  = data.get("char_name", "")  # protagonist name for consistency
    char_desc  = data.get("char_desc", "")  # e.g. "young boy with brown hair, red shirt"

    if not page_text:
        raise HTTPException(status_code=400, detail="No text provided")

    # ── Check disk cache first ─────────────────────────────────────────────────
    # If this page was already generated, return it immediately — no API call needed
    if story_id and page_num:
        for ext in ("webp", "png", "jpg"):
            cached = IMAGES_DIR / f"{story_id}_page_{page_num}.{ext}"
            if cached.exists():
                with open(cached, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                print(f"💾 Cache hit: story {story_id} page {page_num}")
                return {"image": f"data:image/{ext};base64,{img_b64}", "scene_prompt": "cached", "cached": True}

    # ── Step 1: Groq extracts a tight visual scene from the page text ──────────
    scene_prompt = page_text[:120]  # fallback if Groq fails
    try:
        if not USE_FREE_MODE and groq_client:
            summarise = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # 14.4K RPD free — saves 70b quota
                messages=[{
                    "role": "user",
                    "content": (
                        "Read this children's story page and write ONE visual scene description "
                        "(max 40 words) for an illustrator. Describe exactly what is visible: "
                        "characters, their actions, the setting, key objects. No narration, just visuals.\n\n"
                        f"Page text:\n{page_text}"
                    )
                }],
                temperature=0.4,
                max_tokens=80
            )
            scene_prompt = summarise.choices[0].message.content.strip()
            print(f"🎨 Scene prompt: {scene_prompt}")
    except Exception as e:
        print(f"⚠️ Groq scene extract failed, using raw text: {e}")
        sentences = page_text.replace('\n', ' ').split('. ')
        scene_prompt = '. '.join(sentences[:2])

    # ── Step 2: Build prompt with consistent character description ─────────────
    # char_desc is generated ONCE per story by Groq and saved in the DB.
    # Injecting it into every page prompt keeps the protagonist looking the same.
    char_part = ""
    if char_name and char_desc:
        char_part = f"The main character {char_name} looks like this in every scene: {char_desc}. "
    elif char_name:
        char_part = f"The main character is a child named {char_name}. "

    prompt = (
        f"children's picture book illustration: {char_part}{scene_prompt}. "
        "Soft watercolor and gouache style, warm pastel colors, "
        "expressive friendly characters, detailed whimsical background, "
        "storybook art, high quality, vibrant, no text, no words, no letters"
    )

    # Consistent seed per story — same story_id always produces same character look
    # We derive a fixed integer seed from the story_id
    seed = None
    if story_id:
        seed = int(hashlib.md5(str(story_id).encode()).hexdigest()[:8], 16) % 2147483647

    # ── Step 3: Call the selected image backend ────────────────────────────────
    image_mode = os.getenv("IMAGE_MODE", "gradio").lower()
    print(f"🖼️ Image mode: {image_mode}")

    img_b64 = None
    img_ext = "webp"
    used_backend = image_mode

    # --- REPLICATE ---
    if image_mode == "replicate":
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
        if not replicate_token:
            raise HTTPException(status_code=500, detail="REPLICATE_API_TOKEN not set in .env")
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers={"Authorization": f"Bearer {replicate_token}", "Content-Type": "application/json", "Prefer": "wait"},
                json={"input": {"prompt": prompt, "num_outputs": 1, "output_format": "webp", **({"seed": seed} if seed else {})}}
            )
            if r.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail=f"Replicate error {r.status_code}: {r.text[:200]}")
            result = r.json()
            if result.get("status") not in ("succeeded", None) or not result.get("output"):
                poll_url = result.get("urls", {}).get("get", "")
                for _ in range(30):
                    await asyncio.sleep(2)
                    pr = await client.get(poll_url, headers={"Authorization": f"Bearer {replicate_token}"})
                    result = pr.json()
                    if result.get("status") == "succeeded":
                        break
                    if result.get("status") == "failed":
                        raise HTTPException(status_code=502, detail="Replicate prediction failed")
            output = result.get("output")
            if not output:
                raise HTTPException(status_code=502, detail="No output from Replicate")
            img_url = output[0] if isinstance(output, list) else output
            img_b64 = base64.b64encode((await client.get(img_url)).content).decode("utf-8")
            img_ext = "webp"
            print("✅ Replicate success")

    # --- GRADIO ---
    elif image_mode == "gradio":
        from gradio_client import Client as GradioClient

        def _call_gradio():
            gc = GradioClient("evalstate/flux1_schnell")
            result, _ = gc.predict(prompt=prompt, randomize_seed=True, width=1024, height=1024, num_inference_steps=4, api_name="/infer")
            return result

        result = await asyncio.get_event_loop().run_in_executor(None, _call_gradio)
        raw = None
        if isinstance(result, dict):
            url = result.get("url")
            path = result.get("path")
            if url and url.startswith("data:"):
                raw = base64.b64decode(url.split(",", 1)[1])
            elif url:
                async with httpx.AsyncClient(timeout=30) as hc:
                    raw = (await hc.get(url)).content
            elif path:
                with open(path, "rb") as f:
                    raw = f.read()
        elif isinstance(result, str):
            with open(result, "rb") as f:
                raw = f.read()
        if not raw:
            raise HTTPException(status_code=502, detail="No image from Gradio Space")
        img_b64 = base64.b64encode(raw).decode("utf-8")
        img_ext = "jpg"
        print("✅ Gradio success")

    # --- HF INFERENCE ---
    elif image_mode == "inference":
        hf_key = os.getenv("HUGGINGFACE_API_KEY", "")
        if not hf_key:
            raise HTTPException(status_code=500, detail="HUGGINGFACE_API_KEY not set in .env")
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
                headers={"Authorization": f"Bearer {hf_key}"},
                json={"inputs": prompt}
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"HF Inference error {r.status_code}: {r.text[:200]}")
            img_b64 = base64.b64encode(r.content).decode("utf-8")
            img_ext = "jpg"
            print("✅ HF Inference success")

    else:
        raise HTTPException(status_code=500, detail=f"Unknown IMAGE_MODE '{image_mode}'. Use: replicate, gradio, or inference")

    if not img_b64:
        raise HTTPException(status_code=503, detail="Image generation failed")

    # ── Step 4: Save to disk permanently ──────────────────────────────────────
    if story_id and page_num:
        save_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{img_ext}"
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(img_b64))
        print(f"💾 Saved: {save_path} (via {used_backend})")

    return {
        "image": f"data:image/{img_ext};base64,{img_b64}",
        "scene_prompt": scene_prompt,
        "backend": used_backend,
        "cached": False
    }


@app.get("/stats")
async def get_stats():
    """Return total stories and favorites count"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stories")
        total_stories = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stories WHERE is_favorite = 1")
        total_favorites = cursor.fetchone()[0]
        conn.close()
        return {"total_stories": total_stories, "total_favorites": total_favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stories/{story_id}/rate")
async def rate_story(story_id: int, data: dict):
    """Save a 1-5 star rating for a story"""
    try:
        rating = int(data.get("rating", 0))
        if not 1 <= rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be 1-5")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Story not found")
        cursor.execute("UPDATE stories SET rating = ? WHERE id = ?", (rating, story_id))
        conn.commit()
        conn.close()
        print(f"⭐ Story {story_id} rated {rating}/5")
        return {"success": True, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/groq-quota")
async def check_groq_quota():
    """Check Groq API usage/quota by making a minimal test call"""
    if USE_FREE_MODE or not groq_client:
        return {"mode": "FREE", "message": "Groq API not active (USE_FREE_MODE=true)"}
    try:
        # Minimal token call to check if API key works and get rate limit headers
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }
            )
        headers = dict(r.headers)
        # Groq returns rate limit info in headers
        quota_info = {
            "status": r.status_code,
            "requests_limit": headers.get("x-ratelimit-limit-requests"),
            "requests_remaining": headers.get("x-ratelimit-remaining-requests"),
            "requests_reset": headers.get("x-ratelimit-reset-requests"),
            "tokens_limit": headers.get("x-ratelimit-limit-tokens"),
            "tokens_remaining": headers.get("x-ratelimit-remaining-tokens"),
            "tokens_reset": headers.get("x-ratelimit-reset-tokens"),
        }
        if r.status_code == 429:
            quota_info["message"] = "Rate limit hit"
        elif r.status_code == 200:
            quota_info["message"] = "API key valid, quota available"
        else:
            quota_info["message"] = f"Unexpected status: {r.status_code}"
        return quota_info
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    mode = "FREE TEMPLATE MODE (No API costs)" if USE_FREE_MODE else "GROQ AI MODE (llama-3.3-70b, 14400 req/day free)"
    print(f"\n{'='*60}")
    print(f"🚀 Starting HYBRID Kids Story Generator")
    print(f"📊 Mode: {mode}")
    print(f"🌐 Access: http://localhost:8025")
    print(f"💡 Switch modes by editing USE_FREE_MODE in .env")
    print(f"🛑 Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8025,
        log_level="info",
        access_log=False
    )
