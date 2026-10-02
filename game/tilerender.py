"""Bakes the static tiles of a level into one big surface with auto-tiling,
depth shading and biome decorations. Everything is drawn from code."""
import random

import pygame as pg

from .settings import TILE
from .fx import lerp_color


def _rng(tx, ty, salt=0):
    return random.Random((tx * 73856093) ^ (ty * 19349663) ^ salt)


def bake(world, theme):
    surf = pg.Surface((world.px_w, world.px_h), pg.SRCALPHA)
    lights = []      # (x, y, radius, colour) static glow sources found while baking
    grass = []       # dynamic grass blade anchors (x, y, height, colour)
    for ty in range(world.h):
        for tx in range(world.w):
            ch = world.grid[ty][tx]
            if ch == "#":
                _ground(surf, world, theme, tx, ty, lights, grass)
            elif ch == "=":
                _bricks(surf, world, theme, tx, ty)
            elif ch == "I":
                _ice(surf, world, theme, tx, ty)
            elif ch in "/\\":
                _slope(surf, world, theme, tx, ty, ch, grass)
            elif ch == "-":
                _plank(surf, world, theme, tx, ty)
            elif ch == "^":
                _spikes(surf, theme, tx, ty)
    return surf, lights, grass


def _depth(world, tx, ty):
    d = 0
    while d < 5 and world.solidish(tx, ty - d - 1):
        d += 1
    return d


def _ground(s, world, th, tx, ty, lights, grass):
    x, y = tx * TILE, ty * TILE
    r = _rng(tx, ty)
    up = world.solidish(tx, ty - 1)
    dn = world.solidish(tx, ty + 1)
    lf = world.solidish(tx - 1, ty)
    rt = world.solidish(tx + 1, ty)
    depth = _depth(world, tx, ty)
    base = lerp_color(th["dirt"], th["dirt_dark"], min(1.0, depth * 0.17))
    s.fill(base, (x, y, TILE, TILE))
    # strata bands for a layered rock feel
    for py in range(TILE):
        wy = y + py
        if (wy + (tx * 3) % 5) % 9 == 0:
            for px in range(TILE):
                if (px + wy) % 3:
                    s.set_at((x + px, y + py), lerp_color(base, th["dirt_dark"], 0.5))
    # pebbles and specks
    for _ in range(r.randint(2, 5)):
        px, py = r.randint(1, 13), r.randint(3 if not up else 0, 13)
        c = th["speck"] if r.random() < 0.6 else lerp_color(base, th["dirt_hi"], 0.6)
        w = r.choice((1, 2, 2, 3))
        s.fill(c, (x + px, y + py, w, 1 + (w > 2)))
        if w > 1:
            s.fill(lerp_color(c, (255, 255, 255), 0.25), (x + px, y + py, 1, 1))
    if r.random() < 0.08 and depth > 0:
        # buried bone / fossil / gem fleck
        gx, gy = x + r.randint(3, 11), y + r.randint(4, 11)
        if th.get("deco") == "ash":
            pg.draw.line(s, (255, 120, 40), (gx, gy), (gx + r.randint(2, 4), gy + r.randint(-2, 2)))
            lights.append((gx + 1, gy, 10, (255, 90, 20)))
        elif th.get("deco") == "crystals":
            s.fill(th["top_hi"], (gx, gy, 2, 2))
            lights.append((gx + 1, gy + 1, 8, (60, 200, 190)))
        else:
            s.fill(lerp_color(base, (240, 230, 210), 0.5), (gx, gy, 3, 1))
    # side shading
    if not lf:
        s.fill(th["dirt_dark"], (x, y, 1, TILE))
        s.fill(lerp_color(base, th["dirt_dark"], 0.5), (x + 1, y, 1, TILE))
    if not rt:
        s.fill(th["dirt_dark"], (x + TILE - 1, y, 1, TILE))
        s.fill(lerp_color(base, th["dirt_dark"], 0.5), (x + TILE - 2, y, 1, TILE))
    if not dn:
        s.fill(th["dirt_dark"], (x, y + TILE - 2, TILE, 2))
        _ceiling_deco(s, world, th, tx, ty, r, lights)
    if not up:
        _cap(s, th, x, y, r, lf, rt)
        _top_deco(s, world, th, tx, ty, r, lights, grass)


def _cap(s, th, x, y, r, lf, rt):
    top, hi, dk = th["top"], th["top_hi"], th["top_dark"]
    s.fill(top, (x, y, TILE, 4))
    for px in range(TILE):
        h = 4 + ((px * 7 + x) % 3 == 0) + ((px * 5 + x) % 4 == 0)
        s.fill(top, (x + px, y, 1, h))
        s.set_at((x + px, y + h), dk)
    s.fill(hi, (x, y, TILE, 1))
    for px in range(0, TILE, 3):
        s.set_at((x + px + r.randint(0, 1), y + 1), hi)
    if not lf:
        s.set_at((x, y), (0, 0, 0, 0))
        s.fill(dk, (x, y + 1, 1, 4))
    if not rt:
        s.set_at((x + TILE - 1, y), (0, 0, 0, 0))
        s.fill(dk, (x + TILE - 1, y + 1, 1, 4))


def _top_deco(s, world, th, tx, ty, r, lights, grass):
    x, y = tx * TILE, ty * TILE
    deco = th.get("deco")
    above = world.get(tx, ty - 1)
    if above not in ".":
        return
    if deco in ("flowers", "ruins"):
        for _ in range(r.randint(3, 6)):
            grass.append((x + r.randint(0, 15), y + 1, r.randint(3, 6), th["top"] if r.random() < .6 else th["top_dark"]))
        if deco == "flowers" and r.random() < 0.35:
            fx = x + r.randint(2, 13)
            col = r.choice([(255, 236, 110), (255, 140, 170), (250, 250, 255), (160, 140, 255), (255, 170, 80)])
            pg.draw.line(s, th["top_dark"], (fx, y - 1), (fx, y - 4))
            s.fill(col, (fx - 1, y - 6, 3, 2))
            s.fill(col, (fx, y - 7, 1, 4))
            s.set_at((fx, y - 6), (255, 230, 120))
        if deco == "flowers" and r.random() < 0.05:
            mx = x + r.randint(3, 11)
            s.fill((240, 236, 220), (mx, y - 3, 2, 3))
            s.fill((210, 60, 60), (mx - 2, y - 6, 6, 3))
            s.fill((255, 255, 255), (mx - 1, y - 5, 1, 1))
        if deco == "ruins" and r.random() < 0.08:
            px = x + r.randint(2, 10)
            h = r.randint(6, 14)
            s.fill(th["stone"], (px, y - h, 4, h))
            s.fill(th["stone_hi"], (px, y - h, 1, h))
            s.fill(th["stone_dark"], (px - 1, y - h - 2, 6, 2))
    elif deco == "crystals":
        if r.random() < 0.18:
            cx = x + r.randint(3, 12)
            col = r.choice([(110, 255, 230), (190, 140, 255), (120, 200, 255)])
            for i, (dx, h) in enumerate(((0, r.randint(5, 9)), (-2, r.randint(3, 5)), (2, r.randint(3, 6)))):
                pg.draw.polygon(s, col, [(cx + dx - 1, y), (cx + dx, y - h), (cx + dx + 1, y)])
                s.set_at((cx + dx, y - h + 1), (255, 255, 255))
            lights.append((cx, y - 4, 22, tuple(c // 2 for c in col)))
        for _ in range(r.randint(0, 2)):
            grass.append((x + r.randint(0, 15), y + 1, r.randint(2, 4), th["top_dark"]))
    elif deco == "icicles":
        if r.random() < 0.15:
            px = x + r.randint(2, 12)
            s.fill(th["top"], (px, y - 2, r.randint(3, 6), 2))
    elif deco == "ash":
        if r.random() < 0.12:
            px = x + r.randint(2, 12)
            s.fill((60, 50, 50), (px, y - 2, 3, 2))
            s.set_at((px + 1, y - 3), (90, 80, 80))
        if r.random() < 0.25:
            px = x + r.randint(1, 13)
            pg.draw.line(s, (255, 110, 30), (px, y + 6), (px + r.randint(-2, 2), y + 11))
            lights.append((px, y + 8, 9, (200, 60, 10)))


def _ceiling_deco(s, world, th, tx, ty, r, lights):
    x, y = tx * TILE, (ty + 1) * TILE
    deco = th.get("deco")
    if world.get(tx, ty + 1) != ".":
        return
    if deco == "crystals":
        for _ in range(r.randint(1, 3)):
            px = x + r.randint(1, 14)
            h = r.randint(3, 9)
            pg.draw.polygon(s, th["dirt_dark"], [(px - 2, y), (px + 2, y), (px, y + h)])
        if r.random() < 0.12:
            px = x + r.randint(3, 12)
            col = (140, 120, 255)
            pg.draw.polygon(s, col, [(px - 2, y), (px + 2, y), (px, y + 7)])
            lights.append((px, y + 3, 16, (60, 50, 140)))
    elif deco == "icicles":
        for _ in range(r.randint(1, 3)):
            px = x + r.randint(1, 13)
            h = r.randint(3, 10)
            pg.draw.polygon(s, (200, 230, 255), [(px - 1, y), (px + 2, y), (px, y + h)])
            s.set_at((px, y + 1), (255, 255, 255))
    elif deco in ("flowers", "ruins"):
        for _ in range(r.randint(0, 3)):
            px = x + r.randint(1, 14)
            h = r.randint(2, 7)
            pg.draw.line(s, th["top_dark"], (px, y), (px + r.randint(-1, 1), y + h))
    elif deco == "ash":
        if r.random() < 0.3:
            px = x + r.randint(2, 12)
            pg.draw.polygon(s, th["dirt_dark"], [(px - 2, y), (px + 2, y), (px, y + r.randint(3, 6))])


def _bricks(s, world, th, tx, ty):
    x, y = tx * TILE, ty * TILE
    r = _rng(tx, ty, 7)
    s.fill(th["stone"], (x, y, TILE, TILE))
    for row in range(2):
        by = y + row * 8
        off = 0 if (ty * 2 + row) % 2 == 0 else 4
        s.fill(th["stone_dark"], (x, by + 7, TILE, 1))
        for bx in range(-off, TILE, 8):
            if 0 <= bx < TILE:
                s.fill(th["stone_dark"], (x + bx, by, 1, 8))
            left = max(0, bx + 1)
            s.fill(th["stone_hi"], (x + left, by, max(0, min(TILE, bx + 7) - left), 1))
        if r.random() < 0.4:
            s.set_at((x + r.randint(1, 14), by + r.randint(2, 5)), th["stone_dark"])
    if not world.solidish(tx, ty - 1):
        s.fill(th["stone_hi"], (x, y, TILE, 1))
        if th.get("deco") == "icicles":
            s.fill(th["top"], (x, y, TILE, 3))
            s.fill((255, 255, 255), (x, y, TILE, 1))


def _ice(s, world, th, tx, ty):
    x, y = tx * TILE, ty * TILE
    s.fill((150, 206, 246), (x, y, TILE, TILE))
    s.fill((112, 170, 226), (x, y + TILE - 3, TILE, 3))
    s.fill((200, 236, 255), (x + 1, y + 1, TILE - 2, 2))
    pg.draw.line(s, (235, 250, 255), (x + 3, y + 12), (x + 11, y + 4))
    pg.draw.line(s, (235, 250, 255), (x + 6, y + 13), (x + 13, y + 6))
    if not world.solidish(tx, ty - 1):
        s.fill((255, 255, 255), (x, y, TILE, 1))
    pg.draw.rect(s, (90, 140, 200), (x, y, TILE, TILE), 1)


def _slope(s, world, th, tx, ty, ch, grass):
    x, y = tx * TILE, ty * TILE
    depth_col = th["dirt"]
    for lx in range(TILE):
        surf_y = (TILE - lx - 1) if ch == "/" else lx
        s.fill(depth_col, (x + lx, y + surf_y, 1, TILE - surf_y))
        for k, col in ((0, th["top_hi"]), (1, th["top"]), (2, th["top"]), (3, th["top"]), (4, th["top_dark"])):
            if surf_y + k < TILE:
                s.set_at((x + lx, y + surf_y + k), col)
        if lx % 4 == 0 and th.get("deco") in ("flowers", "ruins"):
            grass.append((x + lx, y + surf_y + 1, 3 + (lx * 7) % 3, th["top"]))
    r = _rng(tx, ty, 3)
    for _ in range(3):
        px = r.randint(2, 13)
        lo = (TILE - px) if ch == "/" else px
        if lo + 6 < TILE:
            s.fill(th["speck"], (x + px, y + r.randint(lo + 6, TILE - 1), 2, 1))


def _plank(s, world, th, tx, ty):
    x, y = tx * TILE, ty * TILE
    wood, wood_dk, wood_hi = (150, 104, 66), (96, 62, 40), (196, 146, 96)
    if th.get("deco") == "crystals":
        wood, wood_dk, wood_hi = th["stone"], th["stone_dark"], th["stone_hi"]
    elif th.get("deco") == "icicles":
        wood, wood_dk, wood_hi = (120, 96, 90), (70, 56, 60), (236, 246, 255)
    elif th.get("deco") == "ash":
        wood, wood_dk, wood_hi = (80, 66, 66), (40, 30, 34), (130, 100, 90)
    s.fill(wood, (x, y, TILE, 5))
    s.fill(wood_hi, (x, y, TILE, 1))
    s.fill(wood_dk, (x, y + 4, TILE, 1))
    s.fill(wood_dk, (x + 7, y + 1, 1, 3))
    if world.get(tx - 1, ty) != "-":
        s.fill(wood_dk, (x, y, 1, 5))
        s.fill(wood_dk, (x + 2, y + 5, 2, 4))
    if world.get(tx + 1, ty) != "-":
        s.fill(wood_dk, (x + TILE - 1, y, 1, 5))
        s.fill(wood_dk, (x + TILE - 4, y + 5, 2, 4))


def _spikes(s, th, tx, ty):
    x, y = tx * TILE, ty * TILE
    base = (150, 160, 180)
    for i in range(4):
        bx = x + i * 4
        pg.draw.polygon(s, base, [(bx, y + 16), (bx + 2, y + 7), (bx + 4, y + 16)])
        pg.draw.line(s, (235, 240, 250), (bx + 2, y + 8), (bx + 1, y + 14))
        pg.draw.line(s, (90, 96, 120), (bx + 3, y + 10), (bx + 3, y + 15))
    s.fill((80, 84, 104), (x, y + 14, TILE, 2))
