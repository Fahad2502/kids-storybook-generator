"""
check_system.py -- Full system health check
Run with: venv\Scripts\python check_system.py
"""
import httpx
import asyncio

BASE = 'http://localhost:8025'

async def test():
    results = []

    async with httpx.AsyncClient(timeout=90) as c:

        # 1. Homepage
        r = await c.get(BASE)
        results.append(('Homepage', r.status_code, 'OK' if r.status_code == 200 else 'FAIL'))

        # 2. API health
        r = await c.get(BASE + '/api')
        results.append(('API health', r.status_code, 'OK' if r.status_code == 200 else 'FAIL'))

        # 3. Register
        r = await c.post(BASE + '/register', json={
            'first_name': 'Test', 'last_name': 'User',
            'email': 'syscheck@test.com', 'username': 'syscheck99', 'password': 'Test1234'
        })
        reg_ok = r.status_code in [200, 409]
        results.append(('Register', r.status_code, 'OK' if reg_ok else r.text[:60]))

        # 4. Login
        r = await c.post(BASE + '/login', json={'username': 'syscheck99', 'password': 'Test1234'})
        results.append(('Login', r.status_code, 'OK' if r.status_code == 200 else 'FAIL'))

        # 5. Wrong password
        r = await c.post(BASE + '/login', json={'username': 'syscheck99', 'password': 'wrong'})
        results.append(('Wrong password blocks', r.status_code, 'OK (401)' if r.status_code == 401 else 'FAIL'))

        # 6. Get stories
        r = await c.get(BASE + '/stories')
        count = len(r.json()) if r.status_code == 200 else 0
        results.append(('Get stories', r.status_code, str(count) + ' stories in DB'))

        # 7. Stats
        r = await c.get(BASE + '/stats')
        results.append(('Stats endpoint', r.status_code, 'OK' if r.status_code == 200 else 'FAIL'))

        # 8. Favorites
        r = await c.get(BASE + '/favorites')
        results.append(('Favorites endpoint', r.status_code, 'OK' if r.status_code == 200 else 'FAIL'))

        # 9. Story generation
        r = await c.post(BASE + '/generate-story', json={
            'name': 'TestKid', 'age': 7, 'theme': 'adventure', 'gender': 'boy', 'length': 'short'
        })
        if r.status_code == 200:
            data = r.json()
            title = data.get('title', '')[:35]
            sid = data.get('story_id')
            results.append(('Story generation', 200, 'OK - ' + title + ' (ID:' + str(sid) + ')'))
        else:
            results.append(('Story generation', r.status_code, 'FAIL: ' + r.text[:80]))

        # 10. Image generation
        r = await c.post(BASE + '/generate-image', json={
            'text': 'A brave child standing at the entrance of a cave',
            'story_id': 9001, 'page_num': 1
        })
        if r.status_code == 200:
            data = r.json()
            img = data.get('image', '')
            backend = data.get('backend', '')
            cached = data.get('cached', False)
            results.append(('Image generation', 200, 'backend:' + backend + ' cached:' + str(cached) + ' url:' + img[:45]))
        else:
            results.append(('Image generation', r.status_code, 'FAIL: ' + r.text[:80]))

        # 11. Image cache hit
        r = await c.post(BASE + '/generate-image', json={
            'text': 'any text', 'story_id': 9001, 'page_num': 1
        })
        if r.status_code == 200:
            cached = r.json().get('cached', False)
            results.append(('Image DB cache', 200, 'cached:' + str(cached) + ' (should be True)'))
        else:
            results.append(('Image DB cache', r.status_code, 'FAIL'))

        # 12. Cloudinary check
        if r.status_code == 200:
            img_url = r.json().get('image', '')
            if 'cloudinary' in img_url:
                results.append(('Cloudinary storage', 200, 'OK - permanent CDN URL'))
            elif img_url.startswith('http'):
                results.append(('Cloudinary storage', 200, 'URL present: ' + img_url[:50]))
            else:
                results.append(('Cloudinary storage', 500, 'No URL - check config'))

    print()
    print('=' * 65)
    print('  FULL SYSTEM CHECK — Kids Story Generator')
    print('=' * 65)
    all_ok = True
    for name, status, detail in results:
        ok = status in [200, 201, 409]
        icon = 'OK  ' if ok else 'FAIL'
        if not ok:
            all_ok = False
        print(f'  [{icon}] {name}: {status} — {detail}')
    print('=' * 65)
    print('  Result:', 'ALL SYSTEMS GO' if all_ok else 'ISSUES FOUND — check above')
    print('=' * 65)
    print()

asyncio.run(test())
