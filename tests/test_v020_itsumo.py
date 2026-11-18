"""0.2.0「いつもの外出」：assert で確かめる。
(a) デモで「いつもの外出」の人が12人（D1021〜D1032）。専用タグ T-13〜T-24（T-11・T-12 はデモの予定が予約で使う）、9人は写真を撮っておいた状態。
(b) タグ管理に「〇〇さん 専用」。専用タグは、ほかの人の新規登録のタグのボタンに出ない。
(c) 台帳の「いつもの外出」の設定：同意書の取得日がない人には専用タグを持たせられない（欄のそばに知らせ）。タグなしなら足せる。
(d) 写真の準備：撮ると「✓ 写真」になる。
(e) 出発：帰院予定の初めの候補は 11:45（決まった時刻）。看護師名が空だと出発できない。撮っておいた写真はその外出の写真に移り、撮っておいた分は消える。専用タグは貸出中に。
    写真がない人は出発の画面で撮れる（ボタンの文字が「写真なしで出発」→「服装は同じ。出発」に変わる）。
(f) 帰院予定を過ぎると、その人のカードが赤くなり、上の帯（アラーム）が出る。
(g) 帰院：看護師名を選ぶ（空だと登録できない）。写真は消え、専用タグは回収せず本人が所持（利用可・専用のまま）。くわしい帰院登録でも回収の欄は出ない。
(h) 撮っておいて使わなかった写真は、日付が変わると（0時）消える。
(i) 「しない（外す）」で外すと、専用タグの印も外れる。
(j) 版の2か所が 0.2.0 でそろっている。
時計は 2026/11/18(水) 10:30（日本時間）から。
"""
import os, re
from playwright.sync_api import sync_playwright
from PIL import Image
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []
JPG = os.path.join(OUT, 'v020_fuku.jpg')
Image.new('RGB', (300, 400), (60, 110, 180)).save(JPG, quality=80)


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


def ff(pg, ms_):
    pg.clock.fast_forward(ms_); pg.wait_for_timeout(1300)


def pid_id(pg, pid):
    return pg.evaluate("pid=>patients.find(p=>p.pid===pid).id", pid)


def photo_keys(pg):
    return pg.evaluate("dbKeys('photos')")


def dlg_click(pg, text):
    pg.locator('#dlgActions button', has_text=text).click(); pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 18, 10, 30))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")

    # (j) 版
    v = pg.evaluate("APP_VERSION"); ok(v == '0.2.0', v)
    ok("gaishutsu-tanjikan-v0.2.0" in open(os.path.join(APP, 'sw.js'), encoding='utf-8').read())

    # (a) デモ
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    ok('いつもの外出12人' in pg.inner_text('#toast'), pg.inner_text('#toast'))
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(800)
    ok(pg.locator('#itGrid .it-t').count() == 12)
    ok(pg.inner_text('#cntItsumo') == '12')
    ok(pg.locator('#itGrid .it-ph img').count() == 9, pg.locator('#itGrid .it-ph img').count())
    ok(pg.locator('#itGrid .it-noph').count() == 3)
    a = pid_id(pg, 'D1021'); c = pid_id(pg, 'D1030')
    ok(pg.evaluate("id=>tags.find(t=>t.id==='T-13').owner===id", a))
    ok('T-13 専用' in pg.inner_text(f'[data-itp="{a}"]'))
    ok('11:45まで' in pg.inner_text(f'[data-itp="{a}"]'))
    pg.screenshot(path=os.path.join(OUT, 'v020_1_ichiran.png'))

    # (b) タグ管理・新規登録のタグ
    pg.click('nav button[data-tab=tags]'); pg.wait_for_timeout(300)
    row = pg.locator('#tTable tr', has_text='T-13').first.inner_text()
    ok('さん 専用' in row and '本人が所持' in row, row)
    ok(pg.locator('#tTable [data-town="T-13"]').count() == 1)
    pg.screenshot(path=os.path.join(OUT, 'v020_4_tag.png'))
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
    tb = pg.evaluate("[...document.querySelectorAll('#tagBtns [data-tag]')].map(b=>b.dataset.tag)")
    ok(not any(t in tb for t in ['T-13', 'T-17', 'T-24']), tb)
    ok('T-04' in tb, tb)

    # (c) 台帳から設定。同意書の取得日がない人に専用タグ → 知らせ
    x = pid_id(pg, 'D1041')
    pg.evaluate("id=>{const p=patients.find(q=>q.id===id);p.consentDate='';p.consentWithdrawn='';return dbPut('patients',p);}", x)
    pg.click('nav button[data-tab=patients]'); pg.wait_for_timeout(300)
    pg.fill('#ptQ', 'D1041'); pg.wait_for_timeout(200)
    pg.click(f'[data-ptit="{x}"]'); pg.wait_for_timeout(300)
    pg.select_option('#dlgBody select[name=itTag]', 'T-04')
    dlg_click(pg, '保存')
    ok(pg.locator('#dlg').evaluate('d=>d.open'))
    ok('同意書の取得日' in pg.inner_text('#dlg .ferr'), pg.inner_text('#dlg'))
    pg.screenshot(path=os.path.join(OUT, 'v020_5_settei.png'))
    pg.select_option('#dlgBody select[name=itTag]', '')
    dlg_click(pg, '保存')
    ok(not pg.locator('#dlg').evaluate('d=>d.open'))
    ok(pg.evaluate("id=>{const p=patients.find(q=>q.id===id);return p.itsumo.on&&p.itsumo.dest==='喫煙'&&p.itsumo.dueHM==='11:45'}", x))
    ok(pg.evaluate("tags.find(t=>t.id==='T-04').owner") in (None, ''))
    ok('いつもの外出' in pg.locator('#ptTable tr', has_text='D1041').inner_text())
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(500)
    ok(pg.locator('#itGrid .it-t').count() == 13)

    # (d) 写真の準備
    pg.click('#itPrepBtn'); pg.wait_for_timeout(300)
    ok('写真の準備' in pg.inner_text('#itTitle'))
    with pg.expect_file_chooser() as fc:
        pg.click(f'[data-itsnap="{c}"]')
    fc.value.set_files(JPG)
    pg.wait_for_function("id=>(document.querySelector(`[data-itp=\"${id}\"]`)||{}).innerText?.includes('✓ 写真')", arg=c, timeout=8000)
    ok('✓ 写真' in pg.inner_text(f'[data-itp="{c}"]'), pg.inner_text(f'[data-itp="{c}"]'))
    ok(f'prep:{c}' in photo_keys(pg))
    pg.screenshot(path=os.path.join(OUT, 'v020_3_junbi.png'))
    pg.click('#itPrepBtn'); pg.wait_for_timeout(300)

    # (e) 出発（10:58）
    ff(pg, 28 * 60000)
    pg.click(f'[data-itgo="{a}"]'); pg.wait_for_timeout(500)
    first = pg.locator('#dlgBody [data-itdue]').first
    ok('11:45' in first.inner_text() and 'on' in first.get_attribute('class'), first.inner_text())
    ok('服装は同じ。出発' in pg.locator('#dlgActions button').last.inner_text())
    ok(pg.locator('#itGoPh img').count() == 1)
    pg.fill('#dlgBody input[name=nurse]', '')
    dlg_click(pg, '出発')
    ok('看護師' in pg.inner_text('#dlg .ferr'))
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    pg.screenshot(path=os.path.join(OUT, 'v020_2_go.png'))
    dlg_click(pg, '出発')
    o = pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');return o&&{id:o.id,due:new Date(o.dueAt).getHours()*60+new Date(o.dueAt).getMinutes(),tag:o.tagId,ph:o.hasPhoto,it:o.itsumo,n:o.departNurse}}", a)
    ok(o and o['it'] and o['due'] == 11 * 60 + 45 and o['tag'] == 'T-13' and o['ph'] and o['n'] == '(デモ) 看護師 見本', o)
    keys = photo_keys(pg)
    ok(o['id'] in keys and f'prep:{a}' not in keys, keys)
    ok(pg.evaluate("tags.find(t=>t.id==='T-13').status") == 'inuse')
    ok(pg.evaluate("settings.itsumoNurse") == '(デモ) 看護師 見本')
    # 写真がない人：出発の画面で撮る
    c2 = pid_id(pg, 'D1031')
    pg.click(f'[data-itgo="{c2}"]'); pg.wait_for_timeout(500)
    ok('写真なしで出発' in pg.locator('#dlgActions button').last.inner_text())
    ok(pg.input_value('#dlgBody input[name=nurse]') == '(デモ) 看護師 見本')
    pg.set_input_files('#itGoIn', JPG); pg.wait_for_timeout(800)
    ok('服装は同じ。出発' in pg.locator('#dlgActions button').last.inner_text())
    dlg_click(pg, '出発')
    o2 = pg.evaluate("id=>{const o=outings.find(x=>x.patientId===id&&x.status==='out');return o&&{id:o.id,ph:o.hasPhoto}}", c2)
    ok(o2 and o2['ph'] and o2['id'] in photo_keys(pg), o2)
    pg.wait_for_timeout(1200)
    ok(pg.locator('#itGrid .it-t.out').count() == 2, pg.locator('#itGrid .it-t.out').count())
    # すでに外出中の人は「出発」が出ない
    ok(pg.locator(f'[data-itgo="{a}"]').count() == 0)

    # (f) 11:47：帰院予定を過ぎる
    ff(pg, 49 * 60000)
    ok(pg.locator(f'[data-itp="{a}"].over').count() == 1)
    ok('on' in pg.get_attribute('#banner', 'class'))
    pg.screenshot(path=os.path.join(OUT, 'v020_6_over.png'))

    # (g) 帰院
    pg.click(f'[data-itback="{o["id"]}"]'); pg.wait_for_timeout(400)
    ok(pg.input_value('#dlgBody input[name=nurse]') == '(デモ) 看護師 見本')
    ok('本人が持ったまま' in pg.inner_text('#dlgBody'))
    pg.fill('#dlgBody input[name=nurse]', '')
    dlg_click(pg, '帰院')
    ok('看護師' in pg.inner_text('#dlg .ferr'))
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    dlg_click(pg, '帰院')
    r = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);return {st:o.status,ph:o.hasPhoto,del:!!o.photoDeletedAt,kept:o.tagKept,n:o.returnNurse,log:o.log.map(l=>l.text).join('|')}}", o['id'])
    ok(r['st'] == 'returned' and not r['ph'] and r['del'] and r['kept'] and r['n'] == '(デモ) 看護師 見本', r)
    ok('専用タグ T-13 は本人が持ったまま' in r['log'], r['log'])
    ok(o['id'] not in photo_keys(pg))
    t11 = pg.evaluate("tags.find(t=>t.id==='T-13')")
    ok(t11['status'] == 'available' and t11['owner'] == a and not t11['outingId'], t11)
    pg.wait_for_timeout(1200)
    ok('今日' in pg.inner_text(f'[data-itp="{a}"]') and pg.locator(f'[data-itgo="{a}"]').count() == 1)
    # くわしい帰院登録（ふつうの帰院の画面）：専用タグの回収の欄は出ない
    pg.click(f'[data-itback="{o2["id"]}"]'); pg.wait_for_timeout(400)
    pg.click('#itBackMore'); pg.wait_for_timeout(400)
    ok('帰院登録' in pg.inner_text('#dlgTitle'))
    ok(pg.locator('#dlgBody input[name=tagBack]').count() == 0 and '本人が持ったまま' in pg.inner_text('#dlgBody'))
    pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 見本')
    dlg_click(pg, '帰院を登録')
    tg = pg.evaluate("id=>{const o=outings.find(x=>x.id===id);const t=tags.find(x=>x.id===o.tagId);return {st:o.status,kept:o.tagKept,ts:t.status,ow:t.owner}}", o2['id'])
    ok(tg['st'] == 'returned' and tg['kept'] and tg['ts'] == 'available' and tg['ow'] == c2, tg)
    # 一覧の「タグ回収」
    ok(pg.evaluate("id=>COLS.find(c=>c[0]==='タグ回収')[1](outings.find(x=>x.id===id))", o['id']) == '本人が所持（専用）')

    # (h) 0時：撮っておいた写真が消える（D1022 などはまだ残っている）
    b2 = pid_id(pg, 'D1022')
    ok(f'prep:{b2}' in photo_keys(pg))
    ff(pg, (12 * 60 + 14) * 60000)   # 11:49 → 翌日 0:03
    ok(pg.evaluate("new Date().getDate()") == 19)
    keys = photo_keys(pg)
    ok(not any(str(k).startswith('prep:') for k in keys), keys)
    ok(pg.evaluate("id=>patients.find(p=>p.id===id).itsumoPhotoAt", b2) in (None, 0))
    pg.click('nav button[data-tab=itsumo]'); pg.wait_for_timeout(600)
    ok(pg.locator('#itGrid .it-ph img').count() == 0)

    # (i) 外す → 専用タグの印も外れる
    pg.click('#itMembers'); pg.wait_for_timeout(300)
    pg.fill('#itQ', 'D1021'); pg.wait_for_timeout(200)
    pg.click(f'[data-itset="{a}"]'); pg.wait_for_timeout(300)
    pg.click('#dlgBody label:has(input[name=itOn][value="0"])')
    dlg_click(pg, '保存')
    ok(pg.evaluate("tags.find(t=>t.id==='T-13').owner") in (None, ''))
    ok(pg.evaluate("id=>patients.find(p=>p.id===id).itsumo.on", a) is False)
    pg.wait_for_timeout(500)
    ok(pg.locator('#itGrid .it-t').count() == 12)

    # デモを消す：デモの人の専用タグの印・撮っておいた写真も残らない
    pg.click('nav button[data-tab=settings]'); pg.click('#demoOut')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを消しました')", timeout=30000)
    ok(pg.evaluate("tags.filter(t=>t.owner).length") == 0)
    ok(not any(str(k).startswith('prep:') for k in photo_keys(pg)))
    ctx.close(); b.close()

print('checks', N[0])
print('errors', errs)
