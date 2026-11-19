"""0.4.1 帰院時の確認を「問題なし／問題あり」に（初めは問題なし）：assert で確かめる。
(a) ふつうの帰院登録：4項目（持ち物確認・帰院時の様子・服薬・精神状態）が初めから「問題なし」。メモ欄は隠れている。
(b) 何も触らずに登録 → 記録は「帰院時確認：すべて問題なし」、o.rcNg は false。
(c) 「服薬忘れあり」を押すと服薬が「問題あり」になり、メモ欄が出る。「不穏」「禁止物持ち込みあり」も同じ。
    「問題なし」に戻すと、選んだ言葉は外れる。
(d) 問題ありで登録 → 記録に「服薬：問題あり（服薬忘れあり・メモ）」…「ほかは問題なし」、o.rcNg は true、知らせにも出る。
(e) いつもの外出の帰院：同じ確認があり、初めは問題なし。「不穏」を選んで帰院 → 記録に出る。
(f) 予定の行の写真のボタンは、写真があっても「📷 写真を撮る」。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


def vals(pg):
    return pg.evaluate("Object.fromEntries(RC_ITEMS.map(([k])=>[k,document.querySelector('#dlgBody [name=rcv_'+k+']').value]))")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 19, 10, 30))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    act = pg.evaluate("outings.filter(o=>o.status==='out').map(o=>o.id)")
    ok(len(act) >= 2, act)
    # (a)(b) 何も触らずに
    pg.evaluate("id=>dlgReturn(outings.find(o=>o.id===id))", act[0]); pg.wait_for_timeout(400)
    ok(vals(pg) == {'belong': 'ok', 'state': 'ok', 'med': 'ok', 'mental': 'ok'}, vals(pg))
    ok(pg.locator('#dlgBody .rcseg [data-rcv=ok].on').count() == 4)
    ok(pg.locator('#dlgBody input[name=rcm_med]').is_hidden())
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button', has_text='帰院を登録').click(); pg.wait_for_timeout(600)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {st:o.status,ng:o.rcNg,log:o.log.map(l=>l.text).join('|'),t:rcText(o)}}", act[0])
    ok(r['st'] == 'returned' and r['ng'] is False and r['t'] == 'すべて問題なし' and '帰院時確認：すべて問題なし' in r['log'], r)
    # (c)(d)
    pg.evaluate("id=>dlgReturn(outings.find(o=>o.id===id))", act[1]); pg.wait_for_timeout(400)
    pg.click('#dlgBody [data-rcpick="服薬忘れあり"]'); pg.wait_for_timeout(100)
    ok(vals(pg)['med'] == 'ng' and pg.locator('#dlgBody input[name=rcm_med]').is_visible())
    pg.click('#dlgBody [data-rcpick="不穏"]'); pg.click('#dlgBody [data-rcpick="禁止物持ち込みあり"]'); pg.wait_for_timeout(100)
    ok(vals(pg) == {'belong': 'ng', 'state': 'ok', 'mental': 'ng', 'med': 'ng'}, vals(pg))
    # 持ち物は「問題なし」に戻す → 選んだ言葉は外れる
    pg.click('#dlgBody [data-rck=belong] [data-rcv=ok]'); pg.wait_for_timeout(100)
    ok(vals(pg)['belong'] == 'ok' and pg.locator('#dlgBody [data-rcpick="禁止物持ち込みあり"].on').count() == 0)
    pg.fill('#dlgBody input[name=rcm_med]', '昼の薬を飲み忘れ')
    pg.screenshot(path=os.path.join(OUT, 'v041_kiin.png'))
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button', has_text='帰院を登録').click(); pg.wait_for_timeout(600)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {ng:o.rcNg,t:rcText(o),med:o.rc.med,toast:document.getElementById('toast').textContent}}", act[1])
    ok(r['ng'] is True and r['med']['picks'] == ['服薬忘れあり'] and r['med']['memo'] == '昼の薬を飲み忘れ', r)
    ok(r['t'] == '服薬：問題あり（服薬忘れあり・昼の薬を飲み忘れ）／精神状態：問題あり（不穏）／ほかは問題なし', r['t'])
    ok('問題あり' in r['toast'], r['toast'])
    # 日別一覧の文字にも出る
    ok('服薬忘れあり' in pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return COLS.map(c=>String(c[1](o))).join('|')}", act[1]))
    # (e) いつもの外出
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(600)
    a = pg.evaluate("patients.find(p=>p.pid==='D1022').id")
    pg.click(f'[data-itgo="{a}"]'); pg.wait_for_timeout(400)
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本'); pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(800)
    oid = pg.evaluate("id=>outings.find(x=>x.patientId===id&&x.status==='out').id", a)
    pg.click(f'[data-itback="{oid}"]'); pg.wait_for_timeout(400)
    ok(pg.locator('#dlgBody .rcseg [data-rcv=ok].on').count() == 4)
    pg.click('#dlgBody [data-rcpick="不穏"]')
    pg.screenshot(path=os.path.join(OUT, 'v041_itsumo_kiin.png'))
    pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(700)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {st:o.status,ng:o.rcNg,log:o.log.map(l=>l.text).join('|')}}", oid)
    ok(r['st'] == 'returned' and r['ng'] and '帰院時確認：精神状態：問題あり（不穏）／ほかは問題なし' in r['log'], r)
    # (f)
    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(600)
    ok(pg.evaluate("[...document.querySelectorAll('#planList [data-pact=snap] .lt-l')].every(x=>x.textContent.trim()==='写真を撮る')"))
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
