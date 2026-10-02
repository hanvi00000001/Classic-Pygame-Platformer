"""The Wayfarer: a hooded hero with a physics-simulated scarf.
Coyote time, jump buffering, variable jump height, wall slide / wall jump,
an 8-way dash, double jump (feather), fire orbs and a shield bubble."""
import math
import random

import pygame as pg

from . import audio
from .physics import Body
from .settings import (GRAVITY, MAX_FALL, RUN_SPEED, RUN_ACCEL, GROUND_FRICTION, AIR_ACCEL, AIR_FRICTION,
                       ICE_ACCEL, ICE_FRICTION, JUMP_SPEED, JUMP_CUT, COYOTE_FRAMES, JUMP_BUFFER,
                       WALL_SLIDE_SPEED, WALL_JUMP_X, WALL_JUMP_Y, DASH_SPEED, DASH_FRAMES, INVULN_FRAMES,
                       START_HEARTS, TILE)
from .fx import glow

HOOD = (52, 74, 140)
HOOD_HI = (96, 126, 196)
HOOD_DK = (30, 42, 92)
CLOAK = (40, 56, 112)
CLOAK_DK = (26, 34, 76)
FACE = (12, 10, 22)
EYE = (190, 250, 255)
BOOT = (70, 44, 44)
SCARF = (150, 28, 62)
SCARF_HI = (214, 66, 98)
SCARF_DK = (98, 16, 42)
SCARF_SPENT = (110, 110, 130)


class Scarf:
    def __init__(self, x, y, n=9, seg=2.4):
        self.pts = [[x, y] for _ in range(n)]
        self.prev = [[x, y] for _ in range(n)]
        self.seg = seg
        self.wind = 0.0

    def update(self, ax, ay, facing, speed, t):
        self.pts[0] = [ax, ay]
        self.prev[0] = [ax, ay]
        for i in range(1, len(self.pts)):
            p, q = self.pts[i], self.prev[i]
            vx = (p[0] - q[0]) * 0.86
            vy = (p[1] - q[1]) * 0.86
            q[0], q[1] = p[0], p[1]
            wave = math.sin(t * 0.25 + i * 0.9) * 0.06 * (1 + abs(speed))
            p[0] += vx - facing * 0.05 + self.wind * (0.6 + 0.4 * math.sin(t * 0.13 + i))
            p[1] += vy + 0.10 + wave
        for _ in range(3):
            for i in range(1, len(self.pts)):
                a, b = self.pts[i - 1], self.pts[i]
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy) or 0.001
                k = (d - self.seg) / d
                b[0] -= dx * k
                b[1] -= dy * k

    def draw(self, surf, cam, color, hi):
        ox, oy = cam
        pts = [(p[0] - ox, p[1] - oy) for p in self.pts]
        for i in range(len(pts) - 1):
            w = 3 if i < 4 else 2
            pg.draw.line(surf, color, pts[i], pts[i + 1], w)
        for i in range(0, len(pts) - 1, 2):
            pg.draw.line(surf, hi, pts[i], (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * 0.5,
                                            pts[i][1] + (pts[i + 1][1] - pts[i][1]) * 0.5 - 1))
        # forked tail
        a, b = pts[-2], pts[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        pg.draw.line(surf, color, b, (b[0] + dx + dy * 0.6, b[1] + dy - dx * 0.6))
        pg.draw.line(surf, color, b, (b[0] + dx - dy * 0.6, b[1] + dy + dx * 0.6))


class Player:
    W, H = 10, 14

    def __init__(self, x, y):
        self.body = Body(x + (TILE - self.W) / 2, y + TILE - self.H, self.W, self.H)
        self.facing = 1
        self.max_hearts = START_HEARTS
        self.hearts = START_HEARTS
        self.fire = False
        self.feather = False
        self.shield = False
        self.coyote = 0
        self.jump_buffer = 0
        self.jumps = 0
        self.dash_ready = True
        self.dash_timer = 0
        self.dash_dir = (1, 0)
        self.dash_cool = 0
        self.wall_lock = 0
        self.wall_dir = 0
        self.invuln = 0
        self.hurt_timer = 0
        self.fire_cool = 0
        self.sx = self.sy = 1.0
        self.t = 0
        self.run_phase = 0.0
        self.step_timer = 0
        self.afterimages = []
        self.dead = False
        self.dead_timer = 0
        self.dvy = 0.0
        self.blink = 0
        self.frozen = False      # used by cutscenes / portal
        self.warp = 0.0
        self.jumping = False
        self.scarf = Scarf(self.body.cx, self.body.y + 5)
        self.was_ground = True
        self.fall_peak = 0.0

    # ------------------------------------------------------------------
    @property
    def rect(self):
        return self.body.rect

    def bounce(self, strength=4.6, held=False):
        self.body.vy = -(strength + (1.8 if held else 0))
        self.jumping = True
        self.dash_ready = True
        self.jumps = 1 if self.feather else 0
        self.sx, self.sy = 0.8, 1.25

    def update(self, inp, scene):
        self.t += 1
        b = self.body
        if self.dead:
            self.dead_timer += 1
            if self.dead_timer > 24:
                self.dvy += 0.25
                b.y += self.dvy
            return
        if self.frozen:
            self._update_scarf()
            return
        ix = inp.axis_x()
        locked = self.wall_lock > 0
        if locked:
            self.wall_lock -= 1
            ix = 0
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
            ix = 0
        if self.invuln > 0:
            self.invuln -= 1
        if self.dash_cool > 0:
            self.dash_cool -= 1
        if self.fire_cool > 0:
            self.fire_cool -= 1
        if ix:
            self.facing = ix

        if b.on_ground:
            self.coyote = COYOTE_FRAMES
            if not self.dash_ready and self.dash_timer == 0:
                self.dash_ready = True
                scene.particles.sparkle(b.cx, b.y + 4, (255, 120, 150), 4)
            self.jumps = 1 if self.feather else 0
        elif self.coyote > 0:
            self.coyote -= 1
        if inp.pressed("jump"):
            self.jump_buffer = JUMP_BUFFER
        elif self.jump_buffer > 0:
            self.jump_buffer -= 1

        # ---- dashing ----
        if self.dash_timer > 0:
            self.dash_timer -= 1
            b.vx = self.dash_dir[0] * DASH_SPEED
            b.vy = self.dash_dir[1] * DASH_SPEED
            if self.t % 2 == 0:
                self._afterimage()
            scene.particles.add(b.cx + random.uniform(-3, 3), b.cy + random.uniform(-5, 5),
                                -self.dash_dir[0] * 0.6, -self.dash_dir[1] * 0.6, 14, (255, 140, 170),
                                size=2, kind="puff", glow=4)
            if self.dash_timer == 0:
                b.vx *= 0.55
                b.vy *= 0.35
            # dashing down onto / up into breakables
            if self.dash_dir[1] > 0 and b.on_ground:
                if scene.dash_down(b):
                    b.vy = 2.0
                else:
                    self.dash_timer = 0
                    scene.shake.add(0.2)
                    scene.particles.dust(b.cx, b.bottom, 6, scene.dust_color)
            if b.hit_ceiling:
                scene.bump_tile(*b.hit_ceiling, self)
            if b.wall:
                tx = math.floor((b.x + (b.w + 1 if b.wall > 0 else -1)) / TILE)
                ty = math.floor(b.cy / TILE)
                scene.dash_into(tx, ty)
        else:
            on_ice = b.on_ice
            if b.on_ground:
                accel = ICE_ACCEL if on_ice else RUN_ACCEL
                fric = ICE_FRICTION if on_ice else GROUND_FRICTION
            else:
                accel, fric = AIR_ACCEL, AIR_FRICTION
            target = ix * RUN_SPEED
            if locked:
                pass  # keep wall-jump momentum
            elif ix:
                if b.vx * ix < 0 and not on_ice:
                    b.vx += ix * accel * 1.6
                    if b.on_ground and abs(b.vx) > 1.2 and self.t % 3 == 0:
                        scene.particles.dust(b.cx, b.bottom, 1, scene.dust_color, -ix)
                elif abs(b.vx) < RUN_SPEED or b.vx * ix < 0:
                    b.vx += ix * accel
                    if abs(b.vx) > RUN_SPEED and b.vx * ix > 0:
                        b.vx = target
                else:
                    b.vx -= math.copysign(min(abs(b.vx) - RUN_SPEED, fric * 0.3), b.vx)
            else:
                if abs(b.vx) <= fric:
                    b.vx = 0
                else:
                    b.vx -= math.copysign(fric, b.vx)
            # gravity with a floaty apex while jump is held
            g = GRAVITY
            if inp.held["jump"] and abs(b.vy) < 1.0 and self.jumping:
                g *= 0.55
            b.vy = min(MAX_FALL, b.vy + g)

            # wall slide
            self.wall_dir = 0
            if not b.on_ground:
                for side in (-1, 1):
                    if b.touching_wall(scene.world, side):
                        self.wall_dir = side
                if self.wall_dir and ix == self.wall_dir and b.vy > 0:
                    b.vy = min(b.vy, WALL_SLIDE_SPEED)
                    if self.t % 4 == 0:
                        scene.particles.dust(b.x + (b.w if self.wall_dir > 0 else 0), b.y + 4, 1, scene.dust_color)

            # jumping
            if self.jump_buffer > 0:
                if inp.held["down"] and b.on_ground and self._on_oneway(scene):
                    b.drop_timer = 12
                    b.on_ground = False
                    b.y += 1
                    self.jump_buffer = 0
                elif self.coyote > 0:
                    self._jump(scene, JUMP_SPEED)
                elif self.wall_dir:
                    b.vx = -self.wall_dir * WALL_JUMP_X
                    b.vy = -WALL_JUMP_Y
                    self.facing = -self.wall_dir
                    self.wall_lock = 9
                    self.jump_buffer = 0
                    self.jumping = True
                    self.sx, self.sy = 0.75, 1.3
                    scene.particles.dust(b.x + (b.w if self.wall_dir > 0 else 0), b.cy, 5, scene.dust_color, -self.wall_dir)
                    audio.play("walljump", 0.8)
                elif self.jumps > 0:
                    self.jumps -= 1
                    self._jump(scene, JUMP_SPEED * 0.92, double=True)
            if inp.released("jump") and b.vy < 0 and self.jumping:
                b.vy *= JUMP_CUT
                self.jumping = False

            # dash
            if inp.pressed("dash") and self.dash_ready and self.dash_cool == 0:
                dx = ix
                dy = (1 if inp.held["down"] else 0) - (1 if inp.held["up"] else 0)
                if dx == 0 and dy == 0:
                    dx = self.facing
                if b.on_ground and dy > 0:
                    dy = 0
                    dx = dx or self.facing
                n = math.hypot(dx, dy)
                self.dash_dir = (dx / n, dy / n)
                self.dash_timer = DASH_FRAMES
                self.dash_ready = False
                self.dash_cool = 18
                self.jumping = False
                scene.shake.add(0.25)
                scene.freeze(2)
                scene.particles.ring(b.cx, b.cy, (255, 150, 180), 18, 14)
                audio.play("dash")
            # fire
            if inp.pressed("fire") and self.fire and self.fire_cool == 0 and scene.count_fireballs() < 2:
                scene.spawn_fireball(self)
                self.fire_cool = 14
                audio.play("fire", 0.8)

        self.was_ground = b.on_ground
        vy_before = b.vy
        b.move(scene.world, scene.platforms)
        if not self.was_ground:
            self.fall_peak = max(self.fall_peak, vy_before)
        if b.on_ground and not self.was_ground:
            self._land(scene, self.fall_peak)
            self.fall_peak = 0
        if b.on_ground:
            self.jumping = False
        if b.hit_ceiling and self.dash_timer == 0:
            scene.bump_tile(*b.hit_ceiling, self)

        # run cycle + footsteps
        speed = abs(b.vx)
        if b.on_ground and speed > 0.3:
            self.run_phase += speed * 0.22
            self.step_timer += speed
            if self.step_timer > 13:
                self.step_timer = 0
                audio.play("step", 0.35)
                if random.random() < 0.7:
                    scene.particles.dust(b.cx - self.facing * 3, b.bottom, 1, scene.dust_color, -self.facing)
        else:
            self.run_phase = 0
        # squash recovery
        self.sx += (1 - self.sx) * 0.2
        self.sy += (1 - self.sy) * 0.2
        self.blink = self.blink - 1 if self.blink > 0 else (8 if random.random() < 0.006 else 0)
        for a in self.afterimages:
            a[3] -= 1
        self.afterimages = [a for a in self.afterimages if a[3] > 0]
        self._update_scarf()

    def _on_oneway(self, scene):
        b = self.body
        ty = math.floor((b.bottom + 1) / TILE)
        return any(scene.world.get(math.floor(x / TILE), ty) == "-" for x in (b.x + 1, b.x + b.w - 1))

    def _jump(self, scene, speed, double=False):
        b = self.body
        b.vy = -speed
        if b.platform is not None:
            b.vx += b.platform.dx * 0.5
        self.coyote = 0
        self.jump_buffer = 0
        self.jumping = True
        self.sx, self.sy = 0.7, 1.35
        if double:
            scene.particles.ring(b.cx, b.bottom, (255, 255, 255), 12, 14, 1)
            for i in range(8):
                a = math.pi * (0.1 + 0.8 * i / 7)
                scene.particles.add(b.cx, b.bottom, math.cos(a) * 1.5, math.sin(a) * 0.6 + 0.3, 20,
                                    (240, 240, 255), size=2, kind="puff")
            audio.play("jump2", 0.8)
        else:
            scene.particles.dust(b.cx, b.bottom, 6, scene.dust_color)
            audio.play("jump", 0.7)

    def _land(self, scene, fall_speed):
        b = self.body
        k = min(1.0, fall_speed / MAX_FALL)
        self.sx, self.sy = 1 + 0.45 * k, 1 - 0.38 * k
        if fall_speed > 2.2:
            scene.particles.dust(b.cx, b.bottom, int(3 + 6 * k), scene.dust_color)
            audio.play("land", 0.4 + 0.6 * k)
        if fall_speed > 5.6:
            scene.shake.add(0.15)

    def _afterimage(self):
        surf = self._frame()
        mask = pg.mask.from_surface(surf)
        sil = mask.to_surface(setcolor=(255, 90, 140, 255), unsetcolor=(0, 0, 0, 0))
        b = self.body
        self.afterimages.append([sil, b.cx, b.bottom, 14, self.facing])

    def _update_scarf(self):
        b = self.body
        ax = b.cx - self.facing * 1.5
        ay = b.y + 6 + (1 if self.sy < 0.9 else 0)
        self.scarf.update(ax, ay, self.facing, b.vx, self.t)

    # ------------------------------------------------------------------
    def hurt(self, scene, source_x=None, dmg=1):
        if self.invuln > 0 or self.dead or self.dash_timer > 0 or self.frozen:
            return False
        b = self.body
        if self.shield:
            self.shield = False
            self.invuln = 60
            scene.particles.burst(b.cx, b.cy, 20, (140, 230, 255), 2.5, 30, 2, 0, glow=6)
            scene.particles.ring(b.cx, b.cy, (140, 230, 255), 28, 22, 2)
            audio.play("shield")
            scene.shake.add(0.3)
            return True
        self.hearts -= dmg
        self.fire = False
        scene.shake.add(0.55)
        scene.freeze(6)
        scene.flash(0.35, (255, 60, 80))
        audio.play("hurt")
        if self.hearts <= 0:
            self.die(scene)
            return True
        self.invuln = INVULN_FRAMES
        self.hurt_timer = 14
        d = 1 if (source_x is None or b.cx >= source_x) else -1
        b.vx = d * 2.6
        b.vy = -3.6
        self.dash_timer = 0
        scene.particles.burst(b.cx, b.cy, 10, (255, 90, 120), 2.2, 26, 2, 0.1)
        return True

    def die(self, scene):
        if self.dead:
            return
        self.dead = True
        self.dead_timer = 0
        self.dvy = -4.5
        self.hearts = 0
        b = self.body
        scene.particles.burst(b.cx, b.cy, 30, SCARF_HI, 3, 40, 2, 0.05, glow=4)
        scene.particles.ring(b.cx, b.cy, (255, 255, 255), 40, 26, 2)
        scene.shake.add(0.7)
        scene.freeze(10)
        audio.play("death")

    # ------------------------------------------------------------------
    def _frame(self):
        """Draw the hero (facing right) onto a small surface; origin = bottom centre (12, 25)."""
        s = pg.Surface((24, 26), pg.SRCALPHA)
        b = self.body
        airborne = not b.on_ground and not self.dead
        ph = self.run_phase
        bob = 0
        running = b.on_ground and abs(b.vx) > 0.3
        if running:
            bob = -1 if math.sin(ph * 2) > 0.3 else 0
        elif b.on_ground:
            bob = -1 if (self.t // 30) % 2 == 0 else 0
        # feet
        if airborne:
            if b.vy < 0:
                feet = [(9, 23), (14, 22)]
            else:
                feet = [(8, 24), (14, 24)]
        elif running:
            feet = [(11 + math.sin(ph) * 3.5, 25 - max(0, math.cos(ph)) * 2.5),
                    (11 - math.sin(ph) * 3.5, 25 - max(0, -math.cos(ph)) * 2.5)]
        else:
            feet = [(9, 25), (13, 25)]
        for fx, fy in feet:
            s.fill(BOOT, (int(fx) - 1, int(fy) - 2, 4, 2))
            s.fill(CLOAK_DK, (int(fx), int(fy) - 4, 2, 2))
        # cloak
        hem = 22 + bob
        flutter = 0
        if running or airborne:
            flutter = 2 if (self.t // 5) % 2 else 1
        cloak = [(8, 12 + bob), (16, 12 + bob), (18, hem), (13, hem + 1), (6 - flutter, hem)]
        pg.draw.polygon(s, CLOAK, cloak)
        pg.draw.line(s, CLOAK_DK, (6 - flutter, hem), (18, hem))
        pg.draw.line(s, HOOD_HI, (15, 13 + bob), (17, hem - 1))
        # belt / satchel strap
        pg.draw.line(s, (120, 90, 60), (9, 14 + bob), (15, 19 + bob))
        # head / hood
        hy = 2 + bob
        pg.draw.rect(s, HOOD, (7, hy + 1, 11, 10), border_radius=4)
        pg.draw.polygon(s, HOOD, [(9, hy + 2), (4, hy + 9 + (1 if airborne else 0)), (9, hy + 9)])
        pg.draw.line(s, HOOD_HI, (9, hy + 1), (14, hy + 1))
        pg.draw.line(s, HOOD_HI, (7, hy + 4), (7, hy + 7))
        pg.draw.line(s, HOOD_DK, (8, hy + 10), (17, hy + 10))
        # face opening with glowing eyes
        pg.draw.rect(s, FACE, (12, hy + 4, 6, 6), border_radius=2)
        eye_h = 1 if self.blink else 2
        look = 1 if abs(b.vx) > 0.5 else 0
        s.fill(EYE, (13 + look, hy + 6 + (2 - eye_h) // 2, 1, eye_h))
        s.fill(EYE, (16 + look, hy + 6 + (2 - eye_h) // 2, 1, eye_h))
        # scarf knot
        s.fill(SCARF, (8, 11 + bob, 10, 3))
        s.fill(SCARF_HI, (9, 11 + bob, 8, 1))
        return s

    def draw(self, surf, cam, glow_surf):
        b = self.body
        ox, oy = cam
        for sil, x, y, life, facing in self.afterimages:
            img = sil if facing > 0 else pg.transform.flip(sil, True, False)
            img.set_alpha(int(170 * life / 14))
            surf.blit(img, (int(x - 12 - ox), int(y - 25 - oy)))
        if self.invuln > 0 and not self.dead and (self.invuln // 3) % 2 == 0 and self.invuln < INVULN_FRAMES - 8:
            return
        col = SCARF if (self.dash_ready or self.dash_timer > 0) else SCARF_SPENT
        hi = SCARF_HI if self.dash_ready else (150, 150, 170)
        if self.dash_timer > 0:
            col, hi = (255, 160, 190), (255, 255, 255)
        self.scarf.draw(surf, cam, col, hi)
        frame = self._frame()
        if self.invuln > INVULN_FRAMES - 8 and not self.dead:
            frame = pg.mask.from_surface(frame).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        if self.facing < 0:
            frame = pg.transform.flip(frame, True, False)
        sx, sy = self.sx, self.sy
        if self.warp:
            sx *= max(0.05, 1 - self.warp)
            sy *= max(0.05, 1 - self.warp)
        if self.dead:
            frame = pg.transform.rotate(frame, self.dead_timer * 9 if self.dead_timer > 24 else 0)
        if abs(sx - 1) > 0.02 or abs(sy - 1) > 0.02:
            w, h = frame.get_size()
            frame = pg.transform.scale(frame, (max(1, int(w * sx)), max(1, int(h * sy))))
        w, h = frame.get_size()
        if self.dead:
            surf.blit(frame, (int(b.cx - w / 2 - ox), int(b.cy - h / 2 - oy)))
        else:
            surf.blit(frame, (int(b.cx - w / 2 - ox), int(b.bottom - h + 1 - oy)))
        if self.shield:
            r = 13 + math.sin(self.t * 0.15)
            pg.draw.circle(surf, (140, 230, 255), (int(b.cx - ox), int(b.cy - 1 - oy)), int(r), 1)
            glow_surf.blit(glow(18, (20, 60, 80)), (int(b.cx - ox - 18), int(b.cy - oy - 19)), special_flags=pg.BLEND_ADD)
            a = self.t * 0.08
            surf.fill((255, 255, 255), (int(b.cx - ox + math.cos(a) * r), int(b.cy - 1 - oy + math.sin(a) * r), 1, 1))
        if self.fire:
            a = self.t * 0.12
            fx, fy = b.cx - ox + math.cos(a) * 9, b.y - oy - 2 + math.sin(a * 2) * 2
            pg.draw.circle(surf, (255, 170, 60), (int(fx), int(fy)), 2)
            glow_surf.blit(glow(8, (120, 50, 0)), (int(fx - 8), int(fy - 8)), special_flags=pg.BLEND_ADD)
        if self.feather and not b.on_ground and self.jumps > 0 and self.t % 6 == 0:
            pass
        # dim eye glow for dark levels
        glow_surf.blit(glow(6, (30, 50, 55)), (int(b.cx - ox + self.facing * 3 - 6), int(b.y - oy + 1)), special_flags=pg.BLEND_ADD)
