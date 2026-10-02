"""Level loading, the tile grid and tile collision queries."""
import math
import os

import pygame as pg

from .settings import TILE, LEVEL_DIR

SOLID = set("#=IB?!U")          # U = used loot block
SLOPES = {"/", "\\"}
ONEWAY = {"-"}
STATIC_TILES = set("#=I/\\-^")  # baked into the tile layer
ENTITY_CHARS = set("o*h$PCEsmMxgkbtqKlcB?!~")

LEGEND = {
    "#": "ground", "=": "stone bricks", "I": "ice", "/": "slope up", "\\": "slope down",
    "-": "one-way platform", "^": "spikes", "~": "lava", "B": "breakable brick",
    "?": "coin block", "!": "power-up block", "o": "coin", "*": "star shard (3 per level)",
    "h": "heart", "$": "treasure chest", "P": "player start", "C": "checkpoint",
    "E": "exit portal", "s": "spring", "m": "moving platform (horizontal)",
    "M": "moving platform (vertical)", "x": "crumbling platform", "g": "slime",
    "k": "spike beetle", "b": "bat", "t": "spitter plant", "q": "wisp", "K": "boss: Molten King",
    "l": "lantern (light)", "c": "glow crystal",
}


class Level:
    """Parsed level file: header + rows of characters."""

    def __init__(self, rows, meta=None, path=None):
        self.meta = meta or {}
        width = max(len(r) for r in rows) if rows else 1
        self.rows = [list(r.ljust(width, ".").replace(" ", ".")) for r in rows]
        self.path = path

    @property
    def name(self):
        return self.meta.get("title", "Untitled")

    @property
    def theme(self):
        return self.meta.get("theme", "meadow")

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        return Level.parse(text, path)

    @staticmethod
    def parse(text, path=None):
        meta, rows = {}, []
        lines = text.replace("\r", "").split("\n")
        if "---" in lines:
            sep = lines.index("---")
            for line in lines[:sep]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            lines = lines[sep + 1:]
        for line in lines:
            if line.strip() == "" and not rows:
                continue
            rows.append(line.rstrip())
        while rows and rows[-1] == "":
            rows.pop()
        return Level(rows, meta, path)

    def serialize(self):
        head = "\n".join(f"{k}: {v}" for k, v in self.meta.items())
        body = "\n".join("".join(r).rstrip(".") for r in self.rows)
        return f"{head}\n---\n{body}\n"


def list_campaign():
    files = sorted(f for f in os.listdir(LEVEL_DIR) if f.endswith(".txt"))
    return [os.path.join(LEVEL_DIR, f) for f in files]


class World:
    """Collision grid built from a Level. Entities are spawned separately."""

    def __init__(self, level):
        self.level = level
        self.h = len(level.rows)
        self.w = len(level.rows[0])
        self.grid = []
        self.spawns = []
        for ty, row in enumerate(level.rows):
            out = []
            for tx, ch in enumerate(row):
                if ch in STATIC_TILES:
                    out.append(ch)
                elif ch in ("B", "?", "!"):
                    out.append(ch)
                    self.spawns.append((ch, tx, ty))
                else:
                    out.append(".")
                    if ch != ".":
                        self.spawns.append((ch, tx, ty))
            self.grid.append(out)
        self.px_w = self.w * TILE
        self.px_h = self.h * TILE

    # ---- queries ---------------------------------------------------------
    def get(self, tx, ty):
        if tx < 0 or tx >= self.w:
            return "#"  # side walls
        if ty < 0 or ty >= self.h:
            return "."
        return self.grid[ty][tx]

    def set(self, tx, ty, ch):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            self.grid[ty][tx] = ch

    def solid(self, tx, ty):
        return self.get(tx, ty) in SOLID

    def solidish(self, tx, ty):
        """For auto-tiling: anything that reads as terrain."""
        return self.get(tx, ty) in "#=I/\\B?!U"

    def is_ice(self, tx, ty):
        return self.get(tx, ty) == "I"

    def slope_surface(self, tx, ty, px):
        """Y of the slope surface at world x=px inside tile (tx,ty), or None."""
        ch = self.get(tx, ty)
        if ch not in SLOPES:
            return None
        lx = min(TILE, max(0.0, px - tx * TILE))
        if ch == "/":
            return ty * TILE + TILE - lx
        return ty * TILE + lx

    def tiles_in(self, rect):
        x0 = math.floor(rect.left / TILE)
        x1 = math.floor((rect.right - 1) / TILE)
        y0 = math.floor(rect.top / TILE)
        y1 = math.floor((rect.bottom - 1) / TILE)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                yield tx, ty

    def hazard_at(self, rect):
        """Returns 'spike', 'lava' or None for a hitbox."""
        for tx, ty in self.tiles_in(rect):
            ch = self.get(tx, ty)
            if ch == "^":
                if rect.colliderect(pg.Rect(tx * TILE + 2, ty * TILE + 9, TILE - 4, TILE - 9)):
                    return "spike"
        return None

    def tile_rect(self, tx, ty):
        return pg.Rect(tx * TILE, ty * TILE, TILE, TILE)
