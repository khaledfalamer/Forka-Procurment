"""Item photos and clear supplier amounts. python3 tests/item_photo_test.py"""
import asyncio, os, pathlib, subprocess, sys, time
from playwright.async_api import async_playwright
from PIL import Image
ROOT = str(pathlib.Path(__file__).resolve().parent.parent); PORT = 8802; BASE = f'http://127.0.0.1:{PORT}' + os.environ.get('SITE_PATH', '')
res = []
def check(n, ok, info=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else ' - ' + str(info)[:300]))
async def main():
    img = os.path.join(ROOT, 'tests', 'shots'); os.makedirs(img, exist_ok=True); img = os.path.join(img, '_item.jpg'); Image.new('RGB', (400, 300), '#ccbbaa').save(img)
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=os.environ.get('SITE_ROOT', ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get('PW_CHROMIUM') or None); errs = []
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
            await ctx.route('**/config.js*', lambda r: r.fulfill(body="window.FORKA_CONFIG={SHEET_URL:'',PIN:false,ERP_URL:''};", content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await ctx.add_init_script("try{localStorage.setItem('pp-me',JSON.stringify('Buyer (test)'))}catch(e){}")
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(BASE + '/'); await pg.wait_for_timeout(1200)
            await pg.evaluate("enterSide('plan');tab='fill';render()"); id = await pg.evaluate("BASE[0].id")
            await pg.evaluate(f"invOpen='{id}';render()"); await pg.wait_for_timeout(200)
            check('Drawer has a Photo section; outside Edit it says to press Edit', 'Press Edit' in await pg.inner_text('.invdr .ivph') and await pg.locator('[data-ivphoto]').count() == 0)
            await pg.evaluate("invEdit=true;render()"); await pg.wait_for_timeout(200)
            await pg.locator('[data-ivphoto]').set_input_files(img); await pg.wait_for_timeout(700)
            check('In Edit mode a photo can be added; it is kept on the item as an unsaved change', await pg.evaluate(f"!!line('{id}').img") and await pg.evaluate('nUnsaved()') >= 1 and await pg.locator('.invdr img.ivimg').count() == 1)
            await pg.click('[data-act=ivphrm]'); await pg.wait_for_timeout(200); await pg.click('.cfm [data-x=yes]'); await pg.wait_for_timeout(300)
            check('Remove photo asks first, then removes it', not await pg.evaluate(f"line('{id}').img"))
            await pg.evaluate("invEdit=false;invOpen=null;tab='sups';render()"); await pg.locator('tr.sup-row').first.click(); await pg.wait_for_timeout(300)
            txt = await pg.inner_text('#page')
            check('Supplier items explain the amounts (AED, To buy this month, unit price)', 'AED' in txt and 'To buy this month' in txt and 'Unit price' in txt and 'Right side' in txt)
            check('No page errors', not errs, errs[:3]); await b.close()
    finally:
        srv.terminate()
    print(f'{sum(res)}/{len(res)} item photo checks passed'); sys.exit(0 if all(res) else 1)
asyncio.run(main())
