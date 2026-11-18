"""0.3.0「いつもの外出」で、専用タグのない人に出発の時だけタグを渡す：assert で確かめる。
(a) 専用タグのない人（同意書の取得日あり）：出発の画面に「渡すタグ（必須）」。使えるふつうのタグと「タグなし」が並び、専用タグ・貸出中のタグは出ない。
(b) 何も選ばずに出発 → 欄のそばに知らせ。タグを選ぶとタグの行に大きく出る。
(c) 出発 → 記録にタグ（専用ではない）、タグは貸出中。カードに「T-xx 貸出中」。
(d) 帰院：回収のチェックが出る（回収した → 利用可）。記録は「回収」。
(e) 「タグなし」を選んで出発もできる（タグは空）。
(f) 同意書の取得日がない人：渡すタグの欄は出ず、「タグは渡せません」の説明。タグなしで出発できる。
(g) 専用タグのある人には、渡すタグの欄は出ない。
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


def btn(pg, text):
    pg.locator('#dlgActions button', has_text=text).click(); pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 18, 13, 0))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    # 専用タグのない「いつもの外出」の人を3人：D1041・D1042（同意書あり）、D1043（同意書なし）
    ids = pg.evaluate("""(()=>{const r={};for(const [pid,c] of [['D1041','2026-10-01'],['D1042','2026-10-01'],['D1043','']]){
      const p=patients.find(q=>q.pid===pid);p.itsumo={on:true,dest:'喫煙'};p.consentDate=c;p.consentWithdrawn='';dbPut('patients',p);r[pid]=p.id;}
      itSig='';return r;})()""")
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(800)
    a, b2, c = ids['D1041'], ids['D1042'], ids['D1043']
    ok('専用タグなし' in pg.inner_text(f'[data-itp="{a}"]'))

    # (a)
    pg.click(f'[data-itgo="{a}"]'); pg.wait_for_timeout(500)
    ok(pg.locator('#itLendSeg').count() == 1)
    lend = pg.evaluate("[...document.querySelectorAll('#itLendSeg [data-itlend]')].map(x=>x.dataset.itlend)")
    av = pg.evaluate("tags.filter(t=>t.status==='available'&&!t.owner).map(t=>t.id)")
    ok(lend[-1] == '' and sorted(lend[:-1]) == sorted(av) and len(av) > 0, (lend, av))
    ok(not any(pg.evaluate("tags.filter(t=>t.owner||t.status!=='available').map(t=>t.id)").count(x) for x in lend[:-1]))
    # (b)
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    btn(pg, '出発')
    ok(pg.locator('#dlg').evaluate('d=>d.open') and '渡すタグを選んでください' in pg.inner_text('#dlg .ferr'), pg.inner_text('#dlg'))
    tid = lend[0]
    pg.click(f'#itLendSeg [data-itlend="{tid}"]'); pg.wait_for_timeout(200)
    ok(tid in pg.inner_text('#itLendShow') and '回収' in pg.inner_text('#itLendShow'))
    ok(pg.locator('#dlg .ferr').count() == 0)
    btn(pg, '出発')
    # (c)
    o = pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');return o&&{id:o.id,tag:o.tagId,own:o.tagOwned,cons:o.consent,log:o.log.map(l=>l.text).join('|')}}", a)
    ok(o and o['tag'] == tid and not o['own'] and o['cons'] and f'タグ {tid} を渡す' in o['log'], o)
    ok(pg.evaluate("t=>{const x=tags.find(y=>y.id===t);return x.status+':'+(x.owner||'')}", tid) == 'inuse:')
    pg.wait_for_timeout(1200)
    ok(f'{tid} 貸出中' in pg.inner_text(f'[data-itp="{a}"]'), pg.inner_text(f'[data-itp="{a}"]'))
    # (d) 帰院：回収
    pg.click(f'[data-itback="{o["id"]}"]'); pg.wait_for_timeout(400)
    ok(pg.locator('#dlgBody input[name=tagBack]').count() == 1 and pg.locator('#dlgBody input[name=tagBack]').is_checked())
    btn(pg, '帰院')
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);const t=tags.find(x=>x.id===o.tagId);return {st:o.status,back:o.tagReturned,kept:!!o.tagKept,ts:t.status,ow:t.owner||'',col:COLS.find(c=>c[0]==='タグ回収')[1](o)}}", o['id'])
    ok(r == {'st': 'returned', 'back': True, 'kept': False, 'ts': 'available', 'ow': '', 'col': '回収'}, r)
    # (e) タグなし
    pg.wait_for_timeout(800)
    pg.click(f'[data-itgo="{b2}"]'); pg.wait_for_timeout(500)
    pg.click('#itLendSeg [data-itlend=""]'); pg.wait_for_timeout(200)
    ok('タグなし' in pg.inner_text('#itLendShow'))
    btn(pg, '出発')
    o2 = pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');return o&&{tag:o.tagId,log:o.log.map(l=>l.text).join('|')}}", b2)
    ok(o2 and o2['tag'] == '' and '（タグなし）' in o2['log'], o2)
    # (f) 同意書なし
    pg.wait_for_timeout(800)
    pg.click(f'[data-itgo="{c}"]'); pg.wait_for_timeout(500)
    ok(pg.locator('#itLendSeg').count() == 0 and 'タグは渡せません' in pg.inner_text('#dlgBody'))
    ok(pg.locator('#dlgBody .it-tagbig.none').count() == 1)
    btn(pg, '出発')
    ok(pg.evaluate("id=>!!outings.find(x=>x.patientId===id&&x.status==='out'&&!x.tagId)", c))
    # (g) 専用タグのある人
    pg.wait_for_timeout(800)
    d = pg.evaluate("patients.find(p=>p.pid==='D1022').id")
    pg.click(f'[data-itgo="{d}"]'); pg.wait_for_timeout(500)
    ok(pg.locator('#itLendSeg').count() == 0 and '専用' in pg.inner_text('#dlgBody .it-kv'))
    pg.screenshot(path=os.path.join(HERE, 'out', 'v030_kashidashi_g.png'))
    btn(pg, 'やめる')
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
