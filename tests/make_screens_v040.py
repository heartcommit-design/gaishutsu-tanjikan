"""0.4.0 予定の人の写真を出発の前に撮る：画面写真を docs/screens_v0.4.0/ に撮る（1倍・256色）。suite には入れない。"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image
from v200_util import jst
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v0.4.0'); os.makedirs(DST, exist_ok=True)
URL = 'file://' + APP + '/index.html'
errs = []


def shot(pg, name):
    pg.evaluate("toastHide();document.querySelectorAll('#prBar,#bkBar,#gapBar').forEach(e=>e.hidden=true)"); pg.wait_for_timeout(200)
    f = os.path.join(DST, name + '.png'); pg.screenshot(path=f)
    Image.open(f).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f, optimize=True)


with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h, tag in ((1180, 820, 'yoko'), (1024, 1366, 'tate')):
        ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.clock.install(time=jst(2026, 11, 19, 9, 30))
        pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.evaluate("window.tone=function(){}")
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
        pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
        # 見本：アラームの帯を出さない（デモの外出中の人の帰院予定を先へ）
        pg.evaluate("outings.filter(o=>['out','search'].includes(o.status)).forEach(o=>{o.dueAt=Date.now()+5*3600000;});lastSig='';")
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(800)
        oid = pg.evaluate("outings.filter(o=>o.status==='planned'&&!o.hasPhoto).sort((a,b)=>a.departAt-b.departAt)[0].id")
        # デモの服の絵を、出発の前に撮った写真として入れる
        pg.evaluate("async id=>{const o=outings.find(x=>x.id===id);const c=DEMO_CLOTHES[2];await dbPut('photos',await demoClothesBlob(c[1],c[2]),id);dropPhotoURL(id);o.hasPhoto=true;o.photoAt=Date.now();addLog(o,'服装写真を登録（出発の前）','');await saveOuting(o);planSig='';await renderPlans();}", oid)
        pg.wait_for_timeout(500)
        shot(pg, f'1_yotei_{tag}')
        pg.click(f'#planList .card[data-id="{oid}"] [data-pact=go]'); pg.wait_for_timeout(700)
        shot(pg, f'2_go_{tag}')
        ctx.close()
    b.close()
print('errors', errs)
