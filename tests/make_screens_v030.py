"""0.3.0「帰院の決まり」の画面写真を docs/screens_v0.3.0/ に撮る（1倍）。テストの一覧（suite.txt）には入れない。
使い方：cd tests && python3 make_screens_v020.py
"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v0.3.0'); os.makedirs(DST, exist_ok=True)
URL = 'file://' + APP + '/index.html'
JPG = os.path.join(HERE, 'out', 'v020_fuku.jpg'); os.makedirs(os.path.dirname(JPG), exist_ok=True)
Image.new('RGB', (300, 400), (60, 110, 180)).save(JPG, quality=80)
errs = []


def setup(b, w, h, t, theme='light'):
    ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=t)
    pg.add_init_script("localStorage.setItem('gaishutsu_tanjikan_theme', JSON.stringify({mode:'%s'}))" % theme)
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.evaluate("settings.themeMode='%s';saveSettings();applyTheme()" % theme)
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    # 見本を見やすく：デモの外出・外泊中の人のアラーム帯・控えの帯は消す（画面写真のためだけ）
    pg.evaluate("toastHide();outings.filter(o=>o.demo&&!o.itsumo&&['out','search'].includes(o.status)).forEach(o=>{o.dueAt=Date.now()+5*3600000;});lastSig='';")
    pg.evaluate("document.querySelectorAll('#prBar,#bkBar,#gapBar').forEach(e=>e.hidden=true)")
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(800)
    return ctx, pg


def shot(pg, name):
    pg.evaluate("toastHide();document.querySelectorAll('#prBar,#bkBar,#gapBar').forEach(e=>e.hidden=true)"); pg.wait_for_timeout(200)
    f = os.path.join(DST, name + '.png'); pg.screenshot(path=f)
    # 公開リポジトリを重くしないよう、256色にして保存（文字・形の見え方は変わらない）
    Image.open(f).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f, optimize=True)


def pid_id(pg, pid):
    return pg.evaluate("pid=>patients.find(p=>p.pid===pid).id", pid)


with sync_playwright() as p:
    b = p.chromium.launch()
    # 午前：出発の画面（11:30 が選ばれている）
    ctx, pg = setup(b, 1180, 820, jst(2026, 11, 18, 10, 58))
    pg.click(f'[data-itgo="{pid_id(pg, "D1024")}"]'); pg.wait_for_timeout(600); shot(pg, '1_shuppatsu_gozen')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    pg.click('#itRuleBtn'); pg.wait_for_timeout(400); shot(pg, '3_kiin_no_kimari')
    ctx.close()
    # 午後：15:20 は 16:00、13:10 は一覧に「+60分」
    ctx, pg = setup(b, 1180, 820, jst(2026, 11, 18, 15, 20))
    pg.click(f'[data-itgo="{pid_id(pg, "D1024")}"]'); pg.wait_for_timeout(600); shot(pg, '2_shuppatsu_gogo_1520')
    ctx.close()
    ctx, pg = setup(b, 1180, 820, jst(2026, 11, 18, 13, 10)); shot(pg, '4_ichiran_1310')
    o = pg.evaluate("id=>{const p=patients.find(q=>q.id===id);return p.id}", pid_id(pg, 'D1021'))
    pg.click(f'[data-itgo="{o}"]'); pg.wait_for_timeout(400); pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 青木'); pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(600)
    oid = pg.evaluate("id=>outings.find(x=>x.patientId===id&&x.status==='out').id", o)
    pg.click(f'[data-itback="{oid}"]'); pg.wait_for_timeout(500); shot(pg, '6_kiin_tag'); pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    x = pg.evaluate("(()=>{const p=patients.find(q=>q.pid==='D1041');p.itsumo={on:true,dest:'喫煙'};p.consentDate='2026-10-01';p.consentWithdrawn='';dbPut('patients',p);itSig='';renderItsumo(true);return p.id})()"); pg.wait_for_timeout(600)
    pg.click(f'[data-itgo="{x}"]'); pg.wait_for_timeout(500); shot(pg, '7_shuppatsu_tag_erabu')
    pg.locator('#itLendSeg [data-itlend]').first.click(); pg.wait_for_timeout(300); shot(pg, '7b_shuppatsu_tag_eranda')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    y = pg.evaluate("(()=>{const p=patients.find(q=>q.pid==='D1043');p.itsumo={on:true,dest:'喫煙'};p.consentDate='';p.consentWithdrawn='';dbPut('patients',p);itSig='';renderItsumo(true);return p.id})()"); pg.wait_for_timeout(600)
    pg.click(f'[data-itgo="{y}"]'); pg.wait_for_timeout(500); shot(pg, '7c_shuppatsu_doui_nashi'); pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    pg.click(f'[data-itedit="{o}"]'); pg.wait_for_timeout(400); shot(pg, '8_henkou'); pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    pg.click(f'[data-itgo="{pid_id(pg, "D1024")}"]'); pg.wait_for_timeout(600); shot(pg, '5_shuppatsu_gogo_1310')
    ctx.close()
    b.close()
print('errors', errs)
