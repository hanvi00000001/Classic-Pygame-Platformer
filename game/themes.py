"""Colour palettes and atmosphere settings per biome."""

THEMES = {
    "meadow": dict(
        sky=[(92, 160, 230), (150, 205, 245), (214, 238, 250)],
        top=(98, 196, 78), top_hi=(170, 232, 104), top_dark=(52, 140, 60),
        dirt=(150, 98, 60), dirt_dark=(108, 66, 44), dirt_hi=(184, 128, 80), speck=(122, 80, 50),
        stone=(126, 132, 150), stone_dark=(86, 90, 110), stone_hi=(168, 176, 192),
        far=(116, 146, 196), mid=(92, 150, 128), near=(56, 118, 90),
        darkness=0, weather="pollen", deco="flowers", clouds=True, sun=(255, 246, 200),
        grade=None, fog=None,
    ),
    "caves": dict(
        sky=[(14, 12, 30), (24, 22, 48), (34, 30, 62)],
        top=(84, 214, 196), top_hi=(170, 255, 236), top_dark=(36, 130, 130),
        dirt=(64, 58, 96), dirt_dark=(40, 36, 66), dirt_hi=(88, 82, 128), speck=(52, 46, 82),
        stone=(76, 70, 112), stone_dark=(46, 42, 74), stone_hi=(110, 104, 150),
        far=(30, 28, 56), mid=(40, 36, 70), near=(52, 46, 86),
        darkness=0.86, ambient=(46, 40, 78), weather="drip", deco="crystals", clouds=False, sun=None,
        grade=(10, 0, 30), fog=(60, 50, 120),
    ),
    "sunset": dict(
        sky=[(64, 40, 110), (200, 84, 110), (255, 166, 96)],
        top=(230, 170, 92), top_hi=(255, 214, 140), top_dark=(176, 108, 60),
        dirt=(176, 92, 70), dirt_dark=(126, 56, 54), dirt_hi=(214, 128, 88), speck=(150, 72, 62),
        stone=(160, 96, 96), stone_dark=(110, 60, 72), stone_hi=(206, 140, 124),
        far=(150, 74, 120), mid=(108, 50, 96), near=(72, 34, 74),
        darkness=0.25, ambient=(255, 200, 190), weather="wind", deco="ruins", clouds=True, sun=(255, 220, 140),
        grade=(40, 10, 0), fog=None,
    ),
    "frost": dict(
        sky=[(10, 16, 44), (24, 44, 92), (52, 86, 140)],
        top=(236, 246, 255), top_hi=(255, 255, 255), top_dark=(170, 196, 230),
        dirt=(84, 108, 160), dirt_dark=(56, 72, 118), dirt_hi=(116, 146, 196), speck=(70, 92, 140),
        stone=(108, 128, 170), stone_dark=(70, 84, 126), stone_hi=(160, 186, 220),
        far=(40, 64, 110), mid=(32, 50, 92), near=(24, 38, 72),
        darkness=0.55, ambient=(120, 140, 200), weather="snow", deco="icicles", clouds=False, sun=None,
        grade=(0, 10, 30), fog=None, aurora=True,
    ),
    "volcano": dict(
        sky=[(20, 6, 10), (70, 16, 18), (140, 40, 22)],
        top=(84, 70, 70), top_hi=(140, 110, 100), top_dark=(50, 40, 44),
        dirt=(58, 44, 48), dirt_dark=(34, 26, 30), dirt_hi=(86, 66, 66), speck=(110, 40, 30),
        stone=(70, 56, 60), stone_dark=(40, 30, 34), stone_hi=(104, 84, 86),
        far=(90, 26, 24), mid=(60, 18, 20), near=(36, 12, 16),
        darkness=0.62, ambient=(150, 80, 70), weather="embers", deco="ash", clouds=False, sun=None,
        grade=(40, 0, 0), fog=None,
    ),
    "legacy": dict(
        sky=[(80, 140, 200), (120, 170, 220), (160, 200, 230)],
        top=(88, 190, 50), top_hi=(150, 230, 90), top_dark=(50, 130, 30),
        dirt=(200, 150, 80), dirt_dark=(160, 110, 50), dirt_hi=(230, 190, 120), speck=(176, 126, 64),
        stone=(170, 90, 60), stone_dark=(120, 60, 40), stone_hi=(210, 130, 90),
        far=(140, 176, 214), mid=(92, 150, 128), near=(56, 118, 90),
        darkness=0, weather=None, deco="flowers", clouds=True, sun=None, grade=None, fog=None,
        legacy_bg=True,
    ),
}


def get(name):
    return THEMES.get(name, THEMES["meadow"])
