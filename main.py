"""WAYFARER - a classic pygame platformer, 2026 remaster of a 2022 school project.

    python main.py            play
    python main.py --editor   jump straight into the level editor
    python main.py <file.txt> play a single level file
"""
import asyncio
import sys

import pygame as pg

from game.app import App


async def main():
    app = App()
    args = [a for a in sys.argv[1:]]
    if "--editor" in args:
        from game.editor import EditorScene
        app.push(EditorScene(app))
    elif args and args[0].endswith(".txt"):
        from game.play import PlayScene
        from game.world import Level
        app.push(PlayScene(app, Level.load(args[0])))
    while app.running:
        app.frame()
        await asyncio.sleep(0)
    pg.quit()


if __name__ == "__main__":
    asyncio.run(main())
