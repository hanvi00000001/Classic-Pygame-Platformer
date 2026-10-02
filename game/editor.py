"""In-game level editor (successor of the 2022 level_creator.py).

Mouse: left paint, right erase, middle-drag / arrows / WASD pan, wheel cycles tiles.
Keys: 1-9 pick from the palette page, TAB next page, F5 play-test, CTRL+S save,
CTRL+O load next file, CTRL+N new level, T cycle theme, G toggle grid, ESC back.
"""
import os

import pygame as pg

from . import audio, font, themes, tilerender, ui
from .backgrounds import Background
from .play import PlayScene
from .scene import Scene
from .settings import TILE, VIEW_W, VIEW_H, CUSTOM_DIR, LEVEL_DIR
from .world import Level, World, LEGEND, list_campaign

PALETTE = ["#", "=", "I", "/", "\\", "-", "^", "~", "B", "?", "!", "o", "*", "h", "$", "P", "C", "E", "s",
           "m", "M", "x", "g", "k", "b", "t", "q", "K", "l", "c", "1"]
THEME_ORDER = ["meadow", "caves", "sunset", "frost", "volcano", "legacy"]
PANEL_W = 96


def _new_level():
    rows = ["." * 120 for _ in range(17)]
    lvl = Level(rows, {"title": "My Level", "label": "CUSTOM", "subtitle": "made in the wayfarer editor",
                       "theme": "meadow", "music": "meadow", "powerup": "fire,feather,shield"})
    for y in range(14, 17):
        lvl.rows[y] = ["#"] * 120
    lvl.rows[13][3] = "P"
    lvl.rows[13][114] = "E"
    return lvl


class EditorScene(Scene):
    def __init__(self, app, level=None):
        super().__init__(app)
        self.level = level or self._load_first()
        self.cam = [0.0, max(0, len(self.level.rows) * TILE - VIEW_H)]
        self.sel = 0
        self.grid = True
        self.t = 0
        self.msg = ""
        self.msg_t = 0
        self.dragging = None
        self.dirty_bg = True
        self.preview_cache = {}
        self.files = self._files()
        self.file_i = 0
        self._rebuild()
        audio.music("map")

    # ------------------------------------------------------------ files
    def _files(self):
        os.makedirs(CUSTOM_DIR, exist_ok=True)
        custom = sorted(os.path.join(CUSTOM_DIR, f) for f in os.listdir(CUSTOM_DIR) if f.endswith(".txt"))
        bonus = os.path.join(LEVEL_DIR, "bonus", "legacy_2022.txt")
        return custom + list_campaign() + ([bonus] if os.path.exists(bonus) else [])

    def _load_first(self):
        os.makedirs(CUSTOM_DIR, exist_ok=True)
        custom = sorted(f for f in os.listdir(CUSTOM_DIR) if f.endswith(".txt"))
        if custom:
            return Level.load(os.path.join(CUSTOM_DIR, custom[0]))
        return _new_level()

    def _save(self):
        os.makedirs(CUSTOM_DIR, exist_ok=True)
        path = self.level.path
        if not path or os.path.dirname(os.path.abspath(path)) != os.path.abspath(CUSTOM_DIR):
            n = 1
            while os.path.exists(os.path.join(CUSTOM_DIR, f"custom_{n:02d}.txt")):
                n += 1
            path = os.path.join(CUSTOM_DIR, f"custom_{n:02d}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.level.serialize())
            self.level.path = path
            self._say(f"SAVED {os.path.basename(path)}")
            audio.play("checkpoint")
        except OSError:
            self._say("COULD NOT SAVE")
        self.files = self._files()

    def _say(self, s):
        self.msg = s
        self.msg_t = 150

    def _rebuild(self):
        """Re-bake tiles for the preview (cheap enough at editor scale)."""
        th = themes.get(self.level.theme)
        self.world = World(self.level)
        self.tiles, _, self.grass = tilerender.bake(self.world, th)
        if self.dirty_bg:
            self.bg = Background(self.level.theme, th, self.world.px_h, seed=3)
            self.dirty_bg = False
        self.dirty = False

    # ------------------------------------------------------------ helpers
    @property
    def rows(self):
        return self.level.rows

    def _ensure_size(self, tx, ty):
        w = len(self.rows[0])
        if tx >= w - 2:
            grow = tx - w + 20
            for r in self.rows:
                r.extend(["."] * grow)
        if ty >= len(self.rows):
            for _ in range(ty - len(self.rows) + 1):
                self.rows.append(["."] * len(self.rows[0]))

    def _paint(self, tx, ty, ch):
        if tx < 0 or ty < 0:
            return
        self._ensure_size(tx, ty)
        if self.rows[ty][tx] == ch:
            return
        if ch == "P":
            for r in self.rows:
                for i, c in enumerate(r):
                    if c == "P":
                        r[i] = "."
        self.rows[ty][tx] = ch
        self.dirty = True

    # ------------------------------------------------------------ update
    def update(self):
        self.t += 1
        inp = self.app.inp
        keys = pg.key.get_pressed()
        mods = pg.key.get_mods()
        ctrl = mods & pg.KMOD_CTRL
        for e in self.app.events:
            if e.type == pg.MOUSEWHEEL:
                self.sel = (self.sel - e.y) % len(PALETTE)
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 2:
                self.dragging = (self.app.logical(e.pos), tuple(self.cam))
            elif e.type == pg.MOUSEBUTTONUP and e.button == 2:
                self.dragging = None
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1 and self.app.logical(e.pos)[0] >= VIEW_W - PANEL_W:
                self._click_palette(self.app.logical(e.pos))
            elif e.type == pg.KEYDOWN:
                if ctrl and e.key == pg.K_s:
                    self._save()
                elif ctrl and e.key == pg.K_o:
                    if self.files:
                        self.file_i = (self.file_i + 1) % len(self.files)
                        self.level = Level.load(self.files[self.file_i])
                        self.dirty_bg = True
                        self._rebuild()
                        self.cam = [0.0, max(0, len(self.rows) * TILE - VIEW_H)]
                        self._say("LOADED " + os.path.basename(self.files[self.file_i]))
                elif ctrl and e.key == pg.K_n:
                    self.level = _new_level()
                    self.dirty_bg = True
                    self._rebuild()
                    self._say("NEW LEVEL")
                elif e.key == pg.K_F5:
                    self._playtest()
                elif e.key == pg.K_g:
                    self.grid = not self.grid
                elif e.key == pg.K_t and not ctrl:
                    i = THEME_ORDER.index(self.level.theme) if self.level.theme in THEME_ORDER else 0
                    th = THEME_ORDER[(i + 1) % len(THEME_ORDER)]
                    self.level.meta["theme"] = th
                    self.level.meta["music"] = th
                    self.dirty_bg = True
                    self._rebuild()
                    self._say("THEME " + th.upper())
                elif e.key == pg.K_TAB:
                    self.sel = (self.sel + 9) % len(PALETTE)
                elif pg.K_1 <= e.key <= pg.K_9 and not ctrl:
                    page = self.sel // 9 * 9
                    i = page + e.key - pg.K_1
                    if i < len(PALETTE):
                        self.sel = i
                elif e.key == pg.K_ESCAPE:
                    audio.play("back")
                    self.app.pop()
                    return
        # pan
        sp = 6 if not (mods & pg.KMOD_SHIFT) else 14
        if not ctrl:
            if keys[pg.K_LEFT] or keys[pg.K_a] or keys[pg.K_q]:
                self.cam[0] -= sp
            if keys[pg.K_RIGHT] or keys[pg.K_d]:
                self.cam[0] += sp
            if keys[pg.K_UP] or keys[pg.K_w] or keys[pg.K_z]:
                self.cam[1] -= sp
            if keys[pg.K_DOWN] or (keys[pg.K_s]):
                self.cam[1] += sp
        if self.dragging:
            (mx0, my0), (cx0, cy0) = self.dragging
            mx, my = self.app.mouse()
            self.cam = [cx0 - (mx - mx0), cy0 - (my - my0)]
        self.cam[0] = max(-32, min(len(self.rows[0]) * TILE - VIEW_W + PANEL_W + 64, self.cam[0]))
        self.cam[1] = max(-64, min(len(self.rows) * TILE - VIEW_H + 32, self.cam[1]))
        # paint
        mx, my = self.app.mouse()
        buttons = pg.mouse.get_pressed()
        if mx < VIEW_W - PANEL_W and 14 < my < VIEW_H - 12:
            tx = int((mx + self.cam[0]) // TILE)
            ty = int((my + self.cam[1]) // TILE)
            if buttons[0]:
                self._paint(tx, ty, PALETTE[self.sel])
            elif buttons[2]:
                self._paint(tx, ty, ".")
        painting = buttons[0] or buttons[2]
        if self.dirty and (not painting or self.t % 20 == 0):
            self._rebuild()
        if self.msg_t:
            self.msg_t -= 1
        self.bg.update()

    def _click_palette(self, pos):
        x, y = pos
        col = (x - (VIEW_W - PANEL_W) - 6) // 22
        row = (y - 30) // 22
        i = row * 4 + col
        if 0 <= col < 4 and 0 <= i < len(PALETTE):
            self.sel = i
            audio.play("blip")

    def _playtest(self):
        if self.dirty:
            self._rebuild()
        lvl = Level.parse(self.level.serialize(), self.level.path)
        if not any("P" in r for r in lvl.rows):
            self._say("PLACE A PLAYER START (P) FIRST")
            return
        audio.play("confirm")

        def back(play, completed):
            self.app.pop()
            audio.music("map")
        self.app.push(PlayScene(self.app, lvl, None, back, test_mode=True))

    # ------------------------------------------------------------ draw
    def _icon(self, ch):
        """Small preview of a palette entry, rendered with the real game code."""
        key = (ch, self.level.theme)
        if key in self.preview_cache:
            return self.preview_cache[key]
        s = pg.Surface((16, 16), pg.SRCALPHA)
        th = themes.get(self.level.theme)
        if ch in "#=I/\\-^":
            mini = Level([".", "." + ch + ".", ".##"], {"theme": self.level.theme})
            if ch in "/\\-^":
                mini = Level(["...", "." + ch + ".", "###"], {"theme": self.level.theme})
            w = World(mini)
            surf, _, _ = tilerender.bake(w, th)
            s.blit(surf, (0, 0), (16, 16, 16, 16))
        else:
            try:
                from .play import PlayScene as _P  # noqa: F401
                from . import entities as E, enemies as N
                g = pg.Surface((48, 48))
                tmp = pg.Surface((48, 48), pg.SRCALPHA)
                ent = None
                x, y = 16, 16
                mk = {
                    "~": lambda: E.Lava(x, y, True), "B": lambda: E.Block(x, y, "B", 1, 1),
                    "?": lambda: E.Block(x, y, "?", 1, 1), "!": lambda: E.Block(x, y, "!", 1, 1),
                    "o": lambda: E.Coin(x, y), "*": lambda: E.Gem(x, y), "h": lambda: E.Heart(x, y),
                    "$": lambda: E.Chest(x, y), "C": lambda: E.Checkpoint(x, y), "E": lambda: E.Portal(x, y),
                    "s": lambda: E.Spring(x, y), "x": lambda: E.CrumblePlatform(x, y),
                    "g": lambda: N.Slime(x, y, self.level.theme), "k": lambda: N.Beetle(x, y, ""),
                    "b": lambda: N.Bat(x, y, ""), "t": lambda: N.Spitter(x, y, self.level.theme),
                    "q": lambda: N.Wisp(x, y, ""), "l": lambda: E.Lantern(x, y), "c": lambda: E.Crystal(x, y),
                    "1": lambda: E.Sign(x, y, ""),
                }
                if ch in mk:
                    ent = mk[ch]()
                    ent.t = 0
                    ent.draw(tmp, (0, 0), g)
                    s.blit(tmp, (0, 0), (16, 16, 16, 16))
                elif ch == "P":
                    from .player import Player
                    p = Player(0, 0)
                    p.body.on_ground = True
                    fr = p._frame()
                    s.blit(fr, (-4, -10))
                elif ch in "mM":
                    s.fill((130, 120, 160), (0, 6, 16, 5))
                    font.draw(s, "<>" if ch == "m" else "^", (8, 0), (255, 255, 255), shadow=None, align="center")
                elif ch == "K":
                    s.fill((90, 40, 30), (1, 2, 14, 14))
                    s.fill((255, 140, 40), (4, 6, 3, 2))
                    s.fill((255, 140, 40), (9, 6, 3, 2))
                    s.fill((255, 200, 60), (2, 0, 12, 2))
            except Exception:
                font.draw(s, ch, (8, 4), (255, 255, 255), align="center")
        self.preview_cache[key] = s
        return s

    def draw(self, surf):
        cx, cy = int(self.cam[0]), int(self.cam[1])
        g = pg.Surface((VIEW_W, VIEW_H))
        self.bg.draw(surf, cx, cy, g)
        surf.blit(self.tiles, (-cx, -cy))
        # entity markers
        for ty, row in enumerate(self.rows):
            sy = ty * TILE - cy
            if sy < -16 or sy > VIEW_H:
                continue
            for tx, ch in enumerate(row):
                if ch == "." or ch in "#=I/\\-^":
                    continue
                sx = tx * TILE - cx
                if -16 < sx < VIEW_W:
                    icon = self._icon(ch if ch not in "23456789" else "1")
                    surf.blit(icon, (sx, sy))
        w, h = len(self.rows[0]) * TILE, len(self.rows) * TILE
        if self.grid:
            col = (255, 255, 255, 28)
            grid = pg.Surface((VIEW_W, VIEW_H), pg.SRCALPHA)
            for x in range(-(cx % TILE), VIEW_W, TILE):
                grid.fill(col, (x, 0, 1, VIEW_H))
            for y in range(-(cy % TILE), VIEW_H, TILE):
                grid.fill(col, (0, y, VIEW_W, 1))
            surf.blit(grid, (0, 0))
        pg.draw.rect(surf, (214, 66, 98), (-cx, -cy, w, h), 1)
        # cursor
        mx, my = self.app.mouse()
        if mx < VIEW_W - PANEL_W:
            tx, ty = (mx + cx) // TILE, (my + cy) // TILE
            r = pg.Rect(tx * TILE - cx, ty * TILE - cy, TILE, TILE)
            icon = self._icon(PALETTE[self.sel]).copy()
            icon.set_alpha(150)
            surf.blit(icon, r.topleft)
            pg.draw.rect(surf, (255, 255, 255) if (self.t // 10) % 2 else (214, 66, 98), r, 1)
            font.draw(surf, f"{tx},{ty}", (r.right + 2, r.bottom + 1), ui.PALE, outline=ui.INK)
        # palette panel
        px = VIEW_W - PANEL_W
        ui.panel(surf, (px, 0, PANEL_W, VIEW_H), 225, ui.ACCENT)
        font.draw(surf, "TILES", (px + PANEL_W // 2, 6), ui.PALE, outline=ui.INK, align="center")
        font.draw(surf, self.level.theme.upper(), (px + PANEL_W // 2, 16), (200, 160, 200), outline=ui.INK, align="center")
        for i, ch in enumerate(PALETTE):
            col, row = i % 4, i // 4
            x, y = px + 6 + col * 22, 30 + row * 22
            pg.draw.rect(surf, (40, 34, 60), (x - 2, y - 2, 20, 20))
            surf.blit(self._icon(ch), (x, y))
            if i == self.sel:
                pg.draw.rect(surf, (255, 214, 90), (x - 3, y - 3, 22, 22), 1)
        name = LEGEND.get(PALETTE[self.sel], "sign (text in level header)" if PALETTE[self.sel] == "1" else "")
        y = 30 + ((len(PALETTE) + 3) // 4) * 22 + 2
        for i, line in enumerate(_wrap(name.upper(), 15)):
            font.draw(surf, line, (px + 6, y + i * 10), ui.GOLD, outline=ui.INK)
        # top bar
        bar = pg.Surface((VIEW_W - PANEL_W, 13), pg.SRCALPHA)
        bar.fill((14, 10, 28, 210))
        surf.blit(bar, (0, 0))
        title = self.level.name + ("  (" + os.path.basename(self.level.path) + ")" if self.level.path else "  (UNSAVED)")
        font.draw(surf, title, (4, 3), ui.PALE, shadow=None)
        help_ = "F5 PLAY  CTRL+S SAVE  CTRL+O LOAD  CTRL+N NEW  T THEME"
        hb = pg.Surface((VIEW_W - PANEL_W, 12), pg.SRCALPHA)
        hb.fill((14, 10, 28, 200))
        surf.blit(hb, (0, VIEW_H - 12))
        font.draw(surf, help_, (4, VIEW_H - 10), (180, 170, 210), shadow=None)
        if self.msg_t:
            font.draw(surf, self.msg, ((VIEW_W - PANEL_W) // 2, 22), ui.GOLD, outline=ui.INK, align="center")


def _wrap(text, n):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines
