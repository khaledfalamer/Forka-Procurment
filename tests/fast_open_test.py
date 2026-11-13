"""Fast open after a new sign-in: the copy saved in this browser opens at once, but only for the same person.
Simulated Procurement server and Forka Apps accounts server (no live servers). python3 tests/fast_open_test.py"""
import asyncio, json, os, pathlib, re, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True)
PORT = 8797; BASE = f'http://127.0.0.1:{PORT}'
ACC = 'https://accounts.test/accounts'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/',ACCOUNTS_URL:'" + ACC + "'};"
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-⛿✀-✒✔✖-➿⭐⭕️]')
def tok(n): return f'ERPTOK-{n:020d}'
# token -> person (what both servers know about this sign-in)
PEOPLE = {}
def person(n, email, sides=('plan',)): PEOPLE[tok(n)] = {'email': email, 'sides': list(sides)}
ST = {'delay': 0, 'ver': {'abu@forka.com': 'v1', 'sara@forka.com': 's1'}, 'proc_sides': None, 'acc': 'ok', 'acc_calls': [], 'proc_calls': []}
LINES = {'abu@forka.com': {'abu1': {'id': 'abu1', 'n': 'Basmati rice ABU', 'st': 4}}, 'sara@forka.com': {'sara1': {'id': 'sara1', 'n': 'Olive oil SARA', 'st': 9}}}
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))

async def proc(route):
    b = json.loads(route.request.post_data or '{}'); ST['proc_calls'].append(b)
    if ST['delay']: await asyncio.sleep(ST['delay'])
    p = PEOPLE.get(b.get('erp'))
    if not p: return await route.fulfill(json={'ok': False, 'error': 'erp'})
    em = p['email']; sides = ST['proc_sides'] if ST['proc_sides'] is not None else p['sides']
    me = {'name': em.split('@')[0], 'email': em, 'sides': sides}
    if b.get('side') and b['side'] not in sides: return await route.fulfill(json={'ok': False, 'error': 'side'})
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'):
        v = ST['ver'][em]
        if b.get('ver') and b['ver'] == v: return await route.fulfill(json={'ok': True, 'same': True, 'ver': v, 'me': me})
        return await route.fulfill(json={'ok': True, 'me': me, 'ver': v, 'lines': LINES[em], 'suppliers': {}, 'tabs': {}})
    await route.fulfill(json={'ok': True, 'ver': ST['ver'][em]})

async def accounts(route):
    if route.request.method == 'OPTIONS': return await route.fulfill(status=204, headers={'access-control-allow-origin': '*'})
    b = json.loads(route.request.post_data or '{}'); ST['acc_calls'].append(b)
    if ST['acc'] == 'down': return await route.abort('connectionrefused')
    if ST['acc'] == 'slow': await asyncio.sleep(6)
    if ST['acc'] == 'error': return await route.fulfill(status=500, body='oops')
    p = PEOPLE.get(b.get('token'))
    if b.get('action') != 'who' or not p: return await route.fulfill(json={'ok': False, 'error': 'session'}, headers={'access-control-allow-origin': '*'})
    me = {'email': p['email'], 'name': p['email'].split('@')[0], 'level': 'staff', 'status': 'active', 'apps': {'proc': 1, 'hire': 0, 'branch': 0}, 'sides': p['sides'], 'method': 'google'}
    await route.fulfill(json={'ok': True, 'me': me}, headers={'access-control-allow-origin': '*'})

async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    errs = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            async def new_ctx():
                ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
                await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
                await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
                await ctx.route('https://proc.test/**', proc); await ctx.route('https://accounts.test/**', accounts)
                await ctx.route(re.compile(r'^https://(?!proc\.test|accounts\.test).*'), lambda r: r.abort())   # nothing live
                return ctx
            async def page(ctx):
                pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); return pg
            async def live_at(pg, t0, limit):
                try: await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'&&Object.keys(shared).length>0", timeout=int(limit * 1000), polling=50); return time.time() - t0
                except Exception: return None
            snap = "new Promise(r=>{const q=indexedDB.open('forka-procurement',1);q.onsuccess=()=>{const g=q.result.transaction('kv').objectStore('kv').get('snap');g.onsuccess=()=>r(g.result?{email:g.result.email||'',ids:Object.keys(g.result.r.lines||{})}:null)}})"
            person(1, 'abu@forka.com'); person(2, 'abu@forka.com'); person(3, 'sara@forka.com'); person(4, 'abu@forka.com'); person(5, 'abu@forka.com')
            person(6, 'abu@forka.com'); person(7, 'abu@forka.com'); person(8, 'abu@forka.com'); person(9, 'abu@forka.com'); person(10, 'abu@forka.com')

            # 0. baseline: first ever sign-in, no saved copy, slow server (3 s)
            ctx = await new_ctx(); ST['delay'] = 3.0
            pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(1)); t_cold = await live_at(pg, t0, 8)
            check('No saved copy yet: the app waits for the server, then opens', t_cold is not None and t_cold >= 2.9, t_cold)
            check('...no accounts call is needed when there is no saved copy', not ST['acc_calls'], ST['acc_calls'])
            s = await pg.evaluate(snap); check('...the copy is saved with the email', s and s['email'] == 'abu@forka.com' and s['ids'] == ['abu1'], s)
            await pg.close()

            # a. same person, new sign-in token: opens from the copy at once, then picks up a change
            ST['ver']['abu@forka.com'] = 'v2'; LINES['abu@forka.com'] = {'abu1': {'id': 'abu1', 'n': 'Basmati rice ABU', 'st': 4}, 'abu2': {'id': 'abu2', 'n': 'Sugar ABU', 'st': 2}}
            ST['acc_calls'].clear(); pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(2)); t_warm = await live_at(pg, t0, 2.5)
            check('Same person, new sign-in: the saved copy opens before the slow server answers', t_warm is not None and t_warm < 2.0, t_warm)
            check('...the accounts server was asked "who" with the new token', any(c.get('action') == 'who' and c.get('token') == tok(2) for c in ST['acc_calls']), ST['acc_calls'])
            check('...data from the saved copy is on screen', 'abu1' in await pg.evaluate('Object.keys(shared).join()') and 'abu2' not in await pg.evaluate('Object.keys(shared).join()'))
            upd = await pg.evaluate("(document.getElementById('bgst')||{}).textContent||''")
            check('..."Updating…" shows while the server is asked', upd == 'Updating…', upd)
            await pg.screenshot(path=str(SHOTS / 'fast_open_updating.png'))
            await pg.wait_for_function("Object.keys(shared).includes('abu2')", timeout=6000)
            check('...and the change saved elsewhere appears when the server answers', await pg.evaluate('VER') == 'v2')
            check('..."Updating…" goes away after', not await pg.evaluate("!!document.getElementById('bgst')"))
            body = await pg.inner_text('body'); check('No emojis (English)', not EMOJI.search(body), EMOJI.findall(body)[:5])
            await pg.close()
            # Arabic: same flow, "Updating…" in Arabic and the page is right-to-left
            await (pg := await page(ctx)).goto(BASE + '/'); await pg.evaluate("localStorage.setItem('pp-lang',JSON.stringify('ar'))"); await pg.close()
            ST['ver']['abu@forka.com'] = 'v3'; pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(10)); t_ar = await live_at(pg, t0, 2.5)
            upd = await pg.evaluate("(document.getElementById('bgst')||{}).textContent||''")
            check('Arabic: opens from the copy with "Updating…" in Arabic', t_ar is not None and upd == 'جاري التحديث…', (t_ar, upd))
            check('Arabic: page is right-to-left', await pg.evaluate("document.documentElement.dir||document.body.dir") == 'rtl')
            await pg.screenshot(path=str(SHOTS / 'fast_open_updating_ar.png'))
            await pg.wait_for_timeout(3500); body = await pg.inner_text('body'); check('No emojis (Arabic)', not EMOJI.search(body), EMOJI.findall(body)[:5])
            await pg.evaluate("localStorage.setItem('pp-lang',JSON.stringify('en'))"); await pg.close()

            # b. another person signs in on the same browser: the copy is never shown
            pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(3)); seen = False
            while time.time() - t0 < 2.7:
                txt = await pg.evaluate("document.body.innerText+' '+(typeof shared==='object'?Object.keys(shared).join():'')")
                seen = seen or ('ABU' in txt or 'abu1' in txt); await pg.wait_for_timeout(100)
            check('Different person: the other person\'s copy is not opened', not seen and await pg.evaluate('mode') != 'live')
            t_b = await live_at(pg, t0, 6)
            check('...they wait for the server and then see their own data', t_b is not None and await pg.evaluate("Object.keys(shared).join()") == 'sara1', (t_b, await pg.evaluate("Object.keys(shared).join()")))
            s = await pg.evaluate(snap); check('...and the saved copy is now theirs', s and s['email'] == 'sara@forka.com', s)
            await pg.close()

            # c. accounts server down / failing / slow: falls back to the normal way, still works
            ST['delay'] = 0.2; pg = await page(ctx); await pg.goto(BASE + '/#erp=' + tok(4)); await live_at(pg, time.time(), 4); await pg.close()   # copy back to Abu
            for kind, n in (('down', 5), ('error', 6), ('slow', 7)):
                ST['acc'] = kind; ST['delay'] = 3.0; pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(n))
                await pg.wait_for_timeout(1500); early = await pg.evaluate('mode')
                t_c = await live_at(pg, t0, 8)
                check(f'Accounts server {kind}: the copy is not used, the app still opens from the server', early != 'live' and t_c is not None and t_c >= 2.9, (early, t_c))
                await pg.close()
            ST['acc'] = 'ok'

            # d. access to the section removed on the server: opens from the copy, then leaves as today
            ST['delay'] = 2.0; ST['proc_sides'] = ['ops']
            pg = await page(ctx); t0 = time.time(); await pg.goto(BASE + '/#erp=' + tok(8)); t_d = await live_at(pg, t0, 1.8)
            check('Access removed: the copy opens first (accounts server still says Purchasing)', t_d is not None, t_d)
            await pg.wait_for_timeout(2500)
            check('...then the server says no and the app closes and asks to sign in again', await pg.evaluate('mode') == 'login' and not await pg.evaluate('ERP') and await pg.evaluate('unlocked') is None, await pg.evaluate('mode'))
            check('...and the saved copy is deleted', await pg.evaluate(snap) is None)
            await pg.close(); ST['proc_sides'] = None

            # e. Exit deletes the copy
            ST['delay'] = 0.2; pg = await page(ctx); await pg.goto(BASE + '/#erp=' + tok(9)); await live_at(pg, time.time(), 4); await pg.wait_for_timeout(500)
            check('Before Exit there is a saved copy', (await pg.evaluate(snap) or {}).get('email') == 'abu@forka.com')
            await pg.click('.exitb[data-act=exit]'); await pg.wait_for_timeout(800)
            check('Exit deletes the saved copy', await pg.evaluate(snap) is None and await pg.evaluate('mode') == 'login', await pg.evaluate(snap))
            await pg.close()
            ST['delay'] = 3.0; pg = await page(ctx); await pg.goto(BASE + '/#erp=' + tok(2)); await pg.wait_for_timeout(1500)
            check('...so the next sign-in waits for the server', await pg.evaluate('mode') != 'live')
            await live_at(pg, time.time(), 6); await pg.close(); await ctx.close()

            # demo mode (empty SHEET_URL) never calls the accounts server
            ST['acc_calls'].clear(); ctx = await b.new_context()
            await ctx.route('**/config.js*', lambda r: r.fulfill(body="window.FORKA_CONFIG={SHEET_URL:'',PIN:false,ERP_URL:'',ACCOUNTS_URL:'" + ACC + "'};", content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css')); await ctx.route('https://accounts.test/**', accounts)
            pg = await page(ctx); await pg.goto(BASE + '/#erp=' + tok(1)); await pg.wait_for_timeout(1500)
            check('Demo mode: no accounts call', not ST['acc_calls'], ST['acc_calls']); await ctx.close()

            check('No page errors', not errs, errs[:3])
            print(f'TIMING first data: without saved copy {t_cold:.2f}s, with saved copy (same person, new token) {t_warm:.2f}s (Procurement server delay 3.0s)')
            await b.close()
    finally: srv.terminate()
    print(f'{sum(res)}/{len(res)} fast open checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
