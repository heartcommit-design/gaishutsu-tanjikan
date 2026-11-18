"""0.2.0「いつもの外出」の画面写真を docs/screens_v0.2.0/ に撮る（1倍）。テストの一覧（suite.txt）には入れない。
使い方：cd tests && python3 make_screens_v020.py
"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v0.2.0'); os.makedirs(DST, exist_ok=True)
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
    # 横：一覧（2人外出中・1人予定超過）
    ctx, pg = setup(b, 1180, 820, jst(2026, 11, 18, 10, 58))
    for pid, nurse in (('D1021', '(デモ) 看護師 青木'), ('D1022', '(デモ) 看護師 青木'), ('D1023', '(デモ) 看護師 青木')):
        pg.click(f'[data-itgo="{pid_id(pg, pid)}"]'); pg.wait_for_timeout(400)
        pg.fill('#dlgBody input[name=nurse]', nurse); pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(500)
    # 1人は帰院予定を早めに（予定超過の見本）
    pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');o.dueAt=Date.now()-6*60000;saveOuting(o);lastSig='';itSig='';}", pid_id(pg, 'D1023'))
    pg.wait_for_timeout(1500)
    shot(pg, '1_itsumo_yoko')
    # 出発の画面
    pg.click(f'[data-itgo="{pid_id(pg, "D1024")}"]'); pg.wait_for_timeout(600); shot(pg, '2_shuppatsu')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    # 写真がない人の出発の画面
    pg.click(f'[data-itgo="{pid_id(pg, "D1030")}"]'); pg.wait_for_timeout(600); shot(pg, '3_shuppatsu_shashin_nashi')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    # 帰院の画面
    o = pg.evaluate("id=>outings.find(x=>x.patientId===id&&x.status==='out').id", pid_id(pg, 'D1021'))
    pg.click(f'[data-itback="{o}"]'); pg.wait_for_timeout(500); shot(pg, '4_kiin')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    # 写真の準備
    pg.click('#itPrepBtn'); pg.wait_for_timeout(500); shot(pg, '5_shashin_junbi'); pg.click('#itPrepBtn'); pg.wait_for_timeout(300)
    # 人を足す・外す → 設定
    pg.click('#itMembers'); pg.wait_for_timeout(400); shot(pg, '6_hito_wo_tasu')
    pg.fill('#itQ', 'D1041'); pg.wait_for_timeout(200); pg.click('[data-itset]'); pg.wait_for_timeout(400); shot(pg, '7_settei')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    # タグ管理（専用の行が見える所まで）
    pg.click('nav button[data-tab=tags]'); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#tTable tr:nth-child(14)').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300); shot(pg, '8_tag_kanri')
    # 患者台帳（いつもの外出の印）
    pg.click('nav button[data-tab=patients]'); pg.fill('#ptQ', 'D102'); pg.wait_for_timeout(400); shot(pg, '9_daichou')
    ctx.close()
    # 縦
    ctx, pg = setup(b, 1024, 1366, jst(2026, 11, 18, 10, 58)); shot(pg, '10_itsumo_tate'); ctx.close()
    # 夜の配色
    ctx, pg = setup(b, 1180, 820, jst(2026, 11, 18, 19, 10), theme='dark'); shot(pg, '11_itsumo_yoru'); ctx.close()
    b.close()
print('errors', errs)
