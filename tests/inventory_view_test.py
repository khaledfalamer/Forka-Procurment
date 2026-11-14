"""Inventory workspace: default columns, pinned Item / Stock now, Columns menu, row drawer, windowed rows,
saved views, phone cards, no sideways page scroll, English and Arabic. python3 tests/inventory_view_test.py"""
import asyncio, json, os, pathlib, re, socket, subprocess, sys, time
from playwright.async_api import async_playwright
import json as _j, pathlib as _pl
BASE_TAB = {l['id']: l for l in _j.load(open(_pl.Path(__file__).resolve().parent.parent / 'demo-data.json', encoding='utf-8'))['lines']}  # the server sends the item list after sign-in
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); SHOTS = pathlib.Path(ROOT) / 'tests' / 'shots'; SHOTS.mkdir(exist_ok=True)
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
PORT = free_port(); BASE = f'http://127.0.0.1:{PORT}' + os.environ.get('SITE_PATH', '')
CFG = "window.FORKA_CONFIG={SHEET_URL:'https://proc.test/exec',PIN:'auto',ERP_URL:'https://erp.forka.com/'};"
TOK = 'ERPTOK-00000000000000000000'
SAVED = []; res = []
DEFAULT = ['item', 'stock', 'sup', 'rop', 'buy', 'p', 'bud', 'status']
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-⛿✀-✒✔✖-➿⭐⭕️]')
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def server(route):
    b = json.loads(route.request.post_data or '{}')
    me = {'name': 'Khaled', 'sides': ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'], 'role': 'admin'}
    if b.get('check') and not b.get('load'): return await route.fulfill(json={'ok': True, 'me': me})
    if b.get('load'): return await route.fulfill(json={'ok': True, 'me': me, 'ver': 'v1', 'lines': {}, 'suppliers': {}, 'tabs': {'Base': BASE_TAB}})
    if b.get('batch'): SAVED.extend(b['batch'])
    await route.fulfill(json={'ok': True, 'ver': 'v2'})
async def new_ctx(b, w, h):
    ctx = await b.new_context(viewport={'width': w, 'height': h})
    await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
    await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
    await ctx.route('https://proc.test/**', server)
    return ctx
async def open_inv(pg, errs, lang='en', reload=False):
    if not reload:
        pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(BASE + '/#erp=' + TOK); await pg.wait_for_timeout(1200)
    await pg.evaluate("erpEnter('plan')"); await pg.wait_for_function("mode==='live'", timeout=8000)
    await pg.evaluate(f"lang='{lang}';tab='fill';invEdit=false;render()"); await pg.wait_for_timeout(250)
async def cols(pg): return await pg.eval_on_selector_all('.inv thead th', 'e=>e.map(x=>x.dataset.k)')
async def all_ids(pg):
    """Scroll the table box from top to bottom and collect every row that gets drawn."""
    return await pg.evaluate("""async()=>{const w=document.querySelector('.tbl-wrap.inv');const seen=new Set();let maxDrawn=0;w.scrollTop=0;
      for(let i=0;i<400;i++){await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
        const rows=w.querySelectorAll('tbody tr[data-inv]');maxDrawn=Math.max(maxDrawn,rows.length);rows.forEach(r=>seen.add(r.dataset.inv));
        if(w.scrollTop+w.clientHeight>=w.scrollHeight-2)break;w.scrollTop+=Math.floor(w.clientHeight*0.8)}
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));w.querySelectorAll('tbody tr[data-inv]').forEach(r=>seen.add(r.dataset.inv));
      return {n:seen.size,maxDrawn}}""")
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=os.environ.get('SITE_ROOT', ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None)
            errs = []
            ctx = await new_ctx(b, 1366, 900); pg = await ctx.new_page(); await open_inv(pg, errs)
            # 1. default columns
            check('Default columns: Item, Stock now, Supplier, Reorder point, To buy, Unit price, Budget, Status', await cols(pg) == DEFAULT, await cols(pg))
            await pg.screenshot(path=str(SHOTS / 'inv_view_default.png'))
            # 2. every row reachable through the windowed table, count matches the data
            total = await pg.evaluate('lines().length'); got = await all_ids(pg)
            shown = await pg.inner_text('.ivcount')
            check(f'All {total} items are reachable by scrolling the table (only part drawn at a time)', got['n'] == total and got['maxDrawn'] < total and str(total) in shown.replace(',', ''), (got, total, shown))
            check('The table scrolls inside its own box; the page itself has no sideways scroll', await pg.evaluate("(()=>{const w=document.querySelector('.tbl-wrap.inv');return w.scrollHeight>w.clientHeight&&getComputedStyle(w).overflowY==='auto'&&document.documentElement.scrollWidth<=innerWidth})()"))
            await pg.evaluate("document.querySelector('.tbl-wrap.inv').scrollTop=0"); await pg.wait_for_timeout(150)
            # 3. Columns menu adds / removes a column and remembers it
            await pg.click('[data-act=ivcols]'); await pg.wait_for_timeout(100)
            check('Columns menu lists all 14 columns; Item and Stock now cannot be hidden', await pg.locator('.ivmenu [data-ivcol]').count() == 14 and await pg.is_disabled('[data-ivcol=item]') and await pg.is_disabled('[data-ivcol=stock]'))
            await pg.click('[data-ivcol=pay]'); await pg.wait_for_timeout(150)
            check('Ticking "Payment" adds the column', 'pay' in await cols(pg) and await pg.locator('.inv tbody [data-f=pay]').count() > 10, await cols(pg))
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
            await open_inv(pg, errs, reload=True)
            check('...and it is remembered after reopening the page', 'pay' in await cols(pg), await cols(pg))
            await pg.click('[data-act=ivcols]'); await pg.click('[data-ivcol=pay]'); await pg.wait_for_timeout(150)
            check('Unticking removes it again', await cols(pg) == DEFAULT, await cols(pg))
            await pg.click('h2'); await pg.wait_for_timeout(100)
            check('Clicking outside closes the Columns menu', await pg.locator('.ivmenu').count() == 0)
            # 4. drawer opens on row click and shows conversion / usage / reserve
            await pg.click('.inv tbody tr[data-inv="F-85"] td[data-k=bud]'); await pg.wait_for_timeout(200)
            dr = await pg.inner_text('.invdr') if await pg.locator('.invdr').count() else ''
            check('Clicking a row opens the drawer with conversion, usage and reserve', all(x.lower() in dr.lower() for x in ['Conversion', 'Usage', 'Reserve (min)', 'Each one contains', 'Supply mode', 'Payment', 'days left', '=']), dr[:300])
            box = await pg.evaluate("(()=>{const r=document.querySelector('.invdr').getBoundingClientRect();return [r.left,r.right,innerWidth]})()")
            check('In English the drawer opens from the right', abs(box[1] - box[2]) < 2 and box[0] > 500, box)
            check('Locked (not editing): drawer fields cannot be changed', await pg.eval_on_selector_all('.invdr [data-f]', 'e=>e.length>8&&e.every(x=>x.disabled)'))
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
            check('Escape closes the drawer', await pg.locator('.invdr').count() == 0)
            await pg.focus('.ivopen[data-id="F-85"]'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            check('Keyboard: Enter on the row\'s details button opens the drawer', await pg.locator('.invdr').count() == 1)
            await pg.click('.invdr [data-act=invclose] >> nth=0'); await pg.wait_for_timeout(100)
            # 5. edit in the drawer counts as an unsaved change and Save works like before
            await pg.click('[data-act=invedit]'); await pg.wait_for_timeout(150)
            check('Edit mode: editable cells look like fields, read-only cells stay plain', await pg.evaluate("(()=>{const ed=getComputedStyle(document.querySelector('.inv tbody td.ed')).backgroundColor,ro=getComputedStyle(document.querySelector('.inv tbody td[data-k=bud]')).backgroundColor,inp=getComputedStyle(document.querySelector('.inv tbody td[data-k=stock] input')).backgroundColor;return ed!==ro&&inp==='rgb(255, 255, 255)'})()"))
            pid = await pg.get_attribute('.inv tbody tr >> nth=3', 'data-inv')
            await pg.click(f'.inv tbody tr[data-inv="{pid}"] td[data-k=buy]'); await pg.wait_for_timeout(150)
            await pg.fill('.invdr [data-f=par]', '17'); await pg.dispatch_event('.invdr [data-f=par]', 'change'); await pg.wait_for_timeout(200)
            await pg.select_option('.invdr [data-f=pay]', 'credit'); await pg.wait_for_timeout(200)
            check('A drawer edit (also of a hidden column, Payment) counts as unsaved; status shows it', await pg.evaluate('nUnsaved()') == 1 and '1 unsaved' in await pg.inner_text('.ivsave') and 'Save (1)' in await pg.inner_text('.ivbar [data-act=invsave]') and await pg.evaluate(f"line('{pid}').par") == 17 and await pg.evaluate(f"line('{pid}').pay") == 'credit', [await pg.evaluate('nUnsaved()'), await pg.inner_text('.ivsave'), await pg.inner_text('.ivbar [data-act=invsave]'), await pg.evaluate(f"[line('{pid}').par,line('{pid}').pay]")])
            check('The changed fields are marked in the drawer', await pg.locator('.invdr [data-f=par].chg').count() == 1)
            await pg.screenshot(path=str(SHOTS / 'inv_view_drawer_edit.png'))
            await pg.click('.invdr [data-act=invsave]'); await pg.wait_for_timeout(150)
            check('Save asks first, as before', 'Save 1 changes' in (await pg.inner_text('.cfm') if await pg.locator('.cfm').count() else ''))
            await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(900)
            got = {it['id']: it['data'] for it in SAVED}
            check('...and sends the drawer changes; the inventory locks again and shows "All saved"', got.get(pid, {}).get('par') == 17 and got.get(pid, {}).get('pay') == 'credit' and await pg.evaluate('invEdit') is False and 'All saved' in await pg.inner_text('.ivsave'), got.get(pid))
            await pg.evaluate("invOpen=null;render()")
            # 6. saved views
            sup = await pg.evaluate("line('F-62').sup")
            await pg.select_option('#fsup', sup); await pg.wait_for_timeout(150); await pg.select_option('#fstk', 'order'); await pg.wait_for_timeout(150)
            n_f = await pg.locator('.inv tbody tr[data-inv]').count()
            await pg.click('[data-act=ivsaveview]'); await pg.fill('#ivvname', 'Hoot to order'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            await pg.select_option('#fsup', ''); await pg.wait_for_timeout(100); await pg.select_option('#fstk', ''); await pg.wait_for_timeout(100)
            await open_inv(pg, errs, reload=True)
            check('Saved view is kept in this browser', await pg.locator('#ivview option', has_text='Hoot to order').count() == 1 and await pg.evaluate("fl.sup") == '')
            await pg.select_option('#ivview', label='Hoot to order'); await pg.wait_for_timeout(200)
            check('Choosing the saved view restores its filters', await pg.evaluate('fl.sup') == sup and await pg.evaluate('fl.stk') == 'order' and await pg.input_value('#fsup') == sup and await pg.locator('.inv tbody tr[data-inv]').count() == n_f, (await pg.evaluate('JSON.stringify(fl)'), n_f))
            await pg.click('[data-act=ivdelview]'); await pg.wait_for_timeout(150)
            check('A saved view can be deleted', await pg.locator('#ivview option', has_text='Hoot to order').count() == 0)
            await pg.evaluate("Object.assign(fl,{q:'',st:'all',con:'',sup:'',pay:'',stk:''});render()")
            body = await pg.inner_text('#page')
            check('No emojis in the inventory view', not EMOJI.search(body), EMOJI.findall(body)[:5])
            # 7. pinned columns stay visible after scrolling sideways (EN and AR)
            for lang in ['en', 'ar']:
                await pg.set_viewport_size({'width': 1024, 'height': 768})
                await pg.evaluate(f"lang='{lang}';render()"); await pg.wait_for_timeout(100)
                await pg.click('[data-act=ivcols]')
                for k in ['sm', 'pay', 'use', 'par', 'unit', 'pack']: await pg.click(f'[data-ivcol={k}]'); await pg.wait_for_timeout(60)
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(100)
                r = await pg.evaluate("""(async()=>{const w=document.querySelector('.tbl-wrap.inv');const rtl=document.dir==='rtl';
                  const over=w.scrollWidth>w.clientWidth+50;w.scrollLeft=rtl?-w.scrollWidth:w.scrollWidth;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                  const W=w.getBoundingClientRect(),tr=w.querySelector('tbody tr[data-inv]');const R=k=>tr.querySelector(`td[data-k=${k}]`).getBoundingClientRect();
                  const a=R('item'),b=R('stock'),s=R('sup');const inside=x=>x.left>=W.left-1&&x.right<=W.right+1;
                  const edge=rtl?Math.abs(a.right-W.right)<3:Math.abs(a.left-W.left)<3;const next=rtl?Math.abs(b.right-a.left)<2:Math.abs(b.left-a.right)<2;
                  return {over,scrolled:Math.abs(w.scrollLeft)>50,item:inside(a)&&edge,stock:inside(b)&&next,supGone:!inside(s),thead:w.querySelector('th.pin1').getBoundingClientRect().left>=W.left-1}})()""")
                check(f'{lang.upper()}: after scrolling sideways, Item and Stock now stay pinned ({"right" if lang=="ar" else "left"} side)', all(r.values()), r)
                await pg.screenshot(path=str(SHOTS / f'inv_view_pinned_{lang}.png'))
                await pg.click('[data-act=ivcols]')
                for k in ['sm', 'pay', 'use', 'par', 'unit', 'pack']: await pg.click(f'[data-ivcol={k}]'); await pg.wait_for_timeout(60)
                await pg.keyboard.press('Escape')
            await pg.click('.inv tbody tr[data-inv] td[data-k=buy] >> nth=0'); await pg.wait_for_timeout(150)
            box = await pg.evaluate("(()=>{const r=document.querySelector('.invdr').getBoundingClientRect();return [r.left,r.right,innerWidth]})()")
            dr = await pg.inner_text('.invdr')
            check('In Arabic the drawer opens from the left, with Arabic labels', box[0] < 2 and box[1] < box[2] - 200 and 'التحويل' in dr and 'الاستهلاك' in dr, box)
            await pg.keyboard.press('Escape')
            await ctx.close()
            # 8. phones: card mode
            ctx = await new_ctx(b, 390, 844); pg = await ctx.new_page(); await open_inv(pg, errs)
            card = await pg.evaluate("""(()=>{const tr=document.querySelector('.inv tbody tr[data-inv]');const vis=[...tr.children].filter(td=>getComputedStyle(td).display!=='none').map(td=>td.dataset.k);
              return {thead:getComputedStyle(document.querySelector('.inv thead')).display,tr:getComputedStyle(tr).display,vis}})()""")
            check('Phone (390px): one card per item with name, stock now, reorder point, to buy and status', card['thead'] == 'none' and card['tr'] == 'grid' and card['vis'] == ['item', 'stock', 'rop', 'buy', 'status'], card)
            got = await all_ids(pg); total = await pg.evaluate('lines().length')
            check('Phone: every card is reachable by scrolling', got['n'] == total, (got, total))
            await pg.evaluate("document.querySelector('.tbl-wrap.inv').scrollTop=0"); await pg.wait_for_timeout(100)
            await pg.screenshot(path=str(SHOTS / 'inv_view_cards.png'))
            await pg.click('.inv tbody tr[data-inv] td[data-k=rop] >> nth=0'); await pg.wait_for_timeout(150)
            box = await pg.evaluate("(()=>{const r=document.querySelector('.invdr').getBoundingClientRect();return [r.left,r.right,innerWidth]})()")
            check('Phone: tapping a card opens the drawer full width', box[0] <= 1 and abs(box[1] - box[2]) < 2, box)
            await ctx.close()
            # 9. no page-level sideways scroll at 4 sizes, English and Arabic
            bad = []
            for (w, h) in [(390, 844), (768, 1024), (1024, 768), (1366, 900)]:
                ctx = await new_ctx(b, w, h); pg = await ctx.new_page(); await open_inv(pg, errs)
                for lang in ['en', 'ar']:
                    await pg.evaluate(f"lang='{lang}';invOpen=null;render()"); await pg.wait_for_timeout(120)
                    for st in ['locked', 'drawer']:
                        if st == 'drawer': await pg.evaluate("invEdit=true;invOpen=lines()[0].id;render()"); await pg.wait_for_timeout(120)
                        sw = await pg.evaluate('[document.documentElement.scrollWidth,innerWidth]')
                        if sw[0] > sw[1]: bad.append((w, lang, st, sw))
                    await pg.evaluate("invEdit=false;invOpen=null;render()")
                await ctx.close()
            check('No page-level sideways scroll at 390x844, 768x1024, 1024x768, 1366x900 (EN and AR, with and without the drawer)', not bad, bad)
            check('No page errors', not errs, errs[:3])
            await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} inventory view checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
