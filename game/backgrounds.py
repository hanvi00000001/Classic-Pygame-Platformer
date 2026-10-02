"""Procedural parallax backdrops and weather for each biome."""
import math
import os
import random

import pygame as pg

from .settings import VIEW_W, VIEW_H, LEGACY_DIR
from .fx import glow, lerp_color

LW = 960  # width of a wrapping parallax strip


def _gradient(colors, w, h):
    s = pg.Surface((w, h))
    n = len(colors) - 1
    for y in range(h):
        t = y / (h - 1) * n
        i = min(n - 1, int(t))
        s.fill(lerp_color(colors[i], colors[i + 1], t - i), (0, y, w, 1))
    return s


def _ridge(rng, w, base, amp, rough=0.55, octaves=7):
    """1D midpoint displacement that wraps seamlessly."""
    n = 2 ** octaves
    pts = [0.0] * (n + 1)
    step, scale = n, amp
    while step > 1:
        half = step // 2
        for i in range(half, n, step):
            pts[i] = (pts[i - half] + pts[i + half]) / 2 + rng.uniform(-scale, scale)
        step = half
        scale *= rough
    return [(i * w / n, base + pts[i]) for i in range(n + 1)]


def _fill_poly(surf, ridge, color, h):
    pg.draw.polygon(surf, color, ridge + [(ridge[-1][0], h), (ridge[0][0], h)])


def _snowcaps(surf, ridge, line, snow, shade):
    """Paint snow on every part of a ridge above `line`, with a ragged lower edge."""
    for i in range(len(ridge) - 1):
        (x0, y0), (x1, y1) = ridge[i], ridge[i + 1]
        for x in range(int(x0), int(x1) + 1):
            t = (x - x0) / max(1e-6, x1 - x0)
            y = y0 + (y1 - y0) * t
            depth = line - y
            if depth <= 0:
                continue
            h = min(depth, 4 + depth * 0.45 + ((x * 7) % 5))
            pg.draw.line(surf, snow, (x, y), (x, y + h))
            surf.set_at((x, int(y + h)), shade)


def _pine(surf, x, ground, height, color, hi=None):
    w = height * 0.42
    for i in range(4):
        t = i / 4
        y0 = ground - height + t * height * 0.75
        ww = w * (0.35 + t * 0.65)
        pg.draw.polygon(surf, color, [(x, y0), (x - ww, y0 + height * 0.32), (x + ww, y0 + height * 0.32)])
        if hi:
            pg.draw.line(surf, hi, (x - ww + 1, y0 + height * 0.32 - 1), (x - ww * 0.3, y0 + height * 0.32 - 1))
    surf.fill(color, (x - 1, ground - height * 0.2, 3, height * 0.2))


def _round_tree(surf, x, ground, r, color, hi):
    surf.fill(lerp_color(color, (0, 0, 0), 0.2), (x - 1, ground - r, 3, r))
    for dx, dy, rr in ((0, -r * 1.6, r), (-r * 0.6, -r * 1.2, r * 0.7), (r * 0.6, -r * 1.2, r * 0.75)):
        pg.draw.circle(surf, color, (int(x + dx), int(ground + dy)), int(rr))
    pg.draw.circle(surf, hi, (int(x - r * 0.3), int(ground - r * 1.9)), int(r * 0.35))


class Layer:
    def __init__(self, surf, factor, y_factor=0.1):
        self.surf = surf
        self.factor = factor
        self.y_factor = y_factor


class Background:
    def __init__(self, theme_name, theme, level_h_px, seed=1):
        self.name = theme_name
        self.th = theme
        self.level_h = level_h_px
        rng = random.Random(seed)
        self.sky = _gradient(theme["sky"], VIEW_W, VIEW_H)
        self.layers = []
        self.clouds = []
        self.stars = []
        self.t = 0
        builder = getattr(self, "_build_" + theme_name, self._build_meadow)
        builder(rng)
        if theme.get("clouds"):
            for i in range(9):
                self.clouds.append([rng.uniform(0, LW), rng.uniform(10, 120), rng.uniform(0.05, 0.25),
                                    self._cloud(rng), rng.uniform(0.02, 0.08)])
        self.weather = Weather(theme.get("weather"), rng)

    # ---- builders --------------------------------------------------------
    def _strip(self):
        return pg.Surface((LW, VIEW_H), pg.SRCALPHA)

    def _cloud(self, rng):
        w = rng.randint(40, 90)
        s = pg.Surface((w + 20, 40), pg.SRCALPHA)
        base = (255, 255, 255) if self.name != "sunset" else (255, 200, 190)
        shade = lerp_color(base, self.th["sky"][1], 0.45)
        for _ in range(7):
            cx = rng.randint(14, w + 4)
            cy = rng.randint(16, 24)
            r = rng.randint(7, 13)
            pg.draw.circle(s, shade, (cx, cy + 3), r)
        for _ in range(7):
            cx = rng.randint(14, w + 4)
            cy = rng.randint(14, 22)
            r = rng.randint(6, 11)
            pg.draw.circle(s, base, (cx, cy), r)
        s.fill((0, 0, 0, 0), (0, 28, w + 20, 12))
        s.fill(shade, (8, 27, w + 4, 1))
        return s

    def _build_meadow(self, rng):
        th = self.th
        far = self._strip()
        r = _ridge(rng, LW, 150, 70)
        _fill_poly(far, r, th["far"], VIEW_H)
        _snowcaps(far, r, 112, (236, 244, 255), lerp_color(th["far"], (255, 255, 255), 0.45))
        haze = _gradient([(0, 0, 0), th["sky"][2]], LW, 60)
        far.blit(haze, (0, 170), special_flags=pg.BLEND_RGB_ADD)
        self.layers.append(Layer(far, 0.12, 0.03))
        mid = self._strip()
        hill = [(x, 190 + math.sin(x / LW * math.tau * 3) * 18 + math.sin(x / LW * math.tau * 7) * 6) for x in range(0, LW + 1, 8)]
        _fill_poly(mid, hill, th["mid"], VIEW_H)
        for i in range(36):
            x = rng.uniform(0, LW)
            y = 190 + math.sin(x / LW * math.tau * 3) * 18 + math.sin(x / LW * math.tau * 7) * 6
            _round_tree(mid, x, y + 4, rng.randint(6, 10), lerp_color(th["mid"], (0, 40, 20), 0.3),
                        lerp_color(th["mid"], (255, 255, 200), 0.25))
        self.layers.append(Layer(mid, 0.3, 0.06))
        near = self._strip()
        hill = [(x, 228 + math.sin(x / LW * math.tau * 4 + 1) * 10) for x in range(0, LW + 1, 8)]
        _fill_poly(near, hill, th["near"], VIEW_H)
        for i in range(30):
            x = rng.uniform(0, LW)
            _pine(near, x, 232 + math.sin(x / LW * math.tau * 4 + 1) * 10, rng.randint(26, 46),
                  lerp_color(th["near"], (0, 0, 0), 0.15), lerp_color(th["near"], (200, 255, 200), 0.2))
        self.layers.append(Layer(near, 0.5, 0.1))
        if th.get("legacy_bg"):
            self._legacy_layers()

    _build_legacy = _build_meadow

    def _legacy_layers(self):
        """The 2022 parallax images, finally used in-game."""
        try:
            self.layers = []
            folder = os.path.join(LEGACY_DIR, "img", "background")
            k = VIEW_H / 640 * 1.25
            names = [("sky_cloud.png", 0.1, 0), ("mountain.png", 0.2, 300), ("pine1.png", 0.35, 150), ("pine2.png", 0.5, 0)]
            for name, f, off in names:
                img = pg.image.load(os.path.join(folder, name)).convert_alpha()
                img = pg.transform.scale(img, (int(img.get_width() * k), int(img.get_height() * k)))
                strip = pg.Surface((img.get_width(), VIEW_H), pg.SRCALPHA)
                y = 0 if name == "sky_cloud.png" else VIEW_H - img.get_height() - int(off * k * 0.6)
                strip.blit(img, (0, y))
                if name == "pine2.png":
                    strip.fill((40, 66, 58), (0, y + img.get_height() - 2, strip.get_width(), VIEW_H))
                self.layers.append(Layer(strip, f, 0.05))
            self.sky = _gradient([(150, 200, 230), (190, 220, 240)], VIEW_W, VIEW_H)
        except (pg.error, FileNotFoundError):
            pass

    def _build_caves(self, rng):
        th = self.th
        for depth, (col, f, n) in enumerate(((th["far"], 0.15, 18), (th["mid"], 0.3, 14), (th["near"], 0.5, 10))):
            s = self._strip()
            # stalactites from the top, stalagmites from the bottom
            top = _ridge(rng, LW, 20 + depth * 8, 18)
            pg.draw.polygon(s, col, [(0, 0)] + top + [(LW, 0)])
            for _ in range(n):
                x = rng.uniform(0, LW)
                w = rng.uniform(8, 22)
                h = rng.uniform(30, 90)
                pg.draw.polygon(s, col, [(x - w, 0), (x + w, 0), (x, h)])
                x = rng.uniform(0, LW)
                h = rng.uniform(30, 110 - depth * 20)
                pg.draw.polygon(s, col, [(x - w, VIEW_H), (x + w, VIEW_H), (x, VIEW_H - h)])
            bot = _ridge(rng, LW, VIEW_H - 40 + depth * 10, 16)
            _fill_poly(s, bot, col, VIEW_H)
            for _ in range(10 - depth * 2):
                x, y = rng.uniform(0, LW), rng.uniform(40, VIEW_H - 40)
                c = rng.choice([(70, 200, 190), (150, 110, 230), (90, 150, 230)])
                c = lerp_color(c, col, 0.55 - depth * 0.12)
                pg.draw.polygon(s, c, [(x - 2, y), (x, y - rng.randint(4, 9)), (x + 2, y)])
            self.layers.append(Layer(s, f, 0.08 + depth * 0.04))
        self.motes = [[rng.uniform(0, VIEW_W), rng.uniform(0, VIEW_H), rng.uniform(0, 6.28)] for _ in range(26)]

    def _build_sunset(self, rng):
        th = self.th
        self.sun_pos = (VIEW_W * 0.68, 150)
        far = self._strip()
        # mesas
        x = 0
        while x < LW:
            w = rng.randint(50, 130)
            h = rng.randint(40, 110)
            top = VIEW_H - 60 - h
            pg.draw.polygon(far, th["far"], [(x, VIEW_H), (x + 8, top + 6), (x + 14, top), (x + w - 14, top),
                                              (x + w - 8, top + 6), (x + w, VIEW_H)])
            far.fill(lerp_color(th["far"], th["sky"][2], 0.25), (x + 14, top, w - 28, 2))
            x += w + rng.randint(10, 60)
        self.layers.append(Layer(far, 0.12, 0.03))
        mid = self._strip()
        r = _ridge(rng, LW, 200, 30)
        _fill_poly(mid, r, th["mid"], VIEW_H)
        for i in range(5):  # ruined arches
            ax = rng.uniform(40, LW - 40)
            ay = 200
            col = lerp_color(th["mid"], (0, 0, 0), 0.15)
            mid.fill(col, (ax - 22, ay - 50, 8, 60))
            mid.fill(col, (ax + 14, ay - 50, 8, 60))
            pg.draw.arc(mid, col, (ax - 22, ay - 72, 44, 44), 0, math.pi, 8)
        self.layers.append(Layer(mid, 0.3, 0.06))
        near = self._strip()
        r = _ridge(rng, LW, 236, 14)
        _fill_poly(near, r, th["near"], VIEW_H)
        for _ in range(16):
            x = rng.uniform(0, LW)
            y = 236
            pg.draw.line(near, th["near"], (x, y), (x + rng.uniform(-3, 3), y - rng.randint(20, 40)), 2)
            for k in range(4):
                a = rng.uniform(-2.6, -0.5)
                l = rng.randint(8, 16)
                pg.draw.line(near, th["near"], (x, y - 30), (x + math.cos(a) * l, y - 30 + math.sin(a) * l), 2)
        self.layers.append(Layer(near, 0.5, 0.1))

    def _build_frost(self, rng):
        th = self.th
        self.stars = [(rng.uniform(0, VIEW_W), rng.uniform(0, VIEW_H * 0.7), rng.random()) for _ in range(120)]
        far = self._strip()
        r = _ridge(rng, LW, 140, 80, 0.6)
        _fill_poly(far, r, th["far"], VIEW_H)
        _snowcaps(far, r, 112, (210, 226, 252), lerp_color(th["far"], (255, 255, 255), 0.3))
        self.layers.append(Layer(far, 0.1, 0.03))
        for col, f, base, n, hgt in ((th["mid"], 0.28, 210, 40, (30, 56)), (th["near"], 0.5, 240, 28, (44, 70))):
            s = self._strip()
            r = _ridge(rng, LW, base, 12)
            _fill_poly(s, r, col, VIEW_H)
            for _ in range(n):
                x = rng.uniform(0, LW)
                _pine(s, x, base + 6, rng.randint(*hgt), col, (220, 236, 255))
            self.layers.append(Layer(s, f, 0.07))

    def _build_volcano(self, rng):
        th = self.th
        far = self._strip()
        cx = LW * 0.5
        pg.draw.polygon(far, th["far"], [(cx - 260, VIEW_H), (cx - 40, 70), (cx + 40, 70), (cx + 260, VIEW_H)])
        for i in range(6):  # lava rivers
            x0 = cx + rng.uniform(-30, 30)
            pts = [(x0, 72)]
            y = 72
            x = x0
            while y < VIEW_H:
                y += rng.randint(8, 18)
                x += rng.uniform(-10, 10) + (x - cx) * 0.1
                pts.append((x, y))
            pg.draw.lines(far, (255, 120, 30), False, pts, 2)
        r = _ridge(rng, LW, 210, 40)
        _fill_poly(far, r, lerp_color(th["far"], (0, 0, 0), 0.3), VIEW_H)
        self.volcano_x = cx
        self.layers.append(Layer(far, 0.1, 0.03))
        for col, f, base in ((th["mid"], 0.3, 200), (th["near"], 0.5, 236)):
            s = self._strip()
            r = _ridge(rng, LW, base, 26, 0.65)
            _fill_poly(s, r, col, VIEW_H)
            for _ in range(8):  # jagged spires
                x = rng.uniform(0, LW)
                h = rng.randint(30, 70)
                pg.draw.polygon(s, col, [(x - 8, base + 10), (x - 2, base - h), (x + 3, base - h + 10), (x + 9, base + 10)])
            self.layers.append(Layer(s, f, 0.07))

    # ---- frame -----------------------------------------------------------
    def update(self):
        self.t += 1
        for c in self.clouds:
            c[0] = (c[0] + c[4]) % LW
        self.weather.update()

    def draw(self, surf, cam_x, cam_y, glow_surf):
        t = self.t / 60
        surf.blit(self.sky, (0, 0))
        th = self.th
        if self.stars:
            for x, y, k in self.stars:
                b = 0.5 + 0.5 * math.sin(t * (1 + k * 3) + k * 40)
                c = int(120 + 135 * b * k)
                surf.set_at((int(x), int(y)), (c, c, min(255, c + 20)))
        if th.get("aurora"):
            self._aurora(surf, glow_surf, t)
        if self.name in ("meadow",) and th.get("sun"):
            g = glow(70, (120, 110, 60))
            glow_surf.blit(g, (VIEW_W - 120 - 70, 50 - 70), special_flags=pg.BLEND_ADD)
            pg.draw.circle(surf, th["sun"], (VIEW_W - 120, 50), 16)
        if self.name == "sunset":
            sx, sy = self.sun_pos
            g = glow(140, (150, 80, 40))
            glow_surf.blit(g, (sx - 140, sy - 140), special_flags=pg.BLEND_ADD)
            pg.draw.circle(surf, (255, 220, 140), (int(sx), int(sy)), 36)
            for i in range(5):
                surf.fill(th["sky"][2], (sx - 40, sy + 6 + i * 6, 80, 1 + i // 2))
        if self.name == "frost":
            pg.draw.circle(surf, (230, 236, 255), (90, 56), 13)
            pg.draw.circle(surf, th["sky"][0], (96, 52), 11)
            g = glow(50, (50, 60, 90))
            glow_surf.blit(g, (90 - 50, 56 - 50), special_flags=pg.BLEND_ADD)
        for c in self.clouds:
            x = (c[0] - cam_x * c[2]) % LW - 60
            img = c[3]
            for k in (0, LW):
                xx = x + k - LW if x + k > VIEW_W + LW / 2 else x + k
                if -img.get_width() < xx < VIEW_W:
                    surf.blit(img, (xx, c[1] - cam_y * 0.03))
        ground_anchor = max(0, self.level_h - VIEW_H)
        for L in self.layers:
            w = L.surf.get_width()
            off = -(cam_x * L.factor) % w
            dy = (ground_anchor - cam_y) * L.y_factor
            x = off - w
            while x < VIEW_W:
                surf.blit(L.surf, (x, dy))
                x += w
            if dy > 0:
                # extend the strip's bottom colour when the camera is above the floor
                pass
            if self.name == "volcano" and L is self.layers[0]:
                vx = (self.volcano_x - cam_x * L.factor) % w
                for xx in (vx, vx - w, vx + w):
                    if -100 < xx < VIEW_W + 100:
                        g = glow(60 + 6 * math.sin(t * 2), (160, 50, 10))
                        glow_surf.blit(g, (xx - g.get_width() // 2, 72 + dy - g.get_height() // 2), special_flags=pg.BLEND_ADD)
        if self.name == "caves":
            for m in self.motes:
                m[2] += 0.02
                x = (m[0] - cam_x * 0.2 + math.sin(m[2]) * 6) % VIEW_W
                y = (m[1] - cam_y * 0.1 + math.cos(m[2] * 0.7) * 4) % VIEW_H
                surf.set_at((int(x), int(y)), (120, 220, 210))
                glow_surf.blit(glow(4, (30, 70, 70)), (x - 4, y - 4), special_flags=pg.BLEND_ADD)

    def _aurora(self, surf, glow_surf, t):
        """Curtains rendered at quarter resolution every few frames, then smooth-scaled."""
        if self.t % 3 == 0 or getattr(self, "_aur", None) is None:
            W, H = VIEW_W // 4, VIEW_H // 4
            small = pg.Surface((W, H))
            for band, (col, base, amp) in enumerate((((26, 120, 84), 34, 14), ((50, 60, 140), 58, 10))):
                for xs in range(W):
                    x = xs * 4
                    y = base + math.sin(x * 0.018 + t * 0.4 + band) * amp + math.sin(x * 0.051 - t * 0.6) * 5
                    length = 30 + math.sin(x * 0.03 + t * 0.7) * 12
                    k = 0.5 + 0.5 * math.sin(x * 0.04 - t * 0.9 + band * 2)
                    k *= 0.55 + 0.45 * math.sin(x * 0.011 + t * 0.3 + band) ** 2
                    k *= (0.35 + 0.65 * abs(math.sin(x * 0.37 + math.sin(x * 0.05 + t) * 2))) * 0.7
                    for seg in range(3):
                        f = (1 - seg / 3) ** 1.5 * (0.15 + 0.85 * k)
                        c = (int(col[0] * f), int(col[1] * f), int(col[2] * f))
                        y0 = (y + length * seg / 3) / 4
                        small.fill(c, (xs, int(y0), 1, max(1, int(length / 12) + 1)), special_flags=pg.BLEND_ADD)
            self._aur = pg.transform.smoothscale(small, (VIEW_W, VIEW_H))
        glow_surf.blit(self._aur, (0, 0), special_flags=pg.BLEND_ADD)

    def draw_front(self, surf, cam_x, cam_y, glow_surf):
        self.weather.draw(surf, cam_x, cam_y, glow_surf)


class Weather:
    def __init__(self, kind, rng):
        self.kind = kind
        self.flakes = []
        self.t = 0
        n = {"snow": 110, "pollen": 40, "embers": 70, "drip": 14, "wind": 16}.get(kind, 0)
        for _ in range(n):
            self.flakes.append(self._new(rng, True))
        self.rng = rng

    def _new(self, rng, anywhere=False):
        z = rng.uniform(0.4, 1.3)
        x = rng.uniform(0, VIEW_W + 40)
        if self.kind == "embers":
            y = rng.uniform(0, VIEW_H) if anywhere else VIEW_H + 10
        elif self.kind == "wind":
            y = rng.uniform(0, VIEW_H)
            x = rng.uniform(0, VIEW_W + 40) if anywhere else VIEW_W + 30
        else:
            y = rng.uniform(0, VIEW_H) if anywhere else -10
        return [x, y, z, rng.uniform(0, 6.28)]

    def update(self):
        self.t += 1
        rng = self.rng
        for i, f in enumerate(self.flakes):
            z = f[2]
            f[3] += 0.03
            if self.kind == "snow":
                f[1] += 0.35 * z + 0.1
                f[0] += math.sin(f[3]) * 0.3 * z - 0.15
            elif self.kind == "pollen":
                f[1] += math.sin(f[3]) * 0.15 + 0.05
                f[0] += 0.12 * z + math.cos(f[3] * 0.7) * 0.2
            elif self.kind == "embers":
                f[1] -= 0.45 * z + 0.15
                f[0] += math.sin(f[3] * 1.3) * 0.4
            elif self.kind == "drip":
                f[1] += 2.4 * z
            elif self.kind == "wind":
                f[0] -= 3.0 * z + 1
                f[1] += math.sin(f[3]) * 0.3
            if f[1] > VIEW_H + 12 or f[1] < -14 or f[0] < -40:
                self.flakes[i] = self._new(rng)

    def draw(self, surf, cam_x, cam_y, glow_surf):
        for x, y, z, ph in self.flakes:
            sx = (x - cam_x * z * 0.6) % (VIEW_W + 40) - 20
            sy = (y - cam_y * z * 0.3) % (VIEW_H + 24) - 12
            if self.kind == "snow":
                c = int(180 + 70 * min(1, z))
                s = 2 if z > 1.0 else 1
                surf.fill((c, c, 255), (sx, sy, s, s))
            elif self.kind == "pollen":
                b = 0.5 + 0.5 * math.sin(ph * 3)
                surf.fill((255, 250, 190), (sx, sy, 1, 1))
                glow_surf.blit(glow(4, (int(70 * b), int(70 * b), 30)), (sx - 4, sy - 4), special_flags=pg.BLEND_ADD)
            elif self.kind == "embers":
                c = (255, int(120 + 100 * math.sin(ph * 2) ** 2), 40)
                surf.fill(c, (sx, sy, 1 + (z > 1.0), 1 + (z > 1.0)))
                glow_surf.blit(glow(5, (110, 40, 0)), (sx - 5, sy - 5), special_flags=pg.BLEND_ADD)
            elif self.kind == "drip":
                pg.draw.line(surf, (110, 170, 220), (sx, sy), (sx, sy + 3))
            elif self.kind == "wind":
                l = int(4 + z * 8)
                c = (255, 200, 170) if z > 1.0 else (230, 150, 140)
                pg.draw.line(surf, c, (sx, sy), (sx + l, sy))
