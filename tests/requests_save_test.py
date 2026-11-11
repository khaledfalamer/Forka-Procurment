"""Requests reach Purchasing: no Save button, a confirm before sending, and nothing waits in someone's browser. python3 tests/requests_save_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8798; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
SAVED = []; ST = {'down': False}; res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Branch Manager', 'sides': ['plan', 'dept'], 'role': 'team'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {}})
    if ST['down']: return await route.fulfill(json={'ok': False, 'error': 'net'})
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
            # a request stuck in this browser from before (sent while a Save button was still needed)
            stuck = {'Requests': {'R-old': {'no': 'PRQ-261110-01', 'title': 'Old stuck request', 'kind': 'food', 'dept': 'kitchen', 'status': 'new', 'by': 'Branch Manager', 'date': '2026-11-10T08:00:00Z', 'log': []}}}
            await ctx.add_init_script("try{localStorage.setItem('pp-rlocal',%s)}catch(e){}" % json.dumps(json.dumps(stuck)))
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('dept')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(1500)
            check('A request stuck in a browser from before is sent as soon as the app opens', any(it['id'] == 'R-old' and it['kind'] == 'Requests' for it in SAVED) and await pg.evaluate('nUnsaved()') == 0, [it['id'] for it in SAVED])
            await pg.evaluate("try{localStorage.removeItem('pp-rlocal')}catch(e){}")
            top = await pg.inner_text('#top')
            check('No Save or Cancel button at the top; it says "All saved"', await pg.locator('#top [data-act=saveall]').count() == 0 and await pg.locator('#top [data-act=canceledits]').count() == 0 and 'All saved' in top, top[-120:])
            n0 = len(SAVED)
            await pg.evaluate("tab='rnew';rqDraft={kind:'food',title:'Gloves size L, 10 boxes',dept:'kitchen',qty:10,unit:'BOX'};rqSubmit()"); await pg.wait_for_timeout(200)
            box = await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''
            check('Sending a request asks first', 'Send "Gloves size L, 10 boxes" to Purchasing?' in box, box)
            await pg.screenshot(path=str(SHOTS / 'request_confirm.png'))
            await pg.click('.cfm [data-x=no]'); await pg.wait_for_timeout(300)
            check('Cancel: nothing is sent', len(SAVED) == n0)
            await pg.evaluate("tab='rnew';rqDraft={kind:'food',title:'Gloves size L, 10 boxes',dept:'kitchen',qty:10,unit:'BOX'};rqSubmit()"); await pg.wait_for_timeout(150)
            await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(900)
            got = [it for it in SAVED[n0:] if it['kind'] == 'Requests']
            check('Yes, send: the request reaches the server at once, no Save button needed', len(got) == 1 and got[0]['data']['title'] == 'Gloves size L, 10 boxes', SAVED[n0:])
            check('...and it only says "sent" once the server has it', 'sent' in (await pg.inner_text('#toast')).lower() and await pg.evaluate('nUnsaved()') == 0, await pg.inner_text('#toast'))
            ST['down'] = True; n1 = len(SAVED)
            await pg.evaluate("tab='rnew';rqDraft={kind:'food',title:'Mops',dept:'kitchen'};rqSubmit()"); await pg.wait_for_timeout(150); await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(900)
            check('No connection: it says "Not sent yet" and keeps it (never a false "sent")', 'Not sent yet' in await pg.inner_text('#toast') and await pg.evaluate('nUnsaved()') == 1, await pg.inner_text('#toast'))
            ST['down'] = False; await pg.evaluate("saveAll({lines:true})"); await pg.wait_for_timeout(700)
            check('When the connection is back it is sent', any(it['data'].get('title') == 'Mops' for it in SAVED[n1:]) and await pg.evaluate('nUnsaved()') == 0)
            await pg.evaluate("lang='ar';tab='rnew';rqDraft={kind:'food',title:'Sugar',dept:'kitchen'};render();rqSubmit()"); await pg.wait_for_timeout(150)
            check('The confirm is in Arabic too', 'إرسال' in await pg.inner_text('.cfm'))
            await pg.click('.cfm [data-x=no]')
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} request saving checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
