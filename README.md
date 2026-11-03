# Rewind Studio

Generate an Instagram-ready annual recap from a **Plex SQLite database backup**. This is a small, local-first MVP focused on collecting statistics and rendering the five Odyssey-style slides—not a web editor or a theme marketplace.

## Quick start

Requires Python 3.10+ and Pillow. FFmpeg is optional for MP4 output.

```bash
python -m pip install -r requirements.txt
python rewind.py extract --db "/path/to/com.plexapp.plugins.library.db-2026-11-03" --year 2026 --out stats.json
python rewind.py render --data stats.json --out output --name Odyssey --theme odyssey --cta donation
```

Outputs five 1080×1350 PNG slides in `output/`. If FFmpeg is installed, add `--video` to create an animated, silent 1080×1920 MP4 from the images. Music can be added in Instagram or another editor.

### Customization

```bash
python rewind.py render --data stats.json --out output --name "My Plex Server" --theme minimal --cta none
```

Available `--cta`: `none` (default), `thanks`, `donation`. Donation wording is generic: PayPal / Zelle / DM; edit it with `--cta-text`. No personal payment identifier is required.

### Data accuracy and privacy

- Work **only from Plex's scheduled database backups** or consistent SQLite snapshots. Never copy a live `.db` without its WAL transaction state or interfere with Plex.
- The extraction exports **aggregated statistics only**, never account names, account IDs, playback history rows, or private URLs.
- A playback event is **not** necessarily a completed watch.
- Playback totals use `metadata_item_views`; streaming durations and traffic use a *single* monthly aggregation level (`timespan=1`) to prevent double counting.
- `duration` is interpreted as seconds, based on Plex's aggregation behavior. Inspect your Plex version's data if results seem implausible.
- `du` disk usage is not in the database. Set `library_size_label` manually in the JSON if desired.
- Statistics describe only what was retained in the chosen backup and only through its snapshot date. Use “so far” unless the year has ended.
- Plex metadata type 10 is tracks and type 12 represents other music-related metadata; the tool does not use type 12 to count tracks.

### Planned next improvements

- Better scene-by-scene animation instead of still-slide transitions
- Poster/thumbnail upload and per-slide backgrounds
- More themes and a visual customization interface
- Jellyfin and Tautulli adapters

Contributions welcome. No Plex affiliation.
