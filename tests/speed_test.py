"""Procurement opens fast: browser checks against a simulated Procurement server. python3 tests/speed_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8795; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
ST = {'ver': 'v1', 'delay': 0, 'deny': False, 'sides': ['plan'], 'calls': [], 'lines': {}}
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}'); ST['calls'].append((time.time(), b))
    if ST['delay']: await asyncio.sleep(ST['delay'])
    if ST['deny']: return await route.fulfill(json={'ok': False, 'error': 'erp'})
    me = {'name': 'Abu Ali', 'sides': ST['sides'], 'role': 'team'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'):
        if b.get('ver') and b['ver'] == ST['ver']: return await route.fulfill(json={'ok': True, 'same': True, 'ver': ST['ver'], 'me': me})
        return await route.fulfill(json={'ok': True, 'me': me, 'ver': ST['ver'], 'lines': ST['lines'], 'suppliers': {}, 'tabs': {}})
    await route.fulfill(json={'ok': True, 'ver': ST['ver']})
DJ = []
async def dj(route):
    DJ.append(('start', time.time())); r = await route.fetch(); await asyncio.sleep(0.3); DJ.append(('end', time.time())); await route.fulfill(response=r)
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server); await ctx.route('**/data.json', dj)
            errs = []
            # 1. first open from Forka Apps: server asked while data.json downloads
            ST['delay'] = 1.0; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(2500)
            first_post = ST['calls'][0][0]; dj_end = [t for k, t in DJ if k == 'end'][0]
            check('First open: the server is asked while data.json is still downloading', first_post < dj_end, (first_post, dj_end))
            check('First open: one section enters straight away', await pg.evaluate('mode') == 'live' and await pg.evaluate('unlocked') == 'plan', await pg.evaluate('mode'))
            await pg.close()
            # 2. second open: saved copy shows before the slow server answers
            ST['delay'] = 3.0; n0 = len(ST['calls']); pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            t0 = time.time(); await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'", timeout=2500)
            check('Second open: the app is ready from the saved copy before the server answers', time.time() - t0 < 2.0 and len(ST['calls']) >= n0 + 1, time.time() - t0)
            await pg.screenshot(path=str(SHOTS / 'instant_open.png'))
            await pg.wait_for_timeout(3500)
            check('...and the server is still checked in the background', len(ST['calls']) > n0)
            await pg.close()
            # 3. a change made elsewhere is picked up after the instant open
            ST['delay'] = 0.5; ST['ver'] = 'v2'; ST['lines'] = {'x1': {'id': 'x1', 'stock': 7}}
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(3000)
            check('A change saved by someone else appears a moment later', await pg.evaluate('VER') == 'v2' and 'x1' in (await pg.evaluate("JSON.stringify(shared)")), await pg.evaluate('VER'))
            await pg.close()
            # 4. access removed: the saved copy is closed as soon as the server says so
            ST['deny'] = True; ST['delay'] = 0.5
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(2500)
            check('Access removed in Forka Apps: the app closes and asks to sign in again', await pg.evaluate('mode') == 'login' and not await pg.evaluate('ERP'), await pg.evaluate('mode'))
            await pg.close(); ST['deny'] = False
            # 5. reload inside the app (already signed in this tab) opens at once too
            ST['delay'] = 0.2; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            ST['delay'] = 3.0; t0 = time.time(); await pg.reload(); await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'", timeout=2500)
            check('Reload inside the app opens at once from the saved copy', time.time() - t0 < 2.0, time.time() - t0)
            await pg.wait_for_timeout(3500)
            # 6. two sections: the section picker shows at once, and entering one opens from the saved copy
            await pg.close(); ST['sides'] = ['plan', 'ops']; ST['delay'] = 0.3
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500); await pg.close()
            ST['delay'] = 3.0; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            t0 = time.time(); await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_function("typeof ERP_SIDES!=='undefined'&&ERP_SIDES&&ERP_SIDES.length===2", timeout=2500)
            check('Two sections: the section picker is ready before the server answers', time.time() - t0 < 2.0 and await pg.evaluate('mode') == 'login', time.time() - t0)
            await pg.evaluate("erpEnter('ops')"); await pg.wait_for_timeout(300)
            check('...and entering a section opens at once', await pg.evaluate('mode') == 'live' and await pg.evaluate('unlocked') == 'ops', await pg.evaluate('mode'))
            await pg.screenshot(path=str(SHOTS / 'instant_open_ops.png'))
            await pg.wait_for_timeout(3500)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally: srv.terminate()
    print(f'{sum(res)}/{len(res)} procurement checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
