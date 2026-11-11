"""Oman store: issue vouchers (إذن الصرف) from the Oman store to the restaurant kitchen. python3 tests/oman_issue_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8799; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
ITEMS = {'OM-RICE': {'n': 'Rice (ارز)', 'con': 'Al Matbakh', 'cat': 'Food', 'sup': 'Test Supplier', 'pay': 'credit', 'use': 20, 'par': 5, 'st': 10, 'p': 2.5, 'u': 'BAG', 'pkN': 1, 'pkU': 'BAG', 'isNew': True}}
SAVED = []; res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Oman Manager', 'sides': ['oman'], 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'OmanItems': ITEMS}})
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
            await pg.evaluate("erpEnter('oman')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
            await pg.evaluate("setOmSub('ops');tab='grn';render()"); await pg.wait_for_timeout(200)
            tabs = await pg.locator('#top .tab').all_inner_texts()
            check('Oman > Operations has Issue vouchers (next to Receiving and Stock movements)', 'Issue vouchers' in tabs, tabs)
            await pg.click('[data-tab=req]'); await pg.wait_for_timeout(200)
            check('The page explains it: from the Oman store to the restaurant kitchen', 'restaurant kitchen' in await pg.inner_text('#page'))
            await pg.click('[data-act=tnew]'); await pg.wait_for_timeout(200)
            tid = await pg.evaluate('reqOpen')
            check('New issue voucher opens (TN number)', bool(tid) and 'TN-' in await pg.inner_text('#page'))
            await pg.screenshot(path=str(SHOTS / 'oman_issue_new.png'))
            await pg.evaluate(f"tSet('{tid}',{{branch:'oman',lines:[{{item:'OM-RICE',req:3,iss:3}}]}})"); await pg.wait_for_timeout(100)
            await pg.evaluate(f"tStatus('{tid}','issued')"); await pg.evaluate(f"tStatus('{tid}','issued')"); await pg.wait_for_timeout(1500)
            kinds = {}
            for it in SAVED: kinds[it.get('kind')] = kinds.get(it.get('kind'), 0) + 1
            tn = [it for it in SAVED if it.get('kind') == 'OmanTransfers']
            rice = [it for it in SAVED if it.get('kind') == 'OmanItems' and it['id'] == 'OM-RICE']
            check('Issuing saves the voucher to the Oman tab (OmanTransfers), on its own, no Save button', tn and tn[-1]['data'].get('status') == 'issued', kinds)
            check('...and takes the issued quantity off the Oman store stock (10 - 3 = 7)', rice and rice[-1]['data'].get('st') == 7, rice[-1:] if rice else kinds)
            check('Nothing is saved to the UAE tabs', not any(k in kinds for k in ('Transfers', None, 'line')), kinds)
            await pg.evaluate("lang='ar';render()"); await pg.wait_for_timeout(150)
            check('In Arabic it is called إذن الصرف', 'إذن الصرف' in ' '.join(await pg.locator('#top .tab').all_inner_texts()))
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} Oman issue checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
