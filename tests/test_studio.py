"""Tests for the studio engine. Model and style checks always run; rendering runs when Playwright
and a Chromium build are available (set REWIND_CHROMIUM to use an installed Chrome)."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from studio import engine, model

EXAMPLE = json.loads(Path("examples/odyssey-2026.json").read_text())


def lookup(obj, path):
    for key in path.split("."):
        obj = obj.get(key) if isinstance(obj, dict) else None
    return obj


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.vm = model.build(EXAMPLE, "Odyssey", "donation")

    def test_period_and_derived_figures(self):
        self.assertEqual(self.vm["period"]["days"], 307)
        self.assertEqual(self.vm["period"]["pct"], "84.1%")
        self.assertEqual(self.vm["derived"]["plays_per_day"], "20")
        self.assertEqual(self.vm["derived"]["hours_per_day"], "16")
        self.assertEqual(self.vm["derived"]["hours_per_viewer"], "166")
        self.assertEqual(self.vm["derived"]["gib_per_day"], "37")

    def test_rankings_and_shares(self):
        self.assertEqual(self.vm["top_shows"][2]["title"], "Bluey")  # "(2018)" stripped
        self.assertEqual(self.vm["top_shows"][0]["pct"], "100.0%")
        self.assertEqual(self.vm["top3"], {"total_fmt": "1,621", "share": "26", "label": "The top three shows"})
        self.assertEqual([a["pct"] for a in self.vm["added"]], ["10%", "20%", "11%"])
        self.assertEqual(self.vm["added_seasons"], "82")
        self.assertEqual(self.vm["busiest"]["name"], "May")
        self.assertEqual(self.vm["busiest"]["share"], "14")

    def test_missing_optional_data_is_left_out(self):
        sparse = {k: v for k, v in EXAMPLE.items() if k not in ("busiest_month", "added", "library_size_label")}
        vm = model.build(sparse, "Any Server", "none")
        self.assertIsNone(vm["busiest"])
        self.assertEqual(vm["added"], [])
        self.assertEqual(vm["cta"]["methods"], [])

    def test_any_server_name(self):
        self.assertEqual(model.build(EXAMPLE, "The Vault")["labels"]["info_title"], "The Vault's year on Plex")
        self.assertEqual(model.build(EXAMPLE, "Jones")["labels"]["info_title"], "Jones' year on Plex")
        long_name = model.build(EXAMPLE, "Movie Night at the Garcia House", "donation")
        self.assertNotIn("Garcia", long_name["cta"]["short"])  # one-line footer stays short
        self.assertEqual(long_name["cta"]["methods"], ["PayPal", "Zelle", "DM"])
        custom = model.build(EXAMPLE, "The Vault", "donation", labels={"cta_methods": "Ko-fi / Venmo"})
        self.assertEqual(custom["cta"]["methods"], ["Ko-fi", "Venmo"])

    def test_top_label_matches_how_many_shows(self):
        two = dict(EXAMPLE, top_shows=EXAMPLE["top_shows"][:2])
        self.assertEqual(model.build(two, "X")["top3"]["label"], "The top two shows")
        self.assertEqual(self.vm["top3"]["label"], "The top three shows")

    def test_every_binding_in_the_markup_resolves(self):
        html = re.sub(r"<!--.*?-->", "", (engine.ROOT / "base.html").read_text(), flags=re.S)
        paths = set(re.findall(r'data-(?:k|count|each)="([^"]+)"', html))
        paths |= {p.split(":")[1] for css in re.findall(r'data-css="([^"]+)"', html) for p in css.split(";")}
        missing = [p for p in paths if not p.startswith("it") and lookup(self.vm, p.strip()) is None]
        self.assertEqual(missing, [])


class StyleTests(unittest.TestCase):
    def test_styles_are_complete(self):
        styles = engine.list_styles()
        self.assertGreaterEqual(len(styles), 7)
        for style in styles:
            css = (engine.STYLES / style["id"] / "style.css").read_text()
            self.assertIn(f".style-{style['id']}", css)
            self.assertEqual(set(style["palette"]), set(engine.PALETTE_KEYS), style["id"])
            for scope in ("s-cover", "s-numbers", "s-watched", "s-library", "s-info"):
                self.assertIn(scope, css, f"{style['id']} does not lay out .{scope}")

    def test_unknown_style_is_a_clear_error(self):
        with self.assertRaises(SystemExit):
            engine.load_style("does-not-exist")


def chromium_available():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            engine._browser(pw).close()
        return True
    except BaseException:
        return False


@unittest.skipUnless(chromium_available(), "Playwright/Chromium not installed")
class RenderTests(unittest.TestCase):
    def test_long_server_name_fits(self):
        """Shrink-to-fit keeps any server name inside its box in every style."""
        vm = model.build(EXAMPLE, "Movie Night at the Garcia House", "donation")
        for style in engine.list_styles():
            with self.subTest(style=style["id"]), tempfile.TemporaryDirectory() as tmp:
                session = engine.Session(vm, engine.load_style(style["id"]), style["palette"], tmp)
                try:
                    for sid in engine.SLIDES + ["infographic"]:
                        session.show(sid)
                        clipped = session.page.evaluate("""(id) => [...document.querySelectorAll(
                            `.slide[data-slide="${id}"] .slate-name, .slide[data-slide="${id}"] .slate-name b,
                             .slide[data-slide="${id}"] .title, .slide[data-slide="${id}"] .i-thanks`)]
                            .filter((e) => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow === 'hidden')
                            .map((e) => e.className || e.tagName)""", sid)
                        self.assertEqual(clipped, [], sid)
                finally:
                    session.close()

    def test_each_style_renders_slides_and_infographic(self):
        from PIL import Image
        for style in engine.list_styles():
            with self.subTest(style=style["id"]), tempfile.TemporaryDirectory() as tmp:
                paths = engine.render(EXAMPLE, tmp, "Test Server", style["id"], ["slides", "infographic"], "donation")
                self.assertEqual(len(paths), 6)
                for p in paths:
                    with Image.open(p) as im:
                        self.assertEqual(im.size, (1080, 1350))
                        self.assertGreater(len(im.getcolors(1 << 20) or []), 50)  # not a blank frame


if __name__ == "__main__":
    unittest.main()
