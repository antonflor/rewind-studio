"""Smoke tests for templates, the CLI and the read-only extractor. Run: python -m unittest discover -s tests"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import rewind


class RewindTests(unittest.TestCase):
    def test_template_loading(self):
        for name in ("aurora", "forest"):
            colors, labels = rewind.load_template(name)
            self.assertIn("accent", colors)
            self.assertIn("cover_title", labels)

    def test_template_rejects_bad_colors(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"colors": {"bg": "url(x)"}}))
            with self.assertRaises(SystemExit):
                rewind.load_template(str(bad))
            bad.write_text(json.dumps({"colors": {"glow": "#ffffff"}}))
            with self.assertRaises(SystemExit):
                rewind.load_template(str(bad))

    def test_styles_command_lists_every_style(self):
        out = subprocess.run([sys.executable, "rewind.py", "styles"], capture_output=True, text=True, check=True).stdout
        for style in ("editorial", "marquee", "ticket", "broadsheet", "terminal", "swiss", "vhs"):
            self.assertIn(style, out)

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
            self.assertEqual(data["monthly"], [{"month": 5, "plays": 1, "hours": 1.0}])
            self.assertEqual(data["busiest_month"]["month"], 5)


if __name__ == "__main__":
    unittest.main()
