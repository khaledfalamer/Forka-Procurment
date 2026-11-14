"""Oman store: import suppliers and items from a file (owner), then Save sends them to the Oman tabs. python3 tests/oman_import_test.py"""
import asyncio, json, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True); PORT = 8796; BASE = f'http://127.0.0.1:{PORT}' + os.environ.get('SITE_PATH', '')
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
# made-up suppliers and items (the real Oman file has bank details and is never kept in this public repository)
FILE = {'forka': 'procurement-planner', 'region': 'oman', 'sups': {}, 'lines': {}}
for i in range(29):
    FILE['sups'][f'S-OM-TEST-{i}'] = {'n': 'Test Supplier %d' % i, 'contact': 'Contact', 'phone': '+968 9000 00%02d' % i, 'emirate': 'North Al Batinah', 'terms': 'credit' if i % 2 else 'cash',
                                     'days': 30 if i % 2 else None, 'payFrom': 'uae' if i % 2 else 'oman', 'iban': 'OM00TEST%015d' % i, 'cats': ['veg'], 'notes': ''}
FILE['sups']['S-OM-TAMMRA'] = FILE['sups'].pop('S-OM-TEST-1'); FILE['sups']['S-OM-TAMMRA'].update({'n': 'Tammra', 'phone': '+968 7000 0001'})
FILE['sups']['S-OM-TEST-2']['n'] = 'Bet Al Sahl'
for i in range(52):
    FILE['lines'][f'N-OM-{i:03d}'] = {'n': 'Test item %d' % i, 'con': 'Al Matbakh', 'cat': 'Food', 'sup': 'Test Supplier 3', 'pay': 'credit', 'use': 10, 'par': 5, 'st': 1, 'p': 1.5, 'u': 'KG', 'pkN': 1, 'pkU': 'KG', 'isNew': True}
FILE['lines']['N-OM-007'].update({'n': 'Garlic (توم)', 'sup': 'Oriental Projects', 'p': 0.8, 'use': 150, 'par': 100, 'pkN': 2.5})
SAVED = []
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Khaled', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {}})
    if b.get('batch'): SAVED.extend(b['batch'])
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=os.environ.get('SITE_ROOT', ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.route('https://proc.test/**', server)
            errs = []; pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1500)
            await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000); await pg.wait_for_timeout(300)
            # on the UAE side the Oman file is refused
            await pg.evaluate("tab='sum';render()"); await pg.wait_for_timeout(200)
            await pg.fill('#imp', json.dumps(FILE)); await pg.click('[data-act=import]'); await pg.wait_for_timeout(200)
            check('An Oman file imported on the UAE side is refused (says to open Oman)', 'Oman' in await pg.inner_text('#toast') and await pg.evaluate('Object.keys(local).length') == 0, await pg.inner_text('#toast'))
            await pg.evaluate("goSide('oman');setOmSub('plan');tab='sum';render()"); await pg.wait_for_timeout(300)
            await pg.fill('#imp', json.dumps(FILE)); await pg.click('[data-act=import]'); await pg.wait_for_timeout(300)
            t = await pg.inner_text('#toast')
            check('In Oman: 52 items and 29 suppliers are added and saved straight away', 'Added and saved 52 items and 29 suppliers' in t, t)
            await pg.evaluate("tab='sups';render()"); await pg.wait_for_timeout(200)
            body = await pg.inner_text('body')
            check('The suppliers show in Oman > Suppliers, with missing details marked', 'Tammra' in body and 'Bet Al Sahl' in body)
            await pg.screenshot(path=str(SHOTS / 'oman_suppliers.png'))
            await pg.evaluate("tab='fill';render()"); await pg.wait_for_timeout(200)
            names = await pg.eval_on_selector_all('[data-f=n]', 'e=>e.map(x=>x.value)')
            check('The items show in Oman > Inventory (52 lines)', len(names) == 52 and any(n.startswith('Garlic (توم)') for n in names), len(names))
            await pg.screenshot(path=str(SHOTS / 'oman_items.png'))
            await pg.wait_for_timeout(1500)
            kinds = {}
            for it in SAVED: kinds[it.get('kind')] = kinds.get(it.get('kind'), 0) + 1
            check('Save sends them to the Oman tabs (OmanItems, OmanSuppliers), not the UAE ones', kinds == {'OmanItems': 52, 'OmanSuppliers': 29}, kinds)
            sup = next(it for it in SAVED if it['id'] == 'S-OM-TAMMRA')['data']
            check('A supplier keeps its details (phone, terms, paid from, IBAN, governorate)', sup['phone'] == '+968 7000 0001' and sup['terms'] == 'credit' and sup['payFrom'] == 'uae' and sup['iban'].startswith('OM00TEST') and sup['emirate'] == 'North Al Batinah', sup)
            it = next(x for x in SAVED if x['data'].get('n', '').startswith('Garlic (توم)'))['data']
            check('An item keeps its details (supplier, unit, price, monthly use, minimum, pack)', it['sup'] == 'Oriental Projects' and it['u'] == 'KG' and it['p'] == 0.8 and it['use'] == 150 and it['par'] == 100 and it['pkN'] == 2.5, it)
            check('Nothing left unsaved', await pg.evaluate('Object.keys(local).length+Object.keys(supLocal).length') == 0)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} Oman import checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
