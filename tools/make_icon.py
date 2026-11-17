#!/usr/bin/env python3
"""短時間外出の版のホーム画面アイコンを作る。

図案：明るい橙→濃い朱の斜めグラデーションの地（ほかの外出管理アプリの濃紺・青緑と取り違えない色）。
中央に白い太い「くり返し」の矢印の輪（約300度の弧＋矢じり）、輪の中に白い太字「外出」。

512px の4倍で描いてから、180・192・512 それぞれへ直接縮小する
（以前、小さい版で地の色が左上にしか塗られない不具合があったため、3つとも同じ元絵から作る）。
外部のフォント・画像は使わず、端末にある日本語フォント（Noto Sans CJK JP など）を探して使う。
使い方：python3 tools/make_icon.py   （リポジトリのいちばん上に icon-180/192/512.png を書き出す）
"""
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 512
SS = 4
W = BASE * SS

C_TOP = (0xf7, 0xa2, 0x3b)   # 左上：明るい橙
C_BOT = (0xc8, 0x3a, 0x12)   # 右下：濃い朱
WHITE = (255, 255, 255, 255)


def s(v):
    return int(round(v * SS))


def find_jp_font():
    try:
        out = subprocess.run(['fc-list', ':lang=ja', 'file', 'family', 'style', 'index'],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    cands = []
    for line in out.splitlines():
        path = line.split(':', 1)[0].strip()
        low = line.lower()
        if 'serif' in low or 'mono' in low:
            continue
        idx = 0
        if 'index=' in line:
            try:
                idx = int(line.rsplit('index=', 1)[1].split(':')[0].split(',')[0])
            except ValueError:
                idx = 0
        score = 0
        if ' jp' in low or 'japan' in low or 'gothic' in low or 'ipa' in low:
            score += 10
        for w, pts in (('black', 6), ('heavy', 5), ('bold', 4), ('medium', 2)):
            if w in low:
                score += pts
                break
        cands.append((score, path, idx))
    cands.sort(key=lambda c: -c[0])
    for _, path, idx in cands:
        try:
            ImageFont.truetype(path, 40, index=idx)
            return path, idx
        except Exception:
            continue
    return None


def gradient():
    small = Image.new('RGB', (256, 256))
    px = small.load()
    for y in range(256):
        for x in range(256):
            t = (x + y) / 510
            px[x, y] = tuple(int(round(a + (b - a) * t)) for a, b in zip(C_TOP, C_BOT))
    return small.resize((W, W), Image.BICUBIC).convert('RGBA')


def draw_master():
    img = gradient()
    d = ImageDraw.Draw(img)
    cx = cy = s(256)
    r = s(178)          # 輪の中心線の半径
    th = s(40)          # 輪の太さ
    # 弧：右上のすき間を残して時計回りに（角度は 3時=0度・時計回り、y は下向き）。
    # 中心線の点を並べて太い線で描く（矢じりの付け根と弧の終わりを正確にそろえるため）
    start, end = -42, 222
    angs = [start + (end - start) * i / 600 for i in range(601)]
    ro, ri = r + th / 2, r - th / 2
    outer = [(cx + ro * math.cos(math.radians(t)), cy + ro * math.sin(math.radians(t))) for t in angs]
    inner = [(cx + ri * math.cos(math.radians(t)), cy + ri * math.sin(math.radians(t))) for t in reversed(angs)]
    d.polygon(outer + inner, fill=WHITE)
    pts = [(cx + r * math.cos(math.radians(start)), cy + r * math.sin(math.radians(start))),
           (cx + r * math.cos(math.radians(end)), cy + r * math.sin(math.radians(end)))]
    x, y = pts[0]   # 始まりは丸く
    d.ellipse([x - th / 2, y - th / 2, x + th / 2, y + th / 2], fill=WHITE)
    # 矢じり：付け根の中心を弧の終わりに置き、時計回りの接線の向きへ
    a1 = math.radians(end)
    ex, ey = pts[-1]
    tx, ty = -math.sin(a1), math.cos(a1)
    nx, ny = math.cos(a1), math.sin(a1)
    L, Wd = s(74), s(58)
    tip = (ex + tx * L, ey + ty * L)
    p1 = (ex + nx * Wd, ey + ny * Wd)
    p2 = (ex - nx * Wd, ey - ny * Wd)
    d.polygon([tip, p1, p2], fill=WHITE)
    # 文字「外出」
    f = find_jp_font()
    font = ImageFont.truetype(f[0], s(124), index=f[1]) if f else ImageFont.load_default()
    txt = '外出'
    bb = d.textbbox((0, 0), txt, font=font)
    tw, tht = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - tht / 2 - bb[1]), txt, font=font, fill=WHITE)
    return img.convert('RGB')


def main():
    master = draw_master()
    for size in (512, 192, 180):
        out = master.resize((size, size), Image.LANCZOS)
        out.save(os.path.join(ROOT, f'icon-{size}.png'), optimize=True)
        print('wrote', size, out.getpixel((2, 2)), out.getpixel((size - 3, size - 3)))


if __name__ == '__main__':
    main()
