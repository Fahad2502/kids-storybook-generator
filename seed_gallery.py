"""
seed_gallery.py -- Generate 25 sample stories to populate the gallery.
Run with: venv\Scripts\python -X utf8 seed_gallery.py
Make sure the server is running first.
"""
import httpx
import asyncio
import time

API = "https://kids-story-generator-5due.onrender.com"

STORIES = [
    {"name": "Ali",      "age": 7,  "theme": "adventure",  "gender": "boy",  "length": "medium"},
    {"name": "Sara",     "age": 6,  "theme": "animals",    "gender": "girl", "length": "short"},
    {"name": "Omar",     "age": 9,  "theme": "space",      "gender": "boy",  "length": "medium"},
    {"name": "Zara",     "age": 8,  "theme": "ocean",      "gender": "girl", "length": "medium"},
    {"name": "Hamza",    "age": 10, "theme": "fantasy",    "gender": "boy",  "length": "medium"},
    {"name": "Aisha",    "age": 7,  "theme": "friendship", "gender": "girl", "length": "short"},
    {"name": "Yusuf",    "age": 8,  "theme": "adventure",  "gender": "boy",  "length": "short"},
    {"name": "Fatima",   "age": 6,  "theme": "animals",    "gender": "girl", "length": "medium"},
    {"name": "Ibrahim",  "age": 9,  "theme": "space",      "gender": "boy",  "length": "short"},
    {"name": "Maryam",   "age": 7,  "theme": "fantasy",    "gender": "girl", "length": "medium"},
    {"name": "Bilal",    "age": 10, "theme": "ocean",      "gender": "boy",  "length": "medium"},
    {"name": "Hana",     "age": 8,  "theme": "friendship", "gender": "girl", "length": "short"},
    {"name": "Tariq",    "age": 9,  "theme": "adventure",  "gender": "boy",  "length": "medium"},
    {"name": "Layla",    "age": 6,  "theme": "animals",    "gender": "girl", "length": "short"},
    {"name": "Khalid",   "age": 8,  "theme": "space",      "gender": "boy",  "length": "medium"},
    {"name": "Noor",     "age": 7,  "theme": "fantasy",    "gender": "girl", "length": "medium"},
    {"name": "Saad",     "age": 10, "theme": "ocean",      "gender": "boy",  "length": "short"},
    {"name": "Amira",    "age": 9,  "theme": "friendship", "gender": "girl", "length": "medium"},
    {"name": "Faris",    "age": 7,  "theme": "pirates",    "gender": "boy",  "length": "short"},
    {"name": "Rania",    "age": 8,  "theme": "dinosaurs",  "gender": "girl", "length": "medium"},
    {"name": "Zaid",     "age": 6,  "theme": "superheroes","gender": "boy",  "length": "short"},
    {"name": "Sana",     "age": 9,  "theme": "magic school","gender": "girl","length": "medium"},
    {"name": "Umar",     "age": 10, "theme": "adventure",  "gender": "boy",  "length": "long"},
    {"name": "Dina",     "age": 7,  "theme": "ocean",      "gender": "girl", "length": "medium"},
    {"name": "Malik",    "age": 8,  "theme": "space",      "gender": "boy",  "length": "medium"},
]


async def generate_one(client, i, story):
    name = story["name"]
    theme = story["theme"]
    try:
        r = await client.post(f"{API}/generate-story", json=story, timeout=90)
        if r.status_code == 200:
            data = r.json()
            print(f"  [{i+1}/25] '{data.get('title')}' — {name}, {theme} ✅")
            return True
        else:
            print(f"  [{i+1}/25] FAILED {name}/{theme}: {r.text[:80]}")
            return False
    except Exception as e:
        print(f"  [{i+1}/25] ERROR {name}/{theme}: {str(e)[:80]}")
        return False


async def main():
    print(f"\nGenerating 25 stories... (~8 minutes)\n")
    start = time.time()
    success = 0

    async with httpx.AsyncClient() as client:
        # Check server is running
        try:
            r = await client.get(f"{API}/api", timeout=5)
        except Exception:
            print("ERROR: Server is not running. Start it first with start.bat")
            return

        for i, story in enumerate(STORIES):
            ok = await generate_one(client, i, story)
            if ok:
                success += 1
            await asyncio.sleep(1)  # small delay between requests

    elapsed = time.time() - start
    print(f"\nDone! {success}/25 stories generated in {elapsed/60:.1f} minutes.")
    print("Refresh your gallery at http://localhost:8025")


asyncio.run(main())
