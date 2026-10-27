"""iPhone 用・ループする水槽アニメーション（Live Photo 壁紙の素材）を生成する。

出力: aquarium.mp4（3秒・30fps・1180x2556）と aquarium_still.png
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1180, 2556
FPS = 30
T = 3.0  # ループ周期（秒）
N = int(FPS * T)
OUT = Path(__file__).parent
TAU = math.tau
rng = random.Random(7)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


# ---------- 静的な背景 ----------
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([40, 150, 190])
    bottom = np.array([8, 40, 80])
    grad = top + (bottom - top) * (y ** 0.8)[..., None]
    img = np.broadcast_to(grad, (H, W, 3)).astype(np.uint8)
    bg = Image.fromarray(img).convert("RGBA")

    d = ImageDraw.Draw(bg)
    # 砂
    sand_top = int(H * 0.86)
    pts = [(0, H)]
    for x in range(0, W + 40, 40):
        pts.append((x, sand_top + 25 * math.sin(x / 170) + 15 * math.sin(x / 61)))
    pts.append((W, H))
    d.polygon(pts, fill=(214, 190, 140))
    for _ in range(900):
        x, yy = rng.uniform(0, W), rng.uniform(sand_top + 20, H)
        c = rng.choice([(190, 165, 118), (230, 210, 165), (170, 150, 110)])
        r = rng.uniform(2, 5)
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=c)
    # 岩
    for cx, cy, rx, ry, col in [
        (180, sand_top + 40, 190, 120, (92, 98, 110)),
        (330, sand_top + 70, 120, 80, (110, 116, 128)),
        (960, sand_top + 30, 230, 160, (80, 86, 100)),
        (790, sand_top + 90, 100, 60, (120, 124, 134)),
    ]:
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col)
        d.ellipse((cx - rx * 0.6, cy - ry * 0.85, cx + rx * 0.2, cy - ry * 0.2),
                  fill=lerp(col, (200, 210, 220), 0.25))
    # 小さな城
    cx, base = 600, sand_top + 60
    castle = (196, 120, 96)
    d.rectangle((cx - 110, base - 220, cx + 110, base), fill=castle)
    for tx in (cx - 140, cx + 80):
        d.rectangle((tx, base - 320, tx + 60, base), fill=castle)
        for k in range(3):
            d.rectangle((tx + k * 22, base - 345, tx + k * 22 + 14, base - 320), fill=castle)
    d.rectangle((cx - 40, base - 380, cx + 40, base - 200), fill=lerp(castle, (255, 255, 255), 0.1))
    d.polygon([(cx - 55, base - 380), (cx + 55, base - 380), (cx, base - 470)], fill=(150, 70, 70))
    d.chord((cx - 45, base - 110, cx + 45, base + 70), 180, 360, fill=(50, 30, 30))
    d.rectangle((cx - 45, base - 20, cx + 45, base), fill=(50, 30, 30))
    for wx, wy in [(cx - 120, base - 260), (cx + 100, base - 260), (cx - 12, base - 330)]:
        d.ellipse((wx, wy, wx + 24, wy + 36), fill=(255, 220, 140))
    return bg


# ---------- 光の筋 ----------
def make_rays(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, x0 in enumerate([150, 420, 700, 980]):
        a = int(26 + 18 * math.sin(TAU * t / T + i * 1.7))
        sway = 60 * math.sin(TAU * t / T + i)
        d.polygon([(x0 - 40, -10), (x0 + 50, -10),
                   (x0 + 260 + sway, H * 0.9), (x0 + 60 + sway, H * 0.9)],
                  fill=(255, 255, 230, a))
    return layer.filter(ImageFilter.GaussianBlur(30))


# ---------- 水草 ----------
WEEDS = [(x, rng.uniform(0.25, 0.42), rng.uniform(0, TAU), rng.choice(
    [(40, 150, 80), (70, 175, 90), (30, 120, 90)])) for x in
    [60, 110, 250, 470, 520, 760, 880, 1080, 1130]]


def draw_weeds(d, t):
    for x, hfrac, ph, col in WEEDS:
        base = H * 0.88
        height = H * hfrac
        segs = 18
        left, right = [], []
        for s in range(segs + 1):
            u = s / segs
            sway = 70 * u ** 1.5 * math.sin(TAU * t / T + ph + u * 2.5)
            cx = x + sway
            cy = base - height * u
            w = 22 * (1 - u) + 4
            left.append((cx - w, cy))
            right.append((cx + w, cy))
        d.polygon(left + right[::-1], fill=col)
        d.line([((l[0] + r[0]) / 2, l[1]) for l, r in zip(left, right)],
               fill=lerp(col, (255, 255, 255), 0.25), width=4)


# ---------- 魚 ----------
SS = 3  # スプライトの超解像倍率


def fish_sprite(length, body, accent, tail_phase, facing):
    w, h = int(length * 1.5), int(length * 0.9)
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = SS
    cx, cy = w * 0.58 * s, h * 0.5 * s
    L = length * s
    # 尾びれ
    wag = 0.35 * math.sin(tail_phase)
    tx = cx - L * 0.48
    tail = [(tx + L * 0.05, cy),
            (tx - L * 0.38, cy - L * 0.32 + wag * L * 0.4),
            (tx - L * 0.28, cy + wag * L * 0.3),
            (tx - L * 0.38, cy + L * 0.32 + wag * L * 0.4)]
    d.polygon(tail, fill=accent, outline=(30, 30, 50), width=2 * s)
    # 胴体
    body_pts = []
    for k in range(48):
        a = TAU * k / 48
        bx = math.cos(a) * L * 0.5
        by = math.sin(a) * L * 0.27 * (1 - 0.25 * math.cos(a))
        body_pts.append((cx + bx, cy + by))
    d.polygon(body_pts, fill=body, outline=(30, 30, 50), width=2 * s)
    # 背びれ
    d.polygon([(cx - L * 0.15, cy - L * 0.25), (cx + L * 0.05, cy - L * 0.45),
               (cx + L * 0.15, cy - L * 0.24)], fill=accent, outline=(30, 30, 50), width=2 * s)
    # しま模様
    for k in (-0.12, 0.08):
        d.line([(cx + k * L, cy - L * 0.22), (cx + k * L + L * 0.03, cy + L * 0.22)],
               fill=accent, width=int(L * 0.06))
    # 目
    ex, ey, er = cx + L * 0.3, cy - L * 0.05, L * 0.07
    d.ellipse((ex - er, ey - er, ex + er, ey + er), fill="white", outline=(30, 30, 50), width=s)
    d.ellipse((ex - er * 0.45, ey - er * 0.45, ex + er * 0.45, ey + er * 0.45), fill=(20, 20, 30))
    img = img.resize((w, h), Image.LANCZOS)
    if facing < 0:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


PALETTE = [((255, 140, 60), (255, 230, 90)), ((90, 200, 255), (30, 90, 200)),
           ((255, 120, 170), (255, 220, 240)), ((255, 220, 80), (240, 120, 40)),
           ((170, 120, 255), (90, 230, 210))]

# その場で泳ぐ大きめの魚
BIG = []
for i, (cx, cy) in enumerate([(300, 1150), (820, 1380), (420, 1700), (900, 900), (650, 1980)]):
    body, acc = PALETTE[i % len(PALETTE)]
    BIG.append(dict(cx=cx, cy=cy, L=rng.uniform(170, 240), body=body, acc=acc,
                    facing=rng.choice([-1, 1]), ph=rng.uniform(0, TAU),
                    wag=rng.choice([3, 4, 5])))

# 横切る小魚の群れ（1ループで画面を1周）
SCHOOL = [dict(dx=rng.uniform(-120, 120), dy=rng.uniform(-90, 90), L=rng.uniform(60, 80),
               ph=rng.uniform(0, TAU)) for _ in range(7)]


def draw_fish(frame, t):
    p = TAU * t / T
    for f in BIG:
        x = f["cx"] + 35 * math.sin(p + f["ph"]) * f["facing"]
        y = f["cy"] + 30 * math.sin(2 * p + f["ph"])
        spr = fish_sprite(f["L"], f["body"], f["acc"], f["wag"] * p + f["ph"], f["facing"])
        frame.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height / 2)))
    span = W + 600
    head = -300 + span * (t / T)
    for s in SCHOOL:
        x = head + s["dx"]
        if x > W + 300:
            x -= span
        y = 1560 + s["dy"] + 15 * math.sin(2 * p + s["ph"])
        spr = fish_sprite(s["L"], (200, 230, 255), (80, 140, 220), 6 * p + s["ph"], 1)
        frame.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height / 2)))


# ---------- 泡 ----------
BUBBLES = [dict(x=rng.choice([600, 600, 610, 980, 990]) + rng.uniform(-25, 25),
                off=rng.uniform(0, 1), r=rng.uniform(6, 18), ph=rng.uniform(0, TAU))
           for _ in range(26)]


def draw_bubbles(d, t):
    span = H * 0.9
    for b in BUBBLES:
        u = (b["off"] + t / T) % 1.0
        y = H * 0.85 - span * u
        x = b["x"] + 14 * math.sin(TAU * 3 * t / T + b["ph"])
        r = b["r"] * (0.7 + 0.5 * u)
        d.ellipse((x - r, y - r, x + r, y + r), outline=(220, 245, 255, 200), width=3)
        d.ellipse((x - r * 0.5, y - r * 0.6, x - r * 0.1, y - r * 0.2), fill=(255, 255, 255, 200))


def render(t, bg):
    frame = bg.copy()
    frame.alpha_composite(make_rays(t))
    d = ImageDraw.Draw(frame, "RGBA")
    draw_weeds(d, t)
    draw_fish(frame, t)
    draw_bubbles(ImageDraw.Draw(frame, "RGBA"), t)
    return frame.convert("RGB")


def main():
    bg = make_background()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out = OUT / "aquarium.mp4"
    proc = subprocess.Popen([
        ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
        str(out)], stdin=subprocess.PIPE)
    for i in range(N):
        img = render(i / FPS, bg)
        if i == 0:
            img.save(OUT / "aquarium_still.png")
        proc.stdin.write(img.tobytes())
        print(f"\r{i + 1}/{N}", end="", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    print(f"\n書き出し完了: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
