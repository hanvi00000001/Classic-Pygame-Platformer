"""Everything that lives in a level besides the hero."""
import math
import random

import pygame as pg

from . import audio, font
from .fx import glow, lerp_color
from .physics import Body
from .settings import TILE, GRAVITY, MAX_FALL, SPRING_SPEED, VIEW_W, VIEW_H


class Entity:
    solid = False        # acts as a platform for bodies
    enemy = False
    light = None         # (radius, colour) for dark levels
    layer = 1            # 0 behind tiles-ish, 1 normal, 2 front

    def __init__(self, x, y, w=TILE, h=TILE):
        self.x, self.y, self.w, self.h = float(x), float(y), w, h
        self.alive = True
        self.t = random.randint(0, 1000)

    @property
    def rect(self):
        return pg.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def update(self, scene):
        self.t += 1

    def draw(self, surf, cam, glow_surf):
        pass

    def on_screen(self, cam, margin=32):
        return (-margin < self.x - cam[0] < VIEW_W + margin) and (-margin - self.h < self.y - cam[1] < VIEW_H + margin)


# ============================================================ collectibles
class Coin(Entity):
    light = (14, (70, 60, 20))

    def __init__(self, x, y, vx=0.0, vy=0.0, physics=False):
        super().__init__(x + 4, y + 3, 8, 10)
        self.body = Body(self.x, self.y, 8, 10) if physics else None
        if self.body:
            self.body.vx, self.body.vy = vx, vy
        self.delay = 14 if physics else 0
        self.magnet = False
        self.life = 600 if physics else -1

    def update(self, scene):
        self.t += 1
        p = scene.player
        if self.delay > 0:
            self.delay -= 1
        if self.body:
            b = self.body
            if not self.magnet:
                b.vy = min(MAX_FALL, b.vy + GRAVITY)
                vy = b.vy
                b.move(scene.world, scene.platforms)
                if b.on_ground:
                    b.vy = -vy * 0.5 if vy > 1.2 else 0
                    b.vx *= 0.7
                self.x, self.y = b.x, b.y
            self.life -= 1
            if self.life <= 0:
                self.alive = False
        if not p.dead and self.delay == 0:
            dx, dy = p.body.cx - self.cx, p.body.cy - self.cy
            d = math.hypot(dx, dy)
            if d < 26 or self.magnet:
                self.magnet = True
                sp = 3.5
                self.x += dx / max(d, 1) * sp
                self.y += dy / max(d, 1) * sp
                if self.body:
                    self.body.x, self.body.y = self.x, self.y
            if self.rect.colliderect(p.rect):
                self.alive = False
                scene.collect_coin(self.cx, self.cy)

    def draw(self, surf, cam, glow_surf):
        if self.life > 0 and self.life < 120 and (self.life // 4) % 2:
            return
        x, y = self.x - cam[0], self.y - cam[1]
        bob = 0 if self.body else math.sin(self.t * 0.08) * 1.5
        w = abs(math.cos(self.t * 0.09)) * 8
        cx = x + 4
        r = pg.Rect(int(cx - w / 2), int(y + bob), max(2, int(w)), 10)
        pg.draw.ellipse(surf, (196, 128, 24), r)
        if w > 3:
            pg.draw.ellipse(surf, (255, 206, 60), r.inflate(-2, -2))
            surf.fill((255, 246, 180), (r.x + 2, r.y + 2, 1, 4))
        else:
            surf.fill((255, 230, 120), (int(cx - 1), int(y + bob + 1), 1, 8))
        if self.t % 90 < 6:
            surf.fill((255, 255, 255), (int(cx + 1), int(y + bob + 1), 1, 1))
        glow_surf.blit(glow(9, (40, 30, 5)), (int(cx - 9), int(y + bob - 4)), special_flags=pg.BLEND_ADD)


class Gem(Entity):
    """Star shard: three hidden per level."""
    light = (34, (80, 60, 120))

    def __init__(self, x, y, index=0):
        super().__init__(x + 2, y + 2, 12, 12)
        self.index = index
        self.base_y = self.y

    def update(self, scene):
        self.t += 1
        self.y = self.base_y + math.sin(self.t * 0.05) * 2.5
        if self.t % 7 == 0:
            scene.particles.add(self.cx + random.uniform(-6, 6), self.cy + random.uniform(-6, 6), 0, -0.3, 30,
                                (200, 170, 255), size=1, kind="star", glow=4)
        p = scene.player
        if not p.dead and self.rect.colliderect(p.rect):
            self.alive = False
            scene.collect_gem(self)

    def draw(self, surf, cam, glow_surf):
        cx, cy = self.cx - cam[0], self.cy - cam[1]
        a = self.t * 0.03
        pts = []
        for i in range(10):
            r = 7 if i % 2 == 0 else 3
            ang = a + i * math.pi / 5
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        g = glow(22 + 3 * math.sin(self.t * 0.1), (70, 50, 110))
        glow_surf.blit(g, (cx - g.get_width() / 2, cy - g.get_height() / 2), special_flags=pg.BLEND_ADD)
        pg.draw.polygon(surf, (150, 100, 255), pts)
        inner = [(cx + (x - cx) * 0.55, cy + (y - cy) * 0.55) for x, y in pts]
        pg.draw.polygon(surf, (230, 210, 255), inner)
        surf.fill((255, 255, 255), (int(cx) - 1, int(cy) - 1, 2, 2))


class Heart(Entity):
    light = (16, (80, 20, 30))

    def __init__(self, x, y):
        super().__init__(x + 3, y + 3, 10, 9)
        self.base_y = self.y

    def update(self, scene):
        self.t += 1
        self.y = self.base_y + math.sin(self.t * 0.07) * 2
        p = scene.player
        if not p.dead and self.rect.colliderect(p.rect):
            self.alive = False
            scene.collect_heart(self.cx, self.cy)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        k = 1 + 0.12 * max(0, math.sin(self.t * 0.15)) ** 8
        draw_heart(surf, x + 5, y + 4, k)
        glow_surf.blit(glow(12, (60, 10, 20)), (x - 7, y - 8), special_flags=pg.BLEND_ADD)


_heart_cache = {}


def draw_heart(surf, cx, cy, scale=1.0, full=True, color=(232, 52, 82)):
    key = (round(scale, 2), full, color)
    img = _heart_cache.get(key)
    if img is None:
        img = _heart_cache[key] = _make_heart(scale, full, color)
    surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


def _make_heart(scale, full, color):
    pts = "..##.##..|.#######.|#########|#########|.#######.|..#####..|...###...|....#...."
    rows = pts.split("|")
    s = pg.Surface((9, 8), pg.SRCALPHA)
    hi = (255, 160, 180)
    dk = (140, 20, 50)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "#":
                if full:
                    col = hi if (y == 1 and x in (2, 3)) or (y == 2 and x == 1) else color
                    if y >= 5:
                        col = lerp_color(color, dk, 0.4)
                else:
                    col = (50, 40, 60)
                s.set_at((x, y), col)
    if not full:
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c == "#" and (y == 0 or x == 0 or x == 8 or rows[y - 1][x] != "#" or
                                 (x > 0 and row[x - 1] != "#") or (x < 8 and row[x + 1] != "#") or
                                 (y < len(rows) - 1 and rows[y + 1][x] != "#")):
                    s.set_at((x, y), (110, 90, 110))
    if abs(scale - 1) > 0.01:
        s = pg.transform.scale(s, (int(9 * scale + 0.5), int(8 * scale + 0.5)))
    return s


class PowerUp(Entity):
    COLORS = {"fire": (255, 140, 40), "feather": (240, 240, 255), "shield": (120, 220, 255)}
    light = (24, (90, 70, 40))

    def __init__(self, x, y, kind):
        super().__init__(x + 2, y, 12, 12)
        self.kind = kind
        self.rise = 16
        self.body = None
        self.base_y = y

    def update(self, scene):
        self.t += 1
        if self.rise > 0:
            self.y -= 1
            self.rise -= 1
            if self.rise == 0:
                self.base_y = self.y
        else:
            self.y = self.base_y + math.sin(self.t * 0.08) * 2
        p = scene.player
        if self.rise == 0 and not p.dead and self.rect.colliderect(p.rect):
            self.alive = False
            scene.collect_power(self)

    def draw(self, surf, cam, glow_surf):
        cx, cy = int(self.cx - cam[0]), int(self.cy - cam[1])
        col = self.COLORS[self.kind]
        g = glow(20, tuple(c // 3 for c in col))
        glow_surf.blit(g, (cx - 20, cy - 20), special_flags=pg.BLEND_ADD)
        if self.kind == "fire":
            pg.draw.circle(surf, (200, 60, 20), (cx, cy), 6)
            pg.draw.circle(surf, (255, 150, 40), (cx, cy - 1), 4)
            pg.draw.circle(surf, (255, 240, 160), (cx, cy - 2), 2)
            for i in range(3):
                a = self.t * 0.1 + i * 2.1
                surf.fill((255, 200, 80), (cx + int(math.cos(a) * 8), cy + int(math.sin(a) * 8), 1, 1))
        elif self.kind == "feather":
            sway = math.sin(self.t * 0.1) * 0.3
            pts = [(cx - 5, cy + 5), (cx + 5, cy - 6)]
            pg.draw.line(surf, (200, 200, 220), pts[0], pts[1])
            for i in range(6):
                t = i / 6
                bx = cx - 4 + 9 * t
                by = cy + 4 - 10 * t
                pg.draw.line(surf, (255, 255, 255), (bx, by), (bx - 3 + sway, by - 2))
                pg.draw.line(surf, (220, 225, 255), (bx, by), (bx + 2, by + 3 + sway))
        else:
            r = 6 + math.sin(self.t * 0.15) * 0.8
            pg.draw.circle(surf, (60, 140, 200), (cx, cy), int(r))
            pg.draw.circle(surf, (140, 230, 255), (cx, cy), int(r), 1)
            surf.fill((255, 255, 255), (cx - 3, cy - 3, 2, 2))


class Chest(Entity):
    light = (18, (60, 50, 20))

    def __init__(self, x, y):
        super().__init__(x + 1, y + 4, 14, 12)
        self.open = False
        self.lid = 0.0

    def update(self, scene):
        self.t += 1
        p = scene.player
        if not self.open and not p.dead and self.rect.inflate(4, 4).colliderect(p.rect):
            self.open = True
            audio.play("chest")
            scene.shake.add(0.2)
            for i in range(12):
                a = -math.pi / 2 + random.uniform(-0.9, 0.9)
                sp = random.uniform(2.5, 4.5)
                scene.add(Coin(self.x, self.y - 6, math.cos(a) * sp, math.sin(a) * sp, physics=True))
            if p.hearts < p.max_hearts and random.random() < 0.6:
                scene.add(Heart(self.x, self.y - 22))
            scene.particles.sparkle(self.cx, self.y, (255, 230, 120), 16)
            scene.particles.ring(self.cx, self.cy, (255, 220, 120), 26, 20)
            scene.stats["chests"] += 1
        if self.open:
            self.lid = min(1.0, self.lid + 0.12)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        wood, dark, gold = (150, 84, 44), (90, 46, 28), (255, 200, 70)
        surf.fill(dark, (x, y + 4, 14, 8))
        surf.fill(wood, (x + 1, y + 5, 12, 6))
        surf.fill(gold, (x, y + 4, 14, 1))
        surf.fill(gold, (x + 6, y + 4, 2, 4))
        if self.open:
            glow_surf.blit(glow(16, (90, 70, 20)), (x - 9, y - 12), special_flags=pg.BLEND_ADD)
            ly = y + 4 - int(5 * self.lid)
            surf.fill(dark, (x, ly - 2, 14, 2))
            surf.fill((40, 20, 10), (x + 1, y + 3, 12, 2))
        else:
            surf.fill(dark, (x, y, 14, 5))
            surf.fill(wood, (x + 1, y + 1, 12, 3))
            surf.fill(gold, (x + 6, y + 2, 2, 3))
            if self.t % 120 < 8:
                surf.fill((255, 255, 255), (x + 2 + (self.t % 120), y + 1, 1, 1))


# ============================================================ blocks
class Block(Entity):
    """'?' coin block, '!' power block, 'B' breakable brick. Solid in the tile grid."""

    def __init__(self, x, y, kind, tx, ty, power="fire"):
        super().__init__(x, y)
        self.kind = kind
        self.tx, self.ty = tx, ty
        self.used = False
        self.bump = 0
        self.power = power
        self.coins = 1

    @property
    def light(self):
        if self.used or self.kind == "B":
            return None
        return (18, (70, 55, 15) if self.kind == "?" else (50, 40, 90))

    def hit(self, scene, by_player=True):
        if self.kind == "B":
            self.alive = False
            scene.world.set(self.tx, self.ty, ".")
            scene.particles.burst(self.cx, self.cy, 10, (176, 96, 64), 3.2, 50, 3, 0.25, kind="chunk",
                                  color2=(110, 56, 40), angle=-math.pi / 2, spread=2.6, drag=0.99)
            scene.particles.dust(self.cx, self.cy, 6, (200, 170, 150))
            audio.play("break")
            scene.shake.add(0.2)
            scene.kill_enemies_above(self)
            scene.stats["score"] += 10
            return
        if self.used:
            self.bump = 6
            audio.play("bump", 0.6)
            return
        self.bump = 8
        scene.kill_enemies_above(self)
        if self.kind == "?":
            self.coins -= 1
            scene.add(PopCoin(self.x, self.y - TILE))
            scene.collect_coin(self.cx, self.y - 8, silent=False)
            if self.coins <= 0:
                self._use(scene)
        else:
            scene.add(PowerUp(self.x, self.y, self.power))
            audio.play("powerup", 0.6)
            self._use(scene)

    def _use(self, scene):
        self.used = True
        scene.world.set(self.tx, self.ty, "U")

    def update(self, scene):
        self.t += 1
        if self.bump > 0:
            self.bump -= 1

    def draw(self, surf, cam, glow_surf):
        off = -int(math.sin(self.bump / 8 * math.pi) * 4) if self.bump else 0
        x, y = int(self.x - cam[0]), int(self.y - cam[1]) + off
        if self.kind == "B":
            base, dk, hi = (176, 96, 64), (104, 52, 40), (222, 150, 104)
            surf.fill(dk, (x, y, 16, 16))
            for row in range(4):
                o = 0 if row % 2 == 0 else 4
                for bx in range(-o, 16, 8):
                    l = max(0, bx)
                    r = min(16, bx + 7)
                    if r > l:
                        surf.fill(base, (x + l, y + row * 4, r - l, 3))
                        surf.fill(hi, (x + l, y + row * 4, r - l, 1))
            return
        if self.used:
            surf.fill((92, 70, 60), (x, y, 16, 16))
            surf.fill((130, 100, 84), (x + 1, y + 1, 14, 14))
            surf.fill((92, 70, 60), (x + 2, y + 2, 12, 12))
            for px, py in ((2, 2), (12, 2), (2, 12), (12, 12)):
                surf.fill((60, 44, 40), (x + px, y + py, 2, 2))
            return
        if self.kind == "?":
            base, dk, hi, glyph = (240, 170, 40), (160, 90, 20), (255, 230, 140), "?"
        else:
            base, dk, hi, glyph = (120, 90, 230), (60, 40, 140), (200, 180, 255), "!"
        surf.fill(dk, (x, y, 16, 16))
        surf.fill(base, (x + 1, y + 1, 14, 14))
        surf.fill(hi, (x + 1, y + 1, 14, 1))
        surf.fill(hi, (x + 1, y + 1, 1, 14))
        for px, py in ((2, 2), (13, 2), (2, 13), (13, 13)):
            surf.fill(dk, (x + px, y + py, 1, 1))
        pulse = (self.t // 10) % 6
        gcol = lerp_color(dk, (255, 255, 255), 0.15 * (pulse < 3))
        font.draw(surf, glyph, (x + 8, y + 4), gcol, shadow=None, align="center")
        # travelling shine
        k = (self.t % 140)
        if k < 14:
            for i in range(3):
                px = k + i - 1
                if 1 <= px < 15:
                    surf.fill((255, 255, 255), (x + px, y + 1, 1, 1))
        g = glow(14, (50, 35, 5) if self.kind == "?" else (30, 20, 60))
        glow_surf.blit(g, (x - 6, y - 6), special_flags=pg.BLEND_ADD)


class PopCoin(Entity):
    """The coin that jumps out of a '?' block."""

    def __init__(self, x, y):
        super().__init__(x + 4, y + 8, 8, 10)
        self.vy = -4.2

    def update(self, scene):
        self.t += 1
        self.y += self.vy
        self.vy += 0.3
        if self.t > 26 and self.vy > 0:
            self.alive = False
            scene.particles.sparkle(self.cx, self.cy, (255, 230, 120), 6)

    def draw(self, surf, cam, glow_surf):
        x, y = self.x - cam[0], self.y - cam[1]
        w = abs(math.cos(self.t * 0.4)) * 8
        r = pg.Rect(int(x + 4 - w / 2), int(y), max(2, int(w)), 10)
        pg.draw.ellipse(surf, (196, 128, 24), r)
        pg.draw.ellipse(surf, (255, 206, 60), r.inflate(-2, -2))


# ============================================================ platforms
class MovingPlatform(Entity):
    solid = True

    def __init__(self, x, y, vertical, world, tx, ty):
        super().__init__(x, y, 32, 6)
        self.vertical = vertical
        self.dx = self.dy = 0.0
        # scan free tiles to find travel range
        dist = 0
        if vertical:
            while dist < 8 and not world.solid(tx, ty - dist - 1) and not world.solid(tx + 1, ty - dist - 1):
                dist += 1
        else:
            while dist < 9 and not world.solid(tx + dist + 2, ty) and not world.solid(tx + dist + 2, ty - 1):
                dist += 1
        self.range = max(1, dist) * TILE
        self.x0, self.y0 = float(x), float(y)
        self.phase = 0.0
        self.speed = 0.9 / self.range

    def stood_on(self, body):
        pass

    def update(self, scene):
        self.t += 1
        self.phase += self.speed
        k = (1 - math.cos(self.phase * math.pi)) / 2
        nx = self.x0 + (0 if self.vertical else self.range * k)
        ny = self.y0 - (self.range * k if self.vertical else 0)
        self.dx, self.dy = nx - self.x, ny - self.y
        self.x, self.y = nx, ny

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        th = self.theme_cols
        surf.fill(th[1], (x, y, 32, 6))
        surf.fill(th[0], (x + 1, y + 1, 30, 3))
        surf.fill(th[2], (x + 1, y, 30, 1))
        for i in range(4):
            surf.fill(th[1], (x + 4 + i * 8, y + 2, 2, 1))
        # small engine glow underneath
        if self.vertical or True:
            g = glow(8, (60, 50, 100))
            glow_surf.blit(g, (x + 16 - 8, y + 4 - 4), special_flags=pg.BLEND_ADD)
            surf.fill((180, 160, 255), (x + 14, y + 6, 4, 1))

    theme_cols = ((130, 120, 160), (70, 60, 100), (200, 190, 240))


class CrumblePlatform(Entity):
    solid = True

    def __init__(self, x, y):
        super().__init__(x, y, 16, 6)
        self.x0, self.y0 = x, y
        self.state = "idle"
        self.timer = 0
        self.dx = self.dy = 0.0
        self.vy = 0.0

    def stood_on(self, body):
        if self.state == "idle":
            self.state = "shaking"
            self.timer = 26
            audio.play("crumble", 0.5)

    def update(self, scene):
        self.t += 1
        self.dx = self.dy = 0.0
        if self.state == "shaking":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "falling"
                self.solid = False
                self.vy = 0
                scene.particles.burst(self.cx, self.cy, 6, (150, 120, 100), 1.5, 30, 2, 0.2, kind="chunk")
        elif self.state == "falling":
            self.vy = min(6, self.vy + 0.35)
            self.y += self.vy
            if self.y > self.y0 + 200:
                self.state = "gone"
                self.timer = 150
        elif self.state == "gone":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.solid = True
                self.x, self.y = self.x0, self.y0
                scene.particles.sparkle(self.cx, self.cy, (220, 220, 255), 6)

    def draw(self, surf, cam, glow_surf):
        if self.state == "gone":
            if self.timer < 40 and self.timer % 4 < 2:
                x, y = int(self.x0 - cam[0]), int(self.y0 - cam[1])
                pg.draw.rect(surf, (200, 200, 220), (x, y, 16, 6), 1)
            return
        ox = random.randint(-1, 1) if self.state == "shaking" else 0
        x, y = int(self.x - cam[0]) + ox, int(self.y - cam[1])
        surf.fill((90, 70, 60), (x, y, 16, 6))
        surf.fill((150, 120, 100), (x + 1, y + 1, 14, 3))
        surf.fill((190, 160, 130), (x + 1, y, 14, 1))
        pg.draw.line(surf, (90, 70, 60), (x + 5, y + 1), (x + 7, y + 4))
        pg.draw.line(surf, (90, 70, 60), (x + 11, y + 1), (x + 10, y + 4))


class Spring(Entity):
    def __init__(self, x, y):
        super().__init__(x + 1, y + 8, 14, 8)
        self.squash = 0

    def update(self, scene):
        self.t += 1
        if self.squash > 0:
            self.squash -= 1
        p = scene.player
        b = p.body
        if not p.dead and b.vy >= 0 and b.rect.colliderect(self.rect.inflate(-4, 2)):
            b.y = self.y - b.h
            p.bounce(SPRING_SPEED)
            p.jumping = False
            self.squash = 12
            audio.play("spring")
            scene.particles.ring(self.cx, self.y, (255, 240, 160), 20, 14)
            scene.particles.dust(self.cx, self.y + 4, 6, (255, 255, 255))
        for e in scene.entities:
            if e.enemy and e.alive and hasattr(e, "body") and e.body.vy >= 0 and e.rect.colliderect(self.rect):
                e.body.vy = -6

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        k = math.sin(self.squash / 12 * math.pi) if self.squash else 0
        top = y + int(k * 4) - (2 if self.squash and self.squash < 6 else 0)
        surf.fill((90, 90, 110), (x, y + 6, 14, 2))
        for i in range(3):
            yy = top + 2 + i * (y + 6 - top - 2) // 3
            pg.draw.line(surf, (190, 190, 210), (x + 3, yy), (x + 11, yy + 1))
        surf.fill((230, 70, 80), (x, top, 14, 3))
        surf.fill((255, 150, 150), (x + 1, top, 12, 1))


_lava_frames = {}


def _lava_frame(surface, f):
    """Pre-rendered, tile-seamless lava animation (24 frames)."""
    key = (surface, f)
    s = _lava_frames.get(key)
    if s is not None:
        return s
    s = pg.Surface((16, 16), pg.SRCALPHA)
    t = f / 24 * math.tau
    if surface:
        for px in range(16):
            a = px / 16 * math.tau
            h = 3 + math.sin(a + t) * 1.5 + math.sin(a * 2 - t) * 0.8
            s.fill((255, 120, 30), (px, int(h), 1, 16 - int(h)))
            s.fill((255, 230, 120), (px, int(h), 1, 1))
        for py in range(8, 16, 3):
            s.fill((220, 70, 20), (0, py, 16, 1))
    else:
        s.fill((236, 90, 24))
        for py in range(0, 16, 4):
            off = int(math.sin(t + py * 0.4) * 3)
            s.fill((200, 60, 20), ((2 + off) % 16, py, 8, 1))
    _lava_frames[key] = s
    return s


class Lava(Entity):
    """One tile of lava. Instantly deadly."""

    def __init__(self, x, y, surface):
        super().__init__(x, y)
        self.surface = surface
        self.light = (26, (150, 60, 10)) if surface else None

    def update(self, scene):
        self.t += 1
        if self.surface and random.random() < 0.012 and self.on_screen(scene.cam_xy):
            scene.particles.add(self.x + random.uniform(2, 14), self.y + 2, random.uniform(-0.3, 0.3),
                                random.uniform(-2.2, -1.0), 40, (255, 200, 60), size=2, grav=0.08, glow=6,
                                color2=(200, 60, 20))
        p = scene.player
        if not p.dead and p.rect.colliderect(pg.Rect(self.x, self.y + 6, 16, 10)):
            scene.particles.burst(p.body.cx, p.body.bottom, 20, (255, 160, 40), 3, 30, 2, 0.1, glow=6)
            p.die(scene)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        surf.blit(_lava_frame(self.surface, (pg.time.get_ticks() // 50) % 24), (x, y))
        if self.surface and (int(self.x) // 16) % 2 == 0:
            g = glow(22, (90, 30, 0))
            glow_surf.blit(g, (x + 16 - 22, y + 6 - 22), special_flags=pg.BLEND_ADD)


# ============================================================ landmarks
class Checkpoint(Entity):
    light = (40, (110, 80, 40))

    def __init__(self, x, y):
        super().__init__(x + 4, y - 16, 8, 32)
        self.active = False
        self.flame = 0.0

    def update(self, scene):
        self.t += 1
        p = scene.player
        if not self.active and not p.dead and self.rect.inflate(8, 0).colliderect(p.rect):
            self.active = True
            scene.set_checkpoint(self)
            audio.play("checkpoint")
            scene.particles.ring(self.cx, self.y + 6, (255, 220, 140), 36, 26)
            scene.particles.burst(self.cx, self.y + 6, 24, (255, 200, 90), 2.5, 40, 2, 0.02, glow=6)
            scene.popup(self.cx, self.y - 6, "CHECKPOINT", (255, 230, 150))
        if self.active:
            self.flame = min(1.0, self.flame + 0.05)
            if self.t % 6 == 0:
                scene.particles.add(self.cx + random.uniform(-1, 1), self.y + 4, random.uniform(-0.2, 0.2), -0.6, 26,
                                    (255, 210, 120), size=1, grav=-0.01, glow=3, color2=(200, 60, 20))

    @property
    def light_now(self):
        return (int(16 + 34 * self.flame), (110, 80, 40)) if self.active else (10, (30, 30, 50))

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        surf.fill((60, 50, 60), (x + 3, y + 8, 2, 24))
        surf.fill((110, 100, 110), (x + 3, y + 8, 1, 24))
        surf.fill((60, 50, 60), (x, y + 30, 8, 2))
        # lantern
        surf.fill((70, 60, 70), (x, y + 1, 8, 2))
        surf.fill((70, 60, 70), (x, y + 9, 8, 1))
        surf.fill((40, 36, 50) if not self.active else (255, 210, 120), (x + 1, y + 3, 6, 6))
        surf.fill((70, 60, 70), (x + 3, y + 3, 2, 6))
        if self.active:
            fl = 1 + math.sin(self.t * 0.3) * 0.5
            surf.fill((255, 250, 220), (x + 3, y + 5, 2, 2))
            g = glow(int(18 * self.flame * fl + 6), (120, 80, 30))
            glow_surf.blit(g, (x + 4 - g.get_width() // 2, y + 6 - g.get_height() // 2), special_flags=pg.BLEND_ADD)


class Portal(Entity):
    light = (60, (80, 60, 140))

    def __init__(self, x, y):
        super().__init__(x - 4, y - 16, 24, 32)
        self.locked = False
        self.used = False

    def update(self, scene):
        self.t += 1
        if self.locked:
            return
        if self.t % 3 == 0 and self.on_screen(scene.cam_xy):
            a = random.uniform(0, math.tau)
            r = random.uniform(16, 24)
            scene.particles.add(self.cx + math.cos(a) * r, self.cy + math.sin(a) * r * 1.3,
                                -math.cos(a) * 0.6, -math.sin(a) * 0.8, 26, (200, 170, 255), size=1, kind="star",
                                glow=3, drag=1.0)
        p = scene.player
        if not self.used and not p.dead and self.rect.inflate(-8, -4).colliderect(p.rect):
            self.used = True
            scene.finish_level(self)

    def draw(self, surf, cam, glow_surf):
        cx, cy = int(self.cx - cam[0]), int(self.cy - cam[1])
        if self.locked:
            pg.draw.ellipse(surf, (60, 50, 80), (cx - 10, cy - 15, 20, 30), 1)
            return
        t = self.t * 0.05
        g = glow(44 + 4 * math.sin(t * 2), (60, 40, 110))
        glow_surf.blit(g, (cx - g.get_width() // 2, cy - g.get_height() // 2), special_flags=pg.BLEND_ADD)
        for i in range(5, 0, -1):
            k = i / 5
            col = lerp_color((255, 240, 255), (90, 50, 200), k)
            rw, rh = int(11 * k + 1), int(15 * k + 1)
            pg.draw.ellipse(surf, col, (cx - rw, cy - rh, rw * 2, rh * 2), 0 if i == 1 else 1)
        for i in range(10):
            a = t * 3 + i * math.tau / 10
            r = 9 + 3 * math.sin(t * 4 + i)
            surf.fill((255, 255, 255), (cx + int(math.cos(a) * r * 0.75), cy + int(math.sin(a) * r), 1, 1))
        # stone frame
        pg.draw.ellipse(surf, (90, 80, 110), (cx - 13, cy - 17, 26, 34), 2)
        surf.fill((90, 80, 110), (cx - 14, cy + 14, 28, 3))


class Lantern(Entity):
    light = (50, (110, 80, 40))
    layer = 0

    def __init__(self, x, y):
        super().__init__(x + 4, y, 8, 12)

    def draw(self, surf, cam, glow_surf):
        sway = math.sin(self.t * 0.03) * 2
        x, y = int(self.x - cam[0] + sway), int(self.y - cam[1])
        pg.draw.line(surf, (60, 50, 60), (x + 4 - sway, y - 2), (x + 4, y + 3))
        surf.fill((70, 56, 50), (x + 1, y + 3, 6, 1))
        surf.fill((255, 200, 110), (x + 1, y + 4, 6, 6))
        surf.fill((255, 245, 200), (x + 3, y + 6, 2, 2))
        surf.fill((70, 56, 50), (x + 1, y + 10, 6, 1))
        fl = 1 + 0.06 * math.sin(self.t * 0.4) + 0.04 * math.sin(self.t * 1.3)
        g = glow(int(20 * fl), (110, 70, 25))
        glow_surf.blit(g, (x + 4 - g.get_width() // 2, y + 7 - g.get_height() // 2), special_flags=pg.BLEND_ADD)


class Crystal(Entity):
    light = (56, (40, 110, 120))
    layer = 0

    def __init__(self, x, y):
        super().__init__(x, y, 16, 16)
        self.col = random.choice([(90, 240, 220), (170, 130, 255), (110, 190, 255)])

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        c = self.col
        dk = lerp_color(c, (0, 0, 0), 0.45)
        for dx, h, w in ((3, 11, 3), (8, 16, 4), (12, 9, 3)):
            pts = [(x + dx - w, y + 16), (x + dx, y + 16 - h), (x + dx + w, y + 16)]
            pg.draw.polygon(surf, c, pts)
            pg.draw.line(surf, dk, (x + dx, y + 16 - h), (x + dx + w, y + 16))
            surf.set_at((x + dx, y + 17 - h), (255, 255, 255))
        k = 0.8 + 0.2 * math.sin(self.t * 0.05)
        g = glow(int(22 * k), tuple(int(ch * 0.4) for ch in c))
        glow_surf.blit(g, (x + 8 - g.get_width() // 2, y + 10 - g.get_height() // 2), special_flags=pg.BLEND_ADD)


# ============================================================ projectiles
class Fireball(Entity):
    light = (22, (110, 50, 10))

    def __init__(self, x, y, d):
        super().__init__(x - 3, y - 3, 6, 6)
        self.body = Body(self.x, self.y, 6, 6)
        self.body.vx = d * 4.2
        self.body.vy = 1.0
        self.bounces = 0
        self.life = 150
        self.player_shot = True

    def update(self, scene):
        self.t += 1
        b = self.body
        b.vy = min(5, b.vy + 0.32)
        vx = b.vx
        b.move(scene.world, scene.platforms)
        if b.on_ground:
            b.vy = -3.1
            self.bounces += 1
        if b.wall or self.bounces > 6 or self.life <= 0:
            self.pop(scene)
        self.life -= 1
        self.x, self.y = b.x, b.y
        if self.t % 2 == 0:
            scene.particles.add(self.cx, self.cy, -vx * 0.1, random.uniform(-0.3, 0.1), 16, (255, 200, 80),
                                size=2, kind="puff", color2=(200, 50, 20))
        for e in scene.entities:
            if e.enemy and e.alive and e.rect.colliderect(self.rect):
                if e.take_hit(scene, "fire", self.cx):
                    self.pop(scene)
                    break
        if self.y > scene.world.px_h + 20:
            self.alive = False

    def pop(self, scene):
        if self.alive:
            self.alive = False
            scene.particles.burst(self.cx, self.cy, 8, (255, 180, 60), 1.8, 18, 2, 0, glow=4)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.cx - cam[0]), int(self.cy - cam[1])
        g = glow(10, (140, 60, 10))
        glow_surf.blit(g, (x - 10, y - 10), special_flags=pg.BLEND_ADD)
        pg.draw.circle(surf, (230, 80, 20), (x, y), 3)
        pg.draw.circle(surf, (255, 200, 80), (x, y), 2)
        a = self.t * 0.6
        surf.fill((255, 255, 220), (x + int(math.cos(a) * 1.5), y + int(math.sin(a) * 1.5), 1, 1))


class Seed(Entity):
    """Projectile shot by enemies (spitter plant, boss)."""
    light = (12, (60, 80, 20))

    def __init__(self, x, y, vx, vy, color=(160, 230, 80), grav=0.0, big=False):
        super().__init__(x - 3, y - 3, 6 if not big else 10, 6 if not big else 10)
        self.vx, self.vy = vx, vy
        self.color = color
        self.grav = grav
        self.life = 300
        self.big = big

    def update(self, scene):
        self.t += 1
        self.vy += self.grav
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0 or scene.world.solid(int(self.cx // TILE), int(self.cy // TILE)):
            self.alive = False
            scene.particles.burst(self.cx, self.cy, 6, self.color, 1.5, 16, 1, 0.05)
            return
        p = scene.player
        if not p.dead and self.rect.inflate(-2, -2).colliderect(p.rect):
            if p.hurt(scene, self.cx):
                self.alive = False
        if self.t % 3 == 0:
            scene.particles.add(self.cx, self.cy, 0, 0, 10, self.color, size=1)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.cx - cam[0]), int(self.cy - cam[1])
        r = 3 if not self.big else 5
        pg.draw.circle(surf, lerp_color(self.color, (0, 0, 0), 0.4), (x, y), r)
        pg.draw.circle(surf, self.color, (x, y - 1), r - 1)
        glow_surf.blit(glow(8 + 4 * self.big, tuple(c // 4 for c in self.color)), (x - 8 - 4 * self.big, y - 8 - 4 * self.big),
                       special_flags=pg.BLEND_ADD)


# ============================================================ signs, cameos, gates
class Sign(Entity):
    layer = 0

    def __init__(self, x, y, text):
        super().__init__(x + 2, y + 4, 12, 12)
        self.text = text.upper()
        self.show = 0.0

    def update(self, scene):
        self.t += 1
        p = scene.player.body
        near = abs(p.cx - self.cx) < 36 and abs(p.cy - self.cy) < 40
        self.show = min(1.0, self.show + 0.12) if near else max(0.0, self.show - 0.12)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        wood, dk, hi = (150, 104, 66), (90, 60, 40), (200, 150, 100)
        surf.fill(dk, (x + 5, y + 6, 2, 6))
        surf.fill(dk, (x, y, 12, 8))
        surf.fill(wood, (x + 1, y + 1, 10, 6))
        surf.fill(hi, (x + 1, y + 1, 10, 1))
        surf.fill(dk, (x + 3, y + 3, 6, 1))
        surf.fill(dk, (x + 3, y + 5, 4, 1))
        if self.show <= 0.01:
            if (self.t // 30) % 2:
                font.draw(surf, "!", (x + 6, y - 10), (255, 230, 150), outline=(20, 16, 32), align="center")
            return
        w = font.text_width(self.text) + 12
        k = 1 - (1 - self.show) ** 3
        bx = max(4, min(VIEW_W - w - 4, x + 6 - w // 2))
        by = y - 24 + int((1 - k) * 6)
        s = pg.Surface((w, 15), pg.SRCALPHA)
        s.fill((14, 10, 28, 225))
        pg.draw.rect(s, (255, 220, 150), (0, 0, w, 15), 1)
        font.draw(s, self.text, (6, 4), (255, 240, 210), shadow=None)
        s.set_alpha(int(255 * k))
        surf.blit(s, (bx, by))


class RetroHero(Entity):
    """The red rectangle that was the hero in 2022."""

    def __init__(self, x, y):
        super().__init__(x + 3, y, 10, 16)
        self.said = 0.0
        self.lines = ["I WAS THE HERO IN 2022.", "NO SPRITE. NO ANIMATION. JUST RED.", "GO ON. FINISH WHAT I STARTED."]

    def update(self, scene):
        self.t += 1
        p = scene.player.body
        near = abs(p.cx - self.cx) < 48
        self.said = min(1.0, self.said + 0.1) if near else max(0.0, self.said - 0.1)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        hop = -2 if (self.t // 40) % 6 == 0 and self.t % 40 < 8 else 0
        surf.fill((255, 0, 0), (x, y + hop, 10, 16))
        if self.said > 0.5:
            line = self.lines[(self.t // 150) % len(self.lines)]
            w = font.text_width(line) + 10
            bx = max(4, min(VIEW_W - w - 4, x + 5 - w // 2))
            s = pg.Surface((w, 14), pg.SRCALPHA)
            s.fill((255, 255, 255, 230))
            surf.blit(s, (bx, y - 22))
            surf.fill((255, 255, 255), (x + 4, y - 8, 2, 2))
            font.draw(surf, line, (bx + 5, y - 18), (200, 0, 0), shadow=None)


class Gate(Entity):
    """Iron bars that slam shut behind you when the boss wakes."""

    def __init__(self, tx, rows):
        super().__init__(tx * TILE, rows[0] * TILE, TILE, len(rows) * TILE)
        self.tx = tx
        self.rows = rows
        self.k = 0.0
        self.closed = False

    def close(self, scene):
        if self.closed:
            return
        self.closed = True
        for r in self.rows:
            scene.world.set(self.tx, r, "#")
        scene.shake.add(0.5)
        audio.play("slam", 0.8)

    def open(self, scene):
        self.closed = False
        for r in self.rows:
            scene.world.set(self.tx, r, ".")

    def update(self, scene):
        self.t += 1
        target = 1.0 if self.closed else 0.0
        self.k += (target - self.k) * 0.25

    def draw(self, surf, cam, glow_surf):
        if self.k < 0.02:
            return
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        h = int(self.h * self.k)
        for i in range(4):
            surf.fill((70, 60, 70), (x + 1 + i * 4, y, 2, h))
            surf.fill((130, 120, 130), (x + 1 + i * 4, y, 1, h))
        surf.fill((50, 40, 50), (x, y + h - 3, TILE, 3))
        for k in range(0, h - 4, 12):
            surf.fill((90, 80, 90), (x, y + k + 4, TILE, 1))
