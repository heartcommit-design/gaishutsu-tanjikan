"""0.4.2 帰院時の確認の5項目・「飲酒の疑い」・タグの「紛失した」：assert で確かめる。
(a) 「飲酒の疑い」を「あり」にしてメモ → 記録「飲酒の疑い：あり（メモ）」。「その他の問題」も問題ありにできる。
(b) 貸し出したタグ：「回収した」と「紛失した」はどちらか一方だけ（紛失に✓で回収の✓が外れ、回収に✓で紛失が外れる）。
(c) 紛失した → タグは「紛失」（TAG_ST.lost）、記録「タグ T-xx 紛失」、一覧の「タグ回収」は「紛失」。
(d) どちらも外すと、これまでどおり「未回収」。
(e) いつもの外出の専用タグ：「専用タグを紛失した」だけが出る。紛失にすると専用の印は残したまま「紛失」、記録に出る。
(f) 0.4.1 までの記録（帰院時の様子・精神状態の4項目）も、前の項目名で文字になる。
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


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 19, 10, 30))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    act = pg.evaluate("outings.filter(o=>o.status==='out'&&o.tagId&&!tags.find(t=>t.id===o.tagId).owner).map(o=>o.id)")
    ok(len(act) >= 2, act)
    # (a)(b)(c)
    pg.evaluate("id=>dlgReturn(outings.find(o=>o.id===id))", act[0]); pg.wait_for_timeout(400)
    pg.click('#dlgBody [data-rck=drink] [data-rcv=ng]'); pg.fill('#dlgBody input[name=rcm_drink]', '酒のにおいあり')
    pg.click('#dlgBody [data-rck=etc] [data-rcv=ng]'); pg.fill('#dlgBody input[name=rcm_etc]', '靴をなくした')
    back, lost = '#dlgBody input[name=tagBack]', '#dlgBody input[name=tagLost]'
    ok(pg.is_checked(back) and not pg.is_checked(lost))
    pg.check(lost); ok(pg.is_checked(lost) and not pg.is_checked(back))
    pg.check(back); ok(pg.is_checked(back) and not pg.is_checked(lost))
    pg.check(lost)
    pg.screenshot(path=os.path.join(OUT, 'v042_kiin.png'))
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button', has_text='帰院を登録').click(); pg.wait_for_timeout(600)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);const t=tags.find(x=>x.id===o.tagId);return {t:rcText(o),lost:o.tagLost,ts:t.status,lab:TAG_ST[t.status],log:o.log.map(l=>l.text).join('|'),col:COLS.find(c=>c[0]==='タグ回収')[1](o),tag:o.tagId}}", act[0])
    ok(r['t'] == '飲酒の疑い：あり（酒のにおいあり）／その他の問題：問題あり（靴をなくした）／ほかは問題なし', r['t'])
    ok(r['lost'] and r['ts'] == 'lost' and r['lab'] == '紛失' and f"タグ {r['tag']} 紛失" in r['log'] and r['col'] == '紛失', r)
    # (d) どちらも外す → 未回収
    pg.evaluate("id=>dlgReturn(outings.find(o=>o.id===id))", act[1]); pg.wait_for_timeout(400)
    pg.uncheck(back); pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button', has_text='帰院を登録').click(); pg.wait_for_timeout(600)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);const t=tags.find(x=>x.id===o.tagId);return {ts:t.status,col:COLS.find(c=>c[0]==='タグ回収')[1](o),lost:!!o.tagLost}}", act[1])
    ok(r == {'ts': 'missing', 'col': '未回収', 'lost': False}, r)
    # (e) 専用タグ
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(600)
    a = pg.evaluate("patients.find(p=>p.pid==='D1022').id")
    pg.click(f'[data-itgo="{a}"]'); pg.wait_for_timeout(400)
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本'); pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(800)
    oid = pg.evaluate("id=>outings.find(x=>x.patientId===id&&x.status==='out').id", a)
    pg.click(f'[data-itback="{oid}"]'); pg.wait_for_timeout(400)
    ok(pg.locator(back).count() == 0 and pg.locator(lost).count() == 1 and '専用タグを紛失した' in pg.inner_text('#dlgBody'))
    pg.check(lost)
    pg.screenshot(path=os.path.join(OUT, 'v042_itsumo_kiin.png'))
    pg.locator('#dlgActions button').last.click(); pg.wait_for_timeout(700)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);const t=tags.find(x=>x.id===o.tagId);return {ts:t.status,ow:t.owner===o.patientId,kept:!!o.tagKept,lost:o.tagLost,log:o.log.map(l=>l.text).join('|'),col:COLS.find(c=>c[0]==='タグ回収')[1](o)}}", oid)
    ok(r['ts'] == 'lost' and r['ow'] and not r['kept'] and r['lost'] and '専用タグ' in r['log'] and '紛失' in r['log'] and r['col'] == '紛失', r)
    # (f) 0.4.1 までの記録
    t = pg.evaluate("rcText({rc:{v2:true,belong:{ok:true},state:{ng:true,picks:[],memo:'落ち着きなし'},med:{ok:true},mental:{ok:true}}})")
    ok(t == '帰院時の様子：問題あり（落ち着きなし）／ほかは問題なし', t)
    t = pg.evaluate("rcText({rc:{belong:{ok:true,memo:''},state:{ok:false,memo:'穏やか'},med:{ok:true},mental:{ok:false,memo:''},other:''}})")
    ok(t == '持ち物確認✓／帰院時の様子：穏やか／服薬✓', t)
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
