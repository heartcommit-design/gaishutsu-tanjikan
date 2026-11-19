"""0.5.0 患者を1人ずつ台帳に登録・いつもの外出から登録・新規登録からいつもの外出に入れる：assert で確かめる。
(a) 患者台帳の「＋ 新しい患者を登録」：何も入れずに登録 → 氏名・ID・病棟・職員のそばに知らせ。入れて登録 → 台帳に入る（外出の記録は作らない）。
    同意書の取得日を入れると台帳に残る。「いつもの外出」には入らない（チェックなし）。
(b) すでにある患者IDでは登録できない。
(c) いつもの外出の「人を足す・外す」→「台帳にない人を登録して足す」：チェックは初めから入っている。登録 → いつもの外出に入り、
    続けてその人の設定（行き先・専用タグ）の画面が開く。専用タグを選んで保存 → カードに出る。
(d) 新規登録の画面の「この人を『いつもの外出』にも入れる」：外出を登録すると、その人がいつもの外出に入る（行き先は登録した行き先）。
    すでにいつもの外出の人なら何も変えない。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []
NURSE = 'テスト 看護師'


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 20, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    btn = lambda t: (pg.locator('#dlgActions button', has_text=t).click(), pg.wait_for_timeout(500))

    # (a)
    pg.click('nav button[data-tab=patients]'); pg.wait_for_timeout(300)
    ok(pg.locator('#ptNewBtn').is_visible())
    pg.click('#ptNewBtn'); pg.wait_for_timeout(300)
    ok('新しい患者を台帳に登録' in pg.inner_text('#dlgTitle'))
    ok(not pg.is_checked('#dlgBody input[name=itsumoOn]'))
    btn('台帳に登録')
    ferr = pg.inner_text('#dlgBody')
    ok(all(t in ferr for t in ['患者氏名を入れてください', '患者IDを入れてください', '病棟を選んでください', '職員を入力してください']), ferr)
    pg.fill('#dlgBody input[name=name]', 'テスト　太郎'); pg.fill('#dlgBody input[name=kana]', 'テストタロウ'); pg.fill('#dlgBody input[name=pid]', 'Ｐ０００１')
    pg.click('#dlgBody .wards label:has-text("東1")'); pg.fill('#dlgBody input[name=age]', '45')
    pg.fill('#dlgBody input[name=consentDate]', '2026-11-01'); pg.fill('#dlgBody input[name=staff]', NURSE)
    pg.screenshot(path=os.path.join(OUT, 'v050_1_shinki_kanja.png'))
    btn('台帳に登録')
    ok(not pg.locator('#dlg').evaluate('d=>d.open'))
    r = pg.evaluate("(()=>{const p=patients.find(x=>x.pid==='P0001');return p&&{name:p.name,kana:p.kana,ward:p.ward,age:ageOf(p),cd:p.consentDate,it:!!p.itsumo,led:(p.ledger||[]).map(l=>l.text).join('|'),n:outings.length}})()")
    ok(r and r['name'] == 'テスト 太郎' and r['kana'] == 'てすとたろう' and r['ward'] == '東1' and r['age'] == '45' and r['cd'] == '2026-11-01' and not r['it'] and '台帳に新規登録' in r['led'] and r['n'] == 0, r)
    ok('テスト 太郎' in pg.inner_text('#ptTable'))
    # (b) 同じID
    pg.click('#ptNewBtn'); pg.wait_for_timeout(300)
    pg.fill('#dlgBody input[name=name]', 'テスト 次郎'); pg.fill('#dlgBody input[name=pid]', 'P0001'); pg.click('#dlgBody .wards label:has-text("東1")'); pg.fill('#dlgBody input[name=staff]', NURSE)
    btn('台帳に登録')
    ok('すでに台帳にあります' in pg.inner_text('#dlgBody') and pg.evaluate("patients.length") == 1)
    btn('やめる')

    # (c) いつもの外出から
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(400)
    pg.click('#itMembers'); pg.wait_for_timeout(300)
    ok(pg.locator('#itNewPt').is_visible() and 'テスト 太郎' in pg.inner_text('#itPickList'))
    pg.screenshot(path=os.path.join(OUT, 'v050_2_hito_wo_tasu.png'))
    pg.click('#itNewPt'); pg.wait_for_timeout(300)
    ok(pg.is_checked('#dlgBody input[name=itsumoOn]'))
    pg.fill('#dlgBody input[name=name]', 'テスト 花子'); pg.fill('#dlgBody input[name=pid]', 'P0002'); pg.click('#dlgBody .wards label:has-text("東1")')
    pg.fill('#dlgBody input[name=consentDate]', '2026-11-02'); pg.fill('#dlgBody input[name=staff]', NURSE)
    btn('台帳に登録'); pg.wait_for_timeout(300)
    ok('テスト 花子' in pg.inner_text('#dlgTitle') and 'いつもの外出' in pg.inner_text('#dlgTitle'), pg.inner_text('#dlgTitle'))
    pg.select_option('#dlgBody select[name=itTag]', 'T-01')
    btn('保存')
    r = pg.evaluate("(()=>{const p=patients.find(x=>x.pid==='P0002');return {on:p.itsumo.on,dest:p.itsumo.dest,own:tags.find(t=>t.id==='T-01').owner===p.id,id:p.id}})()")
    ok(r['on'] and r['dest'] == '喫煙' and r['own'], r)
    pg.wait_for_timeout(500)
    ok('T-01 専用' in pg.inner_text(f'[data-itp="{r["id"]}"]'))
    pg.screenshot(path=os.path.join(OUT, 'v050_3_itsumo.png'))

    # (d) 新規登録から
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
    ok(pg.locator('#itsumoRegLab').is_visible())
    pg.fill('#pSearch', 'P0001'); pg.wait_for_timeout(200); pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(200)
    pg.click('#dueQuick button[data-h="1"]'); pg.fill('input[name=dest]', '散歩')
    pg.fill('input[name=departNurse]', NURSE)
    pg.check('input[name=itsumoReg]')
    pg.screenshot(path=os.path.join(OUT, 'v050_4_shinki_touroku.png'))
    pg.evaluate("document.activeElement&&document.activeElement.blur()"); pg.wait_for_timeout(400)
    pg.click('#submitBtn'); pg.wait_for_timeout(900)
    r = pg.evaluate("(()=>{const p=patients.find(x=>x.pid==='P0001');return {it:p.itsumo,o:outings.filter(o=>o.pid==='P0001'&&o.status==='out').length,toast:document.getElementById('toast').textContent,led:(p.ledger||[]).map(l=>l.text).join('|')}})()")
    ok(r['o'] == 1 and r['it'] and r['it']['on'] and r['it']['dest'] == '散歩' and '「いつもの外出」にも入れました' in r['toast'] and '新規登録から' in r['led'], r)
    ok(pg.evaluate("!document.querySelector('input[name=itsumoReg]').checked"))   # 登録の後は外れる
    # すでにいつもの外出の人：何も変えない（行き先はそのまま）
    pg.evaluate("(()=>{const o=outings.find(o=>o.pid==='P0001'&&o.status==='out');o.status='returned';o.returnedAt=Date.now();saveOuting(o);})()")
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
    pg.fill('#pSearch', 'P0001'); pg.wait_for_timeout(200); pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(200)
    pg.click('#dueQuick button[data-h="1"]'); pg.fill('input[name=dest]', '売店'); pg.fill('input[name=departNurse]', NURSE); pg.check('input[name=itsumoReg]')
    pg.evaluate("document.activeElement&&document.activeElement.blur()"); pg.wait_for_timeout(400)
    pg.click('#submitBtn'); pg.wait_for_timeout(900)
    ok(pg.evaluate("patients.find(x=>x.pid==='P0001').itsumo.dest") == '散歩')
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
