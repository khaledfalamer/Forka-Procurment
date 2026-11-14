"""Signed in through Forka Apps the real server sends no role: the page must use the person's name, never ask "Your name" or show Team PIN (Khaled, 14 Nov 2026). Based on base_names_test.
Item names always arrive: a copy saved in the browser before the item list moved to the Base tab,
then a server that answers "nothing new". python3 tests/base_names_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); PORT = 8789; BASE = f'http://127.0.0.1:{PORT}' + os.environ.get('SITE_PATH', '')
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
BASE_TAB = {l['id']: l for l in json.load(open(pathlib.Path(ROOT) / 'demo-data.json', encoding='utf-8'))['lines']}
FIRST = next(iter(BASE_TAB.values()))
EDITS = {FIRST['id']: {'id': FIRST['id'], 'st': 3}}           # counted stock saved in the Lines tab (no name: names live in Base)
ST = {'server': 'old', 'calls': []}; res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}'); ST['calls'].append(b)
    me = {'name': 'Khaled', 'email': 'ceo@forka.com', 'sides': ['plan']}   # like the real server: no role for Forka Apps sign-in
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'):
        if ST['server'] == 'old': return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': EDITS, 'suppliers': {}, 'tabs': {'Lines': EDITS}})
        # new script: same stamp -> "same" (Base is only created and sent on a full load)
        if b.get('ver') == 'v1': return await route.fulfill(json={'ok': True, 'same': True, 'ver': 'v1', 'me': me})
        return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v2', 'lines': EDITS, 'suppliers': {}, 'tabs': {'Lines': EDITS, 'Base': BASE_TAB}})
    await route.fulfill(json={'ok': True, 'ver': 'v1'})
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=os.environ.get('SITE_ROOT', ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            # 1. yesterday: the old script (no Base tab); the browser keeps a copy
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'", timeout=8000); await pg.wait_for_timeout(1500)
            # 2. today: the new script is pasted; nothing was saved since, so its stamp is the same
            ST['server'] = 'new'; ST['calls'].clear()
            await pg.close(); pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'", timeout=8000); await pg.wait_for_timeout(2500)
            name = await pg.evaluate(f"(line('{FIRST['id']}')||{{}}).n")
            loads = [c.get('ver', '') for c in ST['calls'] if c.get('load')]
            check('Opening from an old saved copy: the app asks for everything (not "anything new?") while it has no item list', '' in loads, loads)
            check('Item names arrive and show (was: every row "New item name")', name == FIRST['n'], [name, FIRST['n']])
            check('Counted stock from the Lines tab is still there', str(await pg.evaluate(f"line('{FIRST['id']}').st")) == '3')
            await pg.evaluate("tab='fill';render()"); await pg.wait_for_timeout(300)
            check('The item list shows the name', FIRST['n'] in await pg.inner_text('body'))
            check('Signed in through Forka Apps: no "Your name" box, the name is shown', await pg.locator('#top #me').count() == 0 and 'Khaled' in await pg.inner_text('#top'), await pg.inner_text('#top'))
            check('...and no Team PIN', 'Team PIN' not in await pg.inner_text('#top'))
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'\n{sum(res)}/{len(res)} Forka Apps name checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
