"""Smoke tests for template loading, extraction and rendering. Run: python -m unittest discover -s tests"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import rewind


class RewindTests(unittest.TestCase):
    def test_template_loading(self):
        for name in ("odyssey", "minimal", "aurora", "forest"):
            colors, labels, background = rewind.load_template(name)
            self.assertIn("accent", colors)
            self.assertIn("bg", colors)

    def test_render_five_pngs_without_donation(self):
        example = json.loads(Path("examples/odyssey-2026.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            rewind.render(example, tmp, "Not Odyssey", "aurora", "none", None)
            self.assertEqual(len(list(Path(tmp).glob("slide-*.png"))), 5)
            for png in Path(tmp).glob("slide-*.png"):
                self.assertGreater(png.stat().st_size, 1000)

    def test_single_page_infographic(self):
        example = json.loads(Path("examples/odyssey-2026.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            img = rewind.render_infographic(example, tmp, "Odyssey", "odyssey", "donation", None)
            self.assertTrue(img.exists())
            from PIL import Image
            with Image.open(img) as im:
                self.assertEqual(im.size, (1080, 1350))

    def test_read_only_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "test-backup.db"
            db = sqlite3.connect(backup)
            db.executescript("""
                CREATE TABLE metadata_item_views (
                    viewed_at INTEGER, account_id INTEGER, metadata_type INTEGER,
                    guid TEXT, grandparent_title TEXT, title TEXT);
                CREATE TABLE statistics_media (
                    at INTEGER, timespan INTEGER, duration INTEGER);
                CREATE TABLE statistics_bandwidth (
                    at INTEGER, timespan INTEGER, bytes INTEGER);
                CREATE TABLE metadata_items (
                    metadata_type INTEGER, deleted_at INTEGER, added_at INTEGER);
                INSERT INTO metadata_item_views VALUES
                    (1780000000, 12, 1, 'movie-1', NULL, 'Test Movie');
                INSERT INTO statistics_media VALUES (1780000000, 1, 3600);
                INSERT INTO statistics_bandwidth VALUES (1780000000, 1, 1099511627776);
                INSERT INTO metadata_items VALUES (1, NULL, 1780000000);
            """)
            db.commit()
            db.close()
            data = rewind.extract(backup, 2026)
            self.assertEqual(data["plays"], 1)
            self.assertEqual(data["viewers"], 1)
            self.assertEqual(data["hours"], 1)
            self.assertEqual(data["tib"], 1)
            self.assertEqual(data["library"]["1"], 1)


if __name__ == "__main__":
    unittest.main()
