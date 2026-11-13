"""Clearance rules (Khaled, 13 Nov 2026): Stock moves only for manager clearance and above; staff never get CEO approvals
(the server drops it; the page also never shows it). Mock data only. python3 tests/clearance_test.py"""
import asyncio, json, pathlib, re, socket, subprocess, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
PORT = free_port(); BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'; res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def run(b, level, sides, errs):
    ME = {'name': 'Arman', 'email': 'arman@forka.com', 'sides': sides, 'level': level, 'role': 'admin'}
    async def server(route):
        q = json.loads(route.request.post_data or '{}')
        if q.get('check') and not q.get('load'): return await route.fulfill(json={'ok': True, 'me': ME})
        if q.get('load'): return await route.fulfill(json={'ok': True, 'me': ME, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {}})
        await route.fulfill(json={'ok': True, 'ver': 'v2'})
    ctx = await b.new_context(viewport={'width': 1366, 'height': 900})
    await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
    await ctx.route('https://proc.test/**', server)
    pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
    if len(sides) > 1: await pg.evaluate("erpEnter('ops')"); await pg.wait_for_timeout(800)
    tabs = await pg.evaluate("[...document.querySelectorAll('[data-tab]')].map(e=>e.dataset.tab)")
    cur = await pg.evaluate("tab")
    await pg.evaluate("tab='home';try{render()}catch(e){}"); await pg.wait_for_timeout(200)
    home = await pg.evaluate("typeof vHome==='function'?vHome():''")
    await ctx.close(); return tabs, cur, home
async def main():
    srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    errs = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            tabs, cur, home = await run(b, 'staff', ['ops'], errs)
            check('Staff with Operations: no Stock moves page in the menu', 'moves' not in tabs and 'grn' in tabs, tabs)
            check('Staff with Operations: opens on another page, not Stock moves', cur != 'moves', cur)
            check('Staff: the start screen has no Stock moves row', 'ops:moves' not in home)
            tabs, cur, home = await run(b, 'manager', ['ops'], errs)
            check('Manager with Operations: Stock moves is in the menu', 'moves' in tabs, tabs)
            check('Manager: the start screen shows the Stock moves row', 'ops:moves' in home)
            tabs, cur, home = await run(b, 'staff', ['ops', 'dept'], errs)
            check('Staff with two sections: still no Stock moves', 'moves' not in tabs, tabs)
            await b.close()
    finally:
        srv.terminate()
    check('No page errors', not errs, errs)
    gs = open(ROOT + '/Code.gs').read()
    check('Server drops CEO approvals for staff clearance', "!(x === 'ceo' && level === 'staff')" in gs)
    check('Server sends the clearance to the page', 'level: me.level' in gs)
    print(f'{sum(res)}/{len(res)} clearance checks passed'); raise SystemExit(0 if all(res) else 1)
asyncio.run(main())
