"""Enemies and the final boss."""
import math
import random

import pygame as pg

from . import audio, font
from .entities import Entity, Seed, Coin, Heart
from .fx import glow, lerp_color
from .physics import Body
from .settings import TILE, GRAVITY, MAX_FALL, VIEW_W


class Enemy(Entity):
    enemy = True
    stompable = True
    hp = 1
    score = 100
    contact_damage = True

    def __init__(self, x, y, w, h):
        super().__init__(x + (TILE - w) / 2, y + TILE - h, w, h)
        self.body = Body(self.x, self.y, w, h)
        self.dir = -1
        self.hit_flash = 0
        self.dying = 0
        self.awake = False

    def sync(self):
        self.x, self.y = self.body.x, self.body.y

    def walk(self, scene, speed, turn_at_ledges=True):
        b = self.body
        b.vx = self.dir * speed
        b.vy = min(MAX_FALL, b.vy + GRAVITY)
        b.move(scene.world, scene.platforms)
        if b.wall:
            self.dir = -self.dir
        elif turn_at_ledges and b.on_ground:
            ahead = b.x + (b.w + 1 if self.dir > 0 else -1)
            tx = math.floor(ahead / TILE)
            ty = math.floor((b.bottom + 2) / TILE)
            w = scene.world
            if not (w.solidish(tx, ty) or w.get(tx, ty) == "-" or w.slope_surface(tx, ty, ahead) is not None
                    or w.slope_surface(tx, ty - 1, ahead) is not None):
                self.dir = -self.dir
        self.sync()

    def update(self, scene):
        self.t += 1
        if self.hit_flash:
            self.hit_flash -= 1
        if self.dying:
            self.dying -= 1
            if self.dying <= 0:
                self.alive = False
            return
        if not self.awake:
            if abs(self.cx - scene.player.body.cx) < VIEW_W * 0.7:
                self.awake = True
            else:
                return
        self.think(scene)
        if self.y > scene.world.px_h + 40:
            self.alive = False
        self.check_player(scene)

    def think(self, scene):
        pass

    def check_player(self, scene):
        p = scene.player
        if p.dead or self.dying:
            return
        pr, er = p.rect, self.rect
        if not pr.colliderect(er.inflate(-2, 0)):
            return
        b = p.body
        if p.dash_timer > 0:
            self.take_hit(scene, "dash", b.cx)
            return
        falling_onto = b.vy > 0.5 and (b.bottom - b.vy) <= self.y + 6
        if falling_onto:
            if self.stompable:
                self.take_hit(scene, "stomp", b.cx)
                p.bounce(4.6, scene.inp.held["jump"])
                b.y = self.y - b.h
            else:
                p.bounce(3.6)
                p.hurt(scene, self.cx)
            return
        if self.contact_damage:
            p.hurt(scene, self.cx)

    def take_hit(self, scene, how, src_x=None):
        if self.dying:
            return False
        self.hp -= 1
        self.hit_flash = 8
        if self.hp > 0:
            audio.play("bump")
            return True
        self.kill(scene, how)
        return True

    def kill(self, scene, how="stomp"):
        self.dying = 22 if how == "stomp" else 1
        scene.stats["enemies"] += 1
        scene.stats["score"] += self.score
        scene.popup(self.cx, self.y - 4, str(self.score), (255, 255, 255))
        scene.freeze(3)
        scene.shake.add(0.18)
        if how == "stomp":
            audio.play("stomp")
            scene.particles.ring(self.cx, self.y + self.h, (255, 255, 255), 14, 12, 1)
        else:
            audio.play("kill")
        col = getattr(self, "col", (200, 200, 200))
        scene.particles.burst(self.cx, self.cy, 14, col, 2.6, 30, 2, 0.12, color2=lerp_color(col, (0, 0, 0), 0.5))
        scene.particles.dust(self.cx, self.cy, 6, (240, 240, 240))
        if random.random() < 0.35:
            scene.add(Coin(self.x, self.y - 4, random.uniform(-1, 1), -3, physics=True))


class Slime(Enemy):
    def __init__(self, x, y, theme):
        super().__init__(x, y, 12, 10)
        cols = {"meadow": (110, 210, 90), "caves": (90, 160, 255), "sunset": (255, 150, 90),
                "frost": (150, 230, 255), "volcano": (255, 100, 60), "legacy": (110, 210, 90)}
        self.col = cols.get(theme, (110, 210, 90))
        self.hop = 0

    def think(self, scene):
        b = self.body
        self.hop += 1
        speed = 0.45 + 0.35 * max(0, math.sin(self.hop * 0.12))
        self.walk(scene, speed)

    def draw(self, surf, cam, glow_surf):
        x, y = self.x - cam[0], self.y - cam[1]
        col = self.col if not self.hit_flash else (255, 255, 255)
        if self.dying:
            k = self.dying / 22
            pg.draw.ellipse(surf, col, (x - 2, y + 7, 16, 3 + int(2 * k)))
            return
        s = math.sin(self.hop * 0.12)
        w = 12 + s * 2
        h = 10 - s * 2
        r = pg.Rect(int(x + 6 - w / 2), int(y + 10 - h), int(w), int(h))
        dk = lerp_color(col, (0, 0, 0), 0.4)
        pg.draw.ellipse(surf, dk, r.move(0, 1))
        pg.draw.ellipse(surf, col, r)
        pg.draw.ellipse(surf, lerp_color(col, (255, 255, 255), 0.5), (r.x + 2, r.y + 1, 4, 2))
        ex = r.centerx + self.dir * 2
        ey = r.y + r.h // 2 - 1
        surf.fill((20, 20, 30), (ex - 2, ey, 1, 2))
        surf.fill((20, 20, 30), (ex + 1, ey, 1, 2))


class Beetle(Enemy):
    """Spiky shell: can't be stomped. Dash or fire it."""
    stompable = False
    score = 200

    def __init__(self, x, y, theme):
        super().__init__(x, y, 14, 10)
        self.col = (120, 90, 170)

    def think(self, scene):
        self.walk(scene, 0.55)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        if self.dying:
            return
        flash = self.hit_flash > 0
        shell = (255, 255, 255) if flash else (100, 70, 160)
        hi = (170, 140, 230)
        leg = (40, 30, 50)
        ph = (self.t // 6) % 2
        for i, lx in enumerate((3, 7, 11)):
            surf.fill(leg, (x + lx + (ph if i % 2 else -ph), y + 8, 1, 2))
        pg.draw.ellipse(surf, shell, (x, y + 2, 14, 8))
        pg.draw.line(surf, hi, (x + 3, y + 3), (x + 9, y + 3))
        for i, sx in enumerate((2, 6, 10)):
            pg.draw.polygon(surf, (230, 230, 245), [(x + sx, y + 3), (x + sx + 1.5, y - 1 - (i == 1) * 2), (x + sx + 3, y + 3)])
        hx = x + (13 if self.dir > 0 else -1)
        surf.fill((40, 30, 50), (hx - 1, y + 5, 3, 4))
        surf.fill((255, 220, 90), (hx + (1 if self.dir > 0 else -1), y + 6, 1, 1))


class Bat(Enemy):
    score = 150

    def __init__(self, x, y, theme):
        super().__init__(x, y, 12, 8)
        self.body.y = y + 1
        self.y = y + 1
        self.state = "hang"
        self.col = (110, 80, 140) if theme != "frost" else (90, 110, 170)
        self.vx = self.vy = 0.0
        self.home = (self.x, self.y)

    def think(self, scene):
        p = scene.player.body
        if self.state == "hang" and not getattr(self, "perched", False):
            # hang from the nearest ceiling above the spawn point
            self.perched = True
            tx = int(self.cx // TILE)
            ty = int(self.y // TILE)
            for k in range(12):
                if scene.world.solid(tx, ty - k - 1):
                    self.y = (ty - k) * TILE
                    self.body.y = self.y
                    break
        if self.state == "hang":
            if abs(p.cx - self.cx) < 90 and p.y > self.y - 8 and abs(p.cy - self.cy) < 130:
                self.state = "fly"
                audio.play("blip", 0.3)
            return
        dx, dy = p.cx - self.cx, p.cy - self.cy
        d = max(1, math.hypot(dx, dy))
        self.vx += dx / d * 0.06
        self.vy += dy / d * 0.05 + math.sin(self.t * 0.15) * 0.12
        sp = math.hypot(self.vx, self.vy)
        if sp > 1.4:
            self.vx *= 1.4 / sp
            self.vy *= 1.4 / sp
        self.x += self.vx
        self.y += self.vy
        self.dir = 1 if self.vx > 0 else -1
        self.body.x, self.body.y = self.x, self.y

    def take_hit(self, scene, how, src_x=None):
        r = super().take_hit(scene, how, src_x)
        self.vy = 2
        return r

    def draw(self, surf, cam, glow_surf):
        if self.dying:
            return
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        col = (255, 255, 255) if self.hit_flash else self.col
        dk = lerp_color(col, (0, 0, 0), 0.4)
        if self.state == "hang":
            pg.draw.ellipse(surf, col, (x + 3, y, 6, 8))
            surf.fill(dk, (x + 2, y, 8, 3))
            surf.fill((255, 80, 80), (x + 4, y + 5, 1, 1))
            surf.fill((255, 80, 80), (x + 7, y + 5, 1, 1))
            return
        flap = math.sin(self.t * 0.5)
        wy = int(flap * 4)
        pg.draw.polygon(surf, dk, [(x + 4, y + 3), (x - 3, y + 1 + wy), (x - 1, y + 5 + wy), (x + 3, y + 5)])
        pg.draw.polygon(surf, dk, [(x + 8, y + 3), (x + 15, y + 1 + wy), (x + 13, y + 5 + wy), (x + 9, y + 5)])
        pg.draw.ellipse(surf, col, (x + 2, y + 1, 8, 7))
        surf.fill(col, (x + 3, y, 1, 2))
        surf.fill(col, (x + 8, y, 1, 2))
        surf.fill((255, 90, 90), (x + 4, y + 3, 1, 1))
        surf.fill((255, 90, 90), (x + 7, y + 3, 1, 1))
        glow_surf.blit(glow(5, (60, 10, 10)), (x + 1, y - 2), special_flags=pg.BLEND_ADD)


class Spitter(Enemy):
    score = 150

    def __init__(self, x, y, theme):
        super().__init__(x, y, 12, 14)
        self.col = (90, 190, 90) if theme not in ("volcano", "frost") else ((200, 90, 60) if theme == "volcano" else (110, 170, 200))
        self.cool = random.randint(60, 120)
        self.open = 0

    def think(self, scene):
        b = self.body
        b.vy = min(MAX_FALL, b.vy + GRAVITY)
        b.vx = 0
        b.move(scene.world, scene.platforms)
        self.sync()
        p = scene.player.body
        self.dir = 1 if p.cx > self.cx else -1
        self.cool -= 1
        if self.open:
            self.open -= 1
        if self.cool <= 0 and abs(p.cx - self.cx) < 220 and abs(p.cy - self.cy) < 120:
            self.cool = 110
            self.open = 16
            ang = math.atan2(p.cy - (self.y + 4), p.cx - self.cx)
            ang = max(-2.6, min(-0.5, ang)) if p.cy < self.y else ang
            scene.add(Seed(self.cx + self.dir * 6, self.y + 4, math.cos(ang) * 1.8, math.sin(ang) * 1.8))
            audio.play("shoot", 0.5)

    def draw(self, surf, cam, glow_surf):
        if self.dying:
            return
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        stem = (60, 130, 60) if self.col[1] > 150 else lerp_color(self.col, (0, 0, 0), 0.4)
        surf.fill(stem, (x + 5, y + 8, 2, 6))
        pg.draw.polygon(surf, stem, [(x + 6, y + 12), (x, y + 9), (x + 3, y + 14)])
        pg.draw.polygon(surf, stem, [(x + 6, y + 12), (x + 12, y + 9), (x + 9, y + 14)])
        col = (255, 255, 255) if self.hit_flash else self.col
        pg.draw.circle(surf, col, (x + 6, y + 5), 5)
        mx = x + 6 + self.dir * 3
        o = 2 if self.open else 1
        surf.fill((60, 10, 30), (mx - 1, y + 5 - o, 3, o * 2))
        for i in range(5):
            a = i * 1.25 + self.t * 0.02
            surf.fill(lerp_color(col, (255, 255, 255), 0.4), (x + 6 + int(math.cos(a) * 5), y + 5 + int(math.sin(a) * 5), 1, 1))
        surf.fill((20, 20, 30), (x + 6 - self.dir, y + 3, 1, 1))


class Wisp(Enemy):
    """Ghost flame: drifts toward you through walls, but freezes when you face it."""
    stompable = False
    score = 300
    light = (40, (40, 90, 110))

    def __init__(self, x, y, theme):
        super().__init__(x, y, 12, 12)
        self.body.collides = False
        self.col = (120, 230, 255)
        self.shy = False

    def think(self, scene):
        p = scene.player
        dx, dy = p.body.cx - self.cx, p.body.cy - self.cy
        d = max(1, math.hypot(dx, dy))
        facing_me = (dx < 0 and p.facing > 0) or (dx > 0 and p.facing < 0)
        self.shy = facing_me and d < 200
        if not self.shy and d < 260:
            sp = 0.65
            self.x += dx / d * sp
            self.y += dy / d * sp + math.sin(self.t * 0.08) * 0.2
        else:
            self.y += math.sin(self.t * 0.05) * 0.15
        self.dir = 1 if dx > 0 else -1
        self.body.x, self.body.y = self.x, self.y
        if self.t % 4 == 0:
            scene.particles.add(self.cx + random.uniform(-3, 3), self.y + 10, random.uniform(-0.2, 0.2), -0.5, 22,
                                self.col, size=2, kind="puff", glow=3, color2=(40, 60, 120))

    def draw(self, surf, cam, glow_surf):
        if self.dying:
            return
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        g = glow(22, (30, 70, 90))
        glow_surf.blit(g, (x + 6 - 22, y + 6 - 22), special_flags=pg.BLEND_ADD)
        col = (255, 255, 255) if self.hit_flash else self.col
        body = [(x + 6, y - 4 + int(math.sin(self.t * 0.2) * 2)), (x + 12, y + 7), (x + 9, y + 12), (x + 3, y + 12), (x, y + 7)]
        pg.draw.polygon(surf, lerp_color(col, (40, 60, 140), 0.4), body)
        pg.draw.circle(surf, col, (x + 6, y + 7), 4)
        if self.shy:
            surf.fill((20, 30, 60), (x + 3, y + 6, 2, 1))
            surf.fill((20, 30, 60), (x + 7, y + 6, 2, 1))
        else:
            surf.fill((20, 30, 60), (x + 4 + self.dir, y + 5, 1, 3))
            surf.fill((20, 30, 60), (x + 7 + self.dir, y + 5, 1, 3))


# ============================================================ boss
class Shockwave(Entity):
    def __init__(self, x, y, d):
        super().__init__(x, y - 12, 12, 12)
        self.d = d
        self.life = 90

    def update(self, scene):
        self.t += 1
        self.x += self.d * 3.0
        self.life -= 1
        tx = int((self.cx + self.d * 6) // TILE)
        ty = int((self.y + 14) // TILE)
        if self.life <= 0 or scene.world.solid(tx, int(self.cy // TILE)):
            self.alive = False
        if self.t % 2 == 0:
            scene.particles.add(self.cx, self.y + 12, random.uniform(-0.5, 0.5), random.uniform(-2.5, -1), 24,
                                (255, 160, 60), size=2, grav=0.12, glow=4, color2=(120, 30, 10))
        p = scene.player
        if not p.dead and p.rect.colliderect(self.rect):
            p.hurt(scene, self.cx)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        h = 12 + int(math.sin(self.t * 0.6) * 2)
        pg.draw.polygon(surf, (255, 140, 40), [(x, y + 12), (x + 6, y + 12 - h), (x + 12, y + 12)])
        pg.draw.polygon(surf, (255, 230, 140), [(x + 3, y + 12), (x + 6, y + 16 - h), (x + 9, y + 12)])
        glow_surf.blit(glow(16, (120, 50, 10)), (x - 10, y - 8), special_flags=pg.BLEND_ADD)


class FallingRock(Entity):
    def __init__(self, x, y_target, top):
        super().__init__(x - 6, top, 12, 12)
        self.target = y_target
        self.warn = 50
        self.vy = 0.0

    def update(self, scene):
        self.t += 1
        if self.warn > 0:
            self.warn -= 1
            return
        self.vy = min(7, self.vy + 0.35)
        self.y += self.vy
        p = scene.player
        if not p.dead and p.rect.colliderect(self.rect):
            p.hurt(scene, self.cx)
        if scene.world.solid(int(self.cx // TILE), int((self.y + 12) // TILE)):
            self.alive = False
            scene.particles.burst(self.cx, self.y + 10, 10, (110, 90, 90), 2.5, 34, 3, 0.2, kind="chunk")
            scene.shake.add(0.12)
            audio.play("break", 0.4)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        if self.warn > 0:
            if (self.warn // 4) % 2 == 0:
                ty = int(self.target - cam[1])
                pg.draw.line(surf, (255, 80, 60), (x + 2, ty), (x + 10, ty))
                font.draw(surf, "!", (x + 6, ty - 10), (255, 90, 70), align="center")
            return
        pg.draw.polygon(surf, (90, 70, 72), [(x, y + 4), (x + 4, y), (x + 10, y + 1), (x + 12, y + 7), (x + 7, y + 12), (x + 1, y + 10)])
        pg.draw.line(surf, (255, 120, 40), (x + 3, y + 5), (x + 8, y + 7))


class MoltenKing(Enemy):
    """Final boss. Only vulnerable while stunned after a slam."""
    stompable = True
    score = 5000
    light = (90, (140, 60, 20))

    def __init__(self, x, y, theme):
        super().__init__(x, y, 36, 40)
        self.max_hp = self.hp = 6
        self.state = "sleep"
        self.timer = 0
        self.col = (255, 120, 40)
        self.stun = 0
        self.invuln = 0
        self.arms = 0.0
        self.name = "THE MOLTEN KING"
        self.arena = None
        self.target_x = 0
        self.slams = 0

    @property
    def phase2(self):
        return self.hp <= 3

    def think(self, scene):
        b = self.body
        p = scene.player.body
        if self.invuln:
            self.invuln -= 1
        if self.state == "sleep":
            b.vy = min(MAX_FALL, b.vy + GRAVITY)
            b.move(scene.world, scene.platforms)
            self.sync()
            if abs(p.cx - self.cx) < 150:
                self.state = "intro"
                self.timer = 110
                scene.start_boss(self)
                audio.play("roar")
                scene.shake.add(0.8)
            return
        self.timer -= 1
        self.dir = 1 if p.cx > self.cx else -1
        if self.state == "intro":
            if self.timer % 10 == 0:
                scene.particles.burst(self.cx, self.y, 6, (255, 140, 40), 2.5, 30, 2, 0.05, glow=5)
            if self.timer <= 0:
                self._next(scene)
        elif self.state == "walk":
            b.vx = self.dir * (0.9 if not self.phase2 else 1.3)
            self._phys(scene)
            if self.timer <= 0:
                self._next(scene)
        elif self.state == "windup":
            b.vx = 0
            self._phys(scene)
            if self.timer <= 0:
                self.state = "leap"
                b.vy = -7.6
                self.target_x = p.cx
                audio.play("jump", 1.0)
        elif self.state == "leap":
            dx = self.target_x - self.cx
            b.vx = max(-3.2, min(3.2, dx * 0.05))
            self._phys(scene)
            if b.on_ground and b.vy >= 0:
                self._slam(scene)
        elif self.state == "stunned":
            b.vx = 0
            self._phys(scene)
            if self.t % 6 == 0:
                scene.particles.add(self.cx + random.uniform(-14, 14), self.y, 0, -0.6, 30, (160, 160, 170),
                                    size=3, kind="puff")
            if self.timer <= 0:
                self._next(scene)
        elif self.state == "volley":
            b.vx = 0
            self._phys(scene)
            n = 5 if self.phase2 else 3
            if self.timer % 18 == 0 and self.timer > 0:
                ang = -math.pi / 2 + self.dir * random.uniform(0.25, 0.8)
                sp = random.uniform(3.4, 4.6)
                scene.add(Seed(self.cx, self.y + 6, math.cos(ang) * sp, math.sin(ang) * sp, (255, 150, 50), grav=0.14, big=True))
                audio.play("fire", 0.8)
                self.arms = 1.0
            if self.timer <= 0:
                self._next(scene)
        elif self.state == "rocks":
            b.vx = 0
            self._phys(scene)
            if self.timer % 14 == 0 and self.timer > 0 and self.arena:
                x = random.uniform(self.arena[0] + 20, self.arena[1] - 20)
                if random.random() < 0.4:
                    x = p.cx + random.uniform(-8, 8)
                scene.add(FallingRock(x, scene.ground_below(x, self.y), scene.cam_xy[1] - 20))
            if self.timer <= 0:
                self._next(scene)
        self.arms = max(0.0, self.arms - 0.05)
        if self.t % 3 == 0:
            scene.particles.add(self.cx + random.uniform(-10, 10), self.y - 2, random.uniform(-0.3, 0.3),
                                random.uniform(-1.6, -0.6), 26, (255, 200, 60), size=2, grav=-0.01, glow=5,
                                color2=(200, 40, 20), kind="puff")

    def _phys(self, scene):
        b = self.body
        b.vy = min(MAX_FALL, b.vy + GRAVITY * 1.1)
        b.move(scene.world, scene.platforms)
        if self.arena:
            b.x = max(self.arena[0], min(self.arena[1] - b.w, b.x))
        self.sync()

    def _slam(self, scene):
        scene.shake.add(0.9)
        audio.play("slam")
        scene.particles.burst(self.cx, self.y + self.h, 30, (255, 150, 60), 4, 40, 3, 0.2, glow=5, kind="chunk",
                              color2=(90, 40, 30), angle=-math.pi / 2, spread=2.8)
        scene.particles.ring(self.cx, self.y + self.h, (255, 200, 120), 60, 24, 3)
        for d in (-1, 1):
            scene.add(Shockwave(self.cx - 6, self.y + self.h, d))
        self.slams += 1
        self.state = "stunned"
        self.timer = 100 if not self.phase2 else 75

    def _next(self, scene):
        options = ["walk", "windup", "volley"] + (["rocks", "windup"] if self.phase2 else [])
        prev = self.state
        nxt = random.choice([o for o in options if o != prev] or options)
        if prev in ("intro",):
            nxt = "windup"
        self.state = nxt
        self.timer = {"walk": 80, "windup": 30 if self.phase2 else 45, "volley": 100, "rocks": 120}[nxt]

    def check_player(self, scene):
        p = scene.player
        if p.dead or self.dying or self.state == "sleep":
            return
        pr = p.rect
        er = self.rect.inflate(-6, -2)
        if not pr.colliderect(er):
            return
        b = p.body
        falling_onto = b.vy > 0 and (b.bottom - b.vy) <= self.y + 10
        if falling_onto or p.dash_timer > 0:
            if self.state == "stunned" and not self.invuln:
                self.take_hit(scene, "stomp", b.cx)
                p.bounce(6.0)
                p.body.vx = -self.dir * 2.5
            elif falling_onto:
                p.bounce(4.2)
                if self.state != "stunned":
                    p.hurt(scene, self.cx)
            else:
                p.hurt(scene, self.cx)
            return
        p.hurt(scene, self.cx)

    def take_hit(self, scene, how, src_x=None):
        if self.dying or self.state != "stunned" or self.invuln:
            if how == "fire":
                scene.particles.burst(self.cx, self.cy, 4, (200, 200, 200), 1, 12, 1, 0)
            return how == "fire"
        self.hp -= 1
        self.hit_flash = 14
        self.invuln = 40
        scene.freeze(8)
        scene.shake.add(0.6)
        scene.flash(0.25, (255, 200, 150))
        audio.play("hurt")
        scene.particles.burst(self.cx, self.y, 22, (255, 200, 80), 3.5, 36, 2, 0.15, glow=5)
        if self.hp <= 0:
            self.dying = 160
            self.state = "dead"
            scene.boss_defeated(self)
            audio.play("roar")
        else:
            self.state = "stunned"
            self.timer = 8
            if self.hp == 3:
                scene.popup(self.cx, self.y - 16, "ENRAGED!", (255, 120, 60))
                audio.play("roar")
        return True

    def update(self, scene):
        if self.dying:
            self.t += 1
            self.dying -= 1
            if self.dying % 8 == 0:
                x = self.cx + random.uniform(-20, 20)
                y = self.cy + random.uniform(-20, 20)
                scene.particles.burst(x, y, 16, (255, 180, 60), 3, 30, 3, 0.05, glow=6)
                scene.particles.ring(x, y, (255, 230, 160), 20, 16)
                audio.play("explode", 0.6)
                scene.shake.add(0.3)
            if self.dying <= 0:
                self.alive = False
                scene.particles.burst(self.cx, self.cy, 60, (255, 200, 90), 5, 60, 3, 0.05, glow=8)
                scene.particles.ring(self.cx, self.cy, (255, 255, 255), 120, 40, 3)
                scene.flash(0.8, (255, 255, 255))
                for i in range(30):
                    scene.add(Coin(self.cx, self.cy, random.uniform(-4, 4), random.uniform(-6, -2), physics=True))
                scene.add(Heart(self.cx - 8, self.y))
            return
        super().update(scene)

    def draw(self, surf, cam, glow_surf):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        t = self.t
        shake = random.randint(-1, 1) if self.dying else 0
        x += shake
        stunned = self.state == "stunned"
        heat = 0.35 if stunned else 0.8 + 0.2 * math.sin(t * 0.1)
        if self.dying:
            heat = 1.0
        g = glow(int(50 + 10 * heat), (int(150 * heat), int(50 * heat), 10))
        glow_surf.blit(g, (x + 18 - g.get_width() // 2, y + 20 - g.get_height() // 2), special_flags=pg.BLEND_ADD)
        rock = (64, 48, 52) if not self.hit_flash else (255, 255, 255)
        rock_hi = (100, 80, 82)
        lava = lerp_color((120, 60, 50), (255, 150, 40), heat)
        # legs
        ph = math.sin(t * 0.15) * 2 if self.state == "walk" else 0
        surf.fill(rock, (x + 6, y + 32 + int(ph), 9, 8 - int(ph)))
        surf.fill(rock, (x + 21, y + 32 - int(ph), 9, 8 + int(ph)))
        # body
        body = [(x + 2, y + 14), (x + 8, y + 6), (x + 28, y + 6), (x + 34, y + 14), (x + 32, y + 34), (x + 4, y + 34)]
        pg.draw.polygon(surf, rock, body)
        pg.draw.line(surf, rock_hi, (x + 8, y + 7), (x + 27, y + 7))
        # lava cracks
        for (a, b2) in (((10, 12), (14, 20)), ((14, 20), (11, 28)), ((24, 10), (22, 18)), ((22, 18), (27, 26)), ((17, 24), (19, 31))):
            pg.draw.line(surf, lava, (x + a[0], y + a[1]), (x + b2[0], y + b2[1]))
        # arms (fists)
        lift = int(self.arms * 8)
        for side in (-1, 1):
            ax = x + 18 + side * 20
            ay = y + 18 - (lift if side == self.dir else 0)
            pg.draw.circle(surf, rock, (ax, ay), 6)
            pg.draw.circle(surf, lava, (ax, ay), 2)
        # face
        ey = y + 14
        if stunned:
            for ex in (x + 12, x + 22):
                pg.draw.line(surf, (255, 230, 150), (ex - 2, ey - 2), (ex + 2, ey + 2))
                pg.draw.line(surf, (255, 230, 150), (ex - 2, ey + 2), (ex + 2, ey - 2))
            # stars circling
            for i in range(3):
                a = t * 0.12 + i * 2.1
                surf.fill((255, 240, 120), (x + 18 + int(math.cos(a) * 12), y - 2 + int(math.sin(a) * 3), 2, 2))
        else:
            for ex in (x + 12 + self.dir * 2, x + 22 + self.dir * 2):
                surf.fill((255, 240, 160), (ex - 2, ey - 1, 4, 3))
                surf.fill((255, 90, 20), (ex - 1 + self.dir, ey, 2, 2))
            pg.draw.line(surf, (30, 20, 24), (x + 9, ey - 4), (x + 15, ey - 2))
            pg.draw.line(surf, (30, 20, 24), (x + 27, ey - 4), (x + 21, ey - 2))
        surf.fill(lava, (x + 13, y + 22, 10, 2))
        # crown of fire
        for i in range(5):
            cx = x + 8 + i * 5
            h = 6 + int(4 * math.sin(t * 0.3 + i * 1.7)) + (i == 2) * 4
            if stunned:
                h //= 3
            pg.draw.polygon(surf, (255, 120, 30), [(cx - 3, y + 7), (cx, y + 6 - h), (cx + 3, y + 7)])
            pg.draw.polygon(surf, (255, 230, 120), [(cx - 1, y + 7), (cx, y + 9 - h), (cx + 1, y + 7)])
