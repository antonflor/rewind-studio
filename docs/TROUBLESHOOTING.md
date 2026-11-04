# Troubleshooting

## `python` is not recognized
Use `py` on Windows or `python3` on macOS/Linux. Check `python --version` first.

## `ModuleNotFoundError: playwright` (or `numpy`)
Install dependencies with the same interpreter you run: `python -m pip install -r requirements.txt`.

## "Could not start Chromium"
Run `python -m playwright install chromium` (on a Linux server without a desktop: `python -m playwright install --with-deps chromium`), or set `REWIND_CHROMIUM` to an installed Chrome or Chromium executable.

## "Video export needs ffmpeg on your PATH"
Install ffmpeg (`winget install ffmpeg`, `brew install ffmpeg`, `sudo apt install ffmpeg`) and open a new terminal so the PATH change takes effect.

## The video has no sound
numpy is missing: `python -m pip install -r requirements.txt`.

## Database backup not found
Pass an **absolute path** to a standalone Plex library DB backup. The location differs on Docker, Windows, macOS, NAS, and hosted seedboxes. Paths with spaces must be quoted.

## Can't open database
You may be pointing at the live Plex DB, a partial backup, or an inaccessible path. Use a scheduled backup copied into a writable local directory. Rewind Studio does not need a Plex token or API credentials.

## Database is missing tables
Verify the input is `com.plexapp.plugins.library.db...` and not `com.plexapp.plugins.library.blobs.db...`. Older or different Plex versions can vary.

## Unknown style
Run `python rewind.py styles` for the list. Style names are lowercase: `editorial`, `marquee`, `ticket`, `broadsheet`, `terminal`, `swiss`, `vhs`.

## Template not found
Run `python rewind.py templates` from the repository root. Use a file path to load templates from another directory.

## Part of a slide is missing
That's on purpose: when your stats don't include something (a busiest month, a music library, a library size, three top titles), the cards leave it out instead of guessing. Re-extract with this version to get the monthly breakdown, and add `"library_size_label"` to `stats.json` by hand if you want the size line.

## My year is incomplete
The stats only include data retained in the supplied snapshot. Run with a newer backup for later results.
