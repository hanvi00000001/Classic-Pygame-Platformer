"""Particles, glow sprites, floating text and other juice."""
import math
import random

import pygame as pg

from . import font

_glow_cache = {}


def glow(radius, color, strength=1.0):
    """Soft radial gradient for additive blending (light, bloom)."""
    key = (int(radius), tuple(color), round(strength, 2))
    s = _glow_cache.get(key)
    if s is not None:
        return s
    r = max(1, int(radius))
    s = pg.Surface((r * 2, r * 2))
    s.fill((0, 0, 0))
    steps = min(r, 96)
    for i in range(steps, 0, -1):
        f = i / steps
        k = (1 - f) ** 1.8 * strength
        c = tuple(min(255, int(ch * k)) for ch in color)
        pg.draw.circle(s, c, (r, r), int(r * f))
    _glow_cache[key] = s
    return s


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "color2", "size", "grav",
                 "drag", "kind", "glow", "spin", "angle", "shrink")

    def __init__(self, x, y, vx, vy, life, color, size=1, grav=0.0, drag=0.98, kind="px",
                 glow=0, color2=None, shrink=True):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color = color
        self.color2 = color2
        self.size = size
        self.grav = grav
        self.drag = drag
        self.kind = kind
        self.glow = glow
        self.spin = random.uniform(-0.3, 0.3)
        self.angle = random.uniform(0, 6.28)
        self.shrink = shrink


def lerp_color(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


class Particles:
    def __init__(self):
        self.items = []
        self.texts = []
        self.rings = []

    def add(self, *a, **k):
        if len(self.items) < 1600:
            self.items.append(Particle(*a, **k))

    # -- presets -----------------------------------------------------------
    def burst(self, x, y, n, color, speed=2.0, life=30, size=2, grav=0.12, glow=0, color2=None,
              kind="px", spread=math.tau, angle=0.0, drag=0.96):
        for _ in range(n):
            a = angle + random.uniform(-spread / 2, spread / 2)
            sp = random.uniform(speed * 0.3, speed)
            self.add(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(life // 2, life), color,
                     size=random.choice((size, max(1, size - 1))), grav=grav, glow=glow, color2=color2,
                     kind=kind, drag=drag)

    def dust(self, x, y, n=5, color=(230, 220, 200), direction=0):
        for _ in range(n):
            self.add(x + random.uniform(-4, 4), y - random.uniform(0, 2),
                     random.uniform(-0.8, 0.8) + direction * random.uniform(0.2, 1.0),
                     random.uniform(-0.9, -0.1), random.randint(14, 26), color, size=random.choice((1, 2, 2, 3)),
                     grav=-0.01, drag=0.92, kind="puff")

    def sparkle(self, x, y, color=(255, 240, 150), n=6):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(0.4, 1.8)
            self.add(x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(18, 34), color,
                     size=1, grav=0, drag=0.93, kind="star", glow=6)

    def ring(self, x, y, color, radius=24, life=18, width=2):
        self.rings.append([x, y, 0.0, radius, life, life, color, width])

    def text(self, x, y, s, color=(255, 255, 255), life=50):
        self.texts.append([x, y, s, color, life, life])

    # -- update / draw -----------------------------------------------------
    def update(self):
        alive = []
        for p in self.items:
            p.vy += p.grav
            p.vx *= p.drag
            p.vy *= p.drag
            p.x += p.vx
            p.y += p.vy
            p.angle += p.spin
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.items = alive
        for t in self.texts:
            t[1] -= 0.45
            t[4] -= 1
        self.texts = [t for t in self.texts if t[4] > 0]
        for r in self.rings:
            r[4] -= 1
            k = 1 - r[4] / r[5]
            r[2] = r[3] * (1 - (1 - k) ** 3)
        self.rings = [r for r in self.rings if r[4] > 0]

    def draw(self, surf, cam, glow_surf=None):
        ox, oy = cam
        for p in self.items:
            t = p.life / p.max_life
            col = lerp_color(p.color2, p.color, t) if p.color2 else p.color
            x, y = int(p.x - ox), int(p.y - oy)
            size = max(1, round(p.size * (t if p.shrink else 1) + 0.4)) if p.kind != "px" else p.size
            if p.kind == "puff":
                pg.draw.circle(surf, col, (x, y), max(1, int(p.size * (0.4 + t * 0.8))))
            elif p.kind == "star":
                if t > 0.15 or (p.life // 2) % 2:
                    surf.fill(col, (x, y, 1, 1))
                    if t > 0.5:
                        surf.fill(col, (x - 1, y, 3, 1))
                        surf.fill(col, (x, y - 1, 1, 3))
            elif p.kind == "line":
                pg.draw.line(surf, col, (x, y), (int(x - p.vx * 3), int(y - p.vy * 3)))
            elif p.kind == "chunk":
                s = p.size
                c, sn = math.cos(p.angle), math.sin(p.angle)
                pts = [(x + c * s - sn * s, y + sn * s + c * s), (x - c * s - sn * s, y - sn * s + c * s),
                       (x - c * s + sn * s, y - sn * s - c * s), (x + c * s + sn * s, y + sn * s - c * s)]
                pg.draw.polygon(surf, col, pts)
            else:
                surf.fill(col, (x - size // 2, y - size // 2, size, size))
            if p.glow and glow_surf is not None:
                g = glow(max(2, int(p.glow * (0.4 + t * 0.6))), col, 0.7)
                glow_surf.blit(g, (x - g.get_width() // 2, y - g.get_height() // 2), special_flags=pg.BLEND_ADD)
        for r in self.rings:
            k = r[4] / r[5]
            if r[2] >= 1:
                pg.draw.circle(surf, lerp_color((0, 0, 0), r[6], min(1, k * 1.5)), (int(r[0] - ox), int(r[1] - oy)),
                               int(r[2]), max(1, int(r[7] * k + 0.5)))

    def draw_texts(self, surf, cam):
        ox, oy = cam
        for x, y, s, col, life, ml in self.texts:
            if life < 12 and life % 2 == 0:
                continue
            pop = 1 if ml - life > 4 else 0
            font.draw(surf, s, (int(x - ox), int(y - oy) - pop), col, outline=(20, 16, 30), align="center")


class Shaker:
    def __init__(self):
        self.trauma = 0.0
        self.t = 0

    def add(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self):
        self.t += 1
        self.trauma = max(0.0, self.trauma - 0.035)

    def offset(self):
        s = self.trauma ** 2 * 7
        if s < 0.2:
            return 0, 0
        return (math.sin(self.t * 1.7) * s + random.uniform(-0.5, 0.5) * s,
                math.cos(self.t * 2.3) * s + random.uniform(-0.5, 0.5) * s)
