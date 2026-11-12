"""Forka suite header and module menu in Procurement: same shared files as erp.forka.com, app switcher and role in the header,
no tab hidden without "More", no sideways page scroll (phone, tablet, laptop; English and Arabic), phone drawer.
python3 tests/suite_test.py   (SHOTS=/some/dir also saves screenshots there)"""
import asyncio, hashlib, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; PORT = 8794; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
SHOTS = os.environ.get('SHOTS')
ALL = ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman']
REQS = {f'R-{i}': {'no': f'PRQ-261111-0{i}', 'title': t, 'kind': 'food', 'dept': 'kitchen', 'status': st, 'by': 'Branch Manager', 'date': '2026-11-11T08:00:00Z', 'log': []}
        for i, (t, st) in enumerate([('Gloves size L, 10 boxes', 'new'), ('Chef knives set', 'new'), ('Walk-in chiller repair', 'approval'), ('Menu printing', 'sourcing')])}
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Khaled Alamer', 'sides': ALL, 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'Requests': REQS}})
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
SIZES = [(390, 844), (768, 1024), (1024, 768), (1366, 900)]
# page-level sideways scroll: the document is wider than the window (tables scroll inside .tbl-wrap only)
WIDE = "()=>{const d=document.documentElement;return {sw:d.scrollWidth,cw:d.clientWidth,bad:[...document.querySelectorAll('body *')].filter(e=>{if(e.closest('.tbl-wrap,.fs-pop,.fs-drawer,[hidden]'))return false;const r=e.getBoundingClientRect();return r.width&&(r.right>d.clientWidth+1||r.left<-1)}).slice(0,4).map(e=>e.tagName+'.'+e.className+':'+Math.round(e.getBoundingClientRect().left)+'-'+Math.round(e.getBoundingClientRect().right))}}"
async def main():
    # 1. the shared files are byte-for-byte the ones listed in suite/SUITE_SHA256 (the same list lives in the forka-erp repo)
    want = {}
    for ln in (ROOT / 'suite' / 'SUITE_SHA256').read_text().splitlines():
        if ln.strip(): h, n = ln.split(); want[n] = h
    for n in ('suite.js', 'suite.css'):
        got = hashlib.sha256((ROOT / 'suite' / n).read_bytes()).hexdigest()
        check(f'suite/{n} matches suite/SUITE_SHA256', want.get(n) == got, (want.get(n), got))
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    check('index.html loads suite/suite.css and suite/suite.js', 'href="suite/suite.css"' in html and 'src="suite/suite.js"' in html)
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1366, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            check('Landing (side buttons) shows the suite header with the app switcher', await pg.locator('#top .fs-head [data-fs=apps]').count() == 1 and await pg.locator('[data-door=plan]').count() == 1)
            await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
            # 2. header: switcher, app name, side, user and role, language, Exit
            check('Header has the app switcher', await pg.locator('#top .fs-head [data-fs=apps]').count() == 1)
            await pg.click('#top [data-fs=apps]'); await pg.wait_for_timeout(100)
            apps = await pg.inner_text('#top [data-fs-pop=apps]')
            check('App switcher lists App, Hire, Board, Procurement (brand names)', all(x in apps for x in ('Hire', 'Board', 'Procurement')), apps)
            await pg.keyboard.press('Escape')
            who = await pg.inner_text('#top .fs-user')
            check('Header shows the user name and role', 'Khaled Alamer' in who and 'Admin' in who, who)
            head = await pg.inner_text('#top .fs-head')
            check('Header shows the side (Purchasing) and Exit', 'Purchasing' in head and await pg.locator('#top .fs-head [data-act=exit]').count() == 1, head)
            check('Save status stays in the header area ("All saved")', 'All saved' in await pg.inner_text('#top'))
            check('No sideways-scrolling tab strip (tabs are a module menu)', await pg.locator('#top .fs-menu .tab').count() == 8 and await pg.evaluate("getComputedStyle(document.querySelector('#top .fs-menu')).overflowX") == 'visible')
            # 3. no tab hidden without "More"
            for w in (1366, 1024, 768):
                await pg.set_viewport_size({'width': w, 'height': 900}); await pg.wait_for_timeout(200)
                r = await pg.evaluate("""()=>{const nav=document.querySelector('#top .fs-menu');const it=[...nav.querySelectorAll(':scope>.tab')];
                  const hid=it.filter(e=>!e.offsetWidth).map(e=>e.dataset.tab);const more=[...nav.querySelectorAll('[data-fs-pop=more] [data-tab]')].map(e=>e.dataset.tab);
                  const btn=nav.querySelector('.fs-more-btn');return {hid,more,btn:btn&&!btn.hidden,fits:nav.scrollWidth<=nav.clientWidth+1}}""")
                check(f'{w}: every tab is visible or under "More"', r['fits'] and sorted(r['hid']) == sorted(r['more']) and (bool(r['hid']) == bool(r['btn'])), r)
            # tab change from the More menu still goes through the same click handler
            await pg.set_viewport_size({'width': 768, 'height': 1024}); await pg.wait_for_timeout(200)
            mv = await pg.evaluate("[...document.querySelectorAll('#top [data-fs-pop=more] [data-tab]')].map(e=>e.dataset.tab)")
            if mv:
                await pg.click('#top [data-fs=more]'); await pg.click(f'#top [data-fs-pop=more] [data-tab={mv[-1]}]'); await pg.wait_for_timeout(200)
                check('A tab picked from "More" opens it', await pg.evaluate('tab') == mv[-1], mv)
            await pg.evaluate("tab='prq';render()")
            # 4. no page-level sideways scroll, English and Arabic, on several screens
            for sd, tabs in (('plan', ['prq', 'lpo', 'fill', 'sups']), ('ops', ['moves', 'grn']), ('ceo', ['appr']), ('fin', ['pay'])):
                await pg.evaluate(f"enterSide('{sd}')"); await pg.wait_for_timeout(150)
                for lg in ('en', 'ar'):
                    for (w, h) in SIZES:
                        await pg.set_viewport_size({'width': w, 'height': h})
                        bad = []
                        for tb in tabs:
                            await pg.evaluate(f"lang='{lg}';tab='{tb}';render()"); await pg.wait_for_timeout(120)
                            r = await pg.evaluate(WIDE)
                            if r['sw'] > r['cw']: bad.append((tb, r))
                        check(f'No page sideways scroll: {sd} {lg} {w}x{h}', not bad, bad[:2])
            await pg.evaluate("lang='en';enterSide('plan')")
            # 5. phone: drawer holds the tabs, bottom bar with the side's own tabs
            await pg.set_viewport_size({'width': 390, 'height': 844}); await pg.wait_for_timeout(200)
            check('Phone: the tab menu is folded away, the burger shows', not await pg.locator('#top .fs-menu').is_visible() and await pg.locator('#top [data-fs=burger]').is_visible())
            bt = await pg.evaluate("[...document.querySelectorAll('.fs-bottom [data-tab]')].map(e=>e.dataset.tab)")
            check('Phone: bottom bar has Requests, Orders, Inventory of Purchasing', bt == ['prq', 'lpo', 'fill'], bt)
            await pg.click('#top [data-fs=burger]'); await pg.wait_for_timeout(200)
            dr = await pg.evaluate("[...document.querySelectorAll('.fs-drawer [data-tab]')].map(e=>e.dataset.tab)")
            check('Phone: the drawer opens with every Purchasing tab', await pg.locator('.fs-drawer').is_visible() and dr == ['prq', 'pon', 'lpo', 'fill', 'sups', 'ana', 'sum', 'how'], dr)
            check('Phone: Exit is in the drawer', await pg.locator('.fs-drawer [data-act=exit]').count() == 1)
            if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, 'proc-390-en-drawer.png'))
            await pg.click('.fs-drawer [data-tab=sups]'); await pg.wait_for_timeout(200)
            check('Phone: a tab in the drawer opens it and closes the drawer', await pg.evaluate('tab') == 'sups' and not await pg.locator('.fs-drawer').is_visible())
            await pg.click('.fs-bottom [data-tab=fill]'); await pg.wait_for_timeout(200)
            check('Phone: the bottom bar opens Inventory', await pg.evaluate('tab') == 'fill')
            # 6. language switch in the suite header does what EN / عربي did
            await pg.set_viewport_size({'width': 1366, 'height': 900}); await pg.evaluate("tab='prq';render()")
            await pg.click('#top [data-fs-lang=ar]'); await pg.wait_for_timeout(200)
            check('Header language switch turns the app Arabic (RTL), and it is remembered', await pg.evaluate("lang+document.documentElement.dir+ls('pp-lang')") == 'arrtlar')
            if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, 'proc-1366-ar.png'))
            await pg.click('#top [data-fs-lang=en]'); await pg.wait_for_timeout(200)
            check('...and back to English', await pg.evaluate("lang") == 'en')
            if SHOTS: await pg.screenshot(path=os.path.join(SHOTS, 'proc-1366-en-purchasing.png'))
            body = await pg.evaluate("document.body.innerText")
            check('No emojis on the page', not any(0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x26FF for c in body))
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} suite header checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
