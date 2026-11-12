"""Procurement left menu: every page opens, stays on the LEFT in Arabic, collapses, drawer on phones, no menu on the start screen.
python3 tests/sidebar_test.py"""
import asyncio, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); PORT = 8801; BASE = f'http://127.0.0.1:{PORT}'
CFG = "window.FORKA_CONFIG={SHEET_URL:'',PIN:false,ERP_URL:'https://erp.forka.com/'};"
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None); errs = []
            async def page(w, h, lang='en', side='full'):
                ctx = await b.new_context(viewport={'width': w, 'height': h})
                await ctx.route('**/config.js*', lambda r: r.fulfill(body=CFG, content_type='application/javascript'))
                await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
                await ctx.add_init_script(f"try{{localStorage.setItem('pp-side','{side}')}}catch(e){{}}")
                pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto(BASE + '/'); await pg.wait_for_timeout(1200); await pg.evaluate(f"lang='{lang}';render()"); return ctx, pg
            ctx, pg = await page(1440, 900)
            check('Start screen: no left menu', not await pg.locator('#pside').is_visible())
            ok = True
            for side in ['plan', 'ops', 'fin', 'ceo', 'dept']:
                await pg.evaluate(f"enterSide('{side}');render()"); await pg.wait_for_timeout(100)
                keys = await pg.evaluate('sideTabs()')
                if await pg.locator('#pside .tab').count() != len(keys): ok = False
                for k in keys:
                    await pg.locator(f'#pside .tab[data-tab="{k}"]').click(); await pg.wait_for_timeout(60)
                    if await pg.evaluate('tab') != k or 'on' not in (await pg.locator(f'#pside .tab[data-tab="{k}"]').get_attribute('class')): ok = False
            check('Every side: the menu holds its pages and each one opens and is marked', ok)
            await pg.evaluate("enterSide('oman');setOmSub('ops');tab='grn';render()"); await pg.wait_for_timeout(100)
            await pg.evaluate("enterSide('plan');tab='fill';render()"); await pg.wait_for_timeout(100)
            check('Header shows the side and the page', 'Purchasing' in await pg.inner_text('#top .crumb') and 'Inventory' in await pg.inner_text('#top .crumb'))
            await pg.evaluate("enterSide('oman');setOmSub('ops');tab='grn';render()"); await pg.wait_for_timeout(100)
            check('Oman: the menu shows that part (Receiving, Issue vouchers, Stock movements)', await pg.locator('#pside .tab').count() == 3 and 'Issue vouchers' in await pg.inner_text('#pside'))
            check('Forka Apps link at the bottom of the menu', await pg.locator('#pside .ps-apps[href="https://erp.forka.com/"]').count() == 1)
            await pg.evaluate("enterSide('plan');render()")
            w0 = (await pg.locator('#pside').bounding_box())['width']; await pg.click('.ps-mini'); await pg.wait_for_timeout(200)
            w1 = (await pg.locator('#pside').bounding_box())['width']
            check('Collapse to icons, remembered', w0 > 200 and w1 < 90 and await pg.evaluate("localStorage.getItem('pp-side')") == 'mini', (w0, w1))
            await ctx.close()
            ctx, pg = await page(1440, 900, 'ar'); await pg.evaluate("enterSide('plan');render()"); await pg.wait_for_timeout(200)
            sb = await pg.locator('#pside').bounding_box(); pm = await pg.locator('#pmain').bounding_box()
            check('Arabic: menu stays on the LEFT, page right-to-left', sb['x'] < 5 and pm['x'] > 200 and await pg.evaluate("getComputedStyle(document.querySelector('#page')).direction") == 'rtl', (sb, pm))
            check('Arabic menu items', 'المخزون' in await pg.inner_text('#pside')); await ctx.close()
            ctx, pg = await page(390, 844); await pg.evaluate("enterSide('plan');render()"); await pg.wait_for_timeout(200)
            check('Phone: menu hidden behind the menu button', (await pg.locator('#pside').bounding_box())['x'] < -100 and await pg.locator('.ps-burger').is_visible())
            await pg.click('.ps-burger'); await pg.wait_for_timeout(300)
            check('Phone: the drawer opens; Forka Apps is at the bottom', (await pg.locator('#pside').bounding_box())['x'] > -5 and (await pg.locator('.ps-apps').bounding_box())['y'] > (await pg.locator('#pside .tab').last.bounding_box())['y'])
            await pg.locator('#pside .tab[data-tab="sups"]').click(); await pg.wait_for_timeout(300)
            check('Phone: choosing a page opens it and closes the drawer', await pg.evaluate('tab') == 'sups' and (await pg.locator('#pside').bounding_box())['x'] < -100)
            check('No page errors', not errs, errs[:3]); await ctx.close(); await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} menu checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
