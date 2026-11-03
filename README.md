# Rewind Studio

A small, privacy-first **Plex statistics → Instagram slide generator**. The server can have **any name**; Odyssey is just the included example. This MVP focuses on extracting aggregate statistics and generating the **same five recap slide categories**: title, by the numbers, most played, library, and thank-you/optional donation.

## Setup

Requires Python 3.10+ and Pillow.

```bash
git clone https://github.com/antonflor/rewind-studio.git
cd rewind-studio
python -m pip install -r requirements.txt
```

## Preview using the included example

```bash
python rewind.py render --data examples/odyssey-2026.json --name Odyssey --theme odyssey --cta donation --out output
```

This produces **five 1080 × 1350 PNGs** in `output/`. They are generated programmatically in a restrained dashboard style rather than reusing AI images. The graphics will not yet look identical to the previously generated artwork.

## Generate slides from your own Plex backup

```bash
python rewind.py extract --db "/path/to/com.plexapp.plugins.library.db-2026-11-03" --year 2026 --out stats.json
python rewind.py render --data stats.json --name "My Plex Server" --theme odyssey --cta none --out output
```

Your name may contain spaces. Other examples: `--name "The Vault"`, `--name "Movie Night"`, or `--name "Home Theater"`. No “Odyssey” branding is hardcoded into the renderer.

Themes currently supported: `odyssey` and `minimal`.

Closing slide modes:
- `--cta none` (default): general year-end thank you, no donation request
- `--cta thanks`: thank-you message
- `--cta donation`: generic donation request with PayPal, Zelle, or DM wording
- `--cta-text "Your custom message"`: override the message

## Data and privacy

Only use a **complete standalone scheduled Plex DB backup**. Do not use the live database when Plex is writing to it. The importer opens it read-only and exports **aggregates**, not per-account identities or playback history.

- Playback events may include partial watches.
- Streaming hours are calculated from monthly `statistics_media` duration values interpreted as seconds.
- Bandwidth is calculated from monthly `statistics_bandwidth` bytes.
- Monthly `timespan=1` is selected deliberately to avoid double counting different aggregation levels.
- Library inventory is the snapshot inventory; additions are surviving records with `added_at` in the requested year.
- The stored snapshot may not cover the full year. The graphic explicitly says “so far.”
- Disk size is not in the database. Add `"library_size_label": "~10 TiB"` in `stats.json` if you want to display storage.

## MVP boundaries

This revision exports **PNG slides only**, not an animated MP4. Motion rendering, custom poster image slots, additional themes, and a UI are future features. The first priority is a reliable data export and a reproducible slide generator.

Not affiliated with Plex.
