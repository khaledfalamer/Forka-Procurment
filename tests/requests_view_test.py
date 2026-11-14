"""Purchasing queue and request page (UI redesign 4.1): status pills filter, More filters, saved views, the four blocks of a request,
a confirm before big status changes ("No" changes nothing), separate Email requester / Add to the record buttons, CEO approve after
the confirm, requester phone only where it was before, no sideways page scroll (4 sizes, English and Arabic), no emojis, no page errors.
Mock data only. python3 tests/requests_view_test.py"""
import asyncio, json, os, pathlib, re, socket, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True)
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
PORT = free_port(); BASE = f'http://127.0.0.1:{PORT}' + os.environ.get('SITE_PATH', '')
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-⛿✀-✒✔✖-➿⭐⭕️]')
SAVED = []; res = []
ME = {'name': 'Khaled', 'email': 'khaled@forka.com', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'}
D = '2026-11-10T08:00:00Z'
def rq(no, title, status, **k):
    r = {'no': no, 'title': title, 'kind': 'food', 'dept': 'kitchen', 'branch': 'sharjah', 'status': status, 'by': 'Head Chef', 'byEmail': 'chef@forka.com',
         'date': D, 'qty': 10, 'unit': 'BOX', 'urg': 'normal', 'cost': 'opex', 'log': [{'at': D, 'by': 'Head Chef', 'type': 'status', 'text': 'new'}]}
    r.update(k); return r
PICK = [{'sup': 'Al Ain Foods', 'price': 12, 'lead': '2 days', 'pick': True}]
SPEC = {'brand': 'Any', 'cut': 'Whole', 'pack': 'Box'}
REQS = {
 'R-new1': rq('PRQ-261110-01', 'Chicken breast 30 kg', 'new', urg='urgent', phone='+971 50 111 2233', needBy='2026-11-14', budget=900),
 'R-new2': rq('PRQ-261110-02', 'Takeaway boxes', 'new', kind='other', cost='capex', dept='store'),
 'R-rev': rq('PRQ-261110-03', 'Cleaning supplies', 'review', buyer='Khaled', spec=SPEC),
 'R-rej': rq('PRQ-261110-04', 'Old fryer', 'rejected', prevStatus='new', closeReason='budget', closeNote='Not this month',
            log=[{'at': D, 'by': 'Head Chef', 'type': 'status', 'text': 'new'}, {'at': D, 'by': 'Khaled', 'type': 'status', 'text': 'rejected|Too expensive / no budget now|Not this month'}]),
 'R-src': rq('PRQ-261110-05', 'Olive oil 20 L', 'sourcing', buyer='Khaled', spec=SPEC),
 'R-quo': rq('PRQ-261110-06', 'Basmati rice 25 kg', 'quotes', buyer='Khaled', spec=SPEC, opts=PICK, budget=500, needBy='2026-11-20', refs='Same as last month',
             log=[{'at': D, 'by': 'Head Chef', 'type': 'status', 'text': 'new'}, {'at': D, 'by': 'Khaled', 'type': 'status', 'text': 'review'},
                  {'at': D, 'by': 'Khaled', 'type': 'msg', 'text': 'Is a 10 kg bag OK?'}, {'at': D, 'by': 'Head Chef', 'type': 'reply', 'text': 'Yes, 10 kg is fine'},
                  {'at': D, 'by': 'Khaled', 'type': 'note', 'text': 'Ask two suppliers'}, {'at': D, 'by': 'CEO', 'type': 'status', 'text': 'quotes|Send back to procurement|Get a cheaper quote'}]),
 'R-app': rq('PRQ-261110-07', 'Coffee beans', 'approval', buyer='Khaled', spec=SPEC, opts=PICK, sentCeoAt=D),
 'R-app2': rq('PRQ-261110-08', 'Milk jugs', 'approval', buyer='Khaled', spec=SPEC, opts=PICK, sentCeoAt=D),
 'R-ok': rq('PRQ-261110-09', 'Napkins', 'approved', buyer='Khaled', spec=SPEC, opts=PICK, ceo={'decision': 'approved', 'by': 'Khaled', 'at': D}),
 'R-ord': rq('PRQ-261110-10', 'Gloves', 'ordered', buyer='Khaled', spec=SPEC, opts=PICK),
 'R-later': rq('PRQ-261110-11', 'New oven', 'later', prevStatus='quotes', buyer='Khaled', spec=SPEC, opts=PICK, closeReason='later', closeNote='After Ramadan'),
 'R-mine': rq('PRQ-261110-12', 'Mops for the store', 'new', by='Khaled', byEmail='khaled@forka.com', phone='+971 50 999 8877'),
}
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': ME})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': ME, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'Requests': REQS}})
    if b.get('batch'): SAVED.extend(b['batch'])
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
async def new_ctx(b, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
    await ctx.route('https://proc.test/**', server)
    return ctx
async def open_app(pg, errs, sd='plan'):
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1200)
    await pg.evaluate(f"erpEnter('{sd}')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
    await pg.evaluate("window.MAILS=[];openMail=u=>MAILS.push(u)")
async def show(pg, js):
    await pg.evaluate(js + ';render()'); await pg.wait_for_timeout(120)
async def rows(pg): return await pg.eval_on_selector_all('.rqlist .rq-li', 'e=>e.map(x=>x.dataset.rqopen)')
async def status(pg, rid): return await pg.evaluate(f"(rec('Requests','{rid}')||{{}}).status")
async def no_hscroll(pg): return await pg.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=os.environ.get('SITE_ROOT', ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            errs = []
            ctx = await new_ctx(b, 1366, 900); pg = await ctx.new_page(); await open_app(pg, errs)
            await show(pg, "lang='en';side='plan';tab='prq';rqOpenId=null")
            # 1. status pills: the old KPI cards are a slim row of pills, clicking filters
            pills = await pg.eval_on_selector_all('.rqpills [data-rqst]', 'e=>e.map(x=>x.dataset.rqst)')
            check('Requests tab: status pills Open / New / Review (no big KPI cards)', pills == ['open', 'new', 'review'] and await pg.locator('.card.stat[data-rqst]').count() == 0, pills)
            check('Open pill shows the open count and CAPEX / OPEX split', '3' in await pg.inner_text('.rqpills [data-rqst=open]') and 'CAPEX 1' in await pg.inner_text('.rqpills [data-rqst=open]'), await pg.inner_text('.rqpills'))
            await pg.click('.rqpills [data-rqst=new]'); await pg.wait_for_timeout(120)
            r = await rows(pg)
            check('Clicking the "New" pill shows only new requests', sorted(r) == ['R-mine', 'R-new1', 'R-new2'] and await pg.get_attribute('.rqpills [data-rqst=new]', 'aria-pressed') == 'true', r)
            await pg.click('.rqpills [data-rqst=review]'); await pg.wait_for_timeout(120)
            check('Clicking the "Review" pill shows only requests in review', await rows(pg) == ['R-rev'], await rows(pg))
            await pg.click('.rqpills [data-rqst=open]'); await pg.wait_for_timeout(120)
            # urgent: one strong badge, only on urgent rows
            urg_rows = await pg.eval_on_selector_all('.rqlist .rq-li', 'e=>e.filter(x=>x.querySelector(".rq-urg")).map(x=>x.dataset.rqopen)')
            isurg = await pg.eval_on_selector_all('.rqlist .rq-li.is-urg', 'e=>e.map(x=>x.dataset.rqopen)')
            check('"Urgent" shows only on the urgent request, once', urg_rows == ['R-new1'] and isurg == ['R-new1'] and await pg.locator('.rqlist .rq-li[data-rqopen="R-new1"] .rq-urg').count() == 1, (urg_rows, isurg))
            check('Non-urgent requests carry no red badge at all', await pg.locator('.rqlist .rq-li:not(.is-urg) .rq-urg, .rqlist .rq-li:not(.is-urg) .badge.b-bad').count() == 0)
            check('The list never shows the requester phone (same as before)', '111 2233' not in await pg.inner_text('#page'))
            await pg.click('[data-rqfx=urg]'); await pg.wait_for_timeout(120)
            check('"Urgent" chip filters to urgent requests', await rows(pg) == ['R-new1'], await rows(pg)); await pg.click('[data-rqfx=urg]'); await pg.wait_for_timeout(120)
            await pg.click('[data-rqfx=mine]'); await pg.wait_for_timeout(120)
            check('"Handled by me" chip filters to my requests', await rows(pg) == ['R-rev'], await rows(pg)); await pg.click('[data-rqfx=mine]'); await pg.wait_for_timeout(120)
            # 2. More filters
            check('Kind, cost, department, location and closed statuses are hidden at first; search stays visible',
                  all([await pg.locator(s).count() == 0 for s in ['#rqkind', '#rqcost', '#rqdept', '#rqbranch', '[data-rqst=rejected]']]) and await pg.locator('#rqq').is_visible())
            await pg.click('[data-act=rqmore]'); await pg.wait_for_timeout(120)
            check('"More filters" reveals them', all([await pg.locator(s).is_visible() for s in ['#rqkind', '#rqcost', '#rqdept', '#rqbranch', '#rqmorebox [data-rqst=rejected]', '#rqmorebox [data-rqst=all]']]) and await pg.get_attribute('[data-act=rqmore]', 'aria-expanded') == 'true')
            await pg.select_option('#rqcost', 'capex'); await pg.wait_for_timeout(120)
            check('Cost filter works', await rows(pg) == ['R-new2'], await rows(pg))
            await pg.select_option('#rqcost', ''); await pg.select_option('#rqkind', 'other'); await pg.wait_for_timeout(120)
            check('Kind filter still works', await rows(pg) == ['R-new2'], await rows(pg))
            await pg.click('[data-act=rqmore]'); await pg.wait_for_timeout(120)
            check('With More closed, the button counts the hidden filters in use', (await pg.inner_text('[data-act=rqmore] .rqcnt')).strip() == '1')
            await pg.click('[data-act=rqclear]'); await pg.wait_for_timeout(120)
            check('Clear filters goes back to Open', await pg.evaluate("rqF.kind===''&&rqF.st==='open'") and len(await rows(pg)) == 4, await rows(pg))
            # 3. saved views
            await pg.click('.rqpills [data-rqst=new]'); await pg.fill('#rqq', 'chicken'); await pg.wait_for_timeout(150)
            await pg.click('[data-act=rqsaveview]'); await pg.wait_for_timeout(100); await pg.fill('#rqvname', 'Urgent chicken'); await pg.click('[data-act=rqviewok]'); await pg.wait_for_timeout(150)
            saved = await pg.evaluate("JSON.parse(localStorage.getItem('pp-rq-views')||'[]')")
            check('Save view keeps a name and the filters in this browser', saved and saved[-1]['name'] == 'Urgent chicken' and saved[-1]['f']['st'] == 'new' and saved[-1]['f']['q'] == 'chicken', saved)
            await pg.click('[data-act=rqclear]'); await pg.wait_for_timeout(120)
            await pg.reload(); await pg.wait_for_timeout(1200); await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000)
            await show(pg, "lang='en';side='plan';tab='prq';rqOpenId=null;window.MAILS=[];openMail=u=>MAILS.push(u)")
            await pg.select_option('#rqview', label='Urgent chicken'); await pg.wait_for_timeout(150)
            check('Choosing the saved view (after a reload) restores its filters', await pg.input_value('#rqq') == 'chicken' and await pg.get_attribute('.rqpills [data-rqst=new]', 'aria-pressed') == 'true' and await rows(pg) == ['R-new1'], await rows(pg))
            await pg.click('[data-act=rqdelview]'); await pg.wait_for_timeout(120)
            check('A saved view can be deleted', await pg.evaluate("JSON.parse(localStorage.getItem('pp-rq-views')||'[]').length") == 0)
            await pg.click('[data-act=rqclear]'); await pg.wait_for_timeout(100)
            await show(pg, "tab='pon'")
            check('Procurement ongoing: pills Active / Sourcing / Quotes / CEO / Approved / Ordered / Later', await pg.eval_on_selector_all('.rqpills [data-rqst]', 'e=>e.map(x=>x.dataset.rqst)') == ['active', 'sourcing', 'quotes', 'approval', 'approved', 'ordered', 'later'])
            await pg.click('.rqpills [data-rqst=approval]'); await pg.wait_for_timeout(120)
            check('Clicking the CEO-approval pill filters', sorted(await rows(pg)) == ['R-app', 'R-app2'], await rows(pg))
            await pg.click('.rqpills [data-rqst=active]'); await pg.wait_for_timeout(100)
            await pg.screenshot(path=str(SHOTS / 'rq_queue.png'))
            # 4. the four blocks
            await show(pg, "rqOpenId='R-quo'")
            blks = await pg.eval_on_selector_all('.rqd [data-blk]', 'e=>e.map(x=>x.dataset.blk)')
            check('Request page has four blocks: summary, owner and status, clarification thread, decision history', blks == ['summary', 'owner', 'thread', 'history'], blks)
            sm = await pg.inner_text('[data-blk=summary]'); ow = await pg.inner_text('[data-blk=owner]'); th = await pg.inner_text('[data-blk=thread]'); hi = await pg.inner_text('[data-blk=history]')
            check('Summary: title, number, quantity, needed by, budget, refs', all(x in sm for x in ['Basmati rice 25 kg', 'PRQ-261110-06', '10', 'BOX', 'Needed by', 'AED 500', 'Same as last month']), sm)
            check('Owner and status: buyer box, status, progress steps, action buttons', await pg.locator('[data-blk=owner] [data-rqf=buyer]').count() == 1 and await pg.locator('[data-blk=owner] .rq-steps').count() == 1
                  and await pg.locator('[data-blk=owner] [data-rqgo=approval]').count() == 1 and await pg.locator('[data-blk=owner] [data-rqgo=rejected]').count() == 1, ow)
            check('Thread: messages, replies and notes (not status changes), plus the message box', all(x in th for x in ['Is a 10 kg bag OK?', 'Yes, 10 kg is fine', 'Ask two suppliers']) and 'Get a cheaper quote' not in th
                  and await pg.locator('[data-blk=thread] #rqtext').count() == 1 and await pg.locator('[data-blk=thread] #rqlt').count() == 1, th)
            check('Decision history: status changes and the CEO send-back with its note', 'Get a cheaper quote' in hi and 'Send back to procurement' in hi and 'Is a 10 kg bag OK?' not in hi and await pg.locator('[data-blk=history] li').count() == 3, hi)
            check('Quote options and spec stay on the page', await pg.locator('[data-rqpick]').count() == 1 and await pg.locator('[data-rqspec=brand]').count() == 1)
            await pg.screenshot(path=str(SHOTS / 'rq_detail.png'), full_page=True)
            await show(pg, "rqOpenId='R-rej'")
            hi = await pg.inner_text('[data-blk=history]')
            check('Close reasons show in the decision history (status, reason and note)', all(x in hi for x in ['Not going ahead', 'Too expensive / no budget now', 'Not this month']), hi)
            # 5. Email requester and Add to the record are separate
            await show(pg, "rqOpenId='R-quo'")
            ml, lg = pg.locator('[data-act=rqmail]'), pg.locator('[data-act=rqlog]')
            check('"Email requester" and "Add to the record" are two separate, labelled buttons', await ml.count() == 1 and await lg.count() == 1 and 'Email requester' in await ml.inner_text()
                  and 'Add to the record' in await lg.inner_text() and await pg.evaluate("!document.querySelector('[data-act=rqmail]').contains(document.querySelector('[data-act=rqlog]'))"))
            await pg.fill('#rqtext', 'Price confirmed'); await pg.select_option('#rqlt', 'note'); await lg.click(); await pg.wait_for_timeout(150)
            L = await pg.evaluate("rec('Requests','R-quo').log.slice(-1)[0]")
            check('Add to the record saves a note and opens no email', L['type'] == 'note' and L['text'] == 'Price confirmed' and await pg.evaluate('MAILS.length') == 0, L)
            await pg.fill('#rqtext', 'When can you receive?'); await pg.click('[data-act=rqmail]'); await pg.wait_for_timeout(150)
            L = await pg.evaluate("rec('Requests','R-quo').log.slice(-1)[0]")
            check('Email requester opens the email and notes it as an email', L['type'] == 'mail' and await pg.evaluate('MAILS.length') == 1 and 'chef@forka.com' in (await pg.evaluate('MAILS[0]')), L)
            # 6. confirmations: "No" changes nothing, "Yes" moves it
            async def confirm_flow(name, rid, sel, want, setup="side='plan';tab='prq'"):
                await show(pg, f"{setup};rqOpenId='{rid}';rqClose=null")
                before = await status(pg, rid); n0 = len(SAVED)
                await pg.click(sel); await pg.wait_for_timeout(150)
                box = await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''
                await pg.click('.cfm [data-x=no]') if box else None; await pg.wait_for_timeout(150)
                same = await status(pg, rid) == before and not [x for x in SAVED[n0:] if x['id'] == rid] and await pg.evaluate(f"!(recLocal.Requests||{{}})['{rid}']")
                check(f'{name}: asks first, and "No" changes nothing', bool(box) and same, (box, before, await status(pg, rid)))
                await pg.click(sel); await pg.wait_for_timeout(150); await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(250)
                return box
            await confirm_flow('Accept', 'R-new2', '[data-rqgo=review]', 'review')
            check('...Yes: accepted (now in review)', await status(pg, 'R-new2') == 'review')
            await confirm_flow('Send to CEO', 'R-quo', '[data-rqgo=approval]', 'approval', "side='plan';tab='pon'")
            check('...Yes: sent to the CEO', await status(pg, 'R-quo') == 'approval')
            await confirm_flow('Withdraw from CEO', 'R-app2', '[data-rqgo=withdraw]', 'quotes', "side='plan';tab='pon'")
            check('...Yes: back to quotes', await status(pg, 'R-app2') == 'quotes')
            await confirm_flow('Reopen', 'R-later', '[data-rqgo=reopen]', 'quotes', "side='plan';tab='pon'")
            check('...Yes: reopened to where it was', await status(pg, 'R-later') == 'quotes')
            npo = await pg.evaluate("recs('POs').length")
            box = await confirm_flow('Create LPO', 'R-ok', '[data-act=rqopenpo]', 'approved', "side='plan';tab='pon'")
            check('...Yes: the LPO is created and opened', await pg.evaluate("recs('POs').length") == npo + 1 and await pg.evaluate('tab') == 'lpo' and 'LPO' in box)
            await show(pg, "side='plan';tab='pon';rqOpenId='R-ord';rqClose=null"); await pg.click('[data-rqgo=later]'); await pg.wait_for_timeout(150)
            check('Park for later keeps its reason panel (that is its confirmation), no extra box', await pg.locator('#rqcr').count() == 1 and await pg.locator('#rqcn').count() == 1 and await pg.locator('.cfm').count() == 0)
            await pg.click('[data-act=rqcloseno]'); await pg.wait_for_timeout(100)
            await show(pg, "rqOpenId='R-ord'"); await pg.click('[data-rqgo=rejected]'); await pg.wait_for_timeout(120)
            check('Not going ahead keeps its reason panel', await pg.locator('#rqcr').count() == 1 and await pg.locator('.cfm').count() == 0)
            await pg.click('[data-act=rqcloseno]')
            # CEO approve after the confirm
            await show(pg, "side='ceo';tab='appr';rqOpenId=null;apF='pending'")
            await pg.click('.li[data-rqopen="R-app"]'); await pg.wait_for_timeout(150)
            check('CEO sees the requester line and Approve / Send back / Not going ahead', await pg.locator('[data-rqgo=ceook]').count() == 1 and await pg.locator('[data-rqgo=ceoback]').count() == 1)
            await confirm_flow('CEO approve', 'R-app', '[data-rqgo=ceook]', 'approved', "side='ceo';tab='appr'")
            c = await pg.evaluate("rec('Requests','R-app').ceo")
            check('...Yes: approved by the CEO, LPO prepared', await status(pg, 'R-app') == 'approved' and c['decision'] == 'approved' and await pg.evaluate("!!rec('Requests','R-app').poId"), c)
            await show(pg, "side='ceo';tab='appr';rqOpenId='R-quo';rqClose=null"); await pg.click('[data-rqgo=ceoback]'); await pg.wait_for_timeout(120)
            check('CEO send back keeps its note panel', await pg.locator('#rqcn').count() == 1 and await pg.locator('.cfm').count() == 0); await pg.click('[data-act=rqcloseno]')
            # requester cancels own request
            await confirm_flow('Requester cancels', 'R-mine', '[data-rqgo=cancelled]', 'cancelled', "side='dept';tab='rmine'")
            check('...Yes: cancelled', await status(pg, 'R-mine') == 'cancelled')
            # 7. phone only where it was before: request page (all sides that open it), never the lists
            await show(pg, "side='plan';tab='prq';rqOpenId='R-new1'")
            check('Requester phone on the request page for Purchasing (as before)', '+971 50 111 2233' in await pg.inner_text('[data-blk=summary]'))
            await show(pg, "rqOpenId=null;rqF.st='all'")
            check('...and not in the Purchasing list', '111 2233' not in await pg.inner_text('#page'))
            await show(pg, "side='dept';tab='rmine';rqOpenId=null")
            check('My requests: the "New request" button opens the request form', await pg.locator('[data-act=rqnewgo]').count() == 1)
            await pg.click('[data-act=rqnewgo]'); await pg.wait_for_timeout(120)
            check('...same as the New request tab', await pg.evaluate('tab') == 'rnew')
            await show(pg, "side='plan';tab='prq';rqOpenId=null")
            check('No "New request" button on the Purchasing queue (it has no request form today)', await pg.locator('[data-act=rqnewgo]').count() == 0)
            await show(pg, "side='dept';tab='rmine';rqOpenId='R-mine'")
            check('Requester side: thread has no email button and no internal notes; Send button only', await pg.locator('[data-act=rqmail]').count() == 0 and await pg.locator('#rqlt').count() == 0)
            # 8. Arabic
            await show(pg, "lang='ar';side='plan';tab='pon';rqOpenId=null")
            ar = await pg.inner_text('#page')
            check('Arabic queue: right to left, Arabic pills and filters', await pg.evaluate("getComputedStyle(document.querySelector('.rqpills')).direction") == 'rtl' and 'فلاتر أكثر' in ar and 'المسندة لي' in ar, ar[:200])
            await show(pg, "rqOpenId='R-ord'")
            ar = await pg.inner_text('#page')
            check('Arabic request page: the four block titles in Arabic', all(x in ar for x in ['ملخص الطلب', 'المسؤول والحالة', 'محادثة التوضيح', 'سجل القرارات']), ar[:200])
            check('Arabic: request number kept in its own direction (bdi)', await pg.locator('[data-blk=summary] bdi.rqno').count() == 1)
            await show(pg, "side='ceo';tab='appr';rqOpenId='R-quo'")
            await pg.click('[data-rqgo=ceook]'); await pg.wait_for_timeout(120)
            check('Arabic confirm text', 'الموافقة على' in (await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''))
            await pg.click('.cfm [data-x=no]')
            await ctx.close()
            # 9. no sideways scroll, 4 sizes, English and Arabic, queue and request page; no emojis
            bad = []; emo = []
            for (w, h) in [(390, 844), (768, 1024), (1024, 768), (1366, 900)]:
                c2 = await new_ctx(b, w, h); p2 = await c2.new_page(); await open_app(p2, errs)
                for lg in ['en', 'ar']:
                    for v in ["tab='prq';rqOpenId=null;rqMore.in=true", "tab='pon';rqOpenId=null;rqMore.go=true", "tab='pon';rqOpenId='R-quo'", "tab='prq';rqOpenId='R-new1'", "side='dept';tab='rmine';rqOpenId=null", "side='dept';tab='rmine';rqOpenId='R-mine'"]:
                        await show(p2, f"lang='{lg}';side='plan';{v}"); await p2.wait_for_timeout(80)
                        if not await no_hscroll(p2): bad.append((w, lg, v, await p2.evaluate('document.documentElement.scrollWidth')))
                        m = EMOJI.findall(await p2.inner_text('#page'))
                        if m: emo.append((w, lg, v, m[:3]))
                if w == 390:
                    await show(p2, "lang='en';side='plan';tab='prq';rqOpenId=null;rqMore.in=false"); await p2.screenshot(path=str(SHOTS / 'rq_queue_phone.png'), full_page=True)
                await c2.close()
            check('No sideways page scroll at 390, 768, 1024 and 1366 wide, English and Arabic', not bad, bad)
            check('No emojis in the requests views', not emo, emo)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} requests view checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
