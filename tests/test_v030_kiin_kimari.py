"""0.3.0「いつもの外出」の帰院予定を病棟の決まりで選ぶ：assert で確かめる。
(a) 初めの決まり：午前（11:30 より前）は 11:30。午後は出発の60分後、ただし 16:00 まで60分を切っていたら 16:00。16:00 を過ぎたら60分後。
    決まった時刻より後になる「+○分」の候補は出さない。
(b) カードの文字（「11:30まで」「+60分」「16:00まで」）。
(c) 出発の画面で初めに選ばれているもの・実際に登録される帰院予定（15:20 の出発 → 16:00）。
(d) 「帰院の決まり」で変えられる（午前 11:00・午後 15:30・45分）。午後の時刻は午前より後でないと保存できない。
(e) 人ごとの設定の画面には帰院予定の選び方は出ない（決まりの説明だけ）。
(f) 名前のカードの「変更」から、その人の設定を開ける（写真の準備の間は出さない）。
(g) 出発・帰院の画面に「タグ」の行：専用タグは「T-13 専用」、持たない人は「タグなし」。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


def ms(h, m):
    return int(jst(2026, 11, 18, h, m).timestamp() * 1000)


def opts(pg, h, m):
    return pg.evaluate("t=>itDueOpts(null,t).map(x=>({hm:hm(x.at),label:x.label,def:x.def}))", ms(h, m))


def deff(pg, h, m):
    return [x['hm'] for x in opts(pg, h, m) if x['def']]


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 18, 10, 30))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")

    # (a)
    ok(deff(pg, 8, 0) == ['11:30'])
    o = opts(pg, 10, 58)
    ok([x['hm'] for x in o if x['def']] == ['11:30'] and any('午前の帰院時刻' in x['label'] for x in o), o)
    ok(all(x['hm'] <= '11:30' for x in o), o)              # 11:30 より後の候補は出さない
    ok(deff(pg, 11, 30) == ['12:30'])
    ok(deff(pg, 13, 10) == ['14:10'])
    ok(deff(pg, 14, 59) == ['15:59'])
    ok(deff(pg, 15, 0) == ['16:00'])
    ok(deff(pg, 15, 20) == ['16:00'])
    ok(deff(pg, 15, 59) == ['16:00'])
    o = opts(pg, 15, 20)
    ok(all(x['hm'] <= '16:00' for x in o) and any('午後の帰院時刻' in x['label'] for x in o), o)
    ok(deff(pg, 16, 30) == ['17:30'])
    ok(not any('帰院時刻' in x['label'] for x in opts(pg, 16, 30)))

    # デモ
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(800)
    a = pg.evaluate("patients.find(p=>p.pid==='D1021').id")
    # (b) 10:30 → 11:30まで
    ok('喫煙・11:30まで' in pg.inner_text(f'[data-itp="{a}"]'))

    # (e) 人ごとの設定
    pg.click('#itMembers'); pg.wait_for_timeout(300); pg.fill('#itQ', 'D1021'); pg.wait_for_timeout(200)
    pg.click(f'[data-itset="{a}"]'); pg.wait_for_timeout(300)
    body = pg.inner_text('#dlgBody')
    ok('午前は 11:30' in body and '「帰院の決まり」' in body and pg.locator('#dlgBody [name=itMode]').count() == 0 and pg.locator('#dlgBody [name=itHM]').count() == 0, body)
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(200)

    # (c) 15:20 の出発 → 16:00
    pg.clock.fast_forward(int((ms(15, 20) - ms(10, 30)))); pg.wait_for_timeout(1500)
    ok('16:00まで' in pg.inner_text(f'[data-itp="{a}"]'), pg.inner_text(f'[data-itp="{a}"]'))
    b2 = pg.evaluate("patients.find(p=>p.pid==='D1022').id")
    pg.click(f'[data-itgo="{b2}"]'); pg.wait_for_timeout(500)
    sel = pg.locator('#dlgBody [data-itdue].on')
    ok(sel.count() == 1 and '16:00（午後の帰院時刻）' in sel.inner_text(), sel.inner_text())
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(600)
    due = pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');const d=new Date(o.dueAt);return d.getHours()*60+d.getMinutes()}", b2)
    ok(due == 16 * 60, due)
    # 13:00 台の見本：16:30 になったら +60分
    pg.clock.fast_forward(int(ms(16, 30) - ms(15, 21))); pg.wait_for_timeout(1500)
    ok('+60分' in pg.inner_text(f'[data-itp="{a}"]'), pg.inner_text(f'[data-itp="{a}"]'))

    # (f) カードの「変更」
    pg.click(f'[data-itedit="{a}"]'); pg.wait_for_timeout(300)
    ok('の「いつもの外出」' in pg.inner_text('#dlgTitle') and pg.locator('#dlgBody select[name=itTag]').input_value() == 'T-13')
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(200)
    pg.click('#itPrepBtn'); pg.wait_for_timeout(300); ok(pg.locator('#itGrid [data-itedit]').count() == 0)
    pg.click('#itPrepBtn'); pg.wait_for_timeout(300); ok(pg.locator('#itGrid [data-itedit]').count() == 12)
    # (g) タグの行
    pg.click(f'[data-itgo="{a}"]'); pg.wait_for_timeout(500)
    kv = pg.inner_text('#dlgBody .it-kv')
    ok('タグ' in kv and 'T-13' in kv and '専用' in kv and pg.locator('#dlgBody .it-tagbig').inner_text() == 'T-13', kv)
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(200)
    x = pg.evaluate("(()=>{const p=patients.find(q=>q.pid==='D1041');p.itsumo={on:true,dest:'喫煙'};dbPut('patients',p);itSig='';renderItsumo(true);return p.id})()")
    pg.wait_for_timeout(500)
    pg.click(f'[data-itgo="{x}"]'); pg.wait_for_timeout(500)
    ok(pg.locator('#dlgBody .it-tagbig.none').inner_text() == 'タグなし', pg.inner_text('#dlgBody .it-kv'))
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(200)
    o2 = pg.evaluate("id=>outings.find(x=>x.patientId===id&&x.status==='out').id", b2)
    pg.click(f'[data-itback="{o2}"]'); pg.wait_for_timeout(400)
    kv = pg.inner_text('#dlgBody .it-kv')
    ok('タグ' in kv and '専用' in kv and '回収しません' in kv, kv)
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(200)

    # (d) 帰院の決まりを変える
    pg.click('#itRuleBtn'); pg.wait_for_timeout(300)
    pg.fill('#dlgBody [name=amEnd]', '11:00'); pg.fill('#dlgBody [name=pmEnd]', '10:00')
    pg.locator('#dlgActions button', has_text='保存').click(); pg.wait_for_timeout(300)
    ok('午前の帰院時刻より後' in pg.inner_text('#dlg .ferr'))
    pg.fill('#dlgBody [name=pmEnd]', '15:30'); pg.select_option('#dlgBody [name=pmPlus]', '45')
    pg.locator('#dlgActions button', has_text='保存').click(); pg.wait_for_timeout(300)
    ok(pg.evaluate("settings.itRule") == {'amEnd': '11:00', 'pmEnd': '15:30', 'pmPlus': 45})
    ok(pg.evaluate("dbGet('settings','main').then(s=>s.itRule.amEnd)") == '11:00')
    ok(deff(pg, 10, 30) == ['11:00'])
    ok(deff(pg, 13, 0) == ['13:45'])
    ok(deff(pg, 14, 50) == ['15:30'])
    ok(deff(pg, 16, 0) == ['16:45'])
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
