"""Headless checks of the movement rules the level design relies on.

    python tools/mechanics_test.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game.app import App  # noqa: E402
from game.play import PlayScene  # noqa: E402
from game.settings import TILE  # noqa: E402
from game.world import Level  # noqa: E402

app = App(headless=True)
app.audio.ok = False
FAILS = []


def scene(rows, **meta):
    meta.setdefault("theme", "meadow")
    s = PlayScene(app, Level(rows, meta))
    s.banner_t = 999
    app.stack = [s]
    return s


def step(s, held=(), n=1):
    for _ in range(n):
        app.inp.injected = set(held)
        app.inp.update()
        s.update()


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({info})" if info else ""))
    if not cond:
        FAILS.append(name)


FLAT = ["." * 40 for _ in range(10)] + ["..P" + "." * 37] + ["#" * 40 for _ in range(3)]

# 1. jump height
s = scene(FLAT)
step(s, (), 20)
y0 = s.player.body.bottom
step(s, ("jump",), 1)
top = y0
for _ in range(60):
    step(s, ("jump",))
    top = min(top, s.player.body.bottom)
rise = (y0 - top) / TILE
check("full jump clears 3 tiles", rise >= 3.05, f"{rise:.2f} tiles")
s = scene(FLAT)
step(s, (), 20)
step(s, ("jump",), 3)
top = y0
for _ in range(60):
    step(s, ())
    top = min(top, s.player.body.bottom)
check("short hop is lower", (y0 - top) / TILE < 2.0, f"{(y0 - top) / TILE:.2f} tiles")

# 2. jump distance (running)
rows = ["." * 60 for _ in range(10)] + ["..P" + "." * 57] + ["#" * 20 + "." * 5 + "#" * 35 for _ in range(3)]
s = scene(rows)
step(s, ("right",), 40)
while s.player.body.x + s.player.body.w < 20 * TILE - 2:
    step(s, ("right",))
step(s, ("right", "jump"), 45)
step(s, ("right",), 30)
check("running jump crosses a 5-tile gap", not s.player.dead and s.player.body.x > 25 * TILE, f"x={s.player.body.x / TILE:.1f}")

# 3. spring height
rows = ["." * 30 for _ in range(14)] + [".." + "P.s" + "." * 25] + ["#" * 30 for _ in range(3)]
s = scene(rows)
step(s, (), 10)
y0 = s.player.body.bottom
step(s, ("right",), 14)
top = y0
for _ in range(80):
    step(s, ())
    top = min(top, s.player.body.bottom)
check("spring launches 8+ tiles", (y0 - top) / TILE >= 8.0, f"{(y0 - top) / TILE:.2f} tiles")

# 4. slopes: walk up and down a hill without getting stuck
rows = ["." * 50 for _ in range(10)]
rows += ["." * 14 + "/#####\\" + "." * 29]
rows += ["." * 13 + "/#######\\" + "." * 28]
rows += ["..P" + "." * 9 + "/#########\\" + "." * 27]
rows += ["#" * 50 for _ in range(3)]
s = scene(rows)
step(s, (), 10)
min_bottom = 999
for _ in range(220):
    step(s, ("right",))
    min_bottom = min(min_bottom, s.player.body.bottom)
check("walks over a slope hill", s.player.body.x > 30 * TILE, f"x={s.player.body.x / TILE:.1f}")
check("climbs to the hill top", min_bottom <= 10 * TILE + 1, f"top={min_bottom / TILE:.2f}")
for _ in range(220):
    step(s, ("left",))
check("walks back over the hill", s.player.body.x < 10 * TILE, f"x={s.player.body.x / TILE:.1f}")

# 5. wall jump up a 4-wide chimney
rows = ["." * 30, "##" + "." * 28] + ["###....###" + "." * 20 for _ in range(16)]
rows += ["###P...###" + "." * 20] + ["#" * 30 for _ in range(2)]
s = scene(rows)
step(s, (), 10)
start = s.player.body.y
d = 1
hold = 0
for i in range(400):
    held = {"right" if d > 0 else "left"}
    b = s.player.body
    if hold > 0:
        hold -= 1
        held.add("jump")
    elif (s.player.wall_dir == d and b.vy > -1) or b.on_ground:
        hold = 12
        held.add("jump")
        d = -d
    step(s, held)
climbed = (start - s.player.body.y) / TILE
check("wall jumps climb a chimney", climbed > 10, f"{climbed:.1f} tiles")

# 6. dash breaks a cracked brick wall
rows = ["." * 30 for _ in range(10)] + ["..P.....B" + "." * 21, "........B" + "." * 21] + ["#" * 30 for _ in range(3)]
s = scene(rows)
step(s, (), 10)
step(s, ("right",), 25)
step(s, ("right", "dash"), 2)
step(s, ("right",), 20)
check("dash breaks bricks", s.world.get(8, 10) == "." and s.player.body.x > 9 * TILE, f"x={s.player.body.x / TILE:.1f}")

# 7. down-dash breaks a cracked floor
rows = ["." * 20 for _ in range(10)] + ["...P" + "." * 16] + ["###BB" + "#" * 15] + ["###..###" + "#" * 12] + ["#" * 20]
s = scene(rows)
step(s, (), 10)
step(s, ("jump",), 8)
step(s, ("down", "dash"), 2)
step(s, ("down",), 30)
check("down-dash breaks floor", s.world.get(3, 11) == "." or s.world.get(4, 11) == ".", f"y={s.player.body.bottom / TILE:.1f}")

# 8. drop through one-way platform
rows = ["." * 20 for _ in range(8)] + ["...P" + "." * 16] + ["..------" + "." * 12] + ["." * 20] * 3 + ["#" * 20 for _ in range(2)]
s = scene(rows)
step(s, (), 20)
y0 = s.player.body.bottom
step(s, ("down", "jump"), 2)
step(s, ("down",), 40)
check("drops through one-way", s.player.body.bottom > y0 + 2 * TILE, f"{(s.player.body.bottom - y0) / TILE:.1f} tiles")

# 9. stomp kills a slime and bounces
rows = ["." * 30 for _ in range(10)] + ["..P...g" + "." * 23] + ["#" * 30 for _ in range(3)]
s = scene(rows)
slime = [e for e in s.entities if e.enemy][0]
s.player.body.x = slime.x - 12
s.player.body.y = 7 * TILE
step(s, (), 60)
dead = [e for e in s.entities if e.enemy and e.dying or not e.alive]
check("stomping a slime defeats it", s.stats["enemies"] == 1 and s.player.hearts == 3, f"enemies={s.stats['enemies']} hearts={s.player.hearts}")

# 10. boss takes damage only when stunned
from game.enemies import MoltenKing  # noqa: E402
lvl = Level.load(os.path.join(ROOT, "levels", "05_volcano.txt"))
s = PlayScene(app, lvl)
app.stack = [s]
boss = s.boss
boss.state = "walk"
check("boss immune while walking", not boss.take_hit(s, "stomp") and boss.hp == boss.max_hp)
for i in range(boss.max_hp):
    boss.state = "stunned"
    boss.invuln = 0
    boss.take_hit(s, "stomp")
check("boss can be defeated", boss.hp <= 0 and boss.dying > 0)

print()
print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
