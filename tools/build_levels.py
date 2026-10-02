"""Authoring script for the campaign. Levels are plain-text maps (see levels/*.txt);
this script lays them out with a few helpers so columns stay aligned, then writes
the .txt files. Edit the .txt files directly or with the in-game editor afterwards.

    python tools/build_levels.py
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "levels")


class B:
    def __init__(self, w, h, **meta):
        self.w, self.h = w, h
        self.g = [["."] * w for _ in range(h)]
        self.meta = meta

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return "#"

    def text(self, x, y, s):
        for i, ch in enumerate(s):
            if ch != " ":
                self.put(x + i, y, ch)

    def rect(self, x0, y0, x1, y1, ch="#"):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, ch)

    def ground(self, x0, x1, top, ch="#"):
        self.rect(x0, top, x1, self.h - 1, ch)

    def clear(self, x0, y0, x1, y1):
        self.rect(x0, y0, x1, y1, ".")

    def pit(self, x0, x1):
        self.clear(x0, 0, x1, self.h - 1)

    def hill(self, x, top, height, plateau):
        """Slope up from ground row `top`, flat plateau, slope down."""
        for i in range(height):
            row = top - 1 - i
            self.put(x + i, row, "/")
            self.rect(x + i, row + 1, x + i, top - 1)
        px0 = x + height
        self.rect(px0, top - height, px0 + plateau - 1, top - 1)
        for i in range(height):
            col = px0 + plateau + i
            row = top - height + i
            self.put(col, row, "\\")
            self.rect(col, row + 1, col, top - 1)
        return px0, top - height

    def ramp_up(self, x, top, height):
        for i in range(height):
            row = top - 1 - i
            self.put(x + i, row, "/")
            self.rect(x + i, row + 1, x + i, top - 1)

    def ramp_down(self, x, top, height):
        """Descends to the right, starting at row top-height."""
        for i in range(height):
            row = top - height + i
            self.put(x + i, row, "\\")
            self.rect(x + i, row + 1, x + i, top - 1)

    def coins(self, x, y, n, dy=0):
        for i in range(n):
            self.put(x + i, y + (dy if i % 2 else 0), "o")

    def arc(self, x, y, n):
        for i in range(n):
            k = i / max(1, n - 1)
            self.put(x + i, y - round(2.5 * (1 - (2 * k - 1) ** 2)), "o")

    def save(self, name):
        head = "\n".join(f"{k}: {v}" for k, v in self.meta.items())
        body = "\n".join("".join(r).rstrip(".") or "." for r in self.g)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(f"{head}\n---\n{body}\n")
        print("wrote", name, f"{self.w}x{self.h}")


# ------------------------------------------------------------------ 1
def meadow():
    L = B(232, 20, title="Verdant Meadow", label="WORLD 1", subtitle="where every journey begins",
          theme="meadow", music="meadow", powerup="fire",
          sign1="ARROWS OR WASD TO MOVE - SPACE TO JUMP",
          sign2="HIT BLOCKS FROM BELOW",
          sign3="HOLD JUMP TO JUMP HIGHER",
          sign4="SHIFT TO DASH - DASH INTO CRACKED BRICKS",
          sign5="LAND ON SPRINGS TO FLY")
    G = 16
    L.ground(0, 231, G)
    L.put(3, G - 1, "P")
    L.put(5, G - 1, "1")
    L.coins(7, G - 2, 4)
    L.text(12, G - 4, "?!?")
    L.put(10, G - 1, "2")
    L.put(18, G - 1, "g")
    # first hill
    px, py = L.hill(22, G, 3, 7)
    L.coins(px + 1, py - 2, 5)
    L.put(px + 5, py - 1, "g")
    # pit with coin arc
    L.put(35, G - 1, "3")
    L.pit(36, 38)
    L.arc(35, G - 3, 5)
    # one-way stairs to a shard
    L.text(42, G - 3, "----")
    L.text(47, G - 6, "---")
    L.text(51, G - 9, "---")
    L.coins(42, G - 4, 4)
    L.coins(47, G - 7, 3)
    L.put(52, G - 11, "*")
    L.put(49, G - 1, "g")
    L.put(56, G - 1, "s")
    L.put(54, G - 1, "5")
    L.coins(56, G - 6, 1)
    L.coins(56, G - 8, 1)
    # brick row with hidden coin block
    L.text(60, G - 4, "BB?BB")
    L.put(66, G - 1, "g")
    L.put(70, G - 1, "$")
    # big valley with slopes down and back up
    L.clear(74, G, 85, G + 1)
    L.put(73, G, "\\")
    L.put(74, G + 1, "\\")
    L.put(85, G + 1, "/")
    L.put(86, G, "/")
    L.coins(77, G + 1, 6)
    L.put(80, G + 1, "g")
    L.put(90, G - 1, "C")
    # floating island section
    L.pit(95, 111)
    L.text(95, G - 2, "--")
    L.rect(98, G - 3, 101, G - 3)
    L.coins(98, G - 4, 4)
    L.rect(104, G - 5, 107, G - 5)
    L.put(105, G - 6, "g")
    L.text(110, G - 3, "--")
    L.arc(102, G - 7, 5)
    L.put(106, G - 10, "o")
    L.text(100, G - 7, "?")
    # wall of bricks hiding a shard
    L.put(113, G - 1, "4")
    L.rect(116, G - 3, 116, G - 1, "B")
    L.rect(117, G - 4, 122, G - 4, "#")
    L.rect(122, G - 3, 122, G - 1, "#")
    L.put(119, G - 1, "*")
    L.coins(117, G - 2, 2)
    L.coins(120, G - 2, 2)
    # second hill with slimes and blocks
    px, py = L.hill(128, G, 4, 10)
    L.text(px + 2, py - 4, "?B!B?")
    L.put(px + 8, py - 1, "g")
    L.put(px + 1, py - 1, "g")
    L.coins(px - 2, py - 1, 1)
    # high plateau climb with springs
    L.put(148, G - 1, "s")
    L.rect(152, G - 8, 160, G - 1, "#")
    L.coins(152, G - 9, 9)
    L.put(158, G - 9, "g")
    L.put(162, G - 1, "t")
    L.text(166, G - 4, "---")
    L.put(167, G - 5, "$")
    # final stretch
    L.pit(170, 173)
    L.arc(169, G - 3, 6)
    L.put(176, G - 1, "g")
    L.put(180, G - 1, "g")
    px, py = L.hill(184, G, 2, 4)
    L.put(px + 1, py - 1, "h")
    L.text(196, G - 5, "o o o")
    L.text(195, G - 4, "-------")
    L.put(198, G - 11, "*")
    L.text(197, G - 9, "---")
    L.put(205, G - 1, "g")
    L.text(212, G - 3, "ooo")
    L.put(222, G - 1, "E")
    L.rect(230, 0, 231, G - 1)
    L.save("01_meadow.txt")


# ------------------------------------------------------------------ 2
def caves():
    L = B(236, 22, title="Glimmer Caves", label="WORLD 2", subtitle="mind the wisps - they hate being watched",
          theme="caves", music="caves", powerup="feather",
          sign1="WISPS ONLY MOVE WHILE YOU LOOK AWAY",
          sign2="JUMP, THEN DASH DOWN TO BREAK CRACKED FLOORS",
          sign3="DASH WORKS IN 8 DIRECTIONS - EVEN UP")
    G = 18
    L.ground(0, 235, G)
    # ceiling with uneven bottom
    import random
    rng = random.Random(2)
    for x in range(236):
        depth = 2 + (1 if rng.random() < 0.35 else 0) + (1 if x % 23 < 4 else 0)
        L.rect(x, 0, x, depth)
    L.put(3, G - 1, "P")
    L.put(6, G - 3, "l")
    L.coins(9, G - 2, 4)
    L.put(14, G - 1, "c")
    L.put(18, G - 1, "g")
    L.text(20, G - 4, "?!?")
    # descending steps
    L.ground(26, 40, G + 1)
    L.clear(26, G, 40, G)
    L.put(26, G, "\\")
    L.coins(29, G - 1, 5)
    L.put(34, G, "g")
    L.put(37, G - 5, "b")
    L.put(40, G - 1, "c")
    # spikes pit with crumbling path
    L.ground(41, 56, G + 2)
    L.clear(41, G, 56, G + 1)
    L.rect(41, G + 1, 56, G + 1, "^")
    L.text(43, G - 2, "x x x x x")
    L.coins(43, G - 3, 9, 0)
    for x in range(44, 52, 2):
        L.put(x, G - 3, ".")
    L.put(56, G - 6, "b")
    L.put(58, G - 3, "l")
    # breakable wall + shard pocket
    L.rect(62, G - 4, 62, G - 1, "B")
    L.rect(63, G - 5, 68, G - 5)
    L.rect(68, G - 4, 68, G - 1)
    L.put(65, G - 1, "*")
    L.put(64, G - 1, "c")
    L.coins(66, G - 2, 2)
    # wisp hall
    L.put(72, G - 1, "c")
    L.put(74, G - 1, "1")
    L.put(80, G - 8, "q")
    L.coins(76, G - 2, 10)
    L.text(78, G - 5, "---")
    L.put(86, G - 1, "g")
    L.put(90, G - 1, "C")
    # vertical lifts over a chasm
    L.pit(94, 120)
    for x in range(94, 121):
        L.rect(x, 0, x, 3)
    L.put(92, G - 1, "3")
    L.put(95, G - 1, "M")
    L.coins(99, G - 8, 3)
    L.rect(100, G - 6, 103, G - 6)
    L.put(101, G - 7, "c")
    L.put(106, G - 1, "M")
    L.rect(110, G - 9, 113, G - 9)
    L.put(112, G - 13, "*")
    L.text(111, G - 12, "-")
    L.put(116, G - 1, "M")
    L.put(108, G - 12, "b")
    L.put(118, G - 7, "o")
    L.put(118, G - 9, "o")
    # landing + spikes corridor
    L.put(124, G - 3, "l")
    L.put(126, G - 1, "k")
    L.text(130, G - 1, "^^^")
    L.coins(129, G - 4, 5)
    L.put(136, G - 1, "g")
    L.rect(139, G - 3, 141, G - 1)
    L.text(139, G - 4, "?B?")
    L.put(140, G - 8, "q")
    L.text(144, G - 1, "^^^^")
    L.text(144, G - 4, "----")
    L.put(150, G - 1, "c")
    L.put(152, G - 1, "k")
    # cave heart: big crystal chamber with chest
    L.clear(156, 3, 176, 4)
    L.put(158, G - 1, "c")
    L.put(166, G - 1, "c")
    L.put(174, G - 1, "c")
    L.text(160, G - 4, "-----")
    L.text(165, G - 7, "-----")
    L.text(170, G - 10, "-----")
    L.put(172, G - 11, "$")
    L.coins(160, G - 5, 5)
    L.coins(165, G - 8, 5)
    L.put(162, G - 1, "q")
    L.put(168, G - 9, "b")
    # breakable floor drop with shard below
    L.rect(180, G, 183, G, "B")
    L.rect(180, G + 1, 183, G + 1, ".")
    L.put(181, G + 1, "*")
    L.put(182, G + 1, "o")
    L.ground(178, 185, G + 2)
    L.rect(178, G, 179, G + 1)
    L.rect(184, G, 185, G + 1)
    L.put(177, G - 1, "2")
    L.put(188, G - 1, "g")
    L.put(192, G - 1, "g")
    L.put(196, G - 3, "l")
    L.ramp_up(198, G, 2)
    L.rect(200, G - 2, 214, G - 1)
    L.coins(201, G - 3, 6)
    L.put(208, G - 3, "k")
    L.put(212, G - 7, "q")
    L.put(218, G - 1, "c")
    L.put(224, G - 1, "E")
    L.put(221, G - 3, "l")
    L.put(227, G - 3, "l")
    L.rect(232, 0, 235, G - 1)
    L.save("02_caves.txt")


# ------------------------------------------------------------------ 3
def sunset():
    L = B(244, 20, title="Sunset Ruins", label="WORLD 3", subtitle="an old road, crumbling into the sky",
          theme="sunset", music="sunset", powerup="shield,fire",
          sign1="SPIKE BEETLES CAN'T BE STOMPED - DASH OR BURN THEM")
    G = 16
    L.ground(0, 30, G)
    L.put(3, G - 1, "P")
    L.coins(6, G - 2, 3)
    # ruined columns
    for x in (10, 16):
        L.rect(x, G - 2, x, G - 1, "=")
    L.text(13, G - 4, "!")
    L.put(7, G - 1, "1")
    L.put(13, G - 1, "k")
    L.put(22, G - 1, "t")
    L.text(25, G - 4, "?")
    # long chasm with horizontal platforms
    L.pit(31, 62)
    L.put(31, G - 1, "m")
    L.coins(33, G - 3, 4)
    L.rect(44, G - 2, 47, G - 2, "=")
    L.put(45, G - 3, "t")
    L.put(48, G - 4, "m")
    L.coins(48, G - 6, 3)
    L.text(52, G - 7, "x x")
    L.put(53, G - 8, "*")
    L.ground(63, 80, G)
    L.put(66, G - 1, "C")
    L.put(70, G - 1, "k")
    L.put(74, G - 1, "s")
    L.rect(77, G - 7, 80, G - 1, "=")
    L.coins(77, G - 8, 4)
    # crumbling bridge
    L.pit(81, 100)
    L.text(81, G - 7, "xxxxxxxxxxxxxxxxxxxx")
    L.coins(83, G - 9, 16)
    L.put(90, G - 11, "*")
    L.text(89, G - 10, "---")
    L.put(86, G - 2, "m")
    L.ground(101, 128, G - 4)
    L.rect(101, G - 7, 103, G - 5, "=")
    L.put(106, G - 5, "k")
    L.put(112, G - 5, "t")
    L.text(108, G - 8, "B?B?B")
    L.clear(116, G - 4, 128, G - 1)
    L.ramp_down(116, G, 4)
    L.put(122, G - 1, "k")
    L.put(126, G - 1, "$")
    # ruins temple with arches
    L.ground(129, 170, G)
    L.text(131, G - 3, "---------------------------")
    for x in (131, 157):
        L.rect(x, G - 2, x, G - 1, "=")
    L.text(134, G - 6, "----")
    L.text(150, G - 6, "----")
    L.put(143, G - 9, "*")
    L.text(141, G - 8, "-----")
    L.put(137, G - 1, "l")
    L.put(151, G - 1, "l")
    L.put(136, G - 1, "g")
    L.put(144, G - 1, "k")
    L.put(152, G - 1, "g")
    L.coins(134, G - 4, 4)
    L.coins(150, G - 4, 4)
    L.put(160, G - 1, "s")
    L.put(164, G - 1, "C")
    # final sky bridge with springs and moving platforms
    L.pit(171, 210)
    L.put(171, G - 1, "m")
    L.rect(184, G - 1, 186, G - 1, "=")
    L.put(185, G - 2, "s")
    L.rect(192, G - 6, 195, G - 6, "=")
    L.put(193, G - 7, "t")
    L.put(197, G - 3, "m")
    L.coins(186, G - 9, 5)
    L.text(204, G - 6, "xxx")
    L.ground(211, 243, G)
    L.put(214, G - 1, "k")
    L.put(218, G - 1, "g")
    L.hill(222, G, 2, 6)
    L.put(226, G - 3, "h")
    L.put(236, G - 1, "E")
    L.rect(242, 0, 243, G - 1, "=")
    L.save("03_sunset.txt")


# ------------------------------------------------------------------ 4
def frost():
    L = B(216, 34, title="Frostpeak", label="WORLD 4", subtitle="climb. the summit remembers you",
          theme="frost", music="frost", powerup="feather,fire",
          sign1="SLIDE ON A WALL AND JUMP TO WALL-JUMP",
          sign2="CRUMBLING ICE - KEEP MOVING")
    G = 30
    L.ground(0, 70, G)
    L.put(3, G - 1, "P")
    L.coins(6, G - 2, 4)
    L.text(12, G - 4, "?!?")
    # ice run
    L.rect(18, G, 40, G, "I")
    L.put(24, G - 1, "g")
    L.put(32, G - 1, "g")
    L.text(26, G - 1, "^")
    L.coins(25, G - 3, 3)
    L.put(36, G - 5, "b")
    L.put(44, G - 1, "s")
    L.rect(47, G - 8, 52, G - 1, "=")
    L.put(49, G - 9, "$")
    # wall-jump chimney up (entered from below the left wall)
    L.rect(56, 6, 57, G - 4, "#")
    L.rect(62, 10, 90, 16, "#")
    L.rect(62, 17, 120, 33, "#")
    L.put(59, G - 1, "C")
    L.put(54, G - 1, "1")
    L.text(58, G - 5, "--")
    L.text(60, G - 10, "--")
    L.text(58, G - 15, "--")
    L.text(60, G - 19, "--")
    for y in (G - 7, G - 12, G - 17):
        L.coins(59, y, 2)
    L.put(59, 7, "*")
    # top of the chimney: high ridge going right
    L.put(70, 9, "g")
    L.coins(68, 8, 6)
    L.rect(74, 9, 76, 9, "I")
    L.put(80, 9, "k")
    L.text(82, 5, "?B?")
    L.put(88, 4, "b")
    # descent along icy slopes
    for i in range(6):
        L.put(91 + i, 10 + i, "\\")
        L.rect(91 + i, 11 + i, 91 + i, 16)
    L.rect(97, 16, 120, 18)
    L.put(100, 15, "g")
    L.put(105, 15, "C")
    L.coins(108, 14, 5)
    L.put(114, 11, "b")
    # drop shaft with crumbling ledges
    L.pit(121, 141)
    L.ground(121, 141, G + 2)
    L.rect(121, G + 1, 141, G + 1, "^")
    L.text(122, 19, "xxx")
    L.text(130, 22, "xxx")
    L.text(123, 25, "xxx")
    L.text(133, 28, "xxx")
    L.coins(122, 18, 3)
    L.coins(130, 21, 3)
    L.coins(123, 24, 3)
    L.put(128, 22, "*")
    L.put(118, 15, "2")
    L.ground(142, 160, G)
    L.rect(142, G, 160, G, "I")
    L.ground(142, 160, G)
    L.rect(142, G, 160, G, "I")
    L.put(146, G - 1, "g")
    L.put(152, G - 1, "k")
    L.text(148, G - 4, "?!?")
    L.put(150, G - 9, "b")
    # summit climb (moving platforms upward)
    L.put(162, G - 1, "M")
    L.rect(166, G - 9, 170, G - 9, "#")
    L.put(168, G - 10, "g")
    L.put(172, G - 10, "M")
    L.rect(176, G - 18, 215, G - 18, "#")
    L.rect(176, G - 17, 215, G - 1, "#")
    L.ground(161, 175, G)
    L.coins(177, G - 19, 6)
    L.put(184, G - 19, "g")
    L.put(190, G - 19, "C")
    L.put(196, G - 24, "b")
    L.text(198, G - 21, "-----")
    L.put(200, G - 22, "h")
    L.put(208, G - 19, "E")
    L.rect(214, 0, 215, G - 19, "#")
    L.save("04_frost.txt")


# ------------------------------------------------------------------ 5
def volcano():
    L = B(240, 22, title="Molten Core", label="WORLD 5", subtitle="the king beneath the mountain wakes",
          theme="volcano", music="volcano", powerup="fire,shield", arena="154,206", gate="153",
          sign1="THE KING CAN ONLY BE HURT WHILE HE IS STUNNED")
    G = 18
    L.ground(0, 239, G)
    L.rect(0, 0, 239, 1)
    L.put(3, G - 1, "P")
    L.text(8, G - 4, "!?!")
    L.coins(7, G - 2, 4)
    # lava pools with stepping stones
    def lava(x0, x1):
        L.clear(x0, G, x1, G + 1)
        L.rect(x0, G, x1, G, "~")
        L.rect(x0, G + 1, x1, G + 1, "~")
    lava(16, 30)
    L.rect(19, G - 2, 20, G - 2)
    L.rect(24, G - 3, 25, G - 3)
    L.rect(28, G - 2, 29, G - 2)
    L.coins(19, G - 3, 2)
    L.coins(24, G - 4, 2)
    L.put(34, G - 1, "t")
    L.put(38, G - 1, "k")
    # crumbling over lava
    lava(42, 60)
    L.text(43, G - 3, "xx  xx  xx  xx")
    L.coins(43, G - 5, 14)
    L.put(52, G - 7, "*")
    L.text(51, G - 6, "---")
    L.put(64, G - 1, "C")
    L.put(68, G - 1, "g")
    L.put(72, G - 1, "t")
    L.text(70, G - 4, "?B?")
    # lava lake with moving platforms
    lava(76, 104)
    L.put(77, G - 2, "m")
    L.rect(89, G - 4, 91, G - 4)
    L.put(90, G - 5, "t")
    L.put(93, G - 3, "m")
    L.coins(80, G - 5, 6)
    L.put(98, G - 9, "o")
    L.ground(105, 140, G)
    L.put(108, G - 1, "k")
    L.put(114, G - 1, "k")
    L.text(110, G - 4, "B!B")
    L.rect(118, G - 6, 124, G - 1)
    L.put(121, G - 7, "$")
    L.put(128, G - 1, "g")
    L.put(132, G - 1, "t")
    # shard behind a lava chimney
    lava(136, 139)
    L.text(136, G - 3, "--")
    L.put(138, G - 7, "*")
    L.text(137, G - 6, "---")
    L.put(144, G - 1, "C")
    L.put(146, G - 1, "1")
    L.put(148, G - 1, "h")
    # corridor into arena
    L.rect(152, 2, 153, G - 5)
    L.coins(150, G - 2, 3)
    # boss arena 154..205
    L.rect(206, 2, 207, G - 1)
    L.text(160, G - 5, "---")
    L.text(196, G - 5, "---")
    L.text(178, G - 8, "----")
    L.put(186, G - 1, "K")
    L.put(200, G - 1, "E")
    L.put(176, G - 12, "*")
    L.text(175, G - 11, "---")
    L.rect(208, 2, 239, G - 1)
    L.save("05_volcano.txt")


# ------------------------------------------------------------------ bonus
def legacy():
    """The 2022 level, converted from its original CSV."""
    path = os.path.join(ROOT, "legacy_2022", "level1_data.csv")
    rows = list(csv.reader(open(path)))
    m = {"-1": ".", "0": "#", "1": "#", "2": "#", "3": "#", "4": "#", "5": "#", "6": "\\", "7": "#", "8": "#",
         "9": "/", "10": "B", "11": "?", "12": "#", "13": "P"}
    grid = [[m.get(c, ".") for c in r] for r in rows]
    w = 190
    L = B(w, 18, title="Hills of 2022", label="BONUS", subtitle="the original level, as it was saved in 2022",
          theme="legacy", music="legacy", powerup="fire")
    for y, r in enumerate(grid):
        for x, ch in enumerate(r[:w]):
            L.put(x, y + 2, ch)
    # the 2022 game never had a goal, coins or enemies: add a few
    L.put(4, 14, "R")
    for x in (40, 75, 98, 120):
        L.put(x, 14, "g")
    L.coins(31, 12, 3)
    L.arc(60, 12, 4)
    L.coins(86, 10, 3)
    L.text(110, 9, "?!?")
    L.put(25, 5, "*")
    L.put(116, 4, "*")
    L.put(150, 14, "*")
    L.ground(127, w - 1, 17)
    L.put(140, 16, "C")
    L.put(176, 16, "E")
    L.rect(w - 2, 0, w - 1, 16)
    L.save(os.path.join("bonus", "legacy_2022.txt"))


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "bonus"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "custom"), exist_ok=True)
    meadow()
    caves()
    sunset()
    frost()
    volcano()
    legacy()
