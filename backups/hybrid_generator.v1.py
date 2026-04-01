import os
import sqlite3
import json
import random
import httpx
import base64
import asyncio
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()

USE_FREE_MODE = os.getenv("USE_FREE_MODE", "true").lower() == "true"
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
groq_client   = None

if not USE_FREE_MODE:
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not found — falling back to FREE mode.")
        USE_FREE_MODE = True
    else:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)

# ── Storage paths ─────────────────────────────────────────────────────────────
DATABASE_PATH = "stories.db"
IMAGES_DIR    = Path("img/generated")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
def init_database():
    conn   = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE stories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                theme       TEXT    NOT NULL,
                full_text   TEXT    NOT NULL,
                is_favorite INTEGER DEFAULT 0,
                date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rating      INTEGER DEFAULT NULL
            )
        """)
        print("✅ Created stories table")
    else:
        cursor.execute("PRAGMA table_info(stories)")
        cols = [c[1] for c in cursor.fetchall()]
        migrations = {
            "full_text":   "ALTER TABLE stories ADD COLUMN full_text TEXT",
            "is_favorite": "ALTER TABLE stories ADD COLUMN is_favorite INTEGER DEFAULT 0",
            "rating":      "ALTER TABLE stories ADD COLUMN rating INTEGER DEFAULT NULL",
        }
        for col, sql in migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"✅ Migrated: added '{col}' column")

    conn.commit()
    conn.close()


# ── FastAPI app ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    mode = "FREE TEMPLATE MODE" if USE_FREE_MODE else "GROQ AI MODE (llama-3.3-70b)"
    img_mode = os.getenv("IMAGE_MODE", "gradio")
    print(f"\n{'='*55}")
    print(f"🚀  Kids Story Generator started")
    print(f"📖  Story mode : {mode}")
    print(f"🖼️   Image mode : {img_mode}")
    print(f"🌐  URL        : http://localhost:8025")
    print(f"{'='*55}\n")
    yield

app = FastAPI(title="Kids Story Generator", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8025", "http://127.0.0.1:8025",
                   "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js",  StaticFiles(directory="js"),  name="js")
app.mount("/img", StaticFiles(directory="img"), name="img")

# ── Pydantic models ───────────────────────────────────────────────────────────
class StoryRequest(BaseModel):
    name:   str
    age:    int
    theme:  str
    length: Optional[str] = "medium"   # short / medium / long
    gender: Optional[str] = "boy"      # boy / girl / both

class StoryPage(BaseModel):
    page_number:  int
    text:         str
    image_prompt: Optional[str] = ""

class StoryResponse(BaseModel):
    title:    str
    theme:    str
    pages:    List[StoryPage]
    story_id: Optional[int] = None
    class Config:
        extra = "allow"


# ── Story templates (free mode) ───────────────────────────────────────────────
STORY_TEMPLATES = {
    "adventure": {
        "titles": ["{name}'s Great Adventure", "The Amazing Journey of {name}",
                   "{name} and the Hidden Treasure", "{name}'s Mountain Quest"],
        "pages": [
            "Once upon a time, in a cozy little town, there lived a brave {age}-year-old named {name}. {name} had always dreamed of going on a real adventure, just like the heroes in their favorite books.\n\nOne sunny morning, while playing in the backyard, {name} noticed something unusual. The old oak tree seemed to be glowing with a soft, golden light.\n\nCurious and excited, {name} walked closer to investigate. Hidden in a hollow of the tree trunk was an ancient, rolled-up map covered in mysterious symbols.\n\n{name}'s heart raced with excitement. This was it — the beginning of a real adventure!",
            "The map showed a path leading deep into the enchanted forest beyond the town. {name} packed a small backpack with snacks, water, and a lucky charm.\n\nAs {name} entered the forest, the trees seemed to whisper words of encouragement. Birds chirped cheerful melodies, as if cheering {name} on.\n\nSuddenly, a wise old owl landed on a branch nearby. 'Hello, young adventurer,' the owl hooted. 'I've been expecting you. The forest has many secrets to share.'\n\n{name} couldn't believe it — the owl was talking! This adventure was already more magical than {name} had ever imagined.",
            "Following the map, {name} came to a wide, rushing river. The water sparkled in the sunlight, but there was no bridge to cross.\n\n{name} sat down to think. Giving up wasn't an option — true adventurers always find a way. Looking around, {name} spotted fallen logs and strong vines nearby.\n\nWith determination and clever thinking, {name} began tying the logs together. It took time and effort, but slowly a sturdy raft took shape.\n\nA friendly beaver swam by and offered to help. Together, they created a safe way to cross. {name} learned that asking for help is a sign of wisdom, not weakness.",
            "On the other side of the river, the map led to a beautiful clearing filled with wildflowers. In the center stood an ancient stone chest.\n\n{name}'s hands trembled with excitement as they opened the chest. But instead of gold or jewels, inside were colorful friendship bracelets and a note.\n\nThe note read: 'The greatest treasure is the friends you make and the courage you discover along the way.' {name} smiled, understanding the true meaning.\n\nAll the forest animals gathered around — the owl, the beaver, rabbits, and deer. They had all been part of the adventure.",
            "As the sun began to set, {name} said goodbye to all the new friends. The owl gave {name} a special feather to remember the adventure.\n\n{name} walked back home, feeling taller and braver than before. The backpack was filled with friendship bracelets instead of treasure, but {name} felt richer than ever.\n\nMom and Dad were waiting at home with warm hugs. {name} excitedly shared stories of the magical day and the wonderful friends made along the way.\n\nThat night, {name} placed the owl feather on the bedside table and smiled. This was just the first of many adventures to come.",
            "{name} woke up the next morning still thinking about the adventure. The map was still there, glowing faintly on the desk.\n\nThis time, {name} invited two friends from school to come along. Together they followed a new path on the map, deeper into the forest.\n\nThey discovered a hidden waterfall and a family of deer who needed help finding their way home. Working as a team, the three friends guided the deer safely.\n\nAs they walked home, {name} realized that adventures are even better when shared with friends you trust.",
            "Word spread through the town about {name}'s adventures. Other children began to believe in magic and courage too.\n\n{name} started a small adventure club at school, teaching others how to read maps, work as a team, and be kind to animals.\n\nThe enchanted forest became a place of wonder for the whole town. People stopped cutting down trees and started protecting the animals.\n\n{name} understood that one brave step can change not just your own life, but the lives of everyone around you.",
            "Years later, {name} would look back on that first adventure with a warm smile. The owl feather still sat on the shelf, a reminder of where it all began.\n\nThe friendship bracelets were worn by {name}'s closest friends, a symbol of the bonds formed through courage and kindness.\n\nThe enchanted forest thrived, full of life and magic, because one child had chosen curiosity over fear.\n\nAnd whenever a new child in town felt scared or unsure, {name} would smile and say: 'Every great adventure starts with a single brave step.'"
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "🌟 True courage means trying new things even when you're a little scared",
            "🤝 The best treasures in life are the friends we make along the way",
            "💡 Using your brain to solve problems is just as important as being strong",
            "❤️ Asking for help from others shows wisdom and creates stronger friendships"
        ]}
    },
    "fantasy": {
        "titles": ["{name} and the Magic Kingdom", "The Enchanted World of {name}",
                   "{name}'s Magical Powers", "{name} and the Friendly Dragon"],
        "pages": [
            "{name}, a curious {age}-year-old, was exploring the attic when they found a dusty old trunk. Inside was a beautiful glowing crystal that pulsed with rainbow colors.\n\nThe moment {name} touched the crystal, the whole room filled with sparkling light. The walls seemed to melt away, revealing a magnificent magical kingdom.\n\nTowering castles made of crystal reached toward the clouds. Friendly unicorns grazed in meadows of flowers that sang gentle melodies.\n\n{name} stood in wonder, realizing that magic was real and this incredible adventure was just beginning.",
            "A kind wizard with a long silver beard approached {name} with a warm smile. 'Welcome, young one,' he said. 'We've been waiting for someone with a pure heart like yours.'\n\nThe wizard explained that {name} had a special gift — the ability to see and use magic that others couldn't. This gift came from having a kind and imaginative heart.\n\n{name} met Sparkle, a gentle dragon with scales that shimmered like opals. Sparkle became {name}'s guide and friend in this magical world.\n\nTogether, they began learning simple spells — making flowers bloom, creating tiny rainbows, and helping lost creatures find their way home.",
            "One day, dark storm clouds began covering the magical kingdom. The flowers stopped singing, and the unicorns looked worried.\n\nThe wizard told {name} that the kingdom needed help. Only someone with true magic in their heart could bring back the light and joy.\n\n{name} felt nervous but remembered all the lessons learned. With Sparkle by their side, {name} climbed to the highest tower of the crystal castle.\n\nTaking a deep breath, {name} focused on all the happy memories and kind thoughts. The crystal began to glow brighter and brighter.",
            "A brilliant beam of rainbow light shot from the crystal into the dark clouds. Slowly, the darkness began to fade away, replaced by warm sunshine.\n\nThe flowers started singing again, even more beautifully than before. All the magical creatures cheered and celebrated {name}'s bravery.\n\nThe wizard smiled proudly. 'You see, {name}, the real magic was inside you all along. It's your kindness, courage, and belief in yourself.'\n\n{name} understood now that magic isn't just about spells — it's about having a good heart and helping others.",
            "When it was time to go home, {name} felt sad to leave but knew this wasn't goodbye forever. The wizard gave {name} a small crystal to keep.\n\n'Whenever you need to remember the magic within you, just hold this crystal,' the wizard said. 'And remember, you can return anytime you believe.'\n\nSparkle nuzzled {name} gently, promising they would always be friends. {name} hugged the dragon's warm neck, feeling grateful for this amazing adventure.\n\nBack in the attic, {name} held the crystal tight and smiled. Magic was real, and it lived in every kind act and brave choice.",
            "{name} returned to the magical kingdom many times after that. Each visit brought new challenges and new friends to help.\n\nOne day, a young fairy named Lumi had lost her wings in a storm. {name} and Sparkle searched the entire kingdom until they found them.\n\nLumi was so grateful that she taught {name} a special song that could calm any storm. It was a gift that would prove useful many times.\n\n{name} learned that the more you give, the more magic grows in the world.",
            "The magical kingdom held a grand celebration in {name}'s honor. Creatures from every corner of the land came to give thanks.\n\nThe wizard announced that {name} had earned the title of Guardian of the Crystal Kingdom — a protector of magic and kindness.\n\n{name} accepted with a humble heart, promising to always use the gift of magic to help others, never for selfish reasons.\n\nSparkle roared with joy, sending colorful sparks into the sky that lit up the night like fireworks.",
            "Back home, {name} kept the crystal on the windowsill where moonlight made it glow softly each night.\n\nFriends and family noticed that {name} had changed — more patient, more kind, always ready to help someone in need.\n\nThe magic hadn't stayed in the kingdom. It had come home too, living in {name}'s heart and spreading to everyone around.\n\nAnd on quiet nights, if you listened very carefully, you could almost hear the flowers of the crystal kingdom singing a gentle lullaby."
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "✨ Real magic comes from having a kind heart and believing in yourself",
            "🐉 True friends support you and help you discover your special gifts",
            "🌈 When you help others, you make the whole world a brighter place",
            "💫 The most powerful magic is the love and kindness you share with others"
        ]}
    },
    "friendship": {
        "titles": ["{name} and the New Friend", "The Friendship Adventure of {name}",
                   "{name} Learns About Kindness", "{name}'s Circle of Friends"],
        "pages": [
            "It was {name}'s first day back at school after summer vacation. The {age}-year-old walked into the classroom excited to see old friends.\n\nBut {name} noticed someone new — a quiet student sitting alone in the corner, looking down at their desk. The new student seemed nervous and a little sad.\n\nWhile everyone else was busy chatting, {name} remembered how it felt to be new. It can be scary and lonely.\n\n{name} made a decision. Instead of rushing to sit with old friends, {name} walked over to the new student with a warm smile.",
            "'Hi! I'm {name},' they said cheerfully. 'Would you like to sit with me at lunch today? I can show you around the school.'\n\nThe new student looked up with surprised, hopeful eyes. 'Really? That would be amazing. I'm Alex, and I just moved here. I don't know anyone yet.'\n\nAt lunch, {name} shared their favorite sandwich and told Alex all about the school. Alex started to smile and relax.\n\nThey discovered they both loved the same books, the same games, and even had the same favorite color. It felt like they had known each other forever.",
            "During recess, {name} invited Alex to play with the other kids. At first, Alex was shy, but {name} stayed close and made sure Alex felt included.\n\nThey played tag, swung on the swings, and laughed together. {name} introduced Alex to all their friends, and soon everyone was having fun.\n\nBut then something not-so-nice happened. A couple of kids started making fun of Alex's new backpack, saying it looked different and weird.\n\n{name} saw Alex's face fall and knew this was a moment that mattered. True friends stand up for each other, even when it's hard.",
            "{name} stepped forward bravely. 'I think Alex's backpack is really cool and unique. Being different makes us special, not weird.'\n\nThe other kids looked surprised. {name} continued, 'How would you feel if someone made fun of something you liked? We should be kind to everyone.'\n\nThe kids who had been mean looked down, feeling a bit ashamed. One of them apologized to Alex, and soon everyone was being friendly again.\n\nAlex smiled at {name} with grateful eyes. 'Thank you for being such a good friend. You made me feel like I belong here.'",
            "From that day forward, {name} and Alex became best friends. They did homework together, played together, and shared all their secrets.\n\n{name} learned that being a good friend means more than just having fun together. It means listening when someone is sad, standing up for what's right, and always being kind.\n\nAlex taught {name} new games from their old town, and {name} showed Alex all the best spots in the neighborhood. They made each other's lives brighter and happier.\n\nAs they walked home together that afternoon, both {name} and Alex knew they had found something truly special — a friendship that would last forever.",
            "A few weeks later, {name} noticed that Alex seemed sad again. This time it wasn't about school — Alex missed their old home and old friends.\n\n{name} listened carefully without interrupting. Sometimes the best thing a friend can do is simply listen.\n\nThen {name} had an idea. They helped Alex write letters to their old friends and even set up a video call so Alex could see familiar faces.\n\nAlex's eyes lit up with joy. 'You thought of everything!' {name} smiled. 'That's what friends are for.'",
            "The whole class noticed how kind {name} was to Alex. Inspired, other students began looking out for each other too.\n\nThe classroom became a warmer, kinder place. Even the teacher commented on how the class had grown into a real community.\n\n{name} realized that one act of kindness can start a chain reaction. When you treat someone well, they treat others well too.\n\nKindness, {name} discovered, is like a seed. Plant one, and a whole garden grows.",
            "At the end of the school year, the class made a friendship wall — a big poster covered in handprints and kind words for each other.\n\nAlex wrote next to {name}'s handprint: 'The first person who made me feel at home. My best friend.'\n\n{name} felt a warm glow in their chest reading those words. No trophy or prize could feel better than knowing you made someone feel loved.\n\nAs summer began, {name} and Alex made plans for adventures ahead — proof that the best stories start with a simple, kind hello."
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "🤗 A simple act of kindness can change someone's whole day",
            "💪 Standing up for your friends, even when it's hard, shows true courage",
            "🌟 Everyone deserves to feel included and valued for who they are",
            "❤️ The best friendships are built on kindness, loyalty, and understanding"
        ]}
    },
    "animals": {
        "titles": ["{name} and the Forest Friends", "The Animal Adventure of {name}",
                   "{name}'s Pet Rescue Mission", "{name} and the Talking Animals"],
        "pages": [
            "{name}, an animal-loving {age}-year-old, woke up one morning to discover something incredible. They could understand what animals were saying!\n\nA little bird chirped outside the window, and {name} heard it clearly: 'Good morning! The sunrise is beautiful today!' {name} gasped in amazement.\n\nRunning outside, {name} found the family dog, Max, wagging his tail. 'Finally, you can hear me!' Max barked happily. 'I've been trying to tell you jokes for years!'\n\n{name} laughed with joy. This was the most amazing gift ever — being able to talk with animal friends!",
            "Later that day, a worried rabbit hopped up to {name} in the backyard. 'Please help me,' the rabbit said with tears in her eyes. 'My family is lost in the big forest.'\n\n{name}'s heart filled with concern. 'Don't worry, I'll help you find them,' {name} promised. 'We'll search together until we bring your family home safely.'\n\nThe rabbit, whose name was Rosie, explained that her family had gone looking for food but hadn't returned. They might be scared and alone.\n\n{name} knew this was important. Animals are part of our world too, and they deserve our help and protection.",
            "{name} gathered a team of animal friends to help with the rescue. A wise old owl named Oliver agreed to search from the sky with his sharp eyes.\n\nA strong, gentle bear named Bruno offered to move heavy branches that might be blocking paths. A quick squirrel named Sammy volunteered to check all the tree hollows.\n\nTogether, this amazing team entered the forest. {name} felt proud to be working with such wonderful animal friends, each using their special abilities.\n\nThey followed tiny paw prints in the soft dirt, listened for soft rabbit calls, and checked every burrow and hiding spot they could find.",
            "After hours of searching, Oliver hooted from above. 'I see them! They're trapped in a small cave behind some fallen rocks!'\n\nEveryone rushed to the spot. Bruno used his strength to carefully move the rocks while {name} called out encouraging words to the scared rabbit family.\n\nFinally, the opening was clear. Rosie's family hopped out, tired but safe. The reunion was beautiful — all the rabbits hugged and cried happy tears.\n\nRosie turned to {name} with grateful eyes. 'Thank you for caring about us. You're a true friend to all animals.'",
            "As the sun set, all the forest animals gathered around {name}. They wanted to thank this special human who had shown such kindness and respect.\n\nOliver the owl spoke wisely: '{name}, you have a gift not just to hear us, but to truly care about us. That makes you very special indeed.'\n\n{name} realized that caring for animals and nature wasn't just fun — it was an important responsibility. Every creature, big or small, deserves kindness and protection.\n\nWalking home that evening, {name} made a promise to always be a voice for animals and to protect the natural world.",
            "The next day, {name} visited the local animal shelter and volunteered to help care for the animals there.\n\nThere was a shy cat named Biscuit who wouldn't come near anyone. {name} sat quietly nearby, speaking softly, until Biscuit slowly crept closer.\n\nBy the end of the afternoon, Biscuit was purring in {name}'s lap. The shelter workers were amazed — Biscuit had never trusted anyone before.\n\n{name} understood that patience and gentleness can open even the most frightened heart.",
            "{name} started a nature club at school, teaching classmates about local wildlife and how to protect it.\n\nThey planted a small garden to attract butterflies and bees. They built birdhouses and set up a water station for animals during hot days.\n\nThe school garden became a tiny sanctuary, buzzing and chirping with life. Other schools heard about it and wanted to do the same.\n\n{name} learned that protecting nature doesn't require grand gestures — small, consistent acts of care make a real difference.",
            "Years later, {name} became known in the community as the person to call when an animal was in trouble.\n\nA fox with an injured paw, a bird with a broken wing, a lost puppy in the rain — {name} helped them all.\n\nAnd sometimes, late at night, {name} would hear a familiar hoot outside the window. Oliver the owl, still watching over a dear old friend.\n\n{name} would smile and whisper, 'I hear you, Oliver.' And the owl would hoot back, as if to say, 'I know you do.'"
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "🐾 All animals deserve our kindness, respect, and protection",
            "🌳 Taking care of nature and wildlife is everyone's responsibility",
            "🤝 Working together as a team makes us stronger and helps us achieve great things",
            "💚 When we help animals and nature, we make the whole world a better place"
        ]}
    },
    "space": {
        "titles": ["{name}'s Space Adventure", "Captain {name} and the Star Quest",
                   "{name} Visits the Moon", "{name} and the Friendly Aliens"],
        "pages": [
            "{name}, a {age}-year-old who loved everything about space, spent every night gazing at the stars through a telescope. The universe seemed so vast and full of mysteries.\n\nOne day, {name} decided to build a rocket ship in the backyard using cardboard boxes, aluminum foil, and lots of imagination. It looked amazing!\n\n{name} climbed inside the cardboard rocket, closed their eyes, and imagined blasting off into space. Suddenly, the rocket began to shake and rumble.\n\nTo {name}'s absolute amazement, the cardboard rocket actually lifted off the ground! The power of imagination and dreams had made it real!",
            "The rocket soared higher and higher, past the clouds, past the atmosphere, and into the starry darkness of space. {name} looked out the window in wonder.\n\nPlanets of every color floated by — red Mars, giant Jupiter with its swirling storms, and beautiful Saturn with its glittering rings.\n\n{name} spotted a colorful planet that wasn't on any map. It had purple mountains, orange rivers, and cities that sparkled like diamonds.\n\nDeciding to explore, {name} carefully landed the rocket on this mysterious new world. The adventure was just beginning!",
            "As {name} stepped out of the rocket, a group of friendly alien children came running over. They had big curious eyes and skin that shimmered with different colors.\n\n'Welcome to Planet Harmony!' they said in a musical language that {name} could somehow understand. 'We love meeting new friends from other worlds!'\n\nThe alien children showed {name} their incredible crystal cities that floated in the air. They played games surprisingly similar to Earth games — tag, hide and seek, and catch.\n\n{name} realized that even though they looked different, kids everywhere in the universe loved to play, laugh, and make friends.",
            "The alien children taught {name} how to float and bounce in the planet's low gravity. They soared through the air together, giggling and doing flips.\n\n{name} shared stories about Earth — about oceans, forests, animals, and all the wonderful things back home. The alien children listened with fascination.\n\nIn return, they showed {name} their amazing technology — books that came to life with holograms, food that grew instantly from seeds, and music you could see as colorful lights.\n\n{name} learned that every planet and every culture has something special and beautiful to share with others.",
            "As it was time to go home, the alien children gave {name} a special gift — a small crystal that glowed with the light of their planet's three suns.\n\n'This will help you remember that friendship exists throughout the entire universe,' they said. 'Distance doesn't matter when hearts are connected.'\n\n{name} hugged each new friend goodbye and promised to visit again someday. The rocket lifted off, and {name} waved until the colorful planet was just a tiny dot.\n\nFlying back to Earth, {name} looked at the crystal and smiled. The universe was full of friends waiting to be discovered.",
            "Back on Earth, {name} couldn't stop thinking about Planet Harmony. The crystal glowed softly on the desk each night.\n\n{name} began studying astronomy seriously, learning the names of every star and planet. Teachers were amazed by the sudden passion for science.\n\nOne evening, the crystal pulsed three times — a signal! The alien friends were sending a message in light patterns.\n\n{name} decoded it carefully: 'We miss you. The stars connect us always.' {name} flashed a torch three times back into the night sky.",
            "{name} gave a presentation at school about the visit to Planet Harmony. At first, classmates weren't sure whether to believe it.\n\nBut {name} showed them the glowing crystal, and one by one, their eyes went wide with wonder.\n\nThe presentation inspired the whole class to start a space science project. They built a model solar system and added Planet Harmony to it.\n\n{name} learned that sharing your experiences — even the unbelievable ones — can inspire others to dream bigger.",
            "Years later, {name} became an astronaut. On the first mission to deep space, the crew spotted something extraordinary — a planet with purple mountains and orange rivers.\n\nThe captain looked at {name} with wide eyes. {name} just smiled and said, 'I've been here before.'\n\nThe alien children, now grown, came out to greet their old friend. The reunion was joyful, full of laughter and shared memories.\n\nAnd {name} knew, with absolute certainty, that the universe is not a cold and empty place — it is full of friends, waiting to be found."
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "🌟 The power of imagination and dreams can take you anywhere you want to go",
            "👽 Even though people may look different, we all share the same feelings and desires for friendship",
            "🚀 Being curious and open to new experiences leads to amazing discoveries",
            "💫 Friendship has no boundaries — it exists everywhere in the universe"
        ]}
    },
    "ocean": {
        "titles": ["{name} and the Ocean Adventure", "The Underwater World of {name}",
                   "{name} Meets the Mermaids", "{name}'s Deep Sea Discovery"],
        "pages": [
            "{name}, a {age}-year-old who loved the ocean, was walking along the beach one morning when something caught their eye. A beautiful seashell was glowing with a soft blue light.\n\nPicking up the shell, {name} heard a gentle voice whisper: 'Hold me close and make a wish to explore the ocean depths.' It sounded like the voice of the sea itself.\n\n{name} closed their eyes and wished with all their heart to see the underwater world. Suddenly, the shell glowed brighter and brighter.\n\nWhen {name} opened their eyes, they were standing underwater, breathing easily as if they had gills! The magical seashell had granted the wish!",
            "The underwater world was more beautiful than {name} had ever imagined. Coral reefs in every color of the rainbow stretched as far as the eye could see.\n\nSchools of tropical fish swam by in perfect formation, their scales glittering like jewels. Sea turtles glided gracefully through the water, and seahorses danced among the seaweed.\n\nSuddenly, a friendly dolphin swam up to {name} with a playful smile. 'Hello! I'm Splash! Would you like a tour of our underwater kingdom?'\n\n{name} grabbed onto Splash's fin, and together they zoomed through the water, exploring caves, shipwrecks, and hidden grottos.",
            "As they swam deeper, {name} and Splash discovered a coral city where mermaids and mermen lived in harmony with all sea creatures.\n\nThe mer-people welcomed {name} warmly and showed them their beautiful gardens of sea flowers and their schools where young mer-children learned about ocean life.\n\nBut then {name} noticed something sad — a gentle sea turtle named Shelly was tangled in old fishing nets and plastic trash. She couldn't swim freely and looked very upset.\n\n{name}'s heart ached seeing Shelly in trouble. 'We have to help her!' {name} said to Splash. 'No creature should suffer because of pollution.'",
            "Working carefully and gently, {name} and Splash untangled the nets from Shelly's flippers. It took patience and teamwork, but finally, Shelly was free!\n\nShelly swam in happy circles, thanking {name} over and over. 'You saved me! Not many humans care about us sea creatures like you do.'\n\nThe mer-people gathered around {name} and explained how pollution from land was hurting their ocean home. Plastic, trash, and chemicals were making many sea animals sick.\n\n{name} felt determined to make a difference. 'I promise to help protect the ocean. I'll tell everyone how important it is to keep our seas clean.'",
            "As the magical seashell began to glow again, {name} knew it was time to return to land. Splash and all the new ocean friends gathered to say goodbye.\n\n'Remember,' Splash said, 'the ocean needs guardians like you. Every piece of trash you pick up, every person you teach about ocean protection, makes a real difference.'\n\nThe mer-people gave {name} a special pearl necklace. 'Wear this to remember us and your promise to protect our home,' they said with grateful smiles.\n\nBack on the beach, {name} held the glowing seashell and the pearl necklace close. From that day on, {name} became a true ocean guardian.",
            "The very next weekend, {name} organized a beach clean-up with friends and family. They collected bags and bags of plastic and rubbish.\n\nSplash watched from the waves, leaping joyfully each time a piece of trash was removed from the shore.\n\nA news reporter came to cover the story. {name} spoke confidently about why the ocean matters and how everyone can help.\n\nThe report inspired other towns to organize their own clean-ups. One child's action had started a wave of change.",
            "{name} started an ocean awareness club at school. Members learned about marine life, ocean currents, and the effects of pollution.\n\nThey wrote letters to local businesses asking them to reduce plastic packaging. Some businesses actually listened and made changes.\n\n{name} learned that speaking up — politely but firmly — can move even big organizations to act.\n\nThe ocean, Splash had said, needs guardians. {name} was becoming one of the best.",
            "Years later, {name} became a marine biologist, spending days diving in the very waters where the adventure had begun.\n\nOn one dive, a familiar shape glided up — a sea turtle with a small scar on her flipper. Shelly.\n\nShelly nudged {name}'s hand gently, as if to say thank you, then swam gracefully into the blue.\n\n{name} surfaced with tears of joy, knowing that every act of kindness leaves a mark on the world — sometimes even on the flipper of a grateful sea turtle."
        ],
        "lesson": {"title": "What {name} Learned", "points": [
            "🌊 The ocean is home to amazing creatures that need our protection and care",
            "♻️ Keeping our environment clean helps all living things thrive and stay healthy",
            "🐢 Every small action we take to help nature makes a big difference",
            "💙 We are all connected to nature, and it's our responsibility to be good guardians of the Earth"
        ]}
    }
}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_index():
    return FileResponse("index.html")


@app.get("/api")
async def api_root():
    mode = "FREE (No API costs)" if USE_FREE_MODE else "AI-Powered (Groq llama-3.3-70b)"
    return {"message": "Kids Story Generator API is running!", "mode": mode}


@app.post("/generate-story", response_model=StoryResponse)
async def generate_story(request: StoryRequest):
    if USE_FREE_MODE:
        return await generate_free_story(request)
    return await generate_ai_story(request)


# ── Free story generator ──────────────────────────────────────────────────────

async def generate_free_story(request: StoryRequest):
    try:
        print(f"📝 FREE story: name={request.name}, age={request.age}, theme={request.theme}")
        theme = request.theme.lower()
        if theme not in STORY_TEMPLATES:
            theme = "adventure"

        template = STORY_TEMPLATES[theme]
        title = random.choice(template["titles"]).format(name=request.name)

        length_map = {"short": 3, "medium": 5, "long": 8}
        page_count = length_map.get((request.length or "medium").lower(), 5)

        gender = (request.gender or "boy").lower()
        pronoun_map = {
            "boy":  {"they": "he",  "them": "him", "their": "his",  "they've": "he's",  "they're": "he's"},
            "girl": {"they": "she", "them": "her", "their": "her",  "they've": "she's", "they're": "she's"},
            "both": {},
        }
        pronouns = pronoun_map.get(gender, {})

        def apply_pronouns(text):
            for src, dst in pronouns.items():
                text = text.replace(f" {src} ", f" {dst} ")
                text = text.replace(f" {src.capitalize()} ", f" {dst.capitalize()} ")
            return text

        pages = []
        for i, page_text in enumerate(template["pages"][:page_count], 1):
            formatted = apply_pronouns(page_text.format(name=request.name, age=request.age))
            first_sentence = formatted.split('.')[0].strip()
            pages.append(StoryPage(
                page_number=i,
                text=formatted,
                image_prompt=f"{first_sentence}. {request.name} is the main character, {theme} theme, children's storybook scene"
            ))

        lesson = template["lesson"]
        lesson_text = f"{lesson['title'].format(name=request.name)}\n\n" + "\n\n".join(lesson["points"])
        pages.append(StoryPage(
            page_number=len(pages) + 1,
            text=lesson_text,
            image_prompt=f"A warm educational illustration showing {request.name} reflecting on their journey"
        ))

        story_data = {
            "title": title,
            "theme": request.theme,
            "pages": [{"page_number": p.page_number, "text": p.text, "image_prompt": p.image_prompt} for p in pages]
        }

        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
                (request.name, request.theme, json.dumps(story_data, default=str), datetime.now())
            )
            story_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        print(f"✅ FREE story saved: {title} (ID: {story_id})")
        return {**story_data, "story_id": story_id, "char_desc": f"{request.age}-year-old child named {request.name}"}

    except Exception as e:
        print(f"❌ FREE story error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {e}")


# ── AI story generator ────────────────────────────────────────────────────────

async def generate_ai_story(request: StoryRequest):
    try:
        print(f"📝 AI story: name={request.name}, age={request.age}, theme={request.theme}")

        length_map = {"short": 3, "medium": 5, "long": 8}
        page_count = length_map.get((request.length or "medium").lower(), 5)

        gender = (request.gender or "boy").lower()
        pronoun_str = {
            "boy":  "he/him/his",
            "girl": "she/her/her",
            "both": "they/them/their (two main characters, one boy and one girl)"
        }.get(gender, "they/them/their")

        lesson_num = page_count + 1
        page_jsons = "\n".join([
            f'{{"page_number": {p}, "text": "2-3 short paragraphs for page {p}.", "image_prompt": "Colorful scene"}},'
            for p in range(1, page_count + 1)
        ])

        prompt = f"""Create an educational children's picture book story for a {request.age}-year-old named {request.name} with theme: {request.theme}.
Use pronouns: {pronoun_str} for {request.name}.

CRITICAL: Return ONLY valid JSON, no markdown, no extra text.

{{
    "title": "Story Title Here",
    "pages": [
        {chr(10).join([f'{{"page_number": {p}, "text": "2-3 short paragraphs (3-4 sentences each) for page {p} about {request.name}. Use pronouns {pronoun_str}.", "image_prompt": "Detailed scene: who is there, what they are doing, where they are, key objects visible."}},' for p in range(1, page_count + 1)])}
        {{"page_number": {lesson_num}, "text": "What {request.name} Learned\\n\\n🌟 First lesson\\n\\n💫 Second lesson\\n\\n✨ Third lesson\\n\\n❤️ Fourth lesson", "image_prompt": "{request.name} smiling surrounded by symbols of what they learned, warm glowing background"}}
    ]
}}

REQUIREMENTS:
- Exactly {page_count + 1} pages ({page_count} story + 1 lesson)
- Each story page: 2-3 SHORT paragraphs, 3-4 sentences each
- Use {pronoun_str} pronouns consistently
- Age-appropriate for {request.age} years old
- Educational values: kindness, courage, friendship, problem-solving
- Return ONLY the JSON"""

        response = None
        last_error = None
        for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                print(f"🤖 Trying model: {model_name}")
                chat_response = groq_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=4096
                )
                response = chat_response.choices[0].message.content
                print(f"✅ Success with {model_name}")
                break
            except Exception as model_err:
                last_error = model_err
                print(f"⚠️ {model_name} failed: {str(model_err)[:100]}")

        if response is None:
            raise last_error

        # Strip markdown fences if present
        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end:
            text = text[start:end]

        story_data = json.loads(text)
        if not isinstance(story_data, dict) or "title" not in story_data or "pages" not in story_data:
            raise ValueError("Invalid story structure from AI")

        story_data["theme"] = request.theme

        # Generate consistent character description (once per story)
        char_desc = f"{request.age}-year-old child"
        try:
            desc_resp = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": (
                    f"Write a SHORT physical description of {request.name} for an illustrator. "
                    f"Include: age (~{request.age} years old), hair color/style, eye color, skin tone, one specific outfit. "
                    f"Max 25 words. Descriptive phrases only, no sentences.\n\n"
                    f"Story title: {story_data['title']}\n"
                    f"First page: {story_data['pages'][0]['text'][:200]}"
                )}],
                temperature=0.3,
                max_tokens=50
            )
            char_desc = desc_resp.choices[0].message.content.strip()
            print(f"👤 Char desc: {char_desc}")
        except Exception as e:
            print(f"⚠️ Char desc failed: {e}")

        story_data["char_desc"] = char_desc

        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
                (request.name, request.theme, json.dumps(story_data), datetime.now())
            )
            story_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        print(f"✅ AI story saved: {story_data['title']} (ID: {story_id})")
        return {**story_data, "story_id": story_id}

    except HTTPException:
        raise
    except Exception as e:
        err = str(e)
        print(f"❌ AI story error: {err}")
        if any(x in err for x in ["429", "rate_limit", "quota"]):
            print("⚠️ Quota hit — falling back to FREE templates")
            return await generate_free_story(request)
        raise HTTPException(status_code=500, detail=f"Error generating story: {err}")


# ── Story CRUD routes ─────────────────────────────────────────────────────────

@app.get("/stories")
async def get_recent_stories():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, theme, full_text, date, is_favorite, rating FROM stories ORDER BY date DESC")
            stories = []
            for story_id, name, theme, text_data, date, is_fav, rating in cursor.fetchall():
                try:
                    story_data = json.loads(text_data) if text_data else {}
                    if isinstance(story_data, dict):
                        stories.append({
                            "id": story_id, "name": name, "theme": theme,
                            "title": story_data.get("title", f"Story for {name}"),
                            "date": date, "is_favorite": is_fav == 1, "rating": rating,
                            "preview": (story_data.get("pages") or [{}])[0].get("text", "")[:100] + "...",
                            "customCoverNumber": story_data.get("customCoverNumber"),
                            "isCustomTheme": story_data.get("isCustomTheme", False)
                        })
                    else:
                        stories.append({
                            "id": story_id, "name": name, "theme": theme,
                            "title": f"Story for {name}", "date": date,
                            "is_favorite": is_fav == 1, "rating": rating,
                            "preview": str(story_data)[:100] + "..."
                        })
                except Exception as e:
                    print(f"⚠️ Skipping story {story_id}: {e}")
        finally:
            conn.close()
        print(f"✅ Returning {len(stories)} stories")
        return {"stories": stories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stories: {e}")


@app.get("/stories/{story_id}")
async def get_story(story_id: int):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT full_text, is_favorite, rating FROM stories WHERE id = ?", (story_id,))
            result = cursor.fetchone()
        finally:
            conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="Story not found")

        try:
            parsed = json.loads(result[0])
            if not isinstance(parsed, dict):
                raise ValueError("Not a dict")
            story_data = parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            story_data = {
                "title": f"Story #{story_id}",
                "pages": [{"page_number": 1, "text": str(result[0]), "image_prompt": "A story illustration"}]
            }

        story_data["is_favorite"] = result[1] == 1
        story_data["story_id"] = story_id
        story_data["rating"] = result[2]
        return story_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching story: {e}")


@app.post("/stories/{story_id}/favorite")
async def toggle_favorite(story_id: int):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT is_favorite FROM stories WHERE id = ?", (story_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Story not found")
            new_status = 0 if result[0] == 1 else 1
            cursor.execute("UPDATE stories SET is_favorite = ? WHERE id = ?", (new_status, story_id))
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "is_favorite": new_status == 1}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling favorite: {e}")


@app.get("/favorites")
async def get_favorites():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, theme, full_text, date FROM stories WHERE is_favorite = 1 ORDER BY date DESC")
            favorites = []
            for story_id, name, theme, text_data, date in cursor.fetchall():
                try:
                    story_data = json.loads(text_data) if text_data else {}
                    if isinstance(story_data, dict):
                        favorites.append({
                            "id": story_id, "name": name, "theme": theme,
                            "title": story_data.get("title", f"Story for {name}"),
                            "dateAdded": date,
                            "customCoverNumber": story_data.get("customCoverNumber"),
                            "isCustomTheme": story_data.get("isCustomTheme", False)
                        })
                    else:
                        favorites.append({"id": story_id, "name": name, "theme": theme,
                                          "title": f"Story for {name}", "dateAdded": date})
                except Exception as e:
                    print(f"⚠️ Skipping favorite {story_id}: {e}")
        finally:
            conn.close()
        return {"favorites": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching favorites: {e}")


@app.delete("/stories/{story_id}")
async def delete_story(story_id: int):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Story not found")
            cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            conn.commit()
        finally:
            conn.close()
        print(f"🗑️ Story {story_id} deleted")
        return {"success": True, "message": "Story deleted successfully", "story_id": story_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting story: {e}")


@app.post("/stories/{story_id}/update")
async def update_story_cover(story_id: int, data: dict):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT full_text FROM stories WHERE id = ?", (story_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Story not found")
            story_data = json.loads(result[0])
            story_data["customCoverNumber"] = data.get("customCoverNumber")
            story_data["isCustomTheme"] = data.get("isCustomTheme", False)
            cursor.execute("UPDATE stories SET full_text = ? WHERE id = ?", (json.dumps(story_data), story_id))
            conn.commit()
        finally:
            conn.close()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating story: {e}")


@app.post("/stories/{story_id}/rate")
async def rate_story(story_id: int, data: dict):
    try:
        rating = int(data.get("rating", 0))
        if not 1 <= rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be 1-5")
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Story not found")
            cursor.execute("UPDATE stories SET rating = ? WHERE id = ?", (rating, story_id))
            conn.commit()
        finally:
            conn.close()
        print(f"⭐ Story {story_id} rated {rating}/5")
        return {"success": True, "rating": rating}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stories")
            total_stories = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM stories WHERE is_favorite = 1")
            total_favorites = cursor.fetchone()[0]
        finally:
            conn.close()
        return {"total_stories": total_stories, "total_favorites": total_favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Image routes ──────────────────────────────────────────────────────────────

@app.get("/story-image/{story_id}/{page}")
async def serve_story_image(story_id: int, page: int):
    for ext in ("webp", "png", "jpg"):
        path = IMAGES_DIR / f"{story_id}_page_{page}.{ext}"
        if path.exists():
            return FileResponse(str(path), media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="Image not found")


@app.post("/generate-image")
async def generate_image(data: dict):
    page_text = data.get("text", "")
    story_id  = data.get("story_id")
    page_num  = data.get("page_num", 0)
    char_name = data.get("char_name", "")
    char_desc = data.get("char_desc", "")

    if not page_text:
        raise HTTPException(status_code=400, detail="No text provided")

    # Check disk cache first
    if story_id and page_num:
        for ext in ("webp", "png", "jpg"):
            cached = IMAGES_DIR / f"{story_id}_page_{page_num}.{ext}"
            if cached.exists():
                img_b64 = base64.b64encode(cached.read_bytes()).decode("utf-8")
                print(f"💾 Cache hit: story {story_id} page {page_num}")
                return {"image": f"data:image/{ext};base64,{img_b64}", "scene_prompt": "cached", "cached": True}

    # Extract visual scene via Groq
    scene_prompt = page_text[:120]
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
                max_tokens=80
            )
            scene_prompt = resp.choices[0].message.content.strip()
            print(f"🎨 Scene prompt: {scene_prompt}")
    except Exception as e:
        print(f"⚠️ Scene extract failed: {e}")
        scene_prompt = ". ".join(page_text.replace("\n", " ").split(". ")[:2])

    # Build full prompt with character consistency
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

    # Consistent seed per story
    seed = None
    if story_id:
        seed = int(hashlib.md5(str(story_id).encode()).hexdigest()[:8], 16) % 2147483647

    image_mode = os.getenv("IMAGE_MODE", "gradio").lower()
    print(f"🖼️ Image mode: {image_mode}")
    img_b64 = None
    img_ext = "webp"

    # --- REPLICATE ---
    if image_mode == "replicate":
        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
        if not replicate_token:
            raise HTTPException(status_code=500, detail="REPLICATE_API_TOKEN not set in .env")
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers={"Authorization": f"Bearer {replicate_token}", "Content-Type": "application/json", "Prefer": "wait"},
                json={"input": {"prompt": prompt, "num_outputs": 1, "output_format": "webp",
                                **({"seed": seed} if seed else {})}}
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
            result, _ = gc.predict(prompt=prompt, randomize_seed=True, width=1024, height=1024,
                                   num_inference_steps=4, api_name="/infer")
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
                raw = Path(path).read_bytes()
        elif isinstance(result, str):
            raw = Path(result).read_bytes()
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
        raise HTTPException(status_code=503, detail="Image generation failed — no data returned")

    # Save to disk permanently
    if story_id and page_num:
        save_path = IMAGES_DIR / f"{story_id}_page_{page_num}.{img_ext}"
        save_path.write_bytes(base64.b64decode(img_b64))
        print(f"💾 Saved: {save_path}")

    return {"image": f"data:image/{img_ext};base64,{img_b64}", "scene_prompt": scene_prompt,
            "backend": image_mode, "cached": False}


# ── Groq quota check ──────────────────────────────────────────────────────────

@app.get("/groq-quota")
async def check_groq_quota():
    if USE_FREE_MODE or not groq_client:
        return {"mode": "FREE", "message": "Groq API not active (USE_FREE_MODE=true)"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
            )
        h = dict(r.headers)
        quota = {
            "status": r.status_code,
            "requests_limit":     h.get("x-ratelimit-limit-requests"),
            "requests_remaining": h.get("x-ratelimit-remaining-requests"),
            "requests_reset":     h.get("x-ratelimit-reset-requests"),
            "tokens_limit":       h.get("x-ratelimit-limit-tokens"),
            "tokens_remaining":   h.get("x-ratelimit-remaining-tokens"),
            "tokens_reset":       h.get("x-ratelimit-reset-tokens"),
            "message": "API key valid, quota available" if r.status_code == 200 else f"Status: {r.status_code}"
        }
        return quota
    except Exception as e:
        return {"error": str(e)}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=8025, log_level="info", access_log=False)
