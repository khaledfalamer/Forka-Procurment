"""Issue vouchers and GRNs: Print and Share (PDF) straight from the voucher. python3 tests/share_print_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8800; BASE = f'http://127.0.0.1:{PORT}'
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
async def pdf_of(pg, click):
    async with pg.expect_download(timeout=30000) as dl:
        await pg.click(click)
    d = await dl.value; path = await d.path(); data = open(path, 'rb').read()
    return d.suggested_filename, data
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('oman')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
            await pg.evaluate("window.PRINTS=0;window.print=()=>PRINTS++;lang='ar';setOmSub('ops');tab='req';render()"); await pg.wait_for_timeout(200)
            await pg.click('[data-act=tnew]'); await pg.wait_for_timeout(200)
            tid = await pg.evaluate('reqOpen')
            await pg.evaluate(f"tSet('{tid}',{{branch:'oman',lines:[{{item:'OM-RICE',req:3,iss:3}}]}})"); await pg.evaluate(f"tStatus('{tid}','issued')"); await pg.evaluate(f"tStatus('{tid}','issued')"); await pg.wait_for_timeout(800)
            await pg.evaluate(f"billOpen=null;reqOpen='{tid}';render()"); await pg.wait_for_timeout(200)
            check('Issue voucher (Arabic): Print and Share right on the voucher', await pg.locator('[data-act=tbillgo][data-go=print]').count() == 1 and 'مشاركة' in await pg.inner_text('[data-act=tbillgo][data-go=share]'))
            await pg.screenshot(path=str(SHOTS / 'issue_share_buttons_ar.png'))
            await pg.click('[data-act=tbillgo][data-go=print]'); await pg.wait_for_timeout(600)
            check('Print opens the voucher paper and the print window', await pg.evaluate('PRINTS') == 1 and await pg.locator('#bill').count() == 1)
            name, data = await pdf_of(pg, '[data-act=tshare]')
            check('Oman voucher paper says it comes from the Oman store (not Ajman)', 'مخزن عُمان' in await pg.inner_text('#bill') and 'عجمان' not in await pg.inner_text('#bill'))
            check('Share makes a PDF of the voucher, named by its number', data[:4] == b'%PDF' and name.startswith('TN-') and name.endswith('.pdf') and len(data) > 20000, (name, len(data)))
            jpg = data[data.find(b'\xff\xd8'):data.rfind(b'\xff\xd9') + 2]; open(SHOTS / 'issue_share_pdf_ar.jpg', 'wb').write(jpg)
            await pg.evaluate("lang='en';billOpen=null;tab='grn';render()"); await pg.wait_for_timeout(200)
            await pg.click('[data-act=newgrn]'); await pg.wait_for_timeout(300)
            check('Receiving note (GRN): Print and Share right on the note', await pg.locator('[data-act=gdocgo][data-go=print]').count() == 1 and await pg.locator('[data-act=gdocgo][data-go=share]').count() == 1)
            async with pg.expect_download(timeout=30000) as dl:
                await pg.click('[data-act=gdocgo][data-go=share]')
            d = await dl.value; data = open(await d.path(), 'rb').read()
            check('Share on the GRN makes its PDF straight away (GRN-OM-...pdf)', data[:4] == b'%PDF' and d.suggested_filename.startswith('GRN-OM-'), d.suggested_filename)
            jpg = data[data.find(b'\xff\xd8'):data.rfind(b'\xff\xd9') + 2]; open(SHOTS / 'grn_share_pdf.jpg', 'wb').write(jpg)
            check('The buttons do not appear on the printed paper itself', await pg.evaluate("[...document.querySelectorAll('[data-act=tshare],[data-act=tprint]')].every(b=>b.closest('.no-print'))"))
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} share and print checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
