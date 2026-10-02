"""Tile physics for every moving thing. Handles solids, 45 degree slopes (the 2022
version's signature feature, now done properly), one-way platforms, moving platforms
and a small step-up so slopes meet flat ground without snagging."""
import math

import pygame as pg

from .settings import TILE

STEP_UP = 6


class Body:
    def __init__(self, x, y, w, h):
        self.x = float(x)
        self.y = float(y)
        self.w = w
        self.h = h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.on_slope = False
        self.on_ice = False
        self.wall = 0
        self.hit_ceiling = None
        self.platform = None
        self.drop_timer = 0
        self.collides = True

    @property
    def rect(self):
        return pg.Rect(math.floor(self.x), math.floor(self.y), self.w, self.h)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def bottom(self):
        return self.y + self.h

    def touching_wall(self, world, side):
        """True if a solid tile is directly beside the body (for wall slides)."""
        px = self.x + self.w + 0.5 if side > 0 else self.x - 0.5
        tx = math.floor(px / TILE)
        for py in (self.y + 2, self.y + self.h / 2, self.y + self.h - 3):
            if world.solid(tx, math.floor(py / TILE)):
                return True
        return False

    def move(self, world, platforms=()):
        was_ground = self.on_ground
        if self.drop_timer > 0:
            self.drop_timer -= 1
        # ride moving platforms
        if self.platform is not None and was_ground:
            self.x += self.platform.dx
            self.y += self.platform.dy
        if not self.collides:
            self.x += self.vx
            self.y += self.vy
            return
        # horizontal
        self.x += self.vx
        self.wall = 0
        self._collide_x(world, was_ground)
        # vertical
        prev_bottom = self.y + self.h - (self.platform.dy if (self.platform and was_ground) else 0)
        self.y += self.vy
        self._collide_y(world, platforms, was_ground, prev_bottom)

    def _collide_x(self, world, was_ground):
        r = self.rect
        for tx, ty in world.tiles_in(r):
            if not world.solid(tx, ty):
                continue
            tr = world.tile_rect(tx, ty)
            r = self.rect
            if not r.colliderect(tr):
                continue
            # step up onto small ledges (slope tops meeting flat ground)
            rise = r.bottom - tr.top
            if was_ground and 0 < rise <= STEP_UP and not world.solid(tx, ty - 1):
                head_ok = all(not world.solid(ttx, math.floor((tr.top - self.h) / TILE))
                              for ttx in range(math.floor(self.x / TILE), math.floor((self.x + self.w - 1) / TILE) + 1))
                if head_ok:
                    self.y = tr.top - self.h
                    continue
            if self.cx < tr.centerx:
                self.x = tr.left - self.w
                self.wall = 1
            else:
                self.x = tr.right
                self.wall = -1
            self.vx = 0

    def _collide_y(self, world, platforms, was_ground, prev_bottom):
        self.hit_ceiling = None
        self.on_ground = False
        self.on_slope = False
        self.on_ice = False
        landed_platform = None
        r = self.rect
        if self.vy < 0:
            best = None
            for tx, ty in world.tiles_in(r):
                if world.solid(tx, ty):
                    tr = world.tile_rect(tx, ty)
                    if r.colliderect(tr):
                        d = abs(tr.centerx - self.cx)
                        if best is None or d < best[0]:
                            best = (d, tx, ty, tr.bottom)
            if best:
                self.y = best[3]
                self.vy = 0
                self.hit_ceiling = (best[1], best[2])
            return

        snap = (STEP_UP + abs(self.vx)) if was_ground else 0
        bottom = self.y + self.h
        ground = None
        kind = None
        # solid & one-way tiles under the feet
        x0 = math.floor((self.x + 0.01) / TILE)
        x1 = math.floor((self.x + self.w - 0.01) / TILE)
        row0 = math.floor((prev_bottom - 1) / TILE)
        row1 = math.floor((bottom + snap) / TILE)
        for ty in range(row0, row1 + 1):
            for tx in range(x0, x1 + 1):
                ch = world.get(tx, ty)
                top = ty * TILE
                if ch in "#=IB?!U":
                    if prev_bottom <= top + 0.5 + (STEP_UP if was_ground else 0) and bottom + snap >= top:
                        if ground is None or top < ground:
                            ground, kind = top, ch
                elif ch == "-" and self.drop_timer <= 0:
                    if prev_bottom <= top + 0.5 and bottom + snap >= top:
                        if ground is None or top < ground:
                            ground, kind = top, ch
        # slopes use the foot centre
        fx = self.cx
        ftx = math.floor(fx / TILE)
        for ty in range(math.floor((prev_bottom - TILE) / TILE), row1 + 1):
            s = world.slope_surface(ftx, ty, fx)
            if s is None:
                continue
            if bottom + snap >= s and prev_bottom <= s + TILE * 0.75:
                if ground is None or s < ground:
                    ground, kind = s, "slope"
        # moving / crumbling platforms
        for p in platforms:
            if not p.solid:
                continue
            pr = p.rect
            if r.right <= pr.left or r.left >= pr.right:
                continue
            top = pr.top
            if prev_bottom <= top + 1 + max(0.0, -p.dy) + abs(p.dy) and bottom + snap >= top:
                if ground is None or top < ground:
                    ground, kind = top, "platform"
                    landed_platform = p
        if ground is not None and bottom >= ground - (snap if was_ground else 0) - 0.001:
            self.y = ground - self.h
            self.vy = 0
            self.on_ground = True
            self.on_slope = kind == "slope"
            self.on_ice = kind == "I"
            self.platform = landed_platform if kind == "platform" else None
            if landed_platform is not None:
                landed_platform.stood_on(self)
        else:
            self.platform = None
            # tiles beside the slope can still poke into us from below when falling fast
            r = self.rect
            for tx, ty in world.tiles_in(r):
                if world.solid(tx, ty):
                    tr = world.tile_rect(tx, ty)
                    if r.colliderect(tr) and prev_bottom <= tr.top + self.vy + 1:
                        self.y = tr.top - self.h
                        self.vy = 0
                        self.on_ground = True
                        break
