"""Application shell: window, scene stack, title screen, world map, options, credits."""
import math
import os
import random

import pygame as pg

from . import audio, font, save, themes, ui
from .backgrounds import Background
from .fx import Particles, glow, lerp_color
from .inputs import Input
from .player import Player
from .scene import Scene
from .settings import VIEW_W, VIEW_H, TITLE, LEVEL_DIR, FPS, WEB
from .world import Level, list_campaign


class App:
    def __init__(self, headless=False):
        pg.init()
        self.headless = headless
        # SDL (desktop) or CSS (browser) scales the 480x270 canvas up
        self.zoom = 1
        flags = 0 if (headless or WEB) else (pg.SCALED | pg.RESIZABLE)
        size = (VIEW_W * self.zoom, VIEW_H * self.zoom)
        try:
            self.screen = pg.display.set_mode(size, flags, vsync=0 if headless else 1)
        except Exception:
            self.screen = pg.display.set_mode(size, flags)
        pg.display.set_caption(f"{TITLE} - Classic Pygame Platformer (2026 remaster)")
        try:
            pg.display.set_icon(_icon())
        except pg.error:
            pass
        self.canvas = pg.Surface((VIEW_W, VIEW_H))
        self.clock = pg.time.Clock()
        self.inp = Input()
        self.events = []
        self.audio = audio.init()
        st = save.data()["settings"]
        self.audio.sfx_volume = st.get("sfx", 0.7)
        self.audio.set_music_volume(st.get("music", 0.5))
        if st.get("fullscreen") and not headless and not WEB:
            try:
                pg.display.toggle_fullscreen()
            except pg.error:
                pass
        self.running = True
        self.stack = []
        self.push(TitleScene(self))

    # scene stack
    @property
    def scene(self):
        return self.stack[-1]

    def push(self, s):
        self.stack.append(s)

    def pop(self):
        self.stack.pop()
        if not self.stack:
            self.running = False
        else:
            self.scene.enter()

    def replace(self, s):
        self.stack[-1] = s

    def logical(self, pos):
        """Window mouse position -> canvas pixels."""
        return pos[0] // self.zoom, pos[1] // self.zoom

    def mouse(self):
        return self.logical(pg.mouse.get_pos())

    def quit(self):
        self.running = False

    def frame(self):
        self.events = pg.event.get()
        for e in self.events:
            if e.type == pg.QUIT:
                self.running = False
            elif e.type == pg.KEYDOWN and e.key == pg.K_F11 and not WEB:
                try:
                    pg.display.toggle_fullscreen()
                except pg.error:
                    pass
            elif e.type in (pg.JOYDEVICEADDED, pg.JOYDEVICEREMOVED):
                self.inp.refresh_pads()
        self.inp.update()
        scene = self.scene
        scene.update()
        if not self.running or not self.stack:
            return
        self.scene.draw(self.canvas)
        if self.zoom == 1:
            self.screen.blit(self.canvas, (0, 0))
        else:
            pg.transform.scale(self.canvas, self.screen.get_size(), self.screen)
        pg.display.flip()
        self.audio.update(4.0)
        self.clock.tick(FPS)
        self.frames = getattr(self, "frames", 0) + 1
        if WEB and self.frames % 120 == 0:
            try:
                import platform
                platform.window.document.title = f"Wayfarer {self.clock.get_fps():.0f} fps"
            except Exception:
                pass


def _icon():
    p = Player(0, 0)
    p.body.on_ground = True
    s = p._frame()
    icon = pg.Surface((32, 32), pg.SRCALPHA)
    icon.blit(pg.transform.scale(s, (29, 31)), (2, 0))
    return icon


# =================================================================== title
class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = Background("sunset", themes.get("sunset"), VIEW_H, seed=2026)
        self.cam = 0.0
        self.t = 0
        self.particles = Particles()
        self.glow = pg.Surface((VIEW_W, VIEW_H))
        self.hero = Player(96, 170)
        self.hero.body.on_ground = True
        self.hero.scarf.wind = -0.32
        self.vign = ui.vignette(0.55)
        self.iris = ui.Iris()
        self.iris.k = 1.0
        self.iris.open(speed=0.03)
        items = [("PLAY", self.play), ("LEVEL EDITOR", self.editor), ("OPTIONS", self.options)]
        if not WEB:
            items.append(("QUIT", app.quit))
        self.menu = ui.Menu(items, 168, 15)
        self.cliff = self._make_cliff()
        audio.music("title")

    def enter(self):
        audio.music("title")
        self.iris.open(speed=0.05)

    def _make_cliff(self):
        s = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        th = themes.get("sunset")
        pts = [(0, 186), (60, 184), (100, 186), (122, 190), (130, 204), (128, 230), (140, 270), (0, 270)]
        pg.draw.polygon(s, (44, 22, 50), pts)
        pg.draw.lines(s, (90, 50, 80), False, pts[:4], 2)
        rng = random.Random(4)
        for _ in range(26):
            x = rng.randint(4, 118)
            h = rng.randint(3, 8)
            pg.draw.line(s, (70, 36, 70), (x, 186), (x + rng.randint(-2, 2), 186 - h))
        return s

    def play(self):
        self.iris.close(lambda: self.app.push(MapScene(self.app)), speed=0.06)

    def editor(self):
        from .editor import EditorScene
        self.iris.close(lambda: self.app.push(EditorScene(self.app)), speed=0.06)

    def options(self):
        self.app.push(OptionsScene(self.app, self))

    def update(self):
        self.t += 1
        self.cam += 0.35
        self.bg.update()
        self.iris.update()
        if not self.iris.busy or self.iris.target == 0:
            self.menu.update(self.app.inp, audio.play)
        h = self.hero
        h.t += 1
        h.blink = h.blink - 1 if h.blink > 0 else (8 if random.random() < 0.01 else 0)
        h._update_scarf()
        if self.t % 4 == 0:
            self.particles.add(random.uniform(0, VIEW_W), VIEW_H + 4, random.uniform(-0.6, -0.2), random.uniform(-0.7, -0.3),
                               240, (255, 210, 150), size=1, kind="star", glow=4, drag=1.0)
        if self.t % 30 == 0:
            self.particles.add(VIEW_W + 4, random.uniform(20, 160), random.uniform(-1.6, -1.0), random.uniform(-0.1, 0.2),
                               400, (255, 170, 190), size=2, kind="chunk", drag=1.0)
        self.particles.update()

    def draw(self, surf):
        g = self.glow
        g.fill((0, 0, 0))
        self.bg.draw(surf, self.cam, 0, g)
        surf.blit(self.cliff, (0, 0))
        self.hero.draw(surf, (0, 0), g)
        self.particles.draw(surf, (0, 0), g)
        # logo
        lg = glow(120, (60, 20, 40))
        g.blit(lg, (VIEW_W // 2 - 120, 60 - 120), special_flags=pg.BLEND_ADD)
        surf.blit(g, (0, 0), special_flags=pg.BLEND_ADD)
        self.bg.draw_front(surf, self.cam, 0, g)
        surf.blit(self.vign, (0, 0))
        cols = [(255, 226, 150), (255, 200, 140), (255, 176, 140), (250, 150, 150), (236, 120, 150), (214, 96, 150),
                (190, 80, 150), (160, 70, 150)]
        font.draw_wave(surf, TITLE, (VIEW_W // 2, 44), self.t / 60, scale=5, amp=3, speed=2.2, outline=(40, 14, 40),
                       colors=cols)
        font.draw(surf, "A CLASSIC PYGAME PLATFORMER", (VIEW_W // 2, 92), (255, 220, 200), outline=(40, 14, 40), align="center")
        font.draw(surf, "2022  >  2026 REMASTER", (VIEW_W // 2, 104), (214, 120, 160), outline=(40, 14, 40), align="center")
        ui.panel(surf, (VIEW_W // 2 - 70, 160, 140, len(self.menu.items) * 15 + 8), 150, (255, 160, 180))
        self.menu.draw(surf)
        font.draw(surf, "ARROWS + ENTER    F11 FULLSCREEN", (VIEW_W - 6, VIEW_H - 11), (200, 150, 170), outline=(30, 10, 30), align="right")
        font.draw(surf, "BY RAYEN MALOUCHE", (6, VIEW_H - 11), (200, 150, 170), outline=(30, 10, 30))
        self.iris.draw(surf)


# =================================================================== map
BIOME_COLS = {"meadow": (110, 210, 90), "caves": (150, 110, 255), "sunset": (255, 160, 90), "frost": (200, 236, 255),
              "volcano": (255, 90, 50), "legacy": (230, 40, 40)}


class MapScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.paths = list_campaign()
        self.levels = [Level.load(p) for p in self.paths]
        bonus = os.path.join(LEVEL_DIR, "bonus", "legacy_2022.txt")
        self.bonus = Level.load(bonus) if os.path.exists(bonus) else None
        n = len(self.levels)
        self.nodes = []
        for i in range(n):
            x = 70 + i * (340 / max(1, n - 1))
            y = 120 + math.sin(i * 1.9) * 34
            self.nodes.append((x, y))
        if self.bonus:
            self.nodes.append((VIEW_W - 44, 54))
        self.sel = min(save.data()["unlocked"], n) - 1
        self.pos = list(self.nodes[self.sel])
        self.hero = Player(0, 0)
        self.hero.body.on_ground = True
        self.t = 0
        self.particles = Particles()
        self.glow = pg.Surface((VIEW_W, VIEW_H))
        rng = random.Random(8)
        self.stars = [(rng.uniform(0, VIEW_W), rng.uniform(0, VIEW_H), rng.random()) for _ in range(90)]
        self.sky = pg.Surface((VIEW_W, VIEW_H))
        for y in range(VIEW_H):
            self.sky.fill(lerp_color((10, 14, 40), (40, 30, 80), y / VIEW_H), (0, y, VIEW_W, 1))
        self.islands = self._islands(rng)
        self.iris = ui.Iris()
        self.iris.k = 1.0
        self.iris.open(speed=0.05)
        self.vign = ui.vignette(0.5)
        audio.music("map")

    def enter(self):
        audio.music("map")
        self.iris.open(speed=0.05)
        self.sel = min(self.sel, len(self.nodes) - 1)

    def _islands(self, rng):
        s = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        for i, (x, y) in enumerate(self.nodes):
            lvl = self._level(i)
            col = BIOME_COLS.get(lvl.theme, (120, 120, 160))
            base = lerp_color(col, (20, 20, 50), 0.6)
            for k in range(7):
                r = rng.randint(14, 26)
                pg.draw.ellipse(s, lerp_color(base, (0, 0, 0), 0.4), (x - r + rng.randint(-14, 14), y + 4 + rng.randint(-4, 6), r * 2, r))
            for k in range(6):
                r = rng.randint(12, 22)
                pg.draw.ellipse(s, base, (x - r + rng.randint(-12, 12), y - 4 + rng.randint(-4, 4), r * 2, int(r * 0.8)))
            pg.draw.ellipse(s, lerp_color(col, (20, 20, 50), 0.35), (x - 16, y - 6, 32, 12))
        return s

    def _level(self, i):
        return self.levels[i] if i < len(self.levels) else self.bonus

    def _unlocked(self, i):
        if i >= len(self.levels):
            return True
        return i < save.data()["unlocked"]

    def update(self):
        self.t += 1
        inp = self.app.inp
        self.iris.update()
        tx, ty = self.nodes[self.sel]
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        d = math.hypot(dx, dy)
        moving = d > 1
        if moving:
            sp = min(d, 3.2)
            self.pos[0] += dx / d * sp
            self.pos[1] += dy / d * sp
            self.hero.facing = 1 if dx > 0 else -1
            self.hero.run_phase += 0.5
            self.hero.body.vx = self.hero.facing * 2
        else:
            self.hero.body.vx = 0
            self.hero.run_phase = 0
        h = self.hero
        h.t += 1
        h.body.x = self.pos[0] - h.body.w / 2
        h.body.y = self.pos[1] - h.body.h - 2
        h._update_scarf()
        if not self.iris.busy:
            if inp.pressed("right") or inp.pressed("down"):
                if self.sel + 1 < len(self.nodes) and self._unlocked(self.sel + 1):
                    self.sel += 1
                    audio.play("blip")
            if inp.pressed("left") or inp.pressed("up"):
                if self.sel > 0:
                    self.sel -= 1
                    audio.play("blip")
            if (inp.pressed("confirm") or inp.pressed("jump")) and not moving:
                inp.consume("confirm")
                inp.consume("jump")
                audio.play("confirm")
                self.iris.close(self._start, (self.pos[0], self.pos[1] - 8), 0.05)
            if inp.pressed("back"):
                audio.play("back")
                self.iris.close(self.app.pop, None, 0.06)
        if self.t % 5 == 0:
            x, y = self.nodes[self.sel]
            self.particles.add(x + random.uniform(-14, 14), y + 2, 0, -0.4, 40, BIOME_COLS.get(self._level(self.sel).theme, (255, 255, 255)),
                               size=1, kind="star", glow=3)
        self.particles.update()

    def _start(self):
        from .play import PlayScene
        lvl = self._level(self.sel)
        lvl = Level.load(lvl.path)
        idx = self.sel if self.sel < len(self.levels) else None
        self.app.push(PlayScene(self.app, lvl, idx, self._on_exit))

    def _on_exit(self, play, completed):
        self.app.pop()
        if completed and play.index is not None:
            save.unlock(play.index + 2)
            if play.index + 1 < len(self.levels):
                self.sel = play.index + 1
            elif play.index == len(self.levels) - 1:
                save.data()["finished"] = True
                save.write()
                self.app.push(CreditsScene(self.app, play.stats))

    def draw(self, surf):
        g = self.glow
        g.fill((0, 0, 0))
        surf.blit(self.sky, (0, 0))
        t = self.t / 60
        for x, y, k in self.stars:
            b = 0.5 + 0.5 * math.sin(t * (1 + k * 3) + k * 30)
            c = int(90 + 150 * b * k)
            surf.set_at((int(x), int(y)), (c, c, min(255, c + 30)))
        # sea shimmer
        for i in range(40):
            y = 200 + (i * 37) % 70
            x = (i * 91 + self.t * (0.2 + (i % 3) * 0.1)) % (VIEW_W + 40) - 20
            surf.fill((60, 70, 130), (x, y, 6 + i % 5, 1))
        surf.blit(self.islands, (0, 0))
        # path dots
        for i in range(len(self.levels) - 1):
            (x0, y0), (x1, y1) = self.nodes[i], self.nodes[i + 1]
            open_ = self._unlocked(i + 1)
            steps = 10
            for k in range(1, steps):
                f = k / steps
                x = x0 + (x1 - x0) * f
                y = y0 + (y1 - y0) * f - math.sin(f * math.pi) * 10
                col = (255, 230, 160) if open_ else (70, 70, 100)
                if open_ and (k + self.t // 8) % steps == 0:
                    col = (255, 255, 255)
                surf.fill(col, (int(x) - 1, int(y) - 1, 2, 2))
        # nodes
        for i, (x, y) in enumerate(self.nodes):
            lvl = self._level(i)
            col = BIOME_COLS.get(lvl.theme, (200, 200, 200))
            unlocked = self._unlocked(i)
            rec = save.level_record(lvl.path) if lvl.path else None
            if not unlocked:
                col = (80, 80, 110)
            if i == self.sel:
                gl = glow(26, tuple(c // 3 for c in col))
                g.blit(gl, (x - 26, y - 26), special_flags=pg.BLEND_ADD)
            pg.draw.circle(surf, lerp_color(col, (0, 0, 0), 0.5), (int(x), int(y + 1)), 8)
            pg.draw.circle(surf, col, (int(x), int(y)), 7)
            pg.draw.circle(surf, lerp_color(col, (255, 255, 255), 0.5), (int(x), int(y)), 7, 1)
            if lvl.theme == "legacy":
                surf.fill((255, 40, 40), (int(x) - 2, int(y) - 4, 5, 7))
            elif not unlocked:
                font.draw(surf, "?", (int(x), int(y) - 3), (40, 40, 60), shadow=None, align="center")
            else:
                label = str(i + 1)
                font.draw(surf, label, (int(x), int(y) - 3), (30, 20, 40), shadow=None, align="center")
            if rec:
                for j in range(3):
                    ui.draw_star_icon(surf, x - 10 + j * 10, y + 14, j in rec.get("gems", []))
        self.hero.draw(surf, (0, 0), g)
        self.particles.draw(surf, (0, 0), g)
        surf.blit(g, (0, 0), special_flags=pg.BLEND_ADD)
        surf.blit(self.vign, (0, 0))
        # header
        font.draw(surf, "WORLD MAP", (VIEW_W // 2, 10), ui.PALE, 2, outline=ui.INK, align="center")
        if self.bonus:
            font.draw(surf, "BONUS", (self.nodes[-1][0], self.nodes[-1][1] - 22), (255, 120, 120), outline=ui.INK, align="center")
        # info panel
        lvl = self._level(self.sel)
        ui.panel(surf, (VIEW_W // 2 - 160, VIEW_H - 62, 320, 54), 210, BIOME_COLS.get(lvl.theme, (200, 200, 200)))
        label = lvl.meta.get("label", "")
        font.draw(surf, label, (VIEW_W // 2 - 150, VIEW_H - 55), (180, 170, 210), outline=ui.INK)
        font.draw(surf, lvl.name, (VIEW_W // 2 - 150, VIEW_H - 44), ui.PALE, 2, outline=ui.INK)
        font.draw(surf, lvl.meta.get("subtitle", ""), (VIEW_W // 2 - 150, VIEW_H - 25), (150, 140, 180), outline=ui.INK)
        rec = save.level_record(lvl.path) if lvl.path else None
        if rec:
            tm = rec["time"]
            font.draw(surf, f"BEST {int(tm // 60)}:{int(tm % 60):02d}", (VIEW_W // 2 + 150, VIEW_H - 55), ui.GOLD, outline=ui.INK, align="right")
            font.draw(surf, f"RANK {rec.get('rank', '-')}", (VIEW_W // 2 + 150, VIEW_H - 43), (140, 230, 255), outline=ui.INK, align="right")
        else:
            font.draw(surf, "NOT CLEARED", (VIEW_W // 2 + 150, VIEW_H - 55), (140, 130, 170), outline=ui.INK, align="right")
        if (self.t // 25) % 2:
            font.draw(surf, "ENTER  PLAY", (VIEW_W // 2 + 150, VIEW_H - 25), ui.PALE, outline=ui.INK, align="right")
        self.iris.draw(surf)


# =================================================================== options
class OptionsScene(Scene):
    def __init__(self, app, under):
        super().__init__(app)
        self.under = under
        self.t = 0
        self.index = 0

    def update(self):
        self.t += 1
        inp = self.app.inp
        st = save.data()["settings"]
        n = 4
        if inp.pressed("up"):
            self.index = (self.index - 1) % n
            audio.play("blip")
        if inp.pressed("down"):
            self.index = (self.index + 1) % n
            audio.play("blip")
        d = (1 if inp.pressed("right") else 0) - (1 if inp.pressed("left") else 0)
        a = self.app.audio
        if self.index == 0 and d:
            st["music"] = round(max(0.0, min(1.0, st.get("music", 0.5) + d * 0.1)), 2)
            a.set_music_volume(st["music"])
            audio.play("blip")
        if self.index == 1 and d:
            st["sfx"] = round(max(0.0, min(1.0, st.get("sfx", 0.7) + d * 0.1)), 2)
            a.sfx_volume = st["sfx"]
            audio.play("coin")
        confirm = inp.pressed("confirm") or inp.pressed("jump")
        if self.index == 2 and (confirm or d) and not WEB:
            st["fullscreen"] = not st.get("fullscreen", False)
            try:
                pg.display.toggle_fullscreen()
            except pg.error:
                pass
        if (self.index == 3 and confirm) or inp.pressed("back"):
            inp.consume("confirm")
            inp.consume("jump")
            save.write()
            audio.play("back")
            self.app.pop()

    def draw(self, surf):
        self.under.draw(surf)
        dim = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
        dim.fill((8, 6, 20, 190))
        surf.blit(dim, (0, 0))
        ui.panel(surf, (VIEW_W // 2 - 120, 70, 240, 130), 220, ui.ACCENT)
        font.draw(surf, "OPTIONS", (VIEW_W // 2, 80), ui.PALE, 2, outline=ui.INK, align="center")
        st = save.data()["settings"]
        rows = [("MUSIC", st.get("music", 0.5)), ("SOUND FX", st.get("sfx", 0.7)),
                ("FULLSCREEN", "ON" if st.get("fullscreen") else "OFF"), ("BACK", None)]
        for i, (label, val) in enumerate(rows):
            y = 108 + i * 20
            sel = i == self.index
            col = ui.PALE if sel else (140, 132, 170)
            font.draw(surf, ("> " if sel else "  ") + label, (VIEW_W // 2 - 100, y), col, outline=ui.INK)
            if isinstance(val, float):
                for k in range(10):
                    on = k < round(val * 10)
                    surf.fill(ui.ACCENT if on else (60, 50, 80), (VIEW_W // 2 + 10 + k * 8, y, 6, 7))
            elif val:
                font.draw(surf, val, (VIEW_W // 2 + 90, y), col, outline=ui.INK, align="right")


# =================================================================== credits
class CreditsScene(Scene):
    LINES = [
        ("WAYFARER", 3, (255, 214, 120)),
        ("", 1, None),
        ("THE WAY HOME IS FOUND", 1, (236, 232, 255)),
        ("", 1, None),
        ("ORIGINAL 2022 GAME", 1, (214, 66, 98)),
        ("RAYEN MALOUCHE", 2, (236, 232, 255)),
        ("", 1, None),
        ("2026 REMASTER", 1, (214, 66, 98)),
        ("NEW ENGINE  ART  MUSIC  LEVELS", 1, (236, 232, 255)),
        ("ALL DRAWN AND SYNTHESISED IN CODE", 1, (236, 232, 255)),
        ("", 1, None),
        ("BUILT WITH", 1, (214, 66, 98)),
        ("PYTHON + PYGAME-CE", 1, (236, 232, 255)),
        ("", 1, None),
        ("THE RED RECTANGLE", 1, (214, 66, 98)),
        ("FOR BEING THERE FIRST", 1, (236, 232, 255)),
        ("", 1, None),
        ("", 1, None),
        ("THANK YOU FOR PLAYING", 2, (255, 214, 120)),
    ]

    def __init__(self, app, stats=None):
        super().__init__(app)
        self.t = 0
        self.particles = Particles()
        self.glow = pg.Surface((VIEW_W, VIEW_H))
        self.bg = Background("frost", themes.get("frost"), VIEW_H, seed=77)
        self.hero = Player(0, 0)
        self.hero.body.on_ground = True
        audio.music("title")

    def update(self):
        self.t += 1
        self.bg.update()
        h = self.hero
        h.t += 1
        h.run_phase += 0.45
        h.body.vx = 1.8
        h.body.x = VIEW_W // 2 - 5
        h.body.y = VIEW_H - 40
        h.scarf.wind = -0.2
        h._update_scarf()
        if self.t % 40 == 0:
            x, y = random.uniform(60, VIEW_W - 60), random.uniform(30, 120)
            col = random.choice([(255, 120, 150), (255, 220, 120), (140, 220, 255), (190, 150, 255)])
            self.particles.burst(x, y, 40, col, 2.6, 60, 2, 0.04, glow=5, kind="star")
            self.particles.ring(x, y, col, 30, 30, 1)
            audio.play("explode", 0.25)
        self.particles.update()
        inp = self.app.inp
        if self.t > 120 and (inp.pressed("confirm") or inp.pressed("back")):
            inp.consume("confirm")
            self.app.pop()

    def draw(self, surf):
        g = self.glow
        g.fill((0, 0, 0))
        self.bg.draw(surf, self.t * 1.8, 0, g)
        surf.fill((24, 30, 60), (0, VIEW_H - 26, VIEW_W, 26))
        surf.fill((236, 246, 255), (0, VIEW_H - 26, VIEW_W, 2))
        self.hero.draw(surf, (0, 0), g)
        self.particles.draw(surf, (0, 0), g)
        surf.blit(g, (0, 0), special_flags=pg.BLEND_ADD)
        y = VIEW_H - self.t * 0.45
        for text, sc, col in self.LINES:
            if col and -30 < y < VIEW_H:
                font.draw(surf, text, (VIEW_W // 2, int(y)), col, sc, outline=ui.INK, align="center")
            y += 10 + 8 * sc
        if y < 0:
            font.draw(surf, "PRESS ENTER", (VIEW_W // 2, VIEW_H // 2), ui.PALE, outline=ui.INK, align="center")
