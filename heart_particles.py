#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心之引力 · 粒子炫酷版

粒子聚成爱心并持续变换（爱心 → 双心 → 花 → 星系 → 星球 → 无限），
全程只用鼠标交互，界面不显示任何文字。

鼠标交互：
    移动        粒子被光标吸引，形成绕光标的能量漩涡
    按住左键    强吸引，粒子向光标聚成发光核心
    松开左键    冲击波爆开，粒子荡开后回位
    快速挥动    光标拖出粒子光带
    滚轮        轻微缩放呼吸

键盘（辅助，不显示提示）：空格 音乐开关 / ESC 退出
"""

import os
import sys
import math
import random
import wave
import tempfile

TAU = math.tau

try:
    import pygame
except ImportError:
    print("正在安装 pygame ...")
    import subprocess
    for extra in (["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"], []):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame",
                                   "--disable-pip-version-check", "--quiet"] + extra)
            break
        except Exception:
            continue
    import pygame

VW, VH = 1200, 800
CX, CY = VW / 2.0, VH / 2.0
N = 4200
FPS = 60

PALETTES = [
    # 玫粉：暗玫红 → 粉 → 白粉高光
    [(52, 10, 32), (104, 22, 60), (156, 42, 90), (200, 66, 120),
     (236, 96, 148), (255, 138, 184), (255, 190, 218), (255, 246, 252)],
    # 桃粉
    [(58, 16, 26), (116, 34, 50), (170, 58, 78), (214, 86, 108),
     (245, 118, 138), (255, 158, 176), (255, 204, 214), (255, 248, 246)],
    # 粉紫
    [(46, 12, 44), (96, 26, 86), (146, 46, 126), (192, 70, 164),
     (232, 100, 190), (255, 140, 214), (255, 192, 236), (255, 246, 255)],
]

SH_PARAMS = [
    # (旋转幅度, 旋转速度, 俯视 cos, 俯视 sin, 上下晃动幅度, 晃动速度)
    (0.06, 0.55, 0.885, 0.466, 15.0, 1.00),   # 0 单心：上下轻微晃动
    (0.10, 0.42, 0.885, 0.466, 8.0, 0.90),    # 1 双心叠：轻微摆动
    (0.07, 0.55, 0.885, 0.466, 11.0, 0.90),   # 2 内外双层
    (0.09, 0.34, 0.885, 0.466, 6.0, 0.80),    # 3 一箭穿双心
    (0.12, 0.62, 0.900, 0.435, 10.0, 1.15),   # 4 小爱心群
    (0.06, 0.50, 0.885, 0.466, 12.0, 0.95),   # 5 边缘心 + 手写 love
]

GLOW_SIZES = (4, 6, 8)            # 半径
LEVELS = (0.16, 0.24, 0.36, 0.62)  # 亮度档


# ---------------------------------------------------------------- 工具
def lerp(a, b, t):
    return a + (b - a) * t


def smooth(x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 精灵
def _make_glow(r, col, level):
    d = r * 2 + 1
    surf = pygame.Surface((d, d))
    surf.fill((0, 0, 0))
    peak = 235 * level
    inv = 1.0 / (r * r)
    cx = cy = r
    for y in range(d):
        dy = y - cy
        for x in range(d):
            dx = x - cx
            q = (dx * dx + dy * dy) * inv
            if q > 1.9:
                continue
            g = math.exp(-3.4 * q) - math.exp(-6.6)
            if g <= 0.0:
                continue
            v = peak * g
            surf.set_at((x, y), (min(255, int(col[0] * v / 255.0 * 1.9)),
                                 min(255, int(col[1] * v / 255.0 * 1.9)),
                                 min(255, int(col[2] * v / 255.0 * 1.9))))
    return surf


def build_sprites():
    sprites = []
    for pal in PALETTES:
        sizes = []
        for r in GLOW_SIZES:
            cols = []
            for col in pal:
                cols.append([_make_glow(r, col, lv) for lv in LEVELS])
            sizes.append(cols)
        sprites.append(sizes)
    halo = []
    for pal in PALETTES:
        halo.append([_make_glow(24, col, 0.20) for col in pal])
    ring = []
    for r in (26, 52):
        s = pygame.Surface((r * 2 + 1, r * 2 + 1))
        s.fill((0, 0, 0))
        for a in range(0, 360, 2):
            v = 0.55
            x = int(r + r * math.cos(math.radians(a)))
            y = int(r + r * math.sin(math.radians(a)))
            if 0 <= x <= 2 * r and 0 <= y <= 2 * r:
                s.set_at((x, y), (int(120 * v), int(40 * v), int(90 * v)))
        ring.append(s)
    dim = [[tuple(int(c * 0.30) for c in col) for col in pal] for pal in PALETTES]
    return sprites, halo, ring, dim


# ---------------------------------------------------------------- 背景
def build_bg():
    bg = pygame.Surface((VW, VH))
    # 深空渐变
    for y in range(VH):
        q = (y - CY) / CY
        k = math.exp(-1.6 * q * q)
        c = (int(4 + 15 * k), int(5 + 11 * k), int(15 + 40 * k))
        pygame.draw.line(bg, c, (0, y), (VW, y))

    rnd = random.Random(11)
    # 星云：几团柔光叠加，营造宇宙背景
    neb = pygame.Surface((VW, VH))
    neb.fill((0, 0, 0))
    neb_cols = ((70, 40, 130), (30, 60, 145), (120, 40, 110),
                (28, 110, 132), (90, 50, 120), (40, 70, 120))
    for i in range(9):
        r_ = rnd.uniform(50, 120)
        cx_ = rnd.uniform(-100, VW + 100)
        cy_ = rnd.uniform(-80, VH + 80)
        col = neb_cols[i % len(neb_cols)]
        g = _make_glow(int(r_), col, 0.20)
        g = pygame.transform.smoothscale(g, (int(r_ * 4.2), int(r_ * 4.2)))
        neb.blit(g, (int(cx_ - r_ * 2.1), int(cy_ - r_ * 2.1)),
                 special_flags=pygame.BLEND_RGB_ADD)
    bg.blit(neb, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # 背景繁星
    for _ in range(620):
        x = rnd.randrange(VW)
        y = rnd.randrange(VH)
        b = rnd.randint(28, 118)
        col = (b, b, min(255, int(b * 1.45)))
        rr = 1 if rnd.random() < 0.85 else 2
        pygame.draw.circle(bg, col, (x, y), rr)
    return bg


# ---------------------------------------------------------------- 形态
def _heart_xy(t):
    return (16 * math.sin(t) ** 3,
            13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))


_HEART_ARC = None


def _heart_arc():
    """按弧长均匀采样爱心曲线：返回 (ts, cum, total)"""
    global _HEART_ARC
    if _HEART_ARC is None:
        m = 1440
        ts = []
        cum = []
        acc = 0.0
        px, py = _heart_xy(0.0)
        for i in range(m + 1):
            t = TAU * i / m
            x, y = _heart_xy(t)
            acc += math.hypot(x - px, y - py)
            ts.append(t)
            cum.append(acc)
            px, py = x, y
        _HEART_ARC = (ts, cum, acc)
    return _HEART_ARC


def heart_at(s):
    """s ∈ [0,1) 按弧长取爱心上的点"""
    ts, cum, total = _heart_arc()
    target = (s % 1.0) * total
    lo, hi = 0, len(cum) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if cum[mid] < target:
            lo = mid
        else:
            hi = mid
    return _heart_xy(ts[hi])


_HEART_POLY = None


def _heart_poly():
    global _HEART_POLY
    if _HEART_POLY is None:
        _HEART_POLY = [heart_at(k / 720.0) for k in range(720)]
    return _HEART_POLY


def inside_heart(x, y):
    poly = _heart_poly()
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def gen_shapes():
    """6 个 3D 立体爱心形态，全部由粒子填充，有明显体积与厚度。

    0 单个实心 3D 爱心（上下轻微晃动）
    1 两个中间相叠的爱心（一大一小、部分重叠，轻微摆动）
    2 内外双层爱心（外壳 + 内核实心）
    3 一箭穿双心（两颗并排的心被一支箭穿过）
    4 炸开成无数小爱心
    5 汇聚成一个俯视大爱心（轻微转动）
    """
    rnd = random.Random(20261119)
    shapes = []
    HS = 17.0
    N_ = N
    HYC = -2.0

    def surface(s_, k):
        x0, y0 = heart_at(s_)
        return x0 * k, HYC + (y0 - HYC) * k

    def zmax(k):
        return math.sqrt(max(0.0, 1.0 - 0.90 * k * k))

    def solid_pt(zt=0.95):
        k = math.sqrt(rnd.random()) * 1.0
        x0, y0 = surface(rnd.random(), k)
        z = (rnd.random() * 2.0 - 1.0) * zmax(k) * zt
        return x0, y0, z

    def shell_pt(k, th):
        kk = min(0.995, max(0.0, k + (rnd.random() - 0.5) * th))
        x0, y0 = surface(rnd.random(), kk)
        z = (rnd.random() * 2.0 - 1.0) * zmax(kk) * 0.95
        return x0, y0, z

    def push(xs, ys, zs, x0, y0, z0):
        xs.append(x0 * HS)
        ys.append(-(y0 - 3.0) * HS)
        zs.append(z0)

    # ---- 0 单个实心 3D 爱心
    xs, ys, zs = [], [], []
    for i in range(N_):
        if i % 5 == 0:
            push(xs, ys, zs, *shell_pt(0.955, 0.09))
        else:
            push(xs, ys, zs, *solid_pt())
    shapes.append((xs, ys, zs))

    # ---- 1 两个中间相叠的爱心（一大一小，部分重叠）
    xs, ys, zs = [], [], []
    for i in range(N_):
        if i % 2 == 0:
            sc_, ox_, oy_ = 1.0, -5.5, 1.2
        else:
            sc_, ox_, oy_ = 0.64, 9.4, -6.0
        if i % 6 < 5:
            x0, y0, z0 = shell_pt(0.92, 0.10)
        else:
            x0, y0, z0 = solid_pt(0.50)
        push(xs, ys, zs, x0 * sc_ + ox_, HYC + (y0 - HYC) * sc_ + oy_, z0 * sc_)
    shapes.append((xs, ys, zs))

    # ---- 2 内外双层爱心（外壳 + 内核实心）
    xs, ys, zs = [], [], []
    for i in range(N_):
        if i % 5 < 3:
            push(xs, ys, zs, *shell_pt(0.955, 0.10))
        else:
            k = math.sqrt(rnd.random()) * 0.56
            x0, y0 = surface(rnd.random(), k)
            z0 = (rnd.random() * 2.0 - 1.0) * zmax(k) * 0.95
            push(xs, ys, zs, x0, y0, z0)
    shapes.append((xs, ys, zs))

    # ---- 3 一箭穿双心
    xs, ys, zs = [], [], []
    for i in range(N_):
        if i * 100 < N_ * 72:
            # 两颗并排的心
            if i % 2 == 0:
                sc_, ox_ = 0.80, -11.6
            else:
                sc_, ox_ = 0.80, 11.6
            if i % 6 < 5:
                x0, y0, z0 = shell_pt(0.92, 0.10)
            else:
                x0, y0, z0 = solid_pt(0.50)
            push(xs, ys, zs, x0 * sc_ + ox_, HYC + (y0 - HYC) * sc_, z0 * sc_)
        else:
            # 箭：杆 + 箭头 + 箭羽
            u = rnd.random()
            if u < 0.80:
                x0 = rnd.uniform(-13.5, 13.5)
                y0 = HYC + rnd.uniform(-0.10, 0.10)
                z0 = rnd.uniform(-0.12, 0.12)
            elif u < 0.94:
                x0 = rnd.uniform(12.4, 15.6)
                half = (15.6 - x0) * 1.30
                y0 = HYC + (rnd.random() * 2.0 - 1.0) * max(0.05, half)
                z0 = rnd.uniform(-0.10, 0.10)
            else:
                x0 = rnd.uniform(-15.2, -12.2)
                w_ = (x0 + 15.2) / 3.0
                y0 = HYC + (1.0 if rnd.random() < 0.5 else -1.0) * (0.7 + 1.7 * w_)
                z0 = rnd.uniform(-0.10, 0.10)
            push(xs, ys, zs, x0, y0, z0)
    shapes.append((xs, ys, zs))

    # ---- 4 炸开成无数小爱心
    xs, ys, zs = [], [], []
    n_h = 36
    centers = []
    for h in range(n_h):
        ang = TAU * h / n_h + rnd.uniform(-0.12, 0.12)
        rad = rnd.uniform(140.0, 330.0)
        centers.append((math.cos(ang) * rad, math.sin(ang) * rad * 0.82,
                        rnd.uniform(0.075, 0.135)))
    per_h = max(1, N_ // n_h)
    for i in range(N_):
        h = i // per_h
        if h >= n_h:
            h = n_h - 1
        cx_p, cy_p, sc_p = centers[h]
        k = 0.90 + rnd.uniform(-0.05, 0.05)
        x0, y0 = surface(rnd.random(), k)
        z0 = (rnd.random() * 2.0 - 1.0) * 0.32
        push(xs, ys, zs, x0 * sc_p, HYC + (y0 - HYC) * sc_p, z0 * sc_p)
        xs[-1] += cx_p
        ys[-1] += cy_p
    shapes.append((xs, ys, zs))

    # ---- 5 边缘密、中心疏，中间由粒子写出花体手写 "love"
    def _stroke(pts, n, wjit=4.0):
        out = []
        for j in range(len(pts) - 1):
            x1, y1 = pts[j]
            x2, y2 = pts[j + 1]
            dxs = x2 - x1
            dys = y2 - y1
            nl = math.hypot(dxs, dys) + 1e-6
            for k_ in range(n):
                tt = k_ / float(n)
                ox = -dys / nl * (rnd.random() * 2 - 1) * wjit
                oy = dxs / nl * (rnd.random() * 2 - 1) * wjit
                out.append((x1 + dxs * tt + ox, y1 + dys * tt + oy))
        return out

    # 大写 LOVE，四个字母各自成笔
    love_pts = []
    # L
    love_pts += _stroke([(-150, -66), (-150, -10), (-148, 40), (-104, 42)], 26, 2.4)
    # O
    love_path = []
    for k_ in range(30):
        a_ = math.radians(-90) + math.radians(360) * k_ / 29.0
        love_path.append((-74 + math.cos(a_) * 33, -10 + math.sin(a_) * 45))
    love_path.append(love_path[0])
    love_pts += _stroke(love_path, 26, 2.4)
    # V
    love_pts += _stroke([(-32, -66), (-9, 44), (5, 44), (30, -66)], 26, 2.4)
    # E：一竖三横，各自独立成笔
    love_pts += _stroke([(62, -64), (62, 40)], 26, 2.2)
    love_pts += _stroke([(62, -64), (112, -64)], 26, 2.2)
    love_pts += _stroke([(62, -12), (112, -12)], 26, 2.2)
    love_pts += _stroke([(62, 40), (112, 40)], 26, 2.2)
    love_pts = [(u * 1.20 + 26.0, v * 1.20 + 14.0) for (u, v) in love_pts]

    xs, ys, zs = [], [], []
    n_love = int(N_ * 0.28)
    for i in range(N_):
        if i < n_love:
            u_px, v_px = love_pts[(i * len(love_pts)) // n_love]
            push(xs, ys, zs, u_px / HS, 3.0 - (v_px + 30.0) / HS,
                 rnd.uniform(0.42, 0.46))
        elif i % 8 < 7:
            # 边缘：粒子多、贴轮廓
            push(xs, ys, zs, *shell_pt(0.955, 0.055))
        else:
            # 中间：稀疏
            k = math.sqrt(rnd.random()) * 0.82
            x0, y0 = surface(rnd.random(), k)
            z0 = (rnd.random() * 2.0 - 1.0) * zmax(k) * 0.95
            push(xs, ys, zs, x0, y0, z0)

    shapes.append((xs, ys, zs))

    # ---- 统一立体收边（椭球厚度，让体积更饱满）
    for (xs, ys, zs) in shapes:
        for i in range(N_):
            z = zs[i] * 1.05
            if z > 1.0:
                z = 1.0
            elif z < -1.0:
                z = -1.0
            zs[i] = z
            kxy = math.sqrt(max(0.18, 1.0 - 0.42 * z * z))
            xs[i] *= kxy
            ys[i] = CY + (ys[i] - CY) * kxy

    return shapes


# ---------------------------------------------------------------- 粒子
class Particle(object):
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "ci", "ph", "delay",
                 "size", "spin", "layer")

    def __init__(self, x, y, z, ci, ph, delay, layer=0):
        self.x = x
        self.y = y
        self.z = z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.ci = ci
        self.ph = ph
        self.delay = delay
        self.size = 1
        self.spin = 1.0
        self.layer = layer


class Spark(object):
    __slots__ = ("x", "y", "vx", "vy", "life", "ci", "size")

    def __init__(self, x, y, vx, vy, life, ci, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.ci = ci
        self.size = size


def init_particles(shapes):
    ps = []
    x0, y0, z0 = shapes[0]
    n_s = max(1, N // 4)
    for i in range(N):
        lay = 1 if i % 4 < 1 else 0
        if lay:
            ci = int(((i // 4) / float(n_s)) * 8.0) % 8
        else:
            ci = int(((i * 0.6180339887) % 1.0) * 8) % 8
        ps.append(Particle(x0[i], y0[i], z0[i],
                           ci=ci,
                           ph=(i / float(N)) * TAU * 3.0,
                           delay=((i % 120) / 120.0),
                           layer=lay))
    return ps


# ---------------------------------------------------------------- 音乐
SR = 22050
NT = 2048
SIN = [math.sin(i * TAU / NT) for i in range(NT)]

CHORD_NOTES = [
    [(220.0, 277.2, 392.0, 523.2)],           # Am7
    [(174.6, 261.6, 349.6, 440.0)],           # Fmaj7
    [(261.6, 329.6, 392.0, 523.2)],           # Cmaj7
    [(196.0, 293.7, 392.0, 440.0)],           # G
]
BELL_NOTES = [880.0, 1046.5, 1174.7, 1318.5, 1568.0]


def _soft(buf, i0, ns, freq, gain, decay=2.0, attack=0.10):
    step = freq / SR * NT
    ph = 0.0
    at = attack * SR
    n = len(buf)
    for i in range(ns):
        if i0 + i >= n:
            break
        t = i / SR
        env = math.exp(-decay * t)
        if i < at:
            env *= i / at
        buf[i0 + i] += SIN[int(ph) % NT] * env * gain
        ph += step


def _bell(buf, i0, ns, freq, gain, decay=4.2):
    step = freq / SR * NT
    ph = 0.0
    n = len(buf)
    for i in range(ns):
        if i0 + i >= n:
            break
        t = i / SR
        env = math.exp(-decay * t)
        if i < 30:
            env *= i / 30.0
        v = SIN[int(ph) % NT] * env
        if t < 0.08:
            v += 0.3 * SIN[int(ph * 2.5) % NT] * math.exp(-20.0 * t)
        buf[i0 + i] += v * gain
        ph += step


def build_music(path):
    beat = 2.4
    bars = len(CHORD_NOTES) * 3            # 12 小节循环
    total = bars * beat
    n = int(total * SR) + SR // 2
    buf = [0.0] * n
    for b in range(bars):
        t0 = b * beat
        chord = CHORD_NOTES[b % len(CHORD_NOTES)]
        for f in chord[0]:
            _soft(buf, int(t0 * SR), int(min(beat * 1.25, total - t0) * SR),
                  f, 0.055, 0.55, 0.22)
        root = chord[0][0] * 0.5
        _soft(buf, int(t0 * SR), int(min(beat * 0.9, total - t0) * SR),
              root, 0.075, 1.1, 0.2)
        if b % 2 == 0:
            f = BELL_NOTES[(b // 2) % len(BELL_NOTES)]
            _bell(buf, int((t0 + 0.35) * SR), int(0.9 * SR), f, 0.16, 4.6)
        if b % 6 == 5:
            _bell(buf, int((t0 + 1.2) * SR), int(0.8 * SR),
                  BELL_NOTES[(b + 2) % len(BELL_NOTES)] * 1.1, 0.11, 5.2)
    peak = max(1e-9, max(abs(v) for v in buf))
    buf = [v / peak * 0.86 for v in buf]
    data = array_of_bytes(buf)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def array_of_bytes(buf):
    out = bytearray()
    for v in buf:
        iv = int(v * 32767.0)
        if iv > 32767:
            iv = 32767
        elif iv < -32768:
            iv = -32768
        out += (iv & 0xFFFF).to_bytes(2, "little")
    return bytes(out)


def music_path():
    return os.path.join(tempfile.gettempdir(), "heart_particles_theme_v1.wav")


def setup_music():
    path = music_path()
    ok = os.path.exists(path) and os.path.getsize(path) > 20000
    if not ok:
        try:
            build_music(path)
            ok = True
        except Exception:
            ok = False
    if not ok:
        return None
    try:
        pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
        return pygame.mixer.Sound(path)
    except Exception:
        return None


# ---------------------------------------------------------------- 主程序
class App(object):
    def __init__(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()
        try:
            pygame.mixer.pre_init(SR, -16, 1, 512)
        except Exception:
            pass
        info = pygame.display.Info()
        sw, sh = info.current_w or VW, info.current_h or VH
        # 物理分辨率普遍是逻辑分辨率的 1.25/1.5 倍，按保底尺寸开窗，避免超出屏幕
        w, h = VW, VH
        if sw >= 1600 and sh >= 1000:
            w, h = VW, VH
        else:
            w, h = 1080, 720
        pygame.display.set_caption("❤")
        self.win = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        # 把窗口居中
        try:
            import ctypes
            hwnd = pygame.display.get_wm_info().get("window")
            if hwnd:
                sx = ctypes.windll.user32.GetSystemMetrics(0)
                sy = ctypes.windll.user32.GetSystemMetrics(1)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0,
                    max(0, (sx - w) // 2), max(0, (sy - h) // 2),
                    0, 0, 0x0001 | 0x0004)
        except Exception:
            pass
        # 窗口图标：一颗爱心
        try:
            icon = pygame.Surface((64, 64), pygame.SRCALPHA)
            pts = []
            for k in range(160):
                a = TAU * k / 160.0
                hx = 16 * math.sin(a) ** 3
                hy = -(13 * math.cos(a) - 5 * math.cos(2 * a)
                       - 2 * math.cos(3 * a) - math.cos(4 * a))
                pts.append((32 + hx * 1.55, 30 + hy * 1.55))
            pygame.draw.polygon(icon, (255, 84, 148), pts)
            pygame.draw.polygon(icon, (120, 240, 255), pts, 2)
            pygame.display.set_icon(icon)
        except Exception:
            pass

        self.virt = pygame.Surface((VW, VH))
        self.bg = build_bg()
        # 背景炫彩柔光层（几团彩色大光晕，缓慢漂移）
        self.bg_glows = []
        gcols = ((90, 40, 150), (30, 90, 160), (150, 40, 120),
                 (30, 140, 150), (120, 70, 40), (60, 40, 160))
        gcols2 = ((255, 145, 185), (120, 75, 215), (230, 60, 140),
                  (165, 95, 255), (255, 105, 120), (205, 65, 185))
        self.bg_glow_sets = []
        for gs in (gcols, gcols2):
            one = []
            for c in gs:
                g = _make_glow(90, c, 0.22)
                g = pygame.transform.smoothscale(g, (520, 520))
                one.append(g)
            self.bg_glow_sets.append(one)
        for g in self.bg_glow_sets[0]:
            self.bg_glows.append(g)
        self.sprites, self.halo, self.ring, self.dim_cols = build_sprites()
        self.shapes = gen_shapes()
        self.parts = init_particles(self.shapes)
        self.sparks = []
        self.struct_idx = [i for i in range(N) if i % 4 == 0]
        self.line_cols = [[tuple(int(c * 0.62) for c in col) for col in pal]
                          for pal in PALETTES]
        # 背景：小爱心精灵（多尺寸/多色，用于漂浮变换）
        self.small_hearts = []
        for size in (6, 9, 13):
            for ci in range(5):
                hs = pygame.Surface((size * 2 + 3, size * 2 + 3), pygame.SRCALPHA)
                cc_ = PALETTES[1][ci]
                col = (int(cc_[0] * 0.42), int(cc_[1] * 0.42), int(cc_[2] * 0.42))
                pts = []
                for k in range(30):
                    a_ = TAU * k / 30.0
                    hx = 16 * math.sin(a_) ** 3
                    hy = -(13 * math.cos(a_) - 5 * math.cos(2 * a_)
                           - 2 * math.cos(3 * a_) - math.cos(4 * a_))
                    pts.append((size + 1 + hx * (size / 15.0),
                                size + 1 + hy * (size / 15.0)))
                pygame.draw.polygon(hs, col, pts)
                pygame.draw.polygon(
                    hs, (int(col[0] * 0.6), int(col[1] * 0.6), int(col[2] * 0.6)),
                    pts, 2)
                self.small_hearts.append(hs)
        rnd_bg2 = random.Random(37)
        self.bg_fhearts = [(rnd_bg2.uniform(40, VW - 40), rnd_bg2.uniform(60, VH - 40),
                            rnd_bg2.uniform(12, 34), rnd_bg2.uniform(0.12, 0.40),
                            rnd_bg2.uniform(0, TAU), rnd_bg2.randrange(5),
                            rnd_bg2.randrange(3))
                           for _ in range(20)]
        self.bg_flow = [list((rnd_bg2.uniform(0, VW), rnd_bg2.uniform(0, VH),
                              rnd_bg2.uniform(-9, 9), rnd_bg2.uniform(-14, -4),
                              rnd_bg2.uniform(0, TAU), rnd_bg2.randrange(8),
                              rnd_bg2.uniform(0.5, 2.2)))
                         for _ in range(70)]
        rnd_bg = random.Random(23)
        self.bg_stars = [(rnd_bg.uniform(0, VW), rnd_bg.uniform(0, VH),
                          rnd_bg.uniform(0.8, 2.2), rnd_bg.uniform(0, TAU),
                          rnd_bg.uniform(0.6, 2.0), rnd_bg.randrange(3))
                         for _ in range(120)]
        rnd_b = random.Random(5)
        self.bx = [rnd_b.uniform(70, VW - 70) for _ in range(N)]
        self.by = [VH + rnd_b.uniform(10, 150) for _ in range(N)]
        # 开场：粒子全部从底部升起汇聚成心
        for i, pt in enumerate(self.parts):
            pt.x = self.bx[i]
            pt.y = self.by[i]
            pt.z = 0.0
            pt.vx = 0.0
            pt.vy = 0.0
            pt.vz = 0.0
        self.order = list(range(N))
        self.order.sort(key=lambda i: self.parts[i].z)

        self.clock = pygame.time.Clock()
        self.t = 0.0
        self.mx, self.my = CX, CY
        self.has_mouse = False
        self.hold = False
        self.waves = []
        self.pal = 0
        self.pal_t = 0.0
        self.shape_a = 0
        self.shape_b = 1
        self.morph = 1.0
        self.hold_t = 1.9
        self.morphing = False
        self.scale = 1.0
        self.last_mouse = (CX, CY)
        self.mouse_vel = 0.0
        self.music = setup_music()
        self.music_on = True
        if self.music:
            try:
                self.music.set_volume(0.55)
                self.music.play(loops=-1)
            except Exception:
                self.music = None

    # ---- 交互
    def to_virt(self, pos):
        w, h = self.win.get_size()
        return pos[0] * VW / float(w), pos[1] * VH / float(h)

    def burst(self, x, y):
        self.waves.append([x, y, 0.0, 1.0])
        for _ in range(26):
            a = TAU * random.random()
            sp = random.uniform(50, 260)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     0.7 + random.random() * 0.6,
                                     random.randrange(8), random.choice((0, 1, 2))))

    def on_event(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return False
            if ev.key == pygame.K_SPACE and self.music:
                self.music_on = not self.music_on
                if self.music_on:
                    self.music.play(loops=-1)
                else:
                    self.music.stop()
        elif ev.type == pygame.MOUSEMOTION:
            nx, ny = self.to_virt(ev.pos)
            dx, dy = nx - self.last_mouse[0], ny - self.last_mouse[1]
            self.mouse_vel = math.hypot(dx, dy)
            self.last_mouse = (nx, ny)
            self.mx, self.my = nx, ny
            self.has_mouse = True
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            nx, ny = self.to_virt(ev.pos)
            self.mx, self.my = nx, ny
            self.has_mouse = True
            if ev.button == 1:
                self.hold = True
            elif ev.button == 3:
                self.burst(nx, ny)
        elif ev.type == pygame.MOUSEBUTTONUP:
            if ev.button == 1 and self.hold:
                self.hold = False
                self.burst(self.mx, self.my)
        elif ev.type == pygame.MOUSEWHEEL:
            self.scale = max(0.86, min(1.25, self.scale + ev.y * 0.03))
        elif ev.type == pygame.VIDEORESIZE:
            self.win = pygame.display.set_mode((max(560, ev.w), max(380, ev.h)),
                                               pygame.RESIZABLE)
        return True

    # ---- 物理 + 目标
    def update(self, dt):
        self.t += dt
        self.pal_t += dt
        if self.pal_t > 6.5:
            self.pal_t = 0.0
            self.pal = (self.pal + 1) % len(PALETTES)

        if self.morphing:
            self.morph += dt / 1.10
            if self.morph >= 1.0:
                self.morph = 1.0
                self.morphing = False
                self.shape_a = self.shape_b
                self.shape_b = (self.shape_b + 1) % len(self.shapes)
                self.morph = 1.0
        else:
            self.hold_t -= dt
            if self.hold_t <= 0.0:
                self.hold_t = 2.1
                self.morphing = True
                self.morph = 0.0
                self.shape_b = (self.shape_a + 1) % len(self.shapes)

        # 两个形态的动画参数
        ta = self.t
        pa = SH_PARAMS[self.shape_a]
        pb = SH_PARAMS[self.shape_b]
        rot_a = pa[0] * math.sin(pa[1] * ta)
        ca, sa = math.cos(rot_a), math.sin(rot_a)
        cpa, spa = pa[2], pa[3]
        boba = pa[4] * math.sin(pa[5] * ta)
        beat = 1.0 + 0.055 * max(0.0, math.sin(ta * 2.6)) ** 2
        sb = beat * self.scale
        rot_b = pb[0] * math.sin(pb[1] * ta)
        cb, snb = math.cos(rot_b), math.sin(rot_b)
        cpb, spb = pb[2], pb[3]
        bobb = pb[4] * math.sin(pb[5] * ta)
        scb = self.scale

        ax, ay, az = self.shapes[self.shape_a]
        bx, by, bz = self.shapes[self.shape_b]
        morphing = self.morphing
        m0 = self.morph

        bx_l, by_l = self.bx, self.by
        px, py, pz_pos = self.mx, self.my, 300.0
        hold = self.hold
        radius = 460.0 if hold else 330.0
        pull = 2.55 if hold else 1.0
        has_mouse = self.has_mouse
        if has_mouse:
            dmc_ = math.sqrt((px - CX) ** 2 + (py - CY) ** 2)
            w_mouse = 1.0 if dmc_ < 470.0 else 0.0
        else:
            w_mouse = 0.0

        # 形态过渡：A 轻微旋转呼吸；B 旋转
        for wave in self.waves:
            wave[2] += dt
        self.waves = [w for w in self.waves if w[2] < 1.5]

        waves = self.waves
        damp = 0.885
        k = 0.085

        for i in range(N):
            p = self.parts[i]
            # ---- 目标点
            axr = ax[i] * sb
            ayr = ay[i] * sb
            azr = az[i]
            zl = azr
            per_a = 1.0 + azr * 0.30
            xa = (axr * ca - zl * 40.0 * sa) * per_a + CX
            ya = ayr * per_a * cpa - zl * 100.0 * spa + CY + boba
            za = azr * ca

            bxr = bx[i] * scb
            byr = by[i] * scb
            bzr = bz[i]
            zl_b = bzr
            per_b = 1.0 + bzr * 0.30
            xb = (bxr * cb - zl_b * 40.0 * snb) * per_b + CX
            yb = byr * per_b * cpb - zl_b * 100.0 * spb + CY + bobb
            zb = bzr * cb

            if morphing:
                # 心上的粒子直接就地变化成下一个 3D 形态
                u = smooth((m0 - 0.15 * p.delay) / 1.10)
                tx = xa + (xb - xa) * u
                ty = ya + (yb - ya) * u
                tz = za + (zb - za) * u
            else:
                tx, ty, tz = xa, ya, za

            # ---- 鼠标靠近：少量粒子被吸附，在鼠标旁聚成一个小爱心
            if w_mouse > 0.0 and i % 42 == 0:
                # 鼠标靠近爱心时，一小撮粒子飞到光标处聚成小爱心
                s_l = (p.ph * 0.1591549) % 1.0
                lx_, ly_ = heart_at(s_l)
                kk_ = 1.8 + 1.3 * w_mouse
                mx_t = px + lx_ * kk_
                my_t = py - (ly_ - 3.0) * kk_
                tx = tx + (mx_t - tx) * w_mouse * 0.96
                ty = ty + (my_t - ty) * w_mouse * 0.96
                tz = 0.60

            # ---- 弹簧回到目标
            p.vx += (tx - p.x) * k
            p.vy += (ty - p.y) * k
            p.vz += (tz - p.z) * k * 0.6

            # ---- 鼠标力场
            # ---- 冲击波
            for w in waves:
                wx, wy, wt, _s = w
                r = wt * 760.0
                dx = p.x - wx
                dy = p.y - wy
                d = math.sqrt(dx * dx + dy * dy) + 1e-6
                gap = d - r
                if -70.0 < gap < 90.0:
                    strength = (1.0 - abs(gap) / 90.0) * 900.0 * (1.0 - wt / 1.5)
                    p.vx += dx / d * strength * 0.045
                    p.vy += dy / d * strength * 0.045

            p.vx *= damp
            p.vy *= damp
            p.vz *= damp
            p.x += p.vx * dt * 60.0 * 0.06
            p.y += p.vy * dt * 60.0 * 0.06
            p.z += p.vz * dt * 60.0 * 0.03
            if p.z > 1.4:
                p.z = 1.4
            elif p.z < -1.4:
                p.z = -1.4

            # ---- 尺寸/闪烁
            if p.layer:
                lv = 3 if math.sin(self.t * 3.4 + p.ph) > 0.55 else 2
                sz = 1
            else:
                depth = p.z
                base_lv = 2 if depth > 0.55 else (1 if depth > 0.0 else 0)
                if math.sin(self.t * 3.2 + p.ph) > 0.85:
                    base_lv += 1
                r_d = math.hypot(p.x - CX, p.y - CY) / 330.0
                if r_d > 0.72:
                    base_lv -= 1          # 边缘压暗，突出体积/球感
                lv = base_lv if base_lv < 3 else 3
                if lv < 0:
                    lv = 0
                sz = 1 if depth > 0.22 else 0
            if hold and has_mouse:
                dd = math.hypot(p.x - px, p.y - py)
                if dd < 210.0:
                    lv = 3
                    sz = 2
            p.spin = lv
            p.size = sz

        # ---- 背景流光粒子漂移
        for f in self.bg_flow:
            f[0] = (f[0] + f[2] * dt) % VW
            f[1] = (f[1] + f[3] * dt) % VH

        # ---- 火花
        if has_mouse and self.mouse_vel > 6.0:
            cnt = int(min(6, self.mouse_vel / 26.0))
            for _ in range(cnt):
                a = TAU * random.random()
                self.sparks.append(Spark(self.mx + (random.random() - 0.5) * 16,
                                         self.my + (random.random() - 0.5) * 16,
                                         math.cos(a) * 120.0, math.sin(a) * 120.0,
                                         0.5 + random.random() * 0.55,
                                         random.randrange(8), random.choice((0, 1))))
        self.mouse_vel *= 0.86

        alive = []
        for s in self.sparks:
            s.life -= dt
            if s.life <= 0.0:
                continue
            s.x += s.vx * dt
            s.y += s.vy * dt
            s.vx *= 0.94
            s.vy *= 0.94
            s.vy += 12.0 * dt
            alive.append(s)
        self.sparks = alive[:420]

        # ---- 排序（按 z，隔帧执行）
        if int(self.t * FPS) % 8 == 0:
            self.order.sort(key=lambda idx: self.parts[idx].z)

    # ---- 绘制
    def render(self):
        surf = self.virt
        surf.blit(self.bg, (0, 0))
        # 背景炫彩柔光漂移（配色随节奏切换，形成流光）
        glows_now = self.bg_glow_sets[int(self.t / 3.2) % 2]
        for gi, g in enumerate(glows_now):
            a_ = self.t * (0.18 + 0.05 * gi)
            gx = (CX + math.cos(a_ + gi * 1.05) * (VW * 0.34)) - 260
            gy = (CY + math.sin(a_ * 0.8 + gi * 0.9) * (VH * 0.30)) - 260
            surf.blit(g, (int(gx), int(gy)), special_flags=pygame.BLEND_RGB_ADD)
        # 背景呼吸星
        tt = self.t
        star_cols = ((150, 170, 255), (255, 190, 230), (200, 240, 255))
        for bx_, by_, br_, bp_, bs_, bc_ in self.bg_stars:
            a_ = 0.35 + 0.65 * abs(math.sin(tt * bs_ + bp_))
            col = star_cols[bc_]
            c = (int(col[0] * a_), int(col[1] * a_), int(col[2] * a_))
            pygame.draw.circle(surf, c, (int(bx_), int(by_)), int(br_))

        # 背景漂浮小爱心（缓慢移动 + 尺寸脉动变换）
        tt2 = self.t
        for fx, fy, famp, fsp, fph, fci, fs in self.bg_fhearts:
            n = len(self.small_hearts)
            k_ = (fs * 5 + fci + int((tt2 * 0.45 + fph) % 3) * 5) % n
            spr_ = self.small_hearts[k_]
            w_ = spr_.get_width()
            px2 = fx + math.sin(tt2 * fsp + fph) * famp
            py2 = fy + math.cos(tt2 * fsp * 0.8 + fph) * famp * 0.7
            surf.blit(spr_, (int(px2) - w_ // 2, int(py2) - w_ // 2),
                      special_flags=pygame.BLEND_RGBA_ADD)

        # 背景流光粒子（彩色小光点缓慢漂移）
        glow_min = self.sprites[0][0]
        for gx, gy, gvx, gvy, gph, gci, gsp in self.bg_flow:
            a_ = 0.35 + 0.65 * abs(math.sin(tt2 * gsp + gph))
            spr_ = glow_min[gci][2 if a_ > 0.6 else 1]
            w_ = spr_.get_width()
            surf.blit(spr_, (int(gx) - w_ // 2, int(gy) - w_ // 2),
                      special_flags=pygame.BLEND_RGB_ADD)

        pal = self.sprites[self.pal]
        add = pygame.BLEND_RGBA_ADD
        adder = pygame.BLEND_RGB_ADD
        parts = self.parts
        order = self.order
        dim = self.dim_cols[self.pal]
        draw_line = pygame.draw.line

        # 结构光丝：把相邻结构粒子连成发光线条
        lcols = self.line_cols[self.pal]
        parts = self.parts
        prev_xy = None
        prev_ci = 0
        flow_l = self.t * 1.30
        limit = 56.0 * 56.0
        wires = False
        for idx in (self.struct_idx if wires else ()):
            p = parts[idx]
            px_, py_ = p.x, p.y
            if prev_xy is not None:
                ddx = px_ - prev_xy[0]
                ddy = py_ - prev_xy[1]
                if ddx * ddx + ddy * ddy < limit:
                    draw_line(surf, lcols[prev_ci],
                              (int(prev_xy[0]), int(prev_xy[1])),
                              (int(px_), int(py_)), 2)
            prev_xy = (px_, py_)
            prev_ci = int(((p.ph * 0.3183 + flow_l) % 1.0) * 7.999)

        flow = self.t * 1.75
        for i in order:
            p = parts[i]
            x = p.x
            y = p.y
            if x < -30 or x > VW + 30 or y < -30 or y > VH + 30:
                continue
            # 明暗直接决定色阶：深玫红 → 粉 → 白高光（同一色系，不杂）
            ci_d = 1 + int(p.spin) * 2 + int(
                ((p.x * 0.0016 + p.y * 0.0012 + flow * 0.6) % 1.0) * 1.999)
            if ci_d > 7:
                ci_d = 7
            sp = p.vx * p.vx + p.vy * p.vy
            if sp > 45.0:
                tl = 0.05 if sp < 400.0 else 0.10
                draw_line(surf, dim[ci_d], (int(x), int(y)),
                          (int(x - p.vx * tl), int(y - p.vy * tl)), 1)
            spr = pal[int(p.size)][ci_d][int(p.spin)]
            w = spr.get_width()
            surf.blit(spr, (int(x) - w // 2, int(y) - w // 2), special_flags=adder)

        # 火花
        for s in self.sparks:
            a = max(0.0, min(1.0, s.life))
            ci = s.ci
            spr = pal[s.size][ci][3 if a > 0.5 else 2]
            w = spr.get_width()
            surf.blit(spr, (int(s.x) - w // 2, int(s.y) - w // 2), special_flags=adder)

        # 冲击波环
        for w in self.waves:
            wx, wy, wt, _s = w
            r = int(wt * 760.0)
            if r < 4 or r > 1500:
                continue
            k = max(0.0, 1.0 - wt / 1.5)
            base = self.ring[0] if wt < 0.7 else self.ring[1]
            crop_r = int(r)
            if crop_r < 26:
                continue
            ring = pygame.transform.smoothscale(base, (crop_r * 2, crop_r * 2))
            ring.set_alpha(int(150 * k))
            surf.blit(ring, (int(wx - crop_r), int(wy - crop_r)), special_flags=add)

        # 光标光晕
        if self.has_mouse:
            halo = self.halo[self.pal][(int(self.t * 3) % 8)]
            w = halo.get_width()
            surf.blit(halo, (int(self.mx) - w // 2, int(self.my) - w // 2),
                      special_flags=adder)
            if self.hold:
                h2 = self.halo[self.pal][3]
                w2 = h2.get_width()
                surf.blit(h2, (int(self.mx) - w2 // 2, int(self.my) - w2 // 2),
                          special_flags=adder)

        # 泛光（缩小再放大叠加两次，形成柔和光雾）
        bloom = pygame.transform.smoothscale(surf, (VW // 4, VH // 4))
        bloom = pygame.transform.smoothscale(bloom, (VW, VH))
        bloom.fill((44, 38, 46), special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(bloom, (0, 0), special_flags=adder)

        self.present()

    def present(self):
        win = self.win
        ww, wh = win.get_size()
        if ww == VW and wh == VH:
            win.blit(self.virt, (0, 0))
        else:
            pygame.transform.smoothscale(self.virt, (ww, wh), win)
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            if dt > 0.05:
                dt = 0.05
            for ev in pygame.event.get():
                if not self.on_event(ev):
                    running = False
            self.update(dt)
            self.render()

    def snapshot(self, path, frames=240, at=None):
        """无头渲染若干帧后截图，便于检查画面"""
        steps = frames if at is None else frames
        for _ in range(steps):
            self.update(1.0 / FPS)
        self.render()
        pygame.image.save(self.virt, path)

    def teleport(self, shape_idx):
        self.shape_a = shape_idx
        self.shape_b = (shape_idx + 1) % len(self.shapes)
        self.morphing = False
        self.morph = 1.0
        self.hold_t = 999.0
        x, y, z = self.shapes[shape_idx]
        for i, p in enumerate(self.parts):
            p.x = x[i] + CX
            p.y = y[i] + CY
            p.z = z[i]
            p.vx = p.vy = p.vz = 0.0


def main():
    app = App()
    app.run()
    pygame.quit()


if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        out = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "snap.png"
        frames = 200
        if "--frames" in sys.argv:
            frames = int(sys.argv[sys.argv.index("--frames") + 1])
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        app = App()
        app.has_mouse = True
        app.mx, app.my = 1268.0, 884.0
        if "--shape" in sys.argv:
            app.teleport(int(sys.argv[sys.argv.index("--shape") + 1]))
        app.snapshot(out, frames)
        pygame.quit()
        print(out)
    else:
        main()










