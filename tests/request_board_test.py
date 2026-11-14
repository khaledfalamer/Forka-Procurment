""""Open in Board" on a purchase request (Khaled, 14 Nov 2026): the button shows for Purchasing, the CEO and the person who asked
(matched by email), not for another department, not in Oman; pressing it asks the Procurement server (only the request id), then
becomes "Open the Board card" linking to erp.forka.com/boards/#card=<id>; the thread notes it; "not set up yet" shows a friendly
message; Arabic; the #rq=<id> link from the Board opens the request; no emojis, no page errors. Also runs the Code.gs server check
(tests/request_board_server_test.js). Fake servers only. python3 tests/request_board_test.py   (SHOTS=dir also saves screenshots)"""
import asyncio, json, os, pathlib, re, socket, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
SHOTS = os.environ.get('SHOTS')
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
PORT = free_port(); BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u2712\u2714\u2716-\u27BF\u2B50\u2B55]')   # the plain glyphs ✓ and ✕ are allowed
res = []; POSTS = []
PEOPLE = {
    'buyer': {'name': 'Ali Buyer', 'email': 'buyer@forka.com', 'sides': ['plan'], 'role': 'admin'},
    'chef': {'name': 'Head Chef', 'email': 'chef@forka.com', 'sides': ['dept'], 'role': 'admin'},
    'bar': {'name': 'Bar Lead', 'email': 'bar@forka.com', 'sides': ['dept'], 'role': 'admin'},
    'ceo': {'name': 'Khaled', 'email': 'khaled@forka.com', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'},
}
WHO = {'me': PEOPLE['buyer']}
D = '2026-11-14T08:00:00Z'
def rq(no, title, status, **k):
    r = {'no': no, 'title': title, 'kind': 'design', 'dept': 'kitchen', 'branch': 'sharjah', 'status': status, 'by': 'Head Chef', 'byEmail': 'Chef@Forka.com',
         'date': D, 'qty': 1, 'unit': 'PCS', 'urg': 'normal', 'cost': 'opex', 'needBy': '2026-11-20', 'details': 'New menu board for the counter. We need the logo files and the size.',
         'buyer': 'Ali Buyer', 'log': [{'at': D, 'by': 'Head Chef', 'type': 'status', 'text': 'new'}, {'at': D, 'by': 'Ali Buyer', 'type': 'status', 'text': 'review'},
                                         {'at': D, 'by': 'Ali Buyer', 'type': 'msg', 'text': 'Which size do you need?'}]}
    r.update(k); return r
def fresh():
    return {'R-1': rq('PRQ-261114-01', 'Menu board with the new logo', 'review'), 'R-2': rq('PRQ-261114-02', 'Takeaway bag print', 'sourcing'),
            'R-3': rq('PRQ-261114-03', 'Bar menu cards', 'review', by='Bar Lead', byEmail='bar@forka.com', kind='design')}
REQS = fresh()
BASE_TAB = {l['id']: l for l in json.load(open(pathlib.Path(ROOT) / 'demo-data.json', encoding='utf-8'))['lines']}   # the sample item list
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}'); POSTS.append(b); me = WHO['me']
    if b.get('boardCard'):
        rid = b['boardCard']
        if rid == 'R-2': return await route.fulfill(json={'ok': False, 'error': 'nosetup'})
        r = dict(REQS[rid]); r['boardCard'] = {'id': 'cPR' + rid[-1], 'url': 'https://erp.forka.com/boards/#card=cPR' + rid[-1], 'by': me['name'], 'at': D}
        r['log'] = r['log'] + [{'at': D, 'by': me['name'], 'type': 'board', 'text': 'Board card opened by ' + me['name']}]; REQS[rid] = r
        return await route.fulfill(json={'ok': True, 'cardId': r['boardCard']['id'], 'boardId': 'bPR', 'url': r['boardCard']['url'], 'rec': r})
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v' + str(len(POSTS)), 'lines': {}, 'suppliers': {}, 'tabs': {'Requests': REQS, 'Base': BASE_TAB}})
    await route.fulfill(json={'ok': True, 'ver': 'v2'})

async def main():
    # 1. the server side (Code.gs) with pretend Google services
    out = subprocess.run(['node', os.path.join(ROOT, 'tests', 'request_board_server_test.js')], capture_output=True, text=True)
    print(out.stdout.strip())
    check('Code.gs: the boardCard action passes its checks (node)', out.returncode == 0, out.stdout[-400:] + out.stderr[-400:])
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            errs = []
            async def page_as(who, sd, w=1366, h=900, hash_extra='', enter=True):
                WHO['me'] = PEOPLE[who]
                ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2)
                await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
                await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
                await ctx.route('https://proc.test/**', server)
                pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto(BASE + '/#' + hash_extra + 'erp=' + TOK); await pg.wait_for_timeout(1200)
                if enter: await pg.evaluate(f"erpEnter('{sd}')")
                await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
                return ctx, pg
            async def open_rq(pg, rid, tab):
                await pg.evaluate(f"lang='en';tab='{tab}';rqOpenId='{rid}';render()"); await pg.wait_for_timeout(150)
            async def shot(pg, name):
                if SHOTS: await pg.locator('[data-blk=owner]').scroll_into_view_if_needed(); await pg.screenshot(path=os.path.join(SHOTS, name))
            BTN = '[data-blk=owner] #rqboard'

            # Purchasing
            ctx, pg = await page_as('buyer', 'plan')
            await open_rq(pg, 'R-1', 'prq')
            check('Purchasing: "Open in Board" shows in the Owner and status block', (await pg.inner_text(BTN)).strip() == 'Open in Board' and await pg.locator(BTN).evaluate('e=>e.tagName') == 'BUTTON')
            await pg.reload(); await pg.wait_for_function("typeof mode!=='undefined'&&mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
            await open_rq(pg, 'R-1', 'prq')
            check('After a reload (sign-in step skipped) the button still shows', await pg.locator(BTN).count() == 1, await pg.evaluate('JSON.stringify([ERP_SIDES,MY_SIDES,side])'))
            await shot(pg, 'request_open_in_board.png')
            n0 = len(POSTS)
            await pg.click(BTN); await pg.wait_for_timeout(500)
            sent = [x for x in POSTS[n0:] if x.get('boardCard')]
            check('Pressing it asks the Procurement server with only the request id (and the sign-in), nothing else', len(sent) == 1 and sent[0]['boardCard'] == 'R-1' and sent[0].get('erp') == TOK
                  and not any(k in sent[0] for k in ['data', 'batch', 'key', 'cardId']), sent)
            href = await pg.get_attribute(BTN, 'href')
            check('It turns into "Open the Board card" linking to the card in Board (same window)', (await pg.inner_text(BTN)).strip() == 'Open the Board card' and href == 'https://erp.forka.com/boards/#card=cPR1'
                  and await pg.get_attribute(BTN, 'target') is None, (href, await pg.inner_text(BTN)))
            th = await pg.inner_text('[data-blk=thread]')
            check('The clarification thread notes it: "Opened a Board card for this request" by the person', 'Opened a Board card for this request' in th and 'Ali Buyer' in th, th)
            check('No browser save carried the card link (only the server sets it)', not any('boardCard' in json.dumps(x.get('batch') or x.get('data') or {}) for x in POSTS), '')
            await shot(pg, 'request_board_linked.png')
            await open_rq(pg, 'R-2', 'pon')
            await pg.click(BTN); await pg.wait_for_timeout(500)
            msg = await pg.inner_text('[data-blk=owner] .rqboard .banner')
            check('Not set up yet: a friendly message, the button stays', 'not set up yet' in msg and (await pg.inner_text(BTN)).strip() == 'Open in Board', msg)
            await pg.evaluate("lang='ar';render()"); await pg.wait_for_timeout(150)
            check('Arabic: the message and the button in Arabic, right to left', 'غير مُعدّ بعد' in await pg.inner_text('[data-blk=owner] .rqboard .banner') and (await pg.inner_text(BTN)).strip() == 'افتح في اللوحة'
                  and await pg.evaluate('document.documentElement.dir') == 'rtl')
            await pg.evaluate("rqOpenId='R-1';tab='prq';render()"); await pg.wait_for_timeout(150)
            check('Arabic: "Open the Board card" and the thread note in Arabic', (await pg.inner_text(BTN)).strip() == 'افتح بطاقة اللوحة' and 'فتح بطاقة في اللوحة لهذا الطلب' in await pg.inner_text('[data-blk=thread]'))
            await shot(pg, 'request_board_arabic.png')
            body = await pg.inner_text('body')
            await pg.evaluate("lang='en';rqOpenId='R-2';tab='pon';render()"); await pg.wait_for_timeout(150)
            body += await pg.inner_text('body')
            check('No emojis', not EMOJI.search(body), EMOJI.findall(body)[:5])
            check('Oman section: no "Open in Board"', await pg.evaluate("(()=>{let v=null;inRegion('oman',()=>{v=rqBoardCan({id:'R-1',no:'X',byEmail:'buyer@forka.com'})});return v})()") is False)
            check('No page errors (Purchasing)', not errs, errs)
            await ctx.close()

            # the requester, under My requests (matched by email, not by name)
            ctx, pg = await page_as('chef', 'dept')
            await open_rq(pg, 'R-1', 'rmine')
            check('Requester: "Open the Board card" on their linked request', (await pg.inner_text(BTN)).strip() == 'Open the Board card' and 'Opened a Board card for this request' in await pg.inner_text('[data-blk=thread]'))
            await shot(pg, 'request_board_requester.png')
            await open_rq(pg, 'R-2', 'rmine')
            check('Requester: "Open in Board" on their own request', (await pg.inner_text(BTN)).strip() == 'Open in Board')
            await pg.evaluate("myEmail='someone.else@forka.com';render()"); await pg.wait_for_timeout(100)
            check('The same name with another email does not get the button (email match only)', await pg.locator(BTN).count() == 0)
            await ctx.close()

            # another department
            ctx, pg = await page_as('bar', 'dept')
            await open_rq(pg, 'R-1', 'rmine')
            check('Another department: no button on someone else\'s request', await pg.locator('[data-blk=owner]').count() == 1 and await pg.locator(BTN).count() == 0)
            await open_rq(pg, 'R-3', 'rmine')
            check('...but yes on their own request', (await pg.inner_text(BTN)).strip() == 'Open in Board')
            await ctx.close()

            # the CEO
            ctx, pg = await page_as('ceo', 'ceo')
            await open_rq(pg, 'R-3', 'appr')
            check('CEO: "Open in Board" shows', (await pg.inner_text(BTN)).strip() == 'Open in Board')
            await ctx.close()

            # the link back from the Board card: procurement.forka.com/#rq=<id>
            ctx, pg = await page_as('buyer', 'plan', hash_extra='rq=R-1&', enter=False)   # one section only: it opens by itself, as from the Board
            await pg.wait_for_timeout(300)
            check('The link from the Board card (#rq=<id>) opens that request', await pg.evaluate('rqOpenId') == 'R-1' and await pg.locator('[data-blk=summary]').count() == 1
                  and 'PRQ-261114-01' in await pg.inner_text('[data-blk=summary]'), await pg.evaluate('[rqOpenId,tab]'))
            await ctx.close()
            check('No page errors', not errs, errs)
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} request Board checks passed'); sys.exit(0 if all(res) else 1)

asyncio.run(main())
