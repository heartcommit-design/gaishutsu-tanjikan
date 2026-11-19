"""0.4.0 予定の人の服装写真を、出発の前に撮っておく：assert で確かめる。
(a) 予定の行に「📷 写真を撮る」（写真がある行は「📷 撮り直す」）と、写真の状態（「服装写真なし」／「✓ 服装写真 hh:mm」）。
(b) 「写真を撮る」で撮ると、その予定の写真として保存（hasPhoto・撮った時刻・記録）。行が「✓ 服装写真 09:30」に変わる。
(c) 出発（GO）の画面：撮ってある写真そのものを出し、「今の服装は、この写真（09:30 撮影）と同じですか」と「服装が違う（撮り直す）」。
(d) 写真がない予定の GO：「服装の写真はまだありません」と「📷 撮る」。
(e) GO で撮り直して出発 → 記録に「撮り直し（出発時）」、写真は新しいものに置き換わる。帰院で写真は消える。
(f) 名前を隠す設定の時：GO では写真は出さず「写真を表示（30秒）」で出す。
"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []
J1 = os.path.join(OUT, 'v040_a.jpg'); Image.new('RGB', (300, 400), (40, 90, 160)).save(J1)
J2 = os.path.join(OUT, 'v040_b.jpg')
_im = Image.new('RGB', (300, 400)); _im.putdata([((x * 7) % 256, (y * 3) % 256, (x * y) % 256) for y in range(400) for x in range(300)]); _im.save(J2)   # 1枚目と大きさが変わるよう模様を入れる


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 19, 9, 30))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(800)
    # 写真のない予定・ある予定（今日）
    ids = pg.evaluate("""(()=>{const l=outings.filter(o=>o.status==='planned'&&o.departAt<Date.now()+6*3600000&&o.dueAt>Date.now()+3600000).sort((a,b)=>a.departAt-b.departAt);
      return {no:(l.find(o=>!o.hasPhoto)||{}).id, has:(l.find(o=>o.hasPhoto)||{}).id};})()""")
    ok(ids['no'] and ids['has'], ids)
    row = f'#planList .card[data-id="{ids["no"]}"]'
    # (a)
    ok('服装写真なし' in pg.inner_text(row) and pg.inner_text(f'{row} [data-pact=snap]').strip() == '📷 写真を撮る', pg.inner_text(row))
    ok(pg.inner_text(f'#planList .card[data-id="{ids["has"]}"] [data-pact=snap]').strip() == '📷 撮り直す')
    pg.screenshot(path=os.path.join(OUT, 'v040_1_yotei.png'))
    # (d) 写真なしの GO
    pg.click(f'{row} [data-pact=go]'); pg.wait_for_timeout(400)
    ok('服装の写真はまだありません' in pg.inner_text('#goPhotoQ') and '📷 撮る' in pg.inner_text('#goPhotoBtn'))
    pg.locator('#dlgActions button', has_text='やめる').click(); pg.wait_for_timeout(300)
    # (b) 出発の前に撮る
    with pg.expect_file_chooser() as fc:
        pg.click(f'{row} [data-pact=snap]')
    fc.value.set_files(J1)
    pg.wait_for_function("id=>{const o=outings.find(x=>x.id===id);return o.hasPhoto&&o.photoAt}", arg=ids['no'], timeout=8000)
    pg.wait_for_timeout(400)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {at:new Date(o.photoAt).getHours()*60+new Date(o.photoAt).getMinutes(),log:o.log.map(l=>l.text).join('|')}}", ids['no'])
    ok(r['at'] == 9 * 60 + 30 and '服装写真を登録（出発の前）' in r['log'], r)
    ok(ids['no'] in pg.evaluate("dbKeys('photos')"))
    ok('✓ 服装写真 09:30' in pg.inner_text(row) and pg.inner_text(f'{row} [data-pact=snap]').strip() == '📷 撮り直す', pg.inner_text(row))
    size1 = pg.evaluate("id=>dbGet('photos',id).then(b=>b.size)", ids['no'])
    # (c) GO の画面に写真そのもの
    pg.clock.fast_forward(5 * 60000); pg.wait_for_timeout(1200)
    pg.click(f'{row} [data-pact=go]'); pg.wait_for_timeout(600)
    ok(pg.locator('#goPhotoPrev img').count() == 1 and pg.get_attribute('#goPhotoPrev img', 'src').startswith('blob:'))
    q = pg.inner_text('#goPhotoQ')
    ok('今の服装は、この写真（09:30 撮影）と' in q and '同じですか' in q, q)
    ok('服装が違う（撮り直す）' in pg.inner_text('#goPhotoBtn'))
    pg.screenshot(path=os.path.join(OUT, 'v040_2_go.png'))
    # (e) 撮り直して出発
    pg.set_input_files('#goPhotoInput', J2); pg.wait_for_timeout(600)
    ok('今、撮った写真で出発します' in pg.inner_text('#goPhotoQ'))
    pg.click('#goTagBtns [data-gotag=""]'); pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本'); pg.wait_for_timeout(200)
    pg.locator('#dlgActions button', has_text='出発（GO）').click(); pg.wait_for_timeout(800)
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {st:o.status,ph:o.hasPhoto,log:o.log.map(l=>l.text).join('|')}}", ids['no'])
    ok(r['st'] == 'out' and r['ph'] and '服装写真を撮り直し（出発時）' in r['log'], r)
    size2 = pg.evaluate("id=>dbGet('photos',id).then(b=>b.size)", ids['no'])
    ok(size2 != size1, (size1, size2))
    # 帰院で消える（ふつうの帰院登録）
    pg.evaluate("id=>dlgReturn(outings.find(x=>x.id===id))", ids['no']); pg.wait_for_timeout(400)
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.locator('#dlgActions button', has_text='帰院を登録').click(); pg.wait_for_timeout(800)
    ok(ids['no'] not in pg.evaluate("dbKeys('photos')"))
    # (f) 名前を隠す設定
    pg.evaluate("settings.mask=true;saveSettings();planSig='';renderPlans()"); pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(600)
    pg.click(f'#planList .card[data-id="{ids["has"]}"] [data-pact=go]'); pg.wait_for_timeout(500)
    ok(pg.locator('#goPhotoPrev img').count() == 0 and pg.locator('#goReveal').count() == 1)
    pg.click('#goReveal'); pg.wait_for_timeout(500)
    ok(pg.locator('#goPhotoPrev img').count() == 1)
    pg.locator('#dlgActions button', has_text='やめる').click()
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
