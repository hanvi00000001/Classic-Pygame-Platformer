"""Developer tool: smoke-test every level headless and render full-level previews.

    python tools/preview.py            # smoke test + previews into tools/out/
"""
import os
import random
import sys
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame as pg  # noqa: E402

from game.app import App  # noqa: E402
from game.play import PlayScene  # noqa: E402
from game.world import Level, list_campaign  # noqa: E402

OUT = os.path.join(ROOT, "tools", "out")


def level_paths():
    paths = list_campaign()
    bonus = os.path.join(ROOT, "levels", "bonus", "legacy_2022.txt")
    if os.path.exists(bonus):
        paths.append(bonus)
    return paths


def render_full(app, path):
    lvl = Level.load(path)
    scene = PlayScene(app, lvl)
    w, h = scene.world.px_w, scene.world.px_h
    big = pg.Surface((w, h))
    big.fill(scene.theme["sky"][1])
    big.blit(scene.tiles, (0, 0))
    g = pg.Surface((w, h))
    for e in scene.entities:
        e.draw(big, (0, 0), g)
    scene.player.draw(big, (0, 0), g)
    big.blit(g, (0, 0), special_flags=pg.BLEND_ADD)
    name = os.path.splitext(os.path.basename(path))[0]
    pg.image.save(big, os.path.join(OUT, f"full_{name}.png"))
    return scene


def smoke(app, path, frames=900):
    lvl = Level.load(path)
    scene = PlayScene(app, lvl)
    app.stack = [scene]
    rng = random.Random(1)
    held = set()
    for f in range(frames):
        if f % 20 == 0:
            held = set(a for a in ("left", "right", "jump", "dash", "fire", "down", "up") if rng.random() < 0.35)
            held.add("right")
            held.discard("left")
        app.inp.injected = held
        app.frame()
        if not app.stack:
            break
    return scene


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    app = App(headless=True)
    ok = True
    for p in level_paths():
        try:
            render_full(app, p)
            s = smoke(app, p)
            print(f"OK   {os.path.basename(p):24s} x={s.player.body.x:7.1f} coins={s.stats['coins']} deaths={s.stats['deaths']}")
        except Exception:
            ok = False
            print(f"FAIL {p}")
            traceback.print_exc()
    sys.exit(0 if ok else 1)
