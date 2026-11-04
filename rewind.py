#!/usr/bin/env python3
"""Rewind Studio: a Plex year in review for any server.

  extract   read aggregate stats from a standalone Plex database backup into stats.json
  render    turn stats.json into five slides, a single-page infographic and/or an animated MP4,
            in one of the designed styles under studio/styles/ (rendered locally in headless Chromium)
  styles    list the styles
  templates list color/label templates under templates/
"""
import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
TEMPLATE_COLORS = ("bg", "panel", "accent", "secondary", "fg")
FORMATS = {"slides": ["slides"], "infographic": ["infographic"], "both": ["slides", "infographic"],
           "video": ["video"], "all": ["slides", "infographic", "video"]}


def query(db, sql, params=()):
    return db.execute(sql, params).fetchall()


def extract(path, year):
    p = Path(path).resolve()
    if not p.is_file():
        raise SystemExit("Database backup not found")
    # immutable=1 is for a fully checkpointed, standalone backup; never use with the live Plex DB.
    db = sqlite3.connect("file:" + str(p) + "?mode=ro&immutable=1", uri=True)
    a = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    b = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())

    def scalar(sql, params=(a, b)):
        return query(db, sql, params)[0][0] or 0

    base = "FROM metadata_item_views WHERE viewed_at>=? AND viewed_at<?"
    data = {
        "year": year,
        "plays": scalar("SELECT COUNT(*) " + base),
        "viewers": scalar("SELECT COUNT(DISTINCT account_id) " + base),
        "unique_movies": scalar("SELECT COUNT(DISTINCT CASE WHEN metadata_type=1 THEN guid END) " + base),
        "unique_shows": scalar("SELECT COUNT(DISTINCT CASE WHEN metadata_type=4 THEN grandparent_title END) " + base),
        "hours": round(scalar("SELECT SUM(duration)/3600.0 FROM statistics_media WHERE timespan=1 AND at>=? AND at<?"), 1),
        "tib": round(scalar("SELECT SUM(bytes)/1099511627776.0 FROM statistics_bandwidth WHERE timespan=1 AND at>=? AND at<?"), 2),
        "library": {str(t): n for t, n in query(db, "SELECT metadata_type,COUNT(*) FROM metadata_items WHERE deleted_at IS NULL GROUP BY metadata_type")},
        "added": {str(t): n for t, n in query(db, "SELECT metadata_type,COUNT(*) FROM metadata_items WHERE deleted_at IS NULL AND added_at>=? AND added_at<? GROUP BY metadata_type", (a, b))},
        "through": datetime.fromtimestamp(scalar("SELECT MAX(viewed_at) " + base) or b - 1, timezone.utc).strftime("%b %d, %Y"),
        "library_size_label": None,
    }
    for key, kind, field in [("top_movies", 1, "title"), ("top_shows", 4, "grandparent_title")]:
        data[key] = [{"title": title or "Unknown", "plays": n} for title, n in query(
            db, f"SELECT {field},COUNT(*) FROM metadata_item_views WHERE metadata_type=? AND viewed_at>=? AND viewed_at<? "
                f"GROUP BY {field} ORDER BY COUNT(*) DESC,{field} LIMIT 3", (kind, a, b))]
    plays_by_month = dict(query(db, "SELECT CAST(strftime('%m',viewed_at,'unixepoch') AS INTEGER),COUNT(*) " + base + " GROUP BY 1", (a, b)))
    hours_by_month = dict(query(db, "SELECT CAST(strftime('%m',at,'unixepoch') AS INTEGER),SUM(duration)/3600.0 FROM statistics_media "
                                    "WHERE timespan=1 AND at>=? AND at<? GROUP BY 1", (a, b)))
    data["monthly"] = [{"month": m, "plays": plays_by_month.get(m, 0), "hours": round(hours_by_month.get(m) or 0, 1)}
                       for m in range(1, 13) if plays_by_month.get(m) or hours_by_month.get(m)]
    if data["monthly"]:
        top = max(data["monthly"], key=lambda r: r["plays"])
        if top["plays"]:
            data["busiest_month"] = dict(top)
    db.close()
    return data


def load_template(spec):
    """A template is trusted local JSON (colors and labels), never code. Returns (colors, labels)."""
    path = Path(spec).expanduser()
    if not path.is_file():
        path = Path("templates") / (spec if spec.endswith(".json") else spec + ".json")
    if not path.is_file():
        raise SystemExit(f"Template not found: {spec}. Run 'python rewind.py templates' to list choices.")
    obj = json.loads(path.read_text(encoding="utf-8"))
    colors = {}
    for k, v in obj.get("colors", {}).items():
        if k not in TEMPLATE_COLORS:
            raise SystemExit(f"Unknown template color: {k} (use {', '.join(TEMPLATE_COLORS)})")
        if not HEX.match(str(v)):
            raise SystemExit(f"Invalid color: {v} (use a hex value like #1c2640)")
        colors[k] = v
    return colors, obj.get("labels", {})


def main():
    ap = argparse.ArgumentParser(description="Plex year in review: slides, infographic and video for any server")
    sub = ap.add_subparsers(dest="command", required=True)
    x = sub.add_parser("extract", help="Read aggregate stats from a standalone Plex database backup")
    x.add_argument("--db", required=True)
    x.add_argument("--year", type=int, required=True)
    x.add_argument("--out", default="stats.json")
    r = sub.add_parser("render", help="Render slides, an infographic and/or a video from stats.json")
    r.add_argument("--data", required=True)
    r.add_argument("--out", default="output")
    r.add_argument("--name", default="My Media Server", help="Your server's name, any length")
    r.add_argument("--style", default="editorial", help="Design (run 'python rewind.py styles'); default: editorial")
    r.add_argument("--format", choices=list(FORMATS), default="slides",
                   help="slides (5 PNGs), infographic (1 PNG), both, video (MP4) or all")
    r.add_argument("--theme", help="Template name or path: recolors the style and can relabel it")
    r.add_argument("--cta", choices=["none", "thanks", "donation"], default="none", help="How the closing slide ends")
    r.add_argument("--cta-text", help="Replace the closing message")
    r.add_argument("--cta-methods", help='Donation options, slash-separated (default: "PayPal / Zelle / DM")')
    r.add_argument("--no-sound", action="store_true", help="Video without the sound bed")
    sub.add_parser("styles", help="List the designed styles")
    sub.add_parser("templates", help="List color/label templates in templates/")
    a = ap.parse_args()

    if a.command == "templates":
        for f in sorted(Path("templates").glob("*.json")):
            print(f)
        return
    if a.command == "styles":
        from studio import engine
        for s in engine.list_styles():
            print(f'{s["id"]:<12} {s.get("description", "")}')
        return
    if a.command == "extract":
        data = extract(a.db, a.year)
        Path(a.out).write_text(json.dumps(data, indent=2))
        print("Saved", a.out)
        return

    from studio import engine
    data = json.loads(Path(a.data).read_text())
    colors, labels = load_template(a.theme) if a.theme else (None, {})
    if a.cta_methods:
        labels = dict(labels, cta_methods=a.cta_methods)
    for path in engine.render(data, a.out, a.name, a.style, FORMATS[a.format], a.cta, a.cta_text,
                              colors, labels, sound=not a.no_sound):
        print("Saved", path)


if __name__ == "__main__":
    main()
