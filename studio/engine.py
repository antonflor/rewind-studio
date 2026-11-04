"""Render the shared markup with a style sheet in headless Chromium.

Needs playwright (+ a Chromium build, or REWIND_CHROMIUM) for every export, numpy for video sound
and ffmpeg on PATH for video.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import model

ROOT = Path(__file__).resolve().parent
STYLES = ROOT / "styles"
SLIDES = ["cover", "numbers", "watched", "library", "closing"]
SCENE_SECONDS = {"cover": 4.5, "numbers": 6.0, "watched": 6.5, "library": 6.0, "closing": 6.5}
FPS = 30
PALETTE_KEYS = ("bg", "panel", "accent", "secondary", "fg")


class StudioError(SystemExit):
    pass


def list_styles():
    out = []
    for meta in sorted(STYLES.glob("*/style.json")):
        info = json.loads(meta.read_text(encoding="utf-8"))
        info["id"] = meta.parent.name
        out.append(info)
    return out


def load_style(name):
    folder = STYLES / name
    if not (folder / "style.json").is_file() or not (folder / "style.css").is_file():
        names = ", ".join(s["id"] for s in list_styles())
        raise StudioError(f"Unknown style: {name}. Available styles: {names}")
    info = json.loads((folder / "style.json").read_text(encoding="utf-8"))
    info["id"] = name
    info["css"] = folder / "style.css"
    return info


def page_html(vm, style, palette):
    base = (ROOT / "base.html").read_text(encoding="utf-8")
    css_vars = ";".join(f"--{'muted' if k == 'secondary' else k}:{v}" for k, v in palette.items())
    data = json.dumps(vm, ensure_ascii=False).replace("</", "<\\/")
    uri = lambda p: Path(p).resolve().as_uri()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{style['id']}</title>
<link rel="stylesheet" href="{uri(ROOT / 'fonts' / 'fonts.css')}">
<link rel="stylesheet" href="{uri(ROOT / 'runtime' / 'base.css')}">
<link rel="stylesheet" href="{uri(style['css'])}">
<style>:root{{{css_vars}}}</style>
</head><body class="style-{style['id']}">
{base}
<script>window.REWIND = {data};</script>
<script src="{uri(ROOT / 'runtime' / 'bind.js')}"></script>
<script src="{uri(ROOT / 'runtime' / 'motion.js')}"></script>
<script>window.__bind();</script>
</body></html>"""


def _browser(pw):
    exe = os.environ.get("REWIND_CHROMIUM")
    args = ["--allow-file-access-from-files", "--font-render-hinting=none"]
    attempts = [dict(executable_path=exe)] if exe else [{}, dict(channel="chrome")]
    last = None
    for kw in attempts:
        try:
            return pw.chromium.launch(args=args, **kw)
        except Exception as err:  # pragma: no cover - depends on the machine
            last = err
    raise StudioError("Could not start Chromium. Run 'python -m playwright install chromium' "
                      f"or set REWIND_CHROMIUM to a Chrome/Chromium binary. ({last})")


class Session:
    """One headless page with the deck loaded; reused for every export."""

    def __init__(self, vm, style, palette, workdir):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise StudioError("Rewind Studio needs Playwright: python -m pip install -r requirements.txt "
                              "&& python -m playwright install chromium")
        self.path = (Path(workdir) / ".rewind-page.html").resolve()
        self.path.write_text(page_html(vm, style, palette), encoding="utf-8")
        self._pw = sync_playwright().start()
        self.browser = _browser(self._pw)
        self.page = self.browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        errors = []
        self.page.on("pageerror", lambda e: errors.append(str(e)))
        self.page.goto(self.path.as_uri())
        self.page.wait_for_function("document.body.dataset.ready === '1'")
        # Lay out every slide once so each face the style uses is requested, then wait for all of them:
        # shrink-to-fit must measure with the real fonts, not the fallbacks.
        self.page.evaluate("""async () => {
            document.body.classList.add('preview');
            document.body.offsetHeight;
            await document.fonts.ready;
            await Promise.all([...document.fonts].map((f) => f.status === 'loaded' ? f : f.load().catch(() => null)));
            document.body.classList.remove('preview');
        }""")
        if errors:
            raise StudioError("Style failed to load: " + "; ".join(errors))

    def show(self, slide_id):
        self.page.evaluate(f"window.__show({json.dumps(slide_id)})")

    def png(self, slide_id, dest):
        self.show(slide_id)
        self.page.screenshot(path=str(dest), clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        return dest

    def close(self):
        self.browser.close()
        self._pw.stop()
        self.path.unlink(missing_ok=True)


def resolve_palette(style, theme_colors):
    palette = dict(style.get("palette", {}))
    if theme_colors:
        palette.update({k: v for k, v in theme_colors.items() if k in PALETTE_KEYS})
    return palette


def render(data, out, name, style_name, formats, cta="none", cta_text=None, theme_colors=None,
           labels=None, sound=True):
    """Export the requested formats ('slides', 'infographic', 'video') and return the written paths."""
    style = load_style(style_name)
    vm = model.build(data, name, cta, cta_text, labels)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    if "video" in formats:
        _check_ffmpeg()
    session = Session(vm, style, resolve_palette(style, theme_colors), out)
    try:
        if "slides" in formats:
            for i, sid in enumerate(SLIDES, 1):
                written.append(session.png(sid, out / f"slide-{i}.png"))
        if "infographic" in formats:
            written.append(session.png("infographic", out / "infographic.png"))
        if "video" in formats:
            written.append(_video(session, out, sound))
    finally:
        session.close()
    return written


def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise StudioError("Video export needs ffmpeg on your PATH (https://ffmpeg.org/download.html).")


def _video(session, out, sound):
    page = session.page
    timeline, scenes = [], []
    offset = 0.0
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        tmp = Path(tmp)
        for i, sid in enumerate(SLIDES, 1):
            dur = SCENE_SECONDS[sid]
            info = page.evaluate(f"window.__motion.setup({json.dumps(sid)}, {dur})")
            timeline.append({"scene": sid, "offset": offset, "dur": dur, "events": info["events"]})
            part, final = tmp / f"scene-{i}.part.mp4", tmp / f"scene-{i}.mp4"
            enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                    "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                                    "-pix_fmt", "yuv420p", "-r", str(FPS), str(part)], stdin=subprocess.PIPE)
            held = None
            for f in range(round(dur * FPS)):
                t = f / FPS
                if held is not None and info["animEnd"] + 0.05 < t < info["outroStart"]:
                    frame = held  # nothing moves between the end of the intro and the outro
                else:
                    page.evaluate(f"window.__motion.seek({t})")
                    frame = page.screenshot(type="jpeg", quality=95, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
                    if t > info["animEnd"] + 0.05:
                        held = frame
                enc.stdin.write(frame)
            enc.stdin.close()
            if enc.wait() != 0:
                raise StudioError(f"ffmpeg failed while encoding the {sid} scene")
            part.rename(final)
            scenes.append(final)
            offset += dur
        listing = tmp / "scenes.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in scenes))
        silent = tmp / "silent.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-c", "copy", str(silent)], check=True)
        dest = out / "rewind.mp4"
        part = out / "rewind.part.mp4"
        wav = _sound(timeline, offset, tmp) if sound else None
        if wav:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-map", "0:v",
                            "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-18:TP=-1.5:LRA=11", "-c:a", "aac",
                            "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(part)], check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-c", "copy",
                            "-movflags", "+faststart", str(part)], check=True)
        part.replace(dest)
    return dest


def _sound(timeline, total, tmp):
    try:
        from . import sound
    except ImportError:
        print("numpy is not installed: exporting the video without sound.")
        return None
    wav = tmp / "sound.wav"
    sound.write(timeline, total, wav)
    return wav
