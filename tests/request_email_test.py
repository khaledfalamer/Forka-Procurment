"""Purchasing can email the requester from a request; the email carries the request number and title. python3 tests/request_email_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time, urllib.parse
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8799; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
SAVED = []; res = []; WHO = {'me': {'name': 'Buyer', 'email': 'buyer@forka.com', 'sides': ['plan', 'dept'], 'role': 'team'}}
REQS = {'R-1': {'no': 'PRQ-261112-01', 'title': 'Gloves size L, 10 boxes', 'kind': 'food', 'dept': 'kitchen', 'status': 'review', 'by': 'Head Chef', 'byEmail': 'chef@forka.com', 'date': '2026-11-12T08:00:00Z', 'log': []},
        'R-0': {'no': 'PRQ-261101-02', 'title': 'Old request', 'kind': 'food', 'dept': 'kitchen', 'status': 'review', 'by': 'Someone', 'date': '2026-11-01T08:00:00Z', 'log': []}}
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': WHO['me']})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': WHO['me'], 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'Requests': REQS}})
    if b.get('batch'): SAVED.extend(b['batch'])
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=2)
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(800)
            await pg.evaluate("window.MAILS=[];openMail=u=>MAILS.push(u);tab='prq';rqOpenId='R-1';render()"); await pg.wait_for_timeout(300)
            check('Purchasing sees an "Email requester" button under the message box', await pg.locator('[data-act=rqmail]').count() == 1)
            await pg.fill('#rqtext', 'Which glove brand do you prefer?')
            await pg.locator('[data-act=rqmail]').scroll_into_view_if_needed(); await pg.screenshot(path=str(SHOTS / 'request_email.png'))
            n0 = len(SAVED); await pg.click('[data-act=rqmail]'); await pg.wait_for_timeout(900)
            m = (await pg.evaluate('MAILS'))[-1:] or ['']
            u = urllib.parse.urlparse(m[0]); q = urllib.parse.parse_qs(u.query)
            sub, body = (q.get('subject') or [''])[0], (q.get('body') or [''])[0]
            check('The email goes to the requester', u.scheme == 'mailto' and u.path == 'chef@forka.com', m)
            check('The subject has the request number and title', 'PRQ-261112-01' in sub and 'Gloves size L, 10 boxes' in sub, sub)
            check('The body has the message, the request number and the title', 'Which glove brand' in body and 'Request number: PRQ-261112-01' in body and 'Request: Gloves size L, 10 boxes' in body, body)
            log = [it for it in SAVED[n0:] if it['id'] == 'R-1']
            check('The email is noted in the request record (saved to the server)', log and log[-1]['data']['log'][-1]['type'] == 'mail', SAVED[n0:])
            await pg.evaluate("rqOpenId='R-0';render()"); await pg.wait_for_timeout(200); await pg.click('[data-act=rqmail]'); await pg.wait_for_timeout(300)
            check('Older request with no saved email: the email still opens, and it says to type the address', (await pg.evaluate('MAILS'))[-1].startswith('mailto:?') and 'no saved email' in await pg.inner_text('#toast'))
            await pg.evaluate("lang='ar';rqOpenId='R-1';render()"); await pg.wait_for_timeout(200)
            check('Arabic button', 'مراسلة مقدم الطلب' in await pg.inner_text('[data-act=rqmail]'))
            await pg.click('[data-act=rqmail]'); await pg.wait_for_timeout(300)
            body = urllib.parse.parse_qs(urllib.parse.urlparse((await pg.evaluate('MAILS'))[-1]).query)['body'][0]
            check('Arabic email has رقم الطلب', 'رقم الطلب: PRQ-261112-01' in body, body)
            await pg.evaluate("lang='en';tab='rnew';rqDraft={kind:'food',title:'Mops',dept:'kitchen'};rqSubmit()"); await pg.wait_for_timeout(150); await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(800)
            new = [it for it in SAVED if it['kind'] == 'Requests' and it['data'].get('title') == 'Mops']
            check("New requests save the requester's email, so they can be emailed", new and new[-1]['data'].get('byEmail') == 'buyer@forka.com', new[-1:])
            await pg.evaluate("tab='rmine';rqOpenId=Object.keys(recLocal.Requests||{})[0]||rqOpenId;side='dept';render()"); await pg.wait_for_timeout(200)
            check('The requester (Requests side) does not see the button', await pg.locator('[data-act=rqmail]').count() == 0)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} request email checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
