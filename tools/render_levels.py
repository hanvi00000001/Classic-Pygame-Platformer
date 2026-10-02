"""Render every level to a PNG strip (tools/out/view_*.png) for design review."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import pygame as pg  # noqa: E402

from preview import level_paths, render_full, OUT  # noqa: E402
from game.app import App  # noqa: E402

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    app = App(headless=True)
    app.audio.ok = False
    for p in level_paths():
        if len(sys.argv) > 1 and not any(a in p for a in sys.argv[1:]):
            continue
        render_full(app, p)
        name = os.path.splitext(os.path.basename(p))[0]
        im = pg.image.load(os.path.join(OUT, f"full_{name}.png"))
        w, h = im.get_size()
        parts = 3
        pw = (w + parts - 1) // parts
        out = pg.Surface((pw, (h + 4) * parts))
        for i in range(parts):
            out.blit(im, (0, i * (h + 4)), (i * pw, 0, pw, h))
            for x in range(0, pw, 16 * 10):
                out.fill((255, 0, 0), (x, i * (h + 4), 1, 6))
        pg.image.save(out, os.path.join(OUT, f"view_{name}.png"))
        print("rendered", name)
