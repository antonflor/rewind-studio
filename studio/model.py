"""Turn the aggregate stats JSON into the display model the studio styles bind to.

Everything shown on a card comes from the stats file or from plain arithmetic on it
(plays per day, share of the year's plays, and so on). Nothing is estimated or invented:
when a field is missing, the parts of a design that need it are left out.
"""
import re
from datetime import date, datetime

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
PLAY_NOTE = "A play is a playback event, not always a finished watch."
# Plex metadata_type ids used by the extractor
LIBRARY_ITEMS = [("1", "movies", "Movies"), ("2", "series", "TV series"),
                 ("4", "episodes", "Episodes"), ("10", "tracks", "Music tracks")]
ADDED_ITEMS = [("1", "movies"), ("2", "series"), ("4", "episodes")]


def fmt(n, decimals=0):
    return f"{n:,.{decimals}f}"


def clean_title(title):
    """'Bluey (2018)' -> 'Bluey'. Plex adds the year to disambiguate; it reads as noise on a card."""
    return re.sub(r"\s*\((19|20)\d{2}\)$", "", str(title or "Unknown")).strip() or "Unknown"


def possessive(name):
    """"The Vault" -> "The Vault's", "Jones" -> "Jones'"."""
    return f"{name}'" if name.endswith(("s", "S")) else f"{name}'s"


def short_date(d):
    return f"{d.strftime('%b')} {d.day}"


def parse_through(data):
    year = int(data["year"])
    raw = data.get("through")
    if raw:
        for pattern in ("%b %d, %Y", "%Y-%m-%d", "%B %d, %Y"):
            try:
                d = datetime.strptime(raw, pattern).date()
                if d.year == year:
                    return d
            except ValueError:
                pass
    return date(year, 12, 31)


def _ranked(items, limit=3):
    items = [i for i in (items or []) if i.get("plays")][:limit]
    if not items:
        return []
    top = max(i["plays"] for i in items)
    return [{"rank": str(n + 1), "title": clean_title(i.get("title")), "plays": i["plays"],
             "fmt": fmt(i["plays"]), "pct": f"{i['plays'] / top * 100:.1f}%",
             "cls": "lead" if n == 0 else ""} for n, i in enumerate(items)]


def _cta(kind, cta_text, server, year, plays_fmt, labels):
    if kind == "donation":
        title = labels.get("closing_title", "Thank you.")
        message = cta_text or f"You kept {server} running in {year}. Every one of those {plays_fmt} plays happened because of you."
        methods = [m.strip() for m in labels.get("cta_methods", "PayPal / Zelle / DM").split("/") if m.strip()]
        methods_label = labels.get("cta_methods_label", f"Keep it going in {year + 1}")
        footer = labels.get("closing_footer", f"Every donation helps keep {server} online.")
    elif kind == "thanks":
        title = labels.get("closing_title", "Thank you.")
        message = cta_text or f"You made {year} on {server} something worth looking back on."
        methods, methods_label = [], ""
        footer = labels.get("closing_footer", "See you next year.")
    else:
        title = labels.get("closing_title", "That's a wrap.")
        message = cta_text or "Another year of movies, shows and music. See you next year."
        methods, methods_label = [], ""
        footer = labels.get("closing_footer", f"{server} · {year}")
    words = title.split()
    return {"kind": kind, "title": title,
            "title_a": " ".join(words[:-1]) if len(words) > 1 else title,
            "title_b": words[-1] if len(words) > 1 else "",
            "message": message, "methods": methods, "methods_label": methods_label, "footer": footer,
            "methods_short": [re.sub(r"^(or\s+)?(just\s+)?", "", m, flags=re.I) for m in methods],
            "short": {"donation": f"Thank you for keeping {server} running." if len(server) <= 18 else "Thank you for keeping it running.",
                      "thanks": f"Thank you for watching on {server}." if len(server) <= 18 else "Thank you for watching.",
                      "none": "See you next year."}.get(kind, "See you next year.")}


def build(data, server, cta="none", cta_text=None, labels=None):
    labels = dict(labels or {})
    year = int(data["year"])
    end = parse_through(data)
    start = date(year, 1, 1)
    year_days = (date(year, 12, 31) - start).days + 1
    days = (end - start).days + 1
    partial = days < year_days

    plays = int(data.get("plays") or 0)
    hours = float(data.get("hours") or 0)
    viewers = int(data.get("viewers") or 0)
    tib = float(data.get("tib") or 0)

    months = []
    for m in range(12):
        first = date(year, m + 1, 1)
        nxt = date(year + (m == 11), (m + 1) % 12 + 1, 1)
        months.append({"letter": MONTHS[m][0], "abbr": MONTHS[m][:3], "name": MONTHS[m],
                       "start_pct": f"{(first - start).days / year_days * 100:.2f}%",
                       "width_pct": f"{(nxt - first).days / year_days * 100:.2f}%", "cls": ""})

    monthly = data.get("monthly") or []
    busiest = data.get("busiest_month")
    if not busiest and monthly:
        busiest = max(monthly, key=lambda r: r.get("plays", 0))
    busiest_vm = None
    if busiest and busiest.get("month") and busiest.get("plays"):
        mi = int(busiest["month"]) - 1
        months[mi]["cls"] = "busy"
        b_plays, b_hours = int(busiest["plays"]), busiest.get("hours")
        busiest_vm = {"name": MONTHS[mi], "abbr": MONTHS[mi][:3],
                      "plays_fmt": fmt(b_plays), "hours_fmt": fmt(b_hours, 1) if b_hours else "",
                      "share": f"{b_plays / plays * 100:.0f}" if plays else "",
                      "start_pct": months[mi]["start_pct"], "width_pct": months[mi]["width_pct"],
                      "detail": f"{fmt(b_plays)} plays" + (f" · {fmt(b_hours, 1)} hours" if b_hours else "")}
    if monthly:
        peak = max((r.get("plays", 0) for r in monthly), default=0) or 1
        for r in monthly:
            mi = int(r["month"]) - 1
            months[mi]["plays_fmt"] = fmt(r.get("plays", 0))
            months[mi]["h_pct"] = f"{r.get('plays', 0) / peak * 100:.1f}%"

    shows, movies = _ranked(data.get("top_shows")), _ranked(data.get("top_movies"))
    top3 = sum(s["plays"] for s in shows)

    lib = data.get("library") or {}
    library_items = [{"key": key, "label": label, "v": int(lib[t]), "fmt": fmt(int(lib[t]))}
                     for t, key, label in LIBRARY_ITEMS if lib.get(t)]
    added_src = data.get("added") or {}
    added = []
    for t, unit in ADDED_ITEMS:
        part, whole = int(added_src.get(t) or 0), int(lib.get(t) or 0)
        if part and whole:
            p = part / whole * 100
            added.append({"unit": unit, "part_fmt": fmt(part), "whole_fmt": fmt(whole),
                          "pct": f"{p:.0f}%", "w": f"{p:.1f}%"})

    cover_title = labels.get("cover_title", "Plex Rewind")
    vm = {
        "server": server, "year": str(year), "next_year": str(year + 1),
        "period": {"start": short_date(start), "end": short_date(end), "days": days, "year_days": year_days,
                   "partial": partial, "pct": f"{days / year_days * 100:.1f}%",
                   "range": f"{short_date(start)} – {short_date(end)}" + ("" if partial else f", {year}"),
                   "range_long": f"{short_date(start)} – {short_date(end)}, {year} · {days} days",
                   "day_label": f"Day {days} of {year_days}" if partial else f"All {year_days} days",
                   "so_far": f"{year} so far" if partial else str(year)},
        "kpi": {"plays": {"v": plays, "fmt": fmt(plays)},
                "hours": {"v": round(hours), "fmt": fmt(hours)},
                "viewers": {"v": viewers, "fmt": fmt(viewers)},
                "data": {"v": tib, "fmt": fmt(tib, 2), "unit": "TiB"}},
        "derived": {
            "plays_per_day": fmt(plays / days) if days else "",
            "hours_per_day": fmt(hours / days) if days else "",
            "hours_per_viewer": fmt(hours / viewers) if viewers else "",
            "gib_per_day": fmt(tib * 1024 / days) if days else "",
        },
        "busiest": busiest_vm, "months": months, "monthly": bool(monthly),
        "top_shows": shows, "top_movies": movies,
        "top3": {"total_fmt": fmt(top3), "share": f"{top3 / plays * 100:.0f}" if plays and top3 else "",
                 "label": {1: "The top show", 2: "The top two shows"}.get(len(shows), "The top three shows")} if shows else None,
        "library": {"size_label": data.get("library_size_label") or "", "items": library_items},
        "added": added,
        "added_seasons": fmt(int(added_src["3"])) if added_src.get("3") else "",
        "cta": _cta(cta, cta_text, server, year, fmt(plays), labels),
        "notes": {"plays": PLAY_NOTE},
        "labels": {
            "series": f"{cover_title} {year}",
            "cover_title": cover_title,
            "cover_subtitle": labels.get("cover_subtitle", f"{possessive(server)} year on Plex, in real numbers."),
            "cover_footer": labels.get("cover_footer", ""),
            "stats_title": labels.get("stats_title", "By the numbers"),
            "titles_title": labels.get("titles_title", "What everyone watched"),
            "titles_range": f"Most-played on Plex, {short_date(start)} – {short_date(end)}",
            "library_title": labels.get("library_title", "The library"),
            "info_title": labels.get("info_title", f"{possessive(server)} year on Plex"),
        },
    }
    d = vm["derived"]
    vm["sentences"] = {
        "plays_per_day": f"About {d['plays_per_day']} a day on Plex, every day of the year{' so far' if partial else ''}." if d["plays_per_day"] else "",
        "library": "of movies, shows and music on Plex.",
    }
    return vm
