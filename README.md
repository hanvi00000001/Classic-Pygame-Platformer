# WAYFARER — Classic Pygame Platformer (2022 → 2026)

![Wayfarer gameplay](screenshots/2026/gameplay_meadow.gif)

**▶ Play it in your browser: https://rayenmalouche.github.io/Classic-Pygame-Platformer/**
(or run it locally, see [How to run](#how-to-run))

I made this platformer in 2022 as a student project: a red rectangle walking on hand-placed tiles, with slope
physics and a small level editor. In 2026 I rebuilt it from the ground up. It now has a new hero, five worlds,
a boss, loot, lighting, particles and a soundtrack. **Every sprite, tile, background, sound and song is drawn
or synthesised in code.** The new game ships no image or audio files; only the bonus level reuses the 2022 background paintings.

| ![Title screen](screenshots/2026/title.png) | ![World map](screenshots/2026/map.png) |
| ------------------------------------------- | -------------------------------------- |

The original 2022 code is preserved, untouched, in [`legacy_2022/`](legacy_2022), and its level is playable
inside the remaster as a bonus stage.

---

## 2022 vs 2026

|                   | 2022                                                | 2026                                                       |
| ----------------- | --------------------------------------------------- | ---------------------------------------------------------- |
| **Gameplay**      | ![2022 gameplay](screenshots/2022/gameplay_2.png)   | ![2026 gameplay](screenshots/2026/meadow_hill.png)         |
| **Level editor**  | ![2022 editor](screenshots/2022/level_editor_1.png) | ![2026 editor](screenshots/2026/editor.png)                |
| **The old level** | ![2022 level](screenshots/2022/gameplay_1.png)      | ![2022 level in the remaster](screenshots/2026/legacy.png) |

<details>
<summary>More 2022 screenshots</summary>

|                                          |                                          |
| ---------------------------------------- | ---------------------------------------- |
| ![](screenshots/2022/level_editor_2.png) | ![](screenshots/2022/level_editor_4.png) |
| ![](screenshots/2022/level_editor_3.png) | ![](screenshots/2022/1.png)              |
| ![](screenshots/2022/4.png)              |                                          |

</details>

### What the 2022 version was

An honest assessment of the original code (`legacy_2022/`):

- **What it had:** a tile world loaded from CSV, Mario-style ramps with their own collision maths, horizontal
  scrolling, and a separate level editor with save/load and a tile palette. For a first game, the slope collision
  was the clever part.
- **What it didn't have:** the hero was a 40×60 red rectangle (`image.fill("red")`), and nothing could hurt it or
  be collected. There were no enemies, goal, sound, animation or menus. The parallax backgrounds only appeared in
  the editor, never in the game. The ramp code teleported the player onto the line `y = x + c`, so walking off a
  ramp could snap you around. The world scrolled by moving every tile sprite every frame instead of using
  a camera, and the art was borrowed Mario sprites.

### What the 2026 version is

A new engine built around the same idea: a tile platformer with slopes and a level editor.

---

## Features

**The hero**

- An original hooded wanderer with glowing eyes and a **physics-simulated scarf** (verlet rope) that streams
  behind every move. The scarf turns grey when your dash is spent.
- Modern platformer feel: coyote time, jump buffering, variable jump height, floaty apex, squash & stretch,
  landing dust and footsteps.
- **8-way dash** with afterimages. It breaks cracked bricks, defeats most enemies and refills when you land.
- **Wall slide and wall jump**, and **drop-through** one-way platforms (down + jump).
- Power-ups: 🔥 **Fire orb** (bouncing fireballs), 🪶 **Feather** (double jump), 🫧 **Shield bubble** (absorbs one hit).

**The world**

- 5 hand-designed worlds plus a bonus level, each with its own palette, parallax backdrop, weather, lighting and
  music:

|                                                                                                       |                                                                                                         |                                                                                                    |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| ![Meadow](screenshots/2026/meadow.png) **1 · Verdant Meadow**<br>sunlit hills, pollen, tutorial signs | ![Caves](screenshots/2026/caves.png) **2 · Glimmer Caves**<br>dynamic lighting, glowing crystals, wisps | ![Sunset](screenshots/2026/sunset.png) **3 · Sunset Ruins**<br>crumbling bridges, moving platforms |
| ![Frost](screenshots/2026/frost.png) **4 · Frostpeak**<br>aurora sky, ice physics, wall-jump climb    | ![Volcano](screenshots/2026/volcano.png) **5 · Molten Core**<br>lava, embers, rising heat               | ![Boss](screenshots/2026/boss.png) **Boss · The Molten King**<br>two-phase fight with shockwaves   |

- **Proper 45° slopes.** The 2022 version's signature feature is kept but rewritten as part of a general physics
  body, with step-up so slopes join flat ground cleanly.
- Hazards and gadgets: spikes, lava, springs, crumbling platforms, horizontal and vertical lifts, ice.
- Loot: coins with magnet pickup, `?` blocks, `!` power-up blocks, breakable bricks, treasure chests that burst
  into coins, hearts, and **3 hidden star shards per level**.
- Enemies: slimes, spike beetles (dash or burn them, never stomp), swooping bats, spitter plants, and wisps that
  only move while you look away.
- **Boss fight**: the Molten King leaps, slams, sends shockwaves along the floor, throws fire and rains rocks in
  phase 2. You can only hurt him while he is stunned. The arena gate slams shut behind you.

  ![Boss fight](screenshots/2026/gameplay_boss.gif)

**Presentation**

- Dynamic lighting (light maps plus additive bloom), particles, screen shake, hit-stop, slow-motion boss finish
  and iris transitions.
- Animated title screen, world map with level records, pause menu, results screen with an S/A/B/C rank,
  options and credits.

  ![Results](screenshots/2026/results.png)

- A hand-drawn 5×7 **bitmap font**: every letter on screen is pixel art.
- **Procedural audio**: chiptune sound effects and a small composer that writes a looping track per world
  (melody, bass, arpeggios, drums). Songs render a few milliseconds per frame, so this also works in the
  browser, where threads aren't available.
- Keyboard (QWERTY and AZERTY) and gamepad support. Progress and best times are saved.

**The level editor**

- Built into the game (title → _Level Editor_). Paint with the real tiles and entity previews, switch biome
  with `T`, and press `F5` to play-test instantly.
- Levels are **plain-text files** ([`levels/`](levels)), one character per tile, so you can also edit them in a
  text editor.

---

## How to run

```bash
git clone https://github.com/hanvi00000001/Classic-Pygame-Platformer.git
cd Classic-Pygame-Platformer
pip install -r requirements.txt     # pygame-ce
python main.py
Python 3.11.2
pygame-ce 2.5.8
```

```bash
python main.py --editor                 # open straight into the level editor
python main.py levels/03_sunset.txt     # play a single level file
```

The original 2022 game still runs too:

```bash
cd legacy_2022
pip install pygame
python main_game.py 1       # the red rectangle lives
python level_creator.py     # the original editor
```

## Controls

| Action                   | Keyboard                  | Gamepad       |
| ------------------------ | ------------------------- | ------------- |
| Move                     | ← → / A D (Q D on AZERTY) | stick / d-pad |
| Jump (hold for higher)   | Space / K / C             | A             |
| Dash (8 directions)      | Shift / X / L             | X / RB        |
| Fire (with the fire orb) | F / J / V                 | B / Y         |
| Drop through platforms   | ↓ + Jump                  | down + A      |
| Pause                    | Esc / P                   | Start         |
| Fullscreen               | F11                       |               |

**Editor:** left click paint · right click erase · mouse wheel or `1-9` pick a tile · `TAB` next palette page ·
arrows/WASD or middle-drag to pan · `T` theme · `G` grid · `F5` play-test · `Ctrl+S` save (to
`levels/custom/`) · `Ctrl+O` cycle through existing levels · `Ctrl+N` new level.

## Level format

```
title: Verdant Meadow
theme: meadow            # meadow | caves | sunset | frost | volcano | legacy
powerup: fire            # what "!" blocks give (comma list cycles)
sign1: HIT BLOCKS FROM BELOW
---
................*...........
...P.1....?!?.......g........
########/####\....###########
```

| Char                | Tile / entity                           | Char      | Tile / entity                           |
| ------------------- | --------------------------------------- | --------- | --------------------------------------- |
| `#`                 | ground (auto-tiled)                     | `o`       | coin                                    |
| `=`                 | stone bricks                            | `*`       | star shard                              |
| `I`                 | ice (slippery)                          | `h`       | heart                                   |
| `/` `\`             | 45° slopes                              | `$`       | treasure chest                          |
| `-`                 | one-way platform                        | `P`       | player start                            |
| `^`                 | spikes                                  | `C`       | checkpoint                              |
| `~`                 | lava                                    | `E`       | exit portal                             |
| `B`                 | breakable brick                         | `s`       | spring                                  |
| `?`                 | coin block                              | `m` / `M` | moving platform (horizontal / vertical) |
| `!`                 | power-up block                          | `x`       | crumbling platform                      |
| `g` `k` `b` `t` `q` | slime, spike beetle, bat, spitter, wisp | `K`       | the Molten King                         |
| `l` `c`             | lantern, glow crystal (lights)          | `1`-`9`   | sign (text from `signN:` in the header) |

## Project structure

```
main.py                 entry point (async loop, also used by the web build)
game/
  app.py                window, scene stack, title, world map, options, credits
  play.py               gameplay scene: camera, lighting, collisions, boss, results
  player.py             the hero, scarf physics, abilities
  physics.py            tile physics body: solids, slopes, one-way & moving platforms
  entities.py           loot, blocks, platforms, hazards, checkpoints, portal, signs
  enemies.py            enemies and the Molten King
  tilerender.py         auto-tiling and biome decoration, baked into one surface
  backgrounds.py        procedural parallax backdrops, aurora, weather
  fx.py                 particles, glow sprites, screen shake
  audio.py              sound-effect synth and procedural music composer
  font.py  ui.py        bitmap font, HUD, menus, transitions
  editor.py             in-game level editor
levels/                 campaign levels (+ bonus/legacy_2022.txt, custom/)
legacy_2022/            the original 2022 game, preserved as it was
tools/                  level builder, screenshot/GIF capture, mechanics tests, web build
```

## Developer tools

```bash
python tools/mechanics_test.py   # headless checks: jump height, gaps, springs, slopes, wall jumps, dash, boss
python tools/preview.py          # smoke-test every level and render full-level previews
python tools/capture.py          # README screenshots;  --gif for the animated ones
python tools/build_levels.py     # regenerate the campaign levels from the authoring script
python tools/build_web.py        # WebAssembly build with pygbag -> build/web
```

The browser version is built with [pygbag](https://github.com/pygame-web/pygbag) and deployed to GitHub Pages
by [`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to `main`.

---

Made by **Rayen Malouche**: the original in 2022, the remaster in 2026.
