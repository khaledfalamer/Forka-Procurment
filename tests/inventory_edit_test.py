"""Inventory: locked until Edit, remove an item with X (asks first), Save sends the changes. python3 tests/inventory_edit_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
import json as _j, pathlib as _pl
BASE_TAB = {l['id']: l for l in _j.load(open(_pl.Path(__file__).resolve().parent.parent / 'demo-data.json', encoding='utf-8'))['lines']}  # the server sends the item list after sign-in
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8797; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
SAVED = []; res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Khaled', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'Base': BASE_TAB}})
    if b.get('batch'): SAVED.extend(b['batch'])
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000)
            await pg.evaluate("tab='fill';render()"); await pg.wait_for_timeout(300)
            dis = await pg.eval_on_selector_all('.inv [data-f]', 'e=>e.filter(x=>!x.disabled).length')
            check('Inventory opens locked: nothing can be changed until Edit is pressed', dis == 0 and await pg.locator('[data-act=invedit]').count() == 1 and await pg.locator('.rmx').count() == 0, dis)
            await pg.screenshot(path=str(SHOTS / 'inv_locked.png'))
            await pg.click('[data-act=invedit]'); await pg.wait_for_timeout(200)
            check('Edit unlocks the fields and shows a remove (X) button on each item', await pg.eval_on_selector_all('.inv [data-f]', 'e=>e.filter(x=>!x.disabled).length') > 50 and await pg.locator('.rmx').count() > 50)
            first = await pg.evaluate("lines().map(l=>l.id)[0]"); rows = await pg.locator('.inv tbody tr').count()
            pid = await pg.get_attribute('.inv tbody tr >> nth=1 >> [data-f=p]', 'data-id')
            await pg.fill(f'.inv [data-id="{pid}"][data-f=p]', '9.99'); await pg.dispatch_event(f'.inv [data-id="{pid}"][data-f=p]', 'change'); await pg.wait_for_timeout(200)
            rid = await pg.get_attribute('.inv tbody tr >> nth=0 >> .rmx', 'data-id'); rname = await pg.evaluate(f"line('{rid}').n")
            await pg.click('.inv tbody tr >> nth=0 >> .rmx'); await pg.wait_for_timeout(150)
            box = await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''
            check('Pressing X asks first, naming the item', rname in box and 'Remove' in box, box)
            await pg.screenshot(path=str(SHOTS / 'inv_remove_confirm.png'))
            await pg.click('.cfm [data-x=no]'); await pg.wait_for_timeout(150)
            check('"Keep it" leaves the item where it was', await pg.locator('.cfm').count() == 0 and await pg.locator(f'.rmx[data-id="{rid}"]').count() == 1)
            await pg.click(f'.rmx[data-id="{rid}"]'); await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(200)
            await pg.wait_for_timeout(1000)
            check('"Yes, remove" takes it off the list; inventory edits wait for the inventory\'s Save (not sent on their own)', await pg.locator(f'.rmx[data-id="{rid}"]').count() == 0 and await pg.evaluate('nUnsaved()') == 2 and 'Save (2)' in await pg.inner_text('[data-act=invsave]') and not SAVED)
            await pg.click('[data-act=invsave]'); await pg.wait_for_timeout(150)
            check('Save asks first ("Save 2 changes to the inventory?")', 'Save 2 changes' in (await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''))
            await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(800)
            got = {it['id']: it['data'] for it in SAVED}
            check('Save sends the removal and the price change', got.get(rid, {}).get('off') is True and got.get(pid, {}).get('p') == 9.99, list(got)[:5])
            check('After saving, the inventory is locked again', await pg.evaluate('invEdit') is False and await pg.locator('.rmx').count() == 0 and await pg.eval_on_selector_all('.inv [data-f]', 'e=>e.filter(x=>!x.disabled).length') == 0)
            await pg.click('[data-act=invedit]'); qid = await pg.get_attribute('.inv tbody tr >> nth=2 >> [data-f=st]', 'data-id'); old = await pg.input_value(f'.inv [data-id="{qid}"][data-f=st]')
            await pg.fill(f'.inv [data-id="{qid}"][data-f=st]', '123'); await pg.dispatch_event(f'.inv [data-id="{qid}"][data-f=st]', 'change'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=invcancel]'); await pg.wait_for_timeout(150)
            check('Cancel with unsaved changes asks before dropping them', 'Drop your unsaved changes' in (await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''))
            await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(200)
            check('...and puts everything back as it was', await pg.input_value(f'.inv [data-id="{qid}"][data-f=st]') == old and await pg.evaluate('nUnsaved()') == 0)
            await pg.click('[data-act=invedit]'); await pg.fill(f'.inv [data-id="{qid}"][data-f=st]', '55'); await pg.dispatch_event(f'.inv [data-id="{qid}"][data-f=st]', 'change'); await pg.wait_for_timeout(100)
            await pg.click('[data-tab=sups]'); await pg.wait_for_timeout(150)
            check('Leaving the inventory with unsaved changes asks to save them', 'Save them before leaving' in (await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else '') and await pg.evaluate('tab') == 'fill')
            await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(800)
            check('...Yes saves and moves on', await pg.evaluate('tab') == 'sups' and await pg.evaluate('nUnsaved()') == 0)
            await pg.evaluate("tab='fill';invEdit=false;render()")
            await pg.evaluate("lang='ar';render()"); await pg.click('[data-act=invedit]'); await pg.click('.inv tbody tr >> nth=0 >> .rmx'); await pg.wait_for_timeout(150)
            check('The warning is in Arabic too', 'حذف' in await pg.inner_text('.cfm') and 'إبقاء' in await pg.inner_text('.cfm'))
            await pg.screenshot(path=str(SHOTS / 'inv_remove_confirm_ar.png')); await pg.keyboard.press('Escape')
            check('Escape closes the warning without removing', await pg.locator('.cfm').count() == 0)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} inventory edit checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
