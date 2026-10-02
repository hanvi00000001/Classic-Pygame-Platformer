"""Build the browser version with pygbag (WebAssembly).

    python tools/build_web.py          # -> build/web/  (index.html + wayfarer.apk)

Only the files the game needs are staged, so screenshots and the legacy code
don't end up in the download.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "build", "wayfarer")


CSS = """
    <style>
        /* WAYFARER: scale the 480x270 framebuffer up with crisp pixels */
        html, body { background: #08060f !important; margin: 0; overflow: hidden; }
        canvas.emscripten#canvas {
            image-rendering: pixelated;
            width: min(100vw, calc(100vh * 16 / 9)) !important;
            height: min(100vh, calc(100vw * 9 / 16)) !important;
            margin: auto !important;
        }
    </style>
</head>"""


def _pixel_perfect(index):
    with open(index, encoding="utf-8") as f:
        html = f.read()
    if "WAYFARER: scale" not in html:
        html = html.replace("</head>", CSS, 1)
    with open(index, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    shutil.copy(os.path.join(ROOT, "main.py"), STAGE)
    shutil.copytree(os.path.join(ROOT, "game"), os.path.join(STAGE, "game"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(ROOT, "levels"), os.path.join(STAGE, "levels"),
                    ignore=shutil.ignore_patterns("custom_*"))
    bg = os.path.join("legacy_2022", "img", "background")
    shutil.copytree(os.path.join(ROOT, bg), os.path.join(STAGE, bg))
    cmd = [sys.executable, "-m", "pygbag", "--build", "--title", "Wayfarer", "--ume_block", os.environ.get("UME", "1"), STAGE]
    print(" ".join(cmd))
    subprocess.check_call(cmd)
    out = os.path.join(STAGE, "build", "web")
    _pixel_perfect(os.path.join(out, "index.html"))
    dest = os.path.join(ROOT, "build", "web")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(out, dest)
    print("web build ready:", dest)


if __name__ == "__main__":
    main()
