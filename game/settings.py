"""Global constants. The game renders to a small pixel canvas that is scaled up."""
import os
import sys

TITLE = "WAYFARER"
SUBTITLE = "a classic pygame platformer - 2026 remaster"

TILE = 16
VIEW_W, VIEW_H = 480, 270
SCALE = 3
FPS = 60

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVEL_DIR = os.path.join(ROOT, "levels")
CUSTOM_DIR = os.path.join(LEVEL_DIR, "custom")
LEGACY_DIR = os.path.join(ROOT, "legacy_2022")
SAVE_PATH = os.path.join(ROOT, "save.json")

WEB = sys.platform == "emscripten"

# physics (pixels / frame at 60 fps)
GRAVITY = 0.30
MAX_FALL = 6.0
RUN_SPEED = 2.2
RUN_ACCEL = 0.28
GROUND_FRICTION = 0.32
AIR_ACCEL = 0.20
AIR_FRICTION = 0.08
ICE_ACCEL = 0.05
ICE_FRICTION = 0.03
JUMP_SPEED = 5.8
JUMP_CUT = 0.45
COYOTE_FRAMES = 7
JUMP_BUFFER = 8
WALL_SLIDE_SPEED = 1.1
WALL_JUMP_X = 2.6
WALL_JUMP_Y = 5.0
DASH_SPEED = 5.2
DASH_FRAMES = 11
SPRING_SPEED = 9.0

INVULN_FRAMES = 90
START_HEARTS = 3
MAX_HEARTS = 6
