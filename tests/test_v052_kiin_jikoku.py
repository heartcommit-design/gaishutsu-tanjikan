"""0.5.2 新規登録の帰院の時刻ボタンに「11:30（午前の帰院時刻）」「16:00（午後の帰院時刻）」：assert で確かめる。
(a) 外出の時だけ出る（外泊では隠れる）。
(b) 10:00 に出発 → 11:30 を押すと帰院予定が今日 11:30、16:00 を押すと今日 16:00。押したボタンが選ばれた色になる。
(c) 出発が 12:00 の時は 11:30 は押せない（出発より前）、16:00 は押せる。
(d) 「帰院の決まり」を変えると（午前 11:00・午後 15:30）、ボタンの時刻も変わる。
(e) 登録すると帰院予定は 16:00。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []
SET = "([s,v])=>{const i=document.querySelector(s);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}"


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


def due_hm(pg):
    return pg.evaluate("(()=>{const t=fromLocalInput(nf.elements.dueAt.value);if(!t)return '';const d=new Date(t);return (d.getDate())+' '+tkHmOf(t)})()")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 20, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(400)
    am, pm = '#dueQuick [data-fx=am]', '#dueQuick [data-fx=pm]'
    # (a)
    ok(pg.locator(am).is_visible() and pg.locator(pm).is_visible())
    ok('11:30' in pg.inner_text(am) and '午前の帰院時刻' in pg.inner_text(am) and '16:00' in pg.inner_text(pm))
    pg.click('input[name=kind][value="外泊"] >> xpath=..'); pg.wait_for_timeout(1200)
    ok(pg.locator(am).is_hidden())
    pg.click('input[name=kind][value="外出"] >> xpath=..'); pg.wait_for_timeout(1200)
    # (b) 出発は今（10:00）
    pg.click('#depQuick [data-m="0"]'); pg.wait_for_timeout(300)
    pg.click(am); pg.wait_for_timeout(1200)
    ok(due_hm(pg) == '20 11:30', due_hm(pg))
    ok('on' in pg.get_attribute(am, 'class'))
    pg.click(pm); pg.wait_for_timeout(1200)
    ok(due_hm(pg) == '20 16:00' and 'on' in pg.get_attribute(pm, 'class') and 'on' not in pg.get_attribute(am, 'class'))
    pg.screenshot(path=os.path.join(OUT, 'v052_kiin_jikoku.png'))
    # (c) 出発 12:00
    pg.evaluate(SET, ['input[name=departAt]', '2026-11-20T12:00']); pg.wait_for_timeout(1200)
    ok(pg.is_disabled(am) and not pg.is_disabled(pm))
    pg.evaluate(SET, ['input[name=departAt]', pg.evaluate("toLocalInput(Date.now())")]); pg.wait_for_timeout(1200)
    ok(not pg.is_disabled(am))
    # (d) 帰院の決まりを変える
    pg.evaluate("settings.itRule={amEnd:'11:00',pmEnd:'15:30',pmPlus:60}"); pg.wait_for_timeout(1300)
    ok('11:00' in pg.inner_text(am) and '15:30' in pg.inner_text(pm), (pg.inner_text(am), pg.inner_text(pm)))
    pg.evaluate("settings.itRule={amEnd:'11:30',pmEnd:'16:00',pmPlus:60}"); pg.wait_for_timeout(1300)
    # (e) 登録
    pg.fill('input[name=name]', 'テスト 太郎'); pg.fill('input[name=pid]', 'P0001'); pg.click('#wardRadios label:has-text("東1")')
    pg.click(pm); pg.fill('input[name=departNurse]', 'テスト 看護師')
    pg.evaluate("document.activeElement&&document.activeElement.blur()"); pg.wait_for_timeout(400)
    pg.click('#submitBtn'); pg.wait_for_timeout(900)
    d = pg.evaluate("(()=>{const o=outings.find(o=>o.pid==='P0001');return o&&tkHmOf(o.dueAt)})()")
    ok(d == '16:00', d)
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
