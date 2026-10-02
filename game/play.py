"""The gameplay scene."""
import math
import random

import pygame as pg

from . import audio, font, themes, tilerender, ui, save
from .backgrounds import Background
from .entities import (Coin, Gem, Heart, PowerUp, Chest, Block, MovingPlatform, CrumblePlatform, Spring, Lava,
                       Checkpoint, Portal, Lantern, Crystal, Fireball, Sign, RetroHero, Gate)
from .enemies import Slime, Beetle, Bat, Spitter, Wisp, MoltenKing
from .fx import Particles, Shaker, glow, lerp_color
from .player import Player
from .scene import Scene
from .settings import TILE, VIEW_W, VIEW_H
from .world import World

ENEMIES = {"g": Slime, "k": Beetle, "b": Bat, "t": Spitter, "q": Wisp, "K": MoltenKing}
DUST = {"meadow": (226, 214, 190), "caves": (150, 140, 190), "sunset": (240, 200, 160), "frost": (240, 248, 255),
        "volcano": (130, 110, 110), "legacy": (226, 214, 190)}
PLATFORM_COLS = {
    "meadow": ((150, 104, 66), (96, 62, 40), (196, 146, 96)),
    "caves": ((90, 84, 140), (50, 46, 86), (150, 220, 210)),
    "sunset": ((176, 110, 90), (110, 60, 60), (240, 190, 140)),
    "frost": ((140, 170, 210), (80, 100, 150), (240, 250, 255)),
    "volcano": ((90, 70, 70), (40, 30, 34), (255, 140, 60)),
}


class PlayScene(Scene):
    def __init__(self, app, level, index=None, on_exit=None, test_mode=False):
        super().__init__(app)
        self.level = level
        self.index = index
        self.on_exit = on_exit
        self.test_mode = test_mode
        self.theme_name = level.theme if level.theme in themes.THEMES else "meadow"
        self.theme = themes.get(self.theme_name)
        self.world = World(level)
        self.tiles, self.static_lights, self.grass = tilerender.bake(self.world, self.theme)
        self.bg = Background(self.theme_name, self.theme, self.world.px_h, seed=hash(level.name) & 0xffff)
        self.particles = Particles()
        self.shake = Shaker()
        self.dust_color = DUST.get(self.theme_name, (230, 220, 200))
        self.glow_surf = pg.Surface((VIEW_W, VIEW_H))
        self.light_surf = pg.Surface((VIEW_W, VIEW_H))
        self.world_surf = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        self.vignette = ui.vignette(0.5 if self.theme["darkness"] else 0.35)
        self.entities = []
        self.platforms = []
        self.stats = dict(coins=0, score=0, enemies=0, deaths=0, time=0, chests=0)
        self.gems_found = set()
        self.total_gems = 0
        self.boss = None
        self.boss_bar = 0.0
        self.arena = None
        self.player = None
        self._spawn_all()
        if self.player is None:
            self.player = Player(2 * TILE, (self.world.h - 3) * TILE)
        self.checkpoint = (self.player.body.x, self.player.body.y)
        self.cam_x = self.player.body.cx - VIEW_W / 2
        self.cam_y = self.player.body.cy - VIEW_H * 0.6
        self.look = 0.0
        self._clamp_cam()
        self.freeze_frames = 0
        self.flash_a = 0.0
        self.flash_col = (255, 255, 255)
        self.state = "play"
        self.state_t = 0
        self.t = 0
        self.banner_t = 0
        self.pause_menu = None
        self.results = None
        self.slowmo = 0
        self.inp = app.inp
        self.iris = ui.Iris()
        self.iris.k = 1.0
        self.iris.open(self._player_screen(), 0.04)
        audio.music(level.meta.get("music", self.theme_name))

    # ------------------------------------------------------------ spawning
    def _spawn_all(self):
        w = self.world
        power = self.level.meta.get("powerup", "fire")
        powers = [p.strip() for p in power.split(",")]
        pi = 0
        pc = PLATFORM_COLS.get(self.theme_name, PLATFORM_COLS["meadow"])
        for ch, tx, ty in w.spawns:
            x, y = tx * TILE, ty * TILE
            e = None
            if ch == "P":
                self.player = Player(x, y)
            elif ch == "o":
                e = Coin(x, y)
            elif ch == "*":
                e = Gem(x, y, self.total_gems)
                self.total_gems += 1
            elif ch == "h":
                e = Heart(x, y)
            elif ch == "$":
                e = Chest(x, y)
            elif ch in "B?!":
                e = Block(x, y, ch, tx, ty, powers[pi % len(powers)])
                if ch == "!":
                    pi += 1
            elif ch == "m":
                e = MovingPlatform(x, y, False, w, tx, ty)
                e.theme_cols = pc
            elif ch == "M":
                e = MovingPlatform(x, y, True, w, tx, ty)
                e.theme_cols = pc
            elif ch == "x":
                e = CrumblePlatform(x, y)
            elif ch == "s":
                e = Spring(x, y)
            elif ch == "~":
                e = Lava(x, y, surface=w.level.rows[ty - 1][tx] != "~" if ty > 0 else True)
            elif ch == "C":
                e = Checkpoint(x, y)
            elif ch == "E":
                e = Portal(x, y)
            elif ch == "l":
                e = Lantern(x, y)
            elif ch == "c":
                e = Crystal(x, y)
            elif ch in "123456789":
                e = Sign(x, y, self.level.meta.get("sign" + ch, "..."))
            elif ch == "R":
                e = RetroHero(x, y)
            elif ch in ENEMIES:
                e = ENEMIES[ch](x, y, self.theme_name)
                if ch == "K":
                    self.boss = e
            if e is not None:
                self.add(e)
        self.gate = None
        if self.boss is not None:
            for e in self.entities:
                if isinstance(e, Portal):
                    e.locked = True
            if "arena" in self.level.meta:
                l, r = (int(v) for v in self.level.meta["arena"].split(","))
            else:
                # arena = walls left/right of the boss on its floor row
                ty = int(self.boss.body.bottom // TILE) - 1
                l = r = int(self.boss.cx // TILE)
                while l > 0 and not w.solid(l - 1, ty):
                    l -= 1
                while r < w.w - 1 and not w.solid(r + 1, ty):
                    r += 1
                r += 1
            self.boss.arena = (l * TILE, r * TILE)
            if "gate" in self.level.meta:
                gx = int(self.level.meta["gate"])
                floor = int(self.boss.body.bottom // TILE)
                rows = []
                y = floor - 1
                while y > 0 and not w.solid(gx, y):
                    rows.insert(0, y)
                    y -= 1
                self.gate = self.add(Gate(gx, rows))

    def add(self, e):
        self.entities.append(e)
        if e.solid:
            self.platforms.append(e)
        return e

    # ------------------------------------------------------------ helpers used by entities
    @property
    def cam_xy(self):
        return (self.cam_x, self.cam_y)

    def freeze(self, n):
        self.freeze_frames = max(self.freeze_frames, n)

    def flash(self, a, col):
        self.flash_a = max(self.flash_a, a)
        self.flash_col = col

    def popup(self, x, y, text, col=(255, 255, 255)):
        self.particles.text(x, y, text, col)

    def count_fireballs(self):
        return sum(1 for e in self.entities if isinstance(e, Fireball))

    def spawn_fireball(self, p):
        self.add(Fireball(p.body.cx + p.facing * 6, p.body.cy - 2, p.facing))

    def collect_coin(self, x, y, silent=False):
        self.stats["coins"] += 1
        self.stats["score"] += 10
        self.particles.sparkle(x, y, (255, 230, 120), 5)
        audio.play("coin", 0.55)
        if self.stats["coins"] % 50 == 0:
            p = self.player
            if p.hearts < p.max_hearts:
                p.hearts += 1
                self.popup(x, y - 10, "+1 HEART", (255, 140, 160))
                audio.play("heart")

    def collect_gem(self, g):
        self.gems_found.add(g.index)
        self.stats["score"] += 1000
        audio.play("gem")
        self.particles.ring(g.cx, g.cy, (200, 170, 255), 40, 30, 2)
        self.particles.burst(g.cx, g.cy, 30, (210, 180, 255), 3, 40, 2, 0.03, glow=6, kind="star")
        self.popup(g.cx, g.y - 10, f"SHARD {len(self.gems_found)}/{max(3, self.total_gems)}", (220, 200, 255))
        self.freeze(5)
        self.flash(0.2, (200, 170, 255))

    def collect_heart(self, x, y):
        p = self.player
        if p.hearts < p.max_hearts:
            p.hearts += 1
            self.popup(x, y - 8, "+1", (255, 140, 160))
        else:
            self.stats["score"] += 500
            self.popup(x, y - 8, "500", (255, 140, 160))
        audio.play("heart")
        self.particles.burst(x, y, 12, (255, 120, 150), 2, 30, 2, 0, glow=4)

    def collect_power(self, pu):
        p = self.player
        names = {"fire": "FIRE ORB  -  PRESS F", "feather": "FEATHER  -  DOUBLE JUMP", "shield": "SHIELD BUBBLE"}
        setattr(p, pu.kind, True)
        if pu.kind == "feather":
            p.jumps = 1
        self.popup(pu.cx, pu.y - 10, names[pu.kind], PowerUp.COLORS[pu.kind])
        audio.play("powerup")
        self.particles.ring(pu.cx, pu.cy, PowerUp.COLORS[pu.kind], 30, 24, 2)
        self.particles.burst(pu.cx, pu.cy, 20, PowerUp.COLORS[pu.kind], 2.5, 34, 2, 0, glow=5)
        self.flash(0.25, PowerUp.COLORS[pu.kind])
        self.stats["score"] += 500

    def set_checkpoint(self, cp):
        self.checkpoint = (cp.x, cp.y + cp.h - Player.H)
        p = self.player
        if p.hearts < p.max_hearts:
            p.hearts = max(p.hearts, min(p.max_hearts, p.hearts + 1))

    def bump_tile(self, tx, ty, player):
        for e in self.entities:
            if isinstance(e, Block) and e.alive and e.tx == tx and e.ty == ty:
                e.hit(self)
                return
        if self.world.solid(tx, ty):
            self.particles.dust(tx * TILE + 8, (ty + 1) * TILE, 2, self.dust_color)

    def dash_into(self, tx, ty):
        for e in self.entities:
            if isinstance(e, Block) and e.alive and e.kind == "B" and e.tx == tx and e.ty in (ty, ty - 1, ty + 1):
                if abs(e.ty - ty) <= 1:
                    e.hit(self)

    def dash_down(self, body):
        ty = int((body.bottom + 2) // TILE)
        hit = False
        for e in self.entities:
            if isinstance(e, Block) and e.alive and e.kind == "B" and e.ty == ty and \
                    body.x - 8 <= e.x + TILE and e.x <= body.x + body.w + 8:
                e.hit(self)
                hit = True
        return hit

    def kill_enemies_above(self, block):
        r = pg.Rect(block.x, block.y - 4, TILE, 6)
        for e in self.entities:
            if e.enemy and e.alive and not e.dying and e.rect.colliderect(r):
                e.take_hit(self, "bump", block.cx)

    def ground_below(self, x, y):
        tx = int(x // TILE)
        ty = int(y // TILE)
        while ty < self.world.h and not self.world.solid(tx, ty):
            ty += 1
        return ty * TILE

    def start_boss(self, boss):
        self.arena = boss.arena
        if self.gate:
            self.gate.close(self)
        audio.music("boss")
        self.popup(boss.cx, boss.y - 20, boss.name, (255, 160, 90))

    def boss_defeated(self, boss):
        self.slowmo = 120
        self.stats["enemies"] += 1
        self.stats["score"] += boss.score
        audio.music(None)

    def finish_level(self, portal):
        if self.state != "play":
            return
        self.state = "warp"
        self.state_t = 0
        self.portal = portal
        self.player.frozen = True
        audio.play("portal")

    # ------------------------------------------------------------ update
    def update(self):
        inp = self.inp
        self.iris.update()
        if self.state == "paused":
            self.pause_menu.update(inp, audio.play)
            if inp.pressed("pause"):
                self.state = "play"
                audio.play("back")
            return
        if self.state == "results":
            self.results.update(inp)
            self.particles.update()
            self.bg.update()
            return
        if inp.pressed("pause") and self.state == "play":
            self._open_pause()
            return
        if self.freeze_frames > 0:
            self.freeze_frames -= 1
            self.shake.update()
            return
        if self.slowmo > 0:
            self.slowmo -= 1
            if self.slowmo % 3:
                self.particles.update()
                return
        self.t += 1
        self.state_t += 1
        self.banner_t += 1
        if self.state == "play":
            self.stats["time"] += 1
        p = self.player
        for e in self.platforms:
            e.update(self)
        p.update(inp, self)
        for e in list(self.entities):
            if not e.solid and (e.on_screen(self.cam_xy, 120) or isinstance(e, (MoltenKing, Fireball))):
                e.update(self)
            elif not e.solid and getattr(e, "awake", False):
                e.update(self)
        self.entities = [e for e in self.entities if e.alive]
        self.platforms = [e for e in self.platforms if e.alive]
        # hazards
        if not p.dead and not p.frozen:
            hz = self.world.hazard_at(p.rect.inflate(-2, 0))
            if hz == "spike":
                if p.hurt(self, p.body.cx - p.facing):
                    p.body.vy = -4.2
            if p.body.y > self.world.px_h + 8:
                p.die(self)
                p.body.y = self.world.px_h + 40
        # death -> respawn
        if p.dead and p.dead_timer == 60:
            self.iris.close(self._respawn, self._player_screen(), 0.06)
        # warp into portal
        if self.state == "warp":
            pr = self.portal
            b = p.body
            b.x += (pr.cx - b.cx) * 0.12
            b.y += (pr.cy - b.cy) * 0.12
            p.warp = min(1.0, self.state_t / 50)
            p.t += 1
            if self.state_t % 2 == 0:
                self.particles.sparkle(pr.cx, pr.cy, (220, 200, 255), 3)
            if self.state_t == 55:
                self.flash(0.9, (255, 255, 255))
                self.particles.ring(pr.cx, pr.cy, (255, 255, 255), 80, 30, 3)
                self._show_results()
        self.particles.update()
        self.shake.update()
        self.bg.update()
        self._camera()
        self.flash_a = max(0.0, self.flash_a - 0.04)
        if self.boss is not None and self.arena:
            self.boss_bar = min(1.0, self.boss_bar + 0.03) if self.boss.alive else max(0.0, self.boss_bar - 0.03)
            if not self.boss.alive and self.boss_bar <= 0:
                self.arena = None
                for e in self.entities:
                    if isinstance(e, Portal) and e.locked:
                        e.locked = False
                        self.particles.ring(e.cx, e.cy, (220, 200, 255), 60, 40, 3)
                        self.popup(e.cx, e.y - 10, "THE WAY HOME IS OPEN", (220, 200, 255))
                        audio.play("checkpoint")
                audio.music("volcano")

    def _respawn(self):
        p = self.player
        old = p
        x, y = self.checkpoint
        self.player = Player(x, y)
        self.player.body.x, self.player.body.y = x, y
        self.player.max_hearts = old.max_hearts
        self.player.hearts = old.max_hearts
        self.player.feather = old.feather
        self.player.facing = 1
        self.player.invuln = 60
        self.stats["deaths"] += 1
        self.cam_x = self.player.body.cx - VIEW_W / 2
        self.cam_y = self.player.body.cy - VIEW_H * 0.6
        self._clamp_cam()
        self.iris.open(self._player_screen(), 0.05)
        if self.boss and self.boss.alive and self.boss.state != "sleep":
            # reset the fight
            b = self.boss
            b.state = "sleep"
            b.hp = b.max_hp
            b.body.x = (b.arena[0] + b.arena[1]) / 2 + 40
            b.sync()
            self.arena = None
            self.boss_bar = 0
            if self.gate:
                self.gate.open(self)
            audio.music(self.level.meta.get("music", self.theme_name))
            for e in self.entities:
                if e.__class__.__name__ in ("Shockwave", "FallingRock", "Seed"):
                    e.alive = False

    def _player_screen(self):
        b = self.player.body
        return (b.cx - self.cam_x, b.cy - self.cam_y)

    def _camera(self):
        p = self.player
        b = p.body
        if p.dead:
            return
        self.look += (p.facing * 34 - self.look) * 0.03
        tx = b.cx - VIEW_W / 2 + self.look + b.vx * 6
        ty = b.cy - VIEW_H * 0.58
        self.cam_x += (tx - self.cam_x) * 0.1
        dy = ty - self.cam_y
        k = 0.06 if b.on_ground else (0.1 if b.vy > 3 else 0.03)
        self.cam_y += dy * k
        self._clamp_cam()

    def _clamp_cam(self):
        w = self.world
        lo, hi = 0, w.px_w - VIEW_W
        if self.arena:
            lo = max(lo, self.arena[0] - 16)
            hi = min(hi, max(lo, self.arena[1] + 16 - VIEW_W))
        self.cam_x = max(lo, min(hi, self.cam_x))
        if w.px_h <= VIEW_H:
            self.cam_y = w.px_h - VIEW_H
        else:
            self.cam_y = max(0, min(w.px_h - VIEW_H, self.cam_y))

    # ------------------------------------------------------------ pause / results
    def _open_pause(self):
        self.state = "paused"
        audio.play("blip")

        def resume():
            self.state = "play"

        def restart():
            self.app.replace(PlayScene(self.app, self.level, self.index, self.on_exit, self.test_mode))

        def quit_():
            self._exit()
        self.pause_menu = ui.Menu([("RESUME", resume), ("RESTART", restart),
                                   ("BACK TO EDITOR" if self.test_mode else "QUIT TO MAP", quit_)], 128, 16)

    def _exit(self, completed=False):
        if self.on_exit:
            self.on_exit(self, completed)
        else:
            self.app.pop()

    def _show_results(self):
        self.state = "results"
        audio.play("fanfare")
        audio.music("map")
        self.results = Results(self)

    # ------------------------------------------------------------ draw
    def draw(self, surf):
        sx, sy = self.shake.offset()
        cx, cy = int(self.cam_x + sx), int(self.cam_y + sy)
        cam = (cx, cy)
        g = self.glow_surf
        g.fill((0, 0, 0))
        self.bg.draw(surf, cx, cy, g)
        dark = bool(self.theme["darkness"])
        canvas = surf
        if dark:
            # the world is drawn on its own layer so lighting doesn't crush the backdrop
            surf = self.world_surf
            surf.fill((0, 0, 0, 0))
            if self.bg.name == "caves":
                surf.fill((*self.theme["dirt_dark"], 120))
        # tiles
        surf.blit(self.tiles, (0, 0), pg.Rect(cx, cy, VIEW_W, VIEW_H))
        self._draw_grass(surf, cam)
        visible = [e for e in self.entities if e.on_screen(cam)]
        for e in visible:
            if e.layer == 0:
                e.draw(surf, cam, g)
        for e in visible:
            if e.layer == 1 and not e.enemy:
                e.draw(surf, cam, g)
        for e in visible:
            if e.enemy:
                e.draw(surf, cam, g)
        self.player.draw(surf, cam, g)
        self.particles.draw(surf, cam, g)
        # lighting
        if dark:
            self._lighting(surf, cam, visible)
            canvas.blit(surf, (0, 0))
            surf = canvas
        surf.blit(g, (0, 0), special_flags=pg.BLEND_ADD)
        self.bg.draw_front(surf, cx, cy, g)
        if self.theme.get("grade"):
            surf.fill(self.theme["grade"], special_flags=pg.BLEND_RGB_ADD)
        self.particles.draw_texts(surf, cam)
        surf.blit(self.vignette, (0, 0))
        if self.flash_a > 0.01:
            f = pg.Surface((VIEW_W, VIEW_H))
            f.fill(self.flash_col)
            f.set_alpha(int(255 * self.flash_a))
            surf.blit(f, (0, 0))
        if self.state != "results":
            ui.hud(surf, self)
            if self.boss is not None and self.boss_bar > 0:
                ui.boss_bar(surf, self.boss, self.t, self.boss_bar)
        self._banner(surf)
        if self.state == "paused":
            self._draw_pause(surf)
        if self.state == "results":
            self.results.draw(surf)
        self.iris.draw(surf)

    def _draw_grass(self, surf, cam):
        ox, oy = cam
        b = self.player.body
        t = self.t * 0.05
        for x, y, h, col in self.grass:
            sx = x - ox
            if sx < -4 or sx > VIEW_W + 4:
                continue
            sy = y - oy
            if sy < -8 or sy > VIEW_H + 8:
                continue
            sway = math.sin(t + x * 0.21) * 1.2
            dx = x - b.cx
            if abs(dx) < 10 and abs(b.bottom - y) < 6:
                sway += (10 - abs(dx)) * (1 if dx > 0 else -1) * 0.45
            pg.draw.line(surf, col, (sx, sy), (sx + sway, sy - h))

    def _lighting(self, surf, cam, visible):
        L = self.light_surf
        L.fill(self.theme.get("ambient", (40, 40, 60)))
        ox, oy = cam
        add = pg.BLEND_ADD
        b = self.player.body
        if not self.player.dead or self.player.dead_timer < 40:
            r = 92 + int(math.sin(self.t * 0.05) * 3)
            gl = glow(r, (190, 170, 150))
            L.blit(gl, (b.cx - ox - r, b.cy - oy - r), special_flags=add)
        for x, y, r, col in self.static_lights:
            sx, sy = x - ox, y - oy
            if -r < sx < VIEW_W + r and -r < sy < VIEW_H + r:
                gl = glow(r * 2, col)
                L.blit(gl, (sx - r * 2, sy - r * 2), special_flags=add)
        for e in visible:
            light = getattr(e, "light_now", None) or e.light
            if light:
                r, col = light
                gl = glow(r, tuple(min(255, c * 2) for c in col))
                L.blit(gl, (e.cx - ox - r, e.cy - oy - r), special_flags=add)
        for p in self.particles.items:
            if p.glow:
                r = p.glow * 3
                L.blit(glow(r, (90, 70, 50)), (p.x - ox - r, p.y - oy - r), special_flags=add)
        surf.blit(L, (0, 0), special_flags=pg.BLEND_RGB_MULT)

    def _banner(self, surf):
        t = self.banner_t
        if t > 230 or self.test_mode and t > 150:
            return
        k_in = min(1.0, t / 25)
        k_out = max(0.0, (t - 170) / 30)
        k = (1 - (1 - k_in) ** 3) * (1 - k_out ** 2)
        bar = int(20 * k)
        surf.fill((8, 6, 16), (0, 0, VIEW_W, bar))
        surf.fill((8, 6, 16), (0, VIEW_H - bar, VIEW_W, bar))
        x = int(-260 + (VIEW_W / 2 + 260) * (1 - (1 - k_in) ** 4)) if k_out == 0 else int(VIEW_W / 2 + k_out * 400)
        y = VIEW_H // 2 - 30
        w = 300
        band = pg.Surface((w, 44), pg.SRCALPHA)
        band.fill((14, 10, 28, 200))
        surf.blit(band, (x - w // 2, y))
        surf.fill(ui.ACCENT, (x - w // 2, y, w, 1))
        surf.fill(ui.ACCENT, (x - w // 2, y + 43, w, 1))
        sub = self.level.meta.get("subtitle", "")
        world_label = self.level.meta.get("label", "")
        if world_label:
            font.draw(surf, world_label, (x, y + 6), (200, 180, 230), outline=ui.INK, align="center")
        font.draw(surf, self.level.name, (x, y + 16), ui.PALE, 2, outline=ui.INK, align="center")
        if sub:
            font.draw(surf, sub, (x, y + 34), (160, 150, 190), outline=ui.INK, align="center")

    def _draw_pause(self, surf):
        dim = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        dim.fill((8, 6, 20, 170))
        surf.blit(dim, (0, 0))
        font.draw_wave(surf, "PAUSED", (VIEW_W // 2, 80), self.t * 0.02 + pg.time.get_ticks() / 1000, ui.PALE, 3, 2, 3,
                       outline=ui.INK)
        self.pause_menu.draw(surf)
        y = 196
        for line in ("MOVE  ARROWS / WASD      JUMP  SPACE / K / C",
                     "DASH  SHIFT / X / L      FIRE  F / J / V",
                     "DOWN + JUMP  DROP THROUGH PLATFORMS"):
            font.draw(surf, line, (VIEW_W // 2, y), (150, 140, 180), outline=ui.INK, align="center")
            y += 11


class Results:
    def __init__(self, scene):
        self.s = scene
        self.t = 0
        st = scene.stats
        self.shards = len(scene.gems_found)
        self.time = st["time"] / 60
        deaths = st["deaths"]
        if self.shards >= 3 and deaths == 0:
            self.rank = "S"
        elif self.shards >= 2 and deaths <= 2:
            self.rank = "A"
        elif deaths <= 5:
            self.rank = "B"
        else:
            self.rank = "C"
        self.rows = [
            ("TIME", f"{int(self.time // 60)}:{int(self.time % 60):02d}"),
            ("COINS", f"{st['coins']}"),
            ("STAR SHARDS", f"{self.shards}/{max(3, scene.total_gems)}"),
            ("FOES DEFEATED", f"{st['enemies']}"),
            ("CHESTS", f"{st['chests']}"),
            ("FALLS", f"{deaths}"),
            ("SCORE", f"{st['score']}"),
        ]
        self.new_best = False
        if scene.level.path and not scene.test_mode:
            self.new_best = save.record_level(scene.level.path, self.time, scene.gems_found, self.rank, st["coins"], st["score"])

    def update(self, inp):
        self.t += 1
        if self.t > 30 and self.t % 6 == 0 and self.t < 30 + len(self.rows) * 12:
            audio.play("blip", 0.5)
        if self.t == 30 + len(self.rows) * 12 + 10:
            audio.play("slam", 0.6)
            self.s.shake.add(0.4)
            self.s.particles.burst(VIEW_W - 110 + self.s.cam_x, 120 + self.s.cam_y, 30, (255, 220, 120), 3, 40, 2, 0.05, glow=5)
        if self.t > 60 and (inp.pressed("confirm") or inp.pressed("jump")):
            inp.consume("confirm")
            inp.consume("jump")
            audio.play("confirm")
            self.s.iris.close(lambda: self.s._exit(True), None, 0.05)

    def draw(self, surf):
        dim = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        dim.fill((8, 6, 20, min(190, self.t * 8)))
        surf.blit(dim, (0, 0))
        k = min(1.0, self.t / 25)
        y0 = int(-60 + 90 * (1 - (1 - k) ** 3))
        font.draw_wave(surf, "LEVEL CLEAR!", (VIEW_W // 2, y0), self.t / 60, ui.GOLD, 3, 2, 4, outline=ui.INK)
        ui.panel(surf, (VIEW_W // 2 - 150, 66, 300, 150), 210, ui.ACCENT)
        for i, (label, value) in enumerate(self.rows):
            appear = self.t - 30 - i * 12
            if appear < 0:
                continue
            y = 78 + i * 18
            off = max(0, 12 - appear) * 3
            font.draw(surf, label, (VIEW_W // 2 - 136 + off, y), (170, 160, 200), outline=ui.INK)
            font.draw(surf, value, (VIEW_W // 2 + 30 + off, y), ui.PALE, outline=ui.INK, align="right")
            if label == "STAR SHARDS":
                for j in range(3):
                    ui.draw_star_icon(surf, VIEW_W // 2 + 44 + j * 12, y + 3, j < self.shards)
        rank_t = self.t - (30 + len(self.rows) * 12 + 10)
        if rank_t >= 0:
            sc = max(4, 10 - rank_t)
            col = {"S": (255, 214, 90), "A": (140, 230, 255), "B": (180, 255, 160), "C": (220, 200, 220)}[self.rank]
            cx, cy = VIEW_W // 2 + 100, 136
            g = glow(40, tuple(c // 3 for c in col))
            surf.blit(g, (cx - 40, cy - 40), special_flags=pg.BLEND_ADD)
            pg.draw.circle(surf, col, (cx, cy), 26, 2)
            font.draw(surf, self.rank, (cx, cy - 7 * sc // 2), col, sc, outline=ui.INK, align="center")
            font.draw(surf, "RANK", (cx, cy + 30), col, outline=ui.INK, align="center")
            if self.new_best:
                font.draw(surf, "NEW BEST!", (cx, cy - 40), ui.GOLD, outline=ui.INK, align="center")
        if self.t > 60 and (self.t // 20) % 2:
            font.draw(surf, "PRESS ENTER", (VIEW_W // 2, 228), ui.PALE, outline=ui.INK, align="center")
