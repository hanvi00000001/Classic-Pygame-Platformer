"""Scripted screenshots / GIF frames for the README.

    python tools/capture.py              # screenshots into screenshots/2026/
    python tools/capture.py --gif        # also an animated gameplay GIF
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame as pg  # noqa: E402

from game import app as app_mod  # noqa: E402
from game.play import PlayScene  # noqa: E402
from game.settings import TILE  # noqa: E402
from game.world import Level  # noqa: E402

OUT = os.path.join(ROOT, "screenshots", "2026")
SCALE = 3


def snap(app, name, scale=SCALE):
    app.scene.draw(app.canvas)
    img = pg.transform.scale_by(app.canvas, scale)
    pg.image.save(img, os.path.join(OUT, name + ".png"))
    print("saved", name)


def run(app, frames, held=()):
    for _ in range(frames):
        app.inp.injected = set(held)
        app.frame()


def play(app, file, tx=None, ty=None, setup=None):
    lvl = Level.load(os.path.join(ROOT, "levels", file))
    s = PlayScene(app, lvl)
    app.stack = [s]
    s.iris.k = 0
    s.iris.target = 0
    s.banner_t = 999
    if tx is not None:
        p = s.player
        p.body.x = tx * TILE
        p.body.y = ty * TILE
        s.cam_x = p.body.cx - 240
        s.cam_y = p.body.cy - 150
        s._clamp_cam()
    if setup:
        setup(s)
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    app = app_mod.App(headless=True)
    shots = sys.argv[1:] or ["all"]
    want = lambda k: "all" in shots or k in shots  # noqa: E731

    if want("title"):
        run(app, 150)
        snap(app, "title")
    if want("meadow"):
        s = play(app, "01_meadow.txt", 6, 14)
        run(app, 30, ["right"])
        run(app, 10, ["right", "jump"])
        run(app, 6, ["right"])
        snap(app, "meadow")
    if want("meadow2"):
        s = play(app, "01_meadow.txt", 126, 14)
        s.player.fire = True
        run(app, 40, ["right"])
        run(app, 8, ["right", "jump"])
        run(app, 2, ["right", "jump", "fire"])
        run(app, 8, ["right"])
        snap(app, "meadow_hill")
    if want("caves"):
        s = play(app, "02_caves.txt", 150, 16)
        run(app, 40, ["right"])
        run(app, 14, ["right", "jump"])
        snap(app, "caves")
    if want("sunset"):
        s = play(app, "03_sunset.txt", 100, 10)
        run(app, 30, ["right"])
        run(app, 12, ["right", "jump"])
        snap(app, "sunset")
    if want("frost"):
        s = play(app, "04_frost.txt", 64, 8)
        run(app, 50, ["right"])
        snap(app, "frost")
    if want("volcano"):
        s = play(app, "05_volcano.txt", 60, 16)
        run(app, 30, ["right"])
        snap(app, "volcano")
    if want("boss"):
        s = play(app, "05_volcano.txt", 166, 16)
        run(app, 200, ["right"])
        run(app, 40, [])
        snap(app, "boss")
    if want("legacy"):
        s = play(app, "bonus/legacy_2022.txt", 3, 14)
        run(app, 40, [])
        snap(app, "legacy")
    if want("editor"):
        from game.editor import EditorScene
        from game.world import Level as _L
        ed = EditorScene(app, _L.load(os.path.join(ROOT, "levels", "01_meadow.txt")))
        ed.cam = [1740.0, 50.0]
        ed.sel = 22
        app.stack = [ed]
        run(app, 20)
        snap(app, "editor")
    if want("results"):
        from game.entities import Portal
        s = play(app, "01_meadow.txt", 214, 14)
        s.stats.update(coins=87, score=14230, enemies=19, time=60 * 154, chests=3)
        s.gems_found = {0, 1, 2}
        portal = [e for e in s.entities if isinstance(e, Portal)][0]
        s.finish_level(portal)
        run(app, 230)
        snap(app, "results")
    if want("map"):
        app.stack = [app_mod.MapScene(app)]
        run(app, 60)
        snap(app, "map")


if __name__ == "__main__" and "--gif" not in sys.argv:
    main()


def gif(name, file, script, tx=None, ty=None, scale=1.5, every=2, setup=None):
    """Record a scripted run to screenshots/2026/<name>.gif"""
    from PIL import Image
    app = _APP
    play(app, file, tx, ty, setup)
    frames = []
    i = 0
    for held, n in script:
        for _ in range(n):
            app.inp.injected = set(held)
            app.frame()
            if i % every == 0:
                img = pg.transform.scale_by(app.canvas, scale)
                raw = pg.image.tobytes(img, "RGB")
                frames.append(Image.frombytes("RGB", img.get_size(), raw).quantize(colors=200, method=Image.Quantize.MEDIANCUT))
            i += 1
    path = os.path.join(OUT, name + ".gif")
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / 60 * every), loop=0, optimize=True)
    print("saved", name, f"{os.path.getsize(path) // 1024} KB", len(frames), "frames")


_APP = None

if __name__ == "__main__" and "--gif" in sys.argv:
    os.makedirs(OUT, exist_ok=True)
    _APP = app_mod.App(headless=True)
    R, J, D, F = "right", "jump", "dash", "fire"
    gif("gameplay_meadow", "01_meadow.txt", [
        ((R,), 40), ((R, J), 16), ((R,), 30), ((R, J), 14), ((R,), 20), ((R, J), 18), ((R,), 40),
        ((R, J), 16), ((R,), 12), ((R, D), 3), ((R,), 40), ((R, J), 18), ((R,), 40)], 3, 14)
    gif("gameplay_boss", "05_volcano.txt", [((R,), 60), ((), 60), ((J,), 16), ((), 30), (("left",), 30), ((J,), 16), ((), 60)],
        170, 16, setup=lambda s: setattr(s.player, "fire", True))
