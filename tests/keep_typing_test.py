"""Typed text is never wiped: not by the 30-second server refresh, not by picking a unit (e.g. Bucket). python3 tests/keep_typing_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); PORT = 8794; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
BASE_TAB = {l['id']: l for l in json.load(open(pathlib.Path(__file__).resolve().parent.parent / 'demo-data.json', encoding='utf-8'))['lines']}  # the server sends the item list after sign-in
TOK = 'ERPTOK-00000000000000000000'; res = []; VER = {'n': 1}
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Khaled', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v%d' % VER['n'], 'lines': {}, 'suppliers': {}, 'tabs': {'Base': BASE_TAB}})
    await route.fulfill(json={'ok': True, 'ver': 'v%d' % VER['n']})
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        check('Page has the keep-what-is-typed guard', 'window.__fkKeep' in (pathlib.Path(ROOT) / 'index.html').read_text())
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            await ctx.add_init_script("localStorage.setItem('pp-inv-cols',JSON.stringify(['item','stock','sup','p','unit','pack']))")
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('dept')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(800)
            # typing the reason of a new request while the 30-second server refresh lands
            await pg.evaluate("tab='rnew';rqDraft={kind:'food',title:'Gloves',dept:'kitchen'};render()"); await pg.wait_for_timeout(300)
            await pg.click('textarea[data-rqd=details]'); await pg.keyboard.type('Half-typed reason')
            VER['n'] = 2; await pg.evaluate("REFRESH(false)"); await pg.wait_for_timeout(500)
            check('A server refresh does not redraw while someone is typing (was: text wiped)', await pg.input_value('textarea[data-rqd=details]') == 'Half-typed reason' and await pg.evaluate("document.activeElement.dataset.rqd") == 'details')
            await pg.click('[data-rqd=title]' if await pg.locator('[data-rqd=title]').count() else 'body'); await pg.wait_for_timeout(300)
            check('...after leaving the box the reason is still there (and saved in the request)', await pg.input_value('textarea[data-rqd=details]') == 'Half-typed reason' and await pg.evaluate("rqDraft.details") == 'Half-typed reason', await pg.evaluate("rqDraft.details"))
            # type a pack size, then pick "Bucket" in the unit menu
            await pg.evaluate("erpEnter('plan')"); await pg.wait_for_timeout(800)
            await pg.evaluate("tab='fill';render()"); await pg.wait_for_timeout(300)
            await pg.click('[data-act=invedit]'); await pg.wait_for_timeout(200)
            uid = await pg.get_attribute('.inv tbody tr >> nth=1 >> [data-f=pkN]', 'data-id')
            await pg.click(f'.inv [data-id="{uid}"][data-f=pkN]'); await pg.keyboard.press('Control+A'); await pg.keyboard.type('24')
            await pg.click(f'.inv select[data-id="{uid}"][data-f=pkU]'); await pg.wait_for_timeout(200)   # the menu opens: the number is saved, no redraw under the menu
            same = await pg.evaluate(f"""document.activeElement===document.querySelector('.inv select[data-id="{uid}"][data-f=pkU]')""")
            await pg.select_option(f'.inv select[data-id="{uid}"][data-f=pkU]', 'BUCKET'); await pg.wait_for_timeout(200)
            await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(300)   # the person moves on
            check('Typing a pack size then picking "Bucket": the menu is not replaced while open', same)
            check('...both the number and Bucket are kept and saved', await pg.input_value(f'.inv [data-id="{uid}"][data-f=pkN]') == '24' and await pg.evaluate(f"line('{uid}').pkU") == 'BUCKET' and str(await pg.evaluate(f"line('{uid}').pkN")) == '24', [await pg.input_value(f'.inv [data-id="{uid}"][data-f=pkN]'), await pg.evaluate(f"line('{uid}').pkU")])
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'\n{sum(res)}/{len(res)} keep-typing checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
