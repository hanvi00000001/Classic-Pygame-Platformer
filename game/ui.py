"""HUD, menus, banners and screen transitions."""
import math

import pygame as pg

from . import font
from .entities import draw_heart
from .fx import glow, lerp_color
from .settings import VIEW_W, VIEW_H

INK = (20, 16, 32)
GOLD = (255, 214, 90)
PALE = (236, 232, 255)
ACCENT = (214, 66, 98)


def panel(surf, rect, alpha=200, border=(255, 255, 255)):
    r = pg.Rect(rect)
    s = pg.Surface(r.size, pg.SRCALPHA)
    s.fill((14, 10, 28, alpha))
    surf.blit(s, r.topleft)
    pg.draw.rect(surf, lerp_color(border, (14, 10, 28), 0.55), r, 1)
    for cx, cy in (r.topleft, (r.right - 1, r.top), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1)):
        surf.set_at((cx, cy), (14, 10, 28))


def draw_coin_icon(surf, x, y, t):
    w = max(2, int(abs(math.cos(t * 0.06)) * 7))
    r = pg.Rect(x + 3 - w // 2, y, w, 8)
    pg.draw.ellipse(surf, (196, 128, 24), r)
    if w > 3:
        pg.draw.ellipse(surf, (255, 206, 60), r.inflate(-2, -2))


def draw_star_icon(surf, cx, cy, filled, t=0):
    pts = []
    for i in range(10):
        r = 5 if i % 2 == 0 else 2.2
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    if filled:
        pg.draw.polygon(surf, (180, 140, 255), pts)
        pg.draw.polygon(surf, (240, 225, 255), [(cx + (x - cx) * 0.5, cy + (y - cy) * 0.5) for x, y in pts])
    else:
        pg.draw.polygon(surf, (70, 60, 100), pts, 1)


def hud(surf, scene):
    p = scene.player
    t = scene.t
    # hearts
    for i in range(p.max_hearts):
        full = i < p.hearts
        k = 1.0
        if full and p.hearts == 1:
            k = 1 + 0.18 * max(0, math.sin(t * 0.18)) ** 6
        draw_heart(surf, 12 + i * 11, 12, k, full)
    x = 10 + p.max_hearts * 11 + 4
    # power icons
    icons = []
    if p.fire:
        icons.append(((255, 140, 40), "F"))
    if p.feather:
        icons.append(((240, 240, 255), "2J"))
    if p.shield:
        icons.append(((120, 220, 255), "S"))
    for col, label in icons:
        pg.draw.circle(surf, lerp_color(col, (0, 0, 0), 0.5), (x + 5, 12), 6)
        pg.draw.circle(surf, col, (x + 5, 12), 6, 1)
        font.draw(surf, label, (x + 5, 9), col, shadow=None, align="center")
        x += 15
    # dash pip
    dash_col = (214, 66, 98) if p.dash_ready else (90, 90, 110)
    pg.draw.rect(surf, dash_col, (10, 22, 22, 3))
    font.draw(surf, "DASH", (35, 21), dash_col, shadow=INK)
    # coins + score
    draw_coin_icon(surf, 10, 30, t)
    font.draw(surf, f"x{scene.stats['coins']:03d}", (20, 31), GOLD, outline=INK)
    # star shards
    for i in range(3):
        draw_star_icon(surf, VIEW_W - 50 + i * 13, 12, i in scene.gems_found, t)
    # timer
    secs = scene.stats["time"] / 60
    font.draw(surf, f"{int(secs // 60)}:{int(secs % 60):02d}", (VIEW_W - 10, 22), PALE, outline=INK, align="right")
    font.draw(surf, f"{scene.stats['score']:06d}", (VIEW_W // 2, 6), PALE, outline=INK, align="center")


def boss_bar(surf, boss, t, appear):
    w = int(220 * appear)
    if w < 4:
        return
    x = VIEW_W // 2 - w // 2
    y = VIEW_H - 22
    panel(surf, (x - 4, y - 12, w + 8, 22), 200, (255, 120, 60))
    font.draw(surf, boss.name, (VIEW_W // 2, y - 9), (255, 200, 140), outline=INK, align="center")
    surf.fill((50, 20, 20), (x, y, w, 5))
    k = max(0, boss.hp) / boss.max_hp
    fill = int(w * k)
    col = (255, 90, 40) if (t // 6) % 2 or not boss.hit_flash else (255, 255, 255)
    surf.fill(col, (x, y, fill, 5))
    surf.fill((255, 200, 120), (x, y, fill, 1))


class Iris:
    """Circular wipe transition. closing: 0->1 covers the screen."""

    def __init__(self):
        self.k = 0.0
        self.target = 0.0
        self.speed = 0.05
        self.cx, self.cy = VIEW_W // 2, VIEW_H // 2
        self.done_cb = None
        self.surf = pg.Surface((VIEW_W, VIEW_H))
        self.surf.set_colorkey((255, 0, 255))

    def close(self, cb=None, center=None, speed=0.05):
        self.target = 1.0
        self.done_cb = cb
        self.speed = speed
        if center:
            self.cx, self.cy = center

    def open(self, center=None, speed=0.05):
        self.target = 0.0
        self.speed = speed
        if center:
            self.cx, self.cy = center

    @property
    def busy(self):
        return abs(self.k - self.target) > 1e-3

    def update(self):
        if self.k < self.target:
            self.k = min(self.target, self.k + self.speed)
            if self.k >= self.target and self.done_cb:
                cb, self.done_cb = self.done_cb, None
                cb()
        elif self.k > self.target:
            self.k = max(self.target, self.k - self.speed)

    def draw(self, surf):
        if self.k <= 0:
            return
        maxr = math.hypot(max(self.cx, VIEW_W - self.cx), max(self.cy, VIEW_H - self.cy)) + 4
        r = int(maxr * (1 - self.k) ** 1.6)
        self.surf.fill((8, 6, 16))
        if r > 0:
            pg.draw.circle(self.surf, (255, 0, 255), (int(self.cx), int(self.cy)), r)
            pg.draw.circle(self.surf, (214, 66, 98), (int(self.cx), int(self.cy)), r + 2, 2)
        surf.blit(self.surf, (0, 0))


class Menu:
    def __init__(self, items, y, spacing=14, scale=1):
        self.items = items  # list of (label, callback)
        self.index = 0
        self.y = y
        self.spacing = spacing
        self.scale = scale
        self.t = 0

    def update(self, inp, sound):
        self.t += 1
        if inp.pressed("up"):
            self.index = (self.index - 1) % len(self.items)
            sound("blip")
        if inp.pressed("down"):
            self.index = (self.index + 1) % len(self.items)
            sound("blip")
        if inp.pressed("confirm") or inp.pressed("jump"):
            sound("confirm")
            label, cb = self.items[self.index]
            inp.consume("confirm")
            inp.consume("jump")
            cb()

    def draw(self, surf, cx=VIEW_W // 2):
        for i, (label, _) in enumerate(self.items):
            label = label() if callable(label) else label
            y = self.y + i * self.spacing
            sel = i == self.index
            col = PALE if sel else (140, 132, 170)
            if sel:
                w = font.text_width(label, self.scale)
                off = int(math.sin(self.t * 0.15) * 2)
                font.draw(surf, ">", (cx - w // 2 - 10 - off, y), ACCENT, self.scale, outline=INK)
                font.draw(surf, "<", (cx + w // 2 + 5 + off, y), ACCENT, self.scale, outline=INK)
            font.draw(surf, label, (cx, y), col, self.scale, outline=INK, align="center")


def vignette(strength=0.55):
    s = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
    cx, cy = VIEW_W / 2, VIEW_H / 2
    maxd = math.hypot(cx, cy)
    step = 3
    for y in range(0, VIEW_H, step):
        for x in range(0, VIEW_W, step):
            d = math.hypot((x - cx) / cx, (y - cy) / cy * 0.9)
            a = max(0.0, d - 0.55) / 0.75
            a = min(1.0, a) ** 1.6 * strength
            if a > 0.01:
                s.fill((6, 4, 14, int(255 * a)), (x, y, step, step))
    return s
