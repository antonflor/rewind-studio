"""Regenerate every image the README uses, from the example stats, so screenshots never drift from the code.

    python docs/make_images.py

Writes into docs/images/: hero.jpg, styles-overview.jpg, styles/<style>.jpg, infographic.png,
video-preview.gif (needs ffmpeg) and cli.png (a terminal window showing real command output).
Run it from the repository root after changing a style, the markup or the example data.
Besides requirements.txt it needs Pillow (python -m pip install pillow) and ffmpeg.
"""
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio import engine, model  # noqa: E402

OUT = ROOT / "docs" / "images"
DATA = json.loads((ROOT / "examples" / "odyssey-2026.json").read_text())
NAME = "The Vault"  # a neutral example name: the README is for every server
ORDER = ["editorial", "marquee", "ticket", "broadsheet", "terminal", "swiss", "vhs"]
HERO = [("editorial", "cover"), ("broadsheet", "numbers"), ("ticket", "watched"), ("terminal", "infographic"), ("vhs", "closing")]


def cards(style, tmp):
    paths = engine.render(DATA, tmp, NAME, style, ["slides", "infographic"], "donation")
    return dict(zip(engine.SLIDES + ["infographic"], [Image.open(p).convert("RGB") for p in paths]))


def grid(ims, cols, w, h, gap):
    rows = -(-len(ims) // cols)
    out = Image.new("RGB", (cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap), "#ffffff")
    for i, im in enumerate(ims):
        out.paste(im.resize((w, h), Image.LANCZOS), ((i % cols) * (w + gap), (i // cols) * (h + gap)))
    return out


def save_jpg(im, path):
    im.save(path, quality=85, optimize=True, progressive=True)
    print("wrote", path.relative_to(ROOT))


def stills():
    (OUT / "styles").mkdir(parents=True, exist_ok=True)
    every = {}
    with tempfile.TemporaryDirectory() as tmp:
        for style in ORDER:
            every[style] = cards(style, Path(tmp) / style)
    for style in ORDER:
        save_jpg(grid(list(every[style].values()), 3, 400, 500, 16), OUT / "styles" / f"{style}.jpg")
    save_jpg(grid([every[s]["cover"] for s in ORDER], 7, 300, 375, 14), OUT / "styles-overview.jpg")
    save_jpg(grid([every[s][c] for s, c in HERO], 5, 360, 450, 18), OUT / "hero.jpg")
    every["editorial"]["infographic"].save(OUT / "infographic.png", optimize=True)
    print("wrote", (OUT / "infographic.png").relative_to(ROOT))


def video_preview():
    with tempfile.TemporaryDirectory() as tmp:
        mp4 = engine.render(DATA, tmp, NAME, "editorial", ["video"], "donation")[0]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-t", "10.5", "-i", str(mp4), "-vf",
                        "fps=12,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];"
                        "[b][p]paletteuse=dither=bayer:bayer_scale=4", str(OUT / "video-preview.gif")], check=True)
    print("wrote", (OUT / "video-preview.gif").relative_to(ROOT))


def cli_screenshot():
    """Run the real commands and draw their output in a terminal window."""
    py = [sys.executable, str(ROOT / "rewind.py")]
    styles = subprocess.run(py + ["styles"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "examples").mkdir()
        (Path(tmp) / "examples" / "odyssey-2026.json").write_text(json.dumps(DATA))
        args = ["render", "--data", "examples/odyssey-2026.json", "--name", NAME, "--style", "ticket",
                "--cta", "donation", "--format", "all", "--out", "output"]
        saved = subprocess.run(py + args, cwd=tmp, capture_output=True, text=True, check=True).stdout.splitlines()
    esc = html.escape
    lines = ['<b class="p">$</b> python rewind.py styles']
    lines += [f'<b class="k">{esc(s[:12])}</b> <span class="d">{esc(s[13:])}</span>' for s in styles]
    lines += ["", '<b class="p">$</b> python rewind.py render --data examples/odyssey-2026.json \\',
              f'    --name "{esc(NAME)}" --style ticket --cta donation --format all --out output']
    lines += [f'<span class="ok">Saved</span> {esc(s.split(" ", 1)[1])}' for s in saved]
    fonts = (ROOT / "studio" / "fonts" / "fonts.css").as_uri()
    page = f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{fonts}"><style>
body{{margin:0;background:transparent}}
.win{{width:880px;margin:24px;border-radius:12px;overflow:hidden;background:#15140f;box-shadow:0 0 0 1px #2c2a24}}
.bar{{height:38px;display:flex;align-items:center;gap:8px;padding:0 16px;background:#211f1a}}
.bar i{{width:12px;height:12px;border-radius:50%;background:#4a463d;display:block}}
.bar span{{flex:1;text-align:center;margin-right:52px;font:500 13px "JetBrains Mono",monospace;color:#8e877a}}
pre{{margin:0;padding:22px 26px 26px;font:400 14.5px/1.6 "JetBrains Mono",monospace;color:#e9e3d8;white-space:pre-wrap}}
.p{{color:#e5a00d}} .k{{color:#f2ede4}} .d{{color:#a39b8f}} .ok{{color:#9fcf7a}}
</style></head><body><div class="win"><div class="bar"><i></i><i></i><i></i><span>rewind-studio</span></div>
<pre>{chr(10).join(lines)}</pre></div></body></html>"""
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        page_path = Path(tmp) / "cli.html"
        page_path.write_text(page)
        browser = engine._browser(pw)
        pg = browser.new_page(viewport={"width": 928, "height": 600}, device_scale_factor=2)
        pg.goto(page_path.as_uri())
        pg.evaluate("document.fonts.ready.then(() => true)")
        pg.locator(".win").screenshot(path=str(OUT / "cli.png"), omit_background=True)
        browser.close()
    print("wrote", (OUT / "cli.png").relative_to(ROOT))


if __name__ == "__main__":
    stills()
    video_preview()
    cli_screenshot()
