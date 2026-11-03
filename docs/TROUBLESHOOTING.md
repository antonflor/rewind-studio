# Troubleshooting

## `python` is not recognized
Use `py` on Windows or `python3` on macOS/Linux. Check `python --version` first.

## `ModuleNotFoundError: PIL`
Install dependencies with the same interpreter you run: `python -m pip install -r requirements.txt`.

## Database backup not found
Pass an **absolute path** to a standalone Plex library DB backup. The location differs on Docker, Windows, macOS, NAS, and hosted seedboxes. Paths with spaces must be quoted.

## Can't open database
You may be pointing at the live Plex DB, a partial backup, or an inaccessible path. Use a scheduled backup copied into a writable local directory. Rewind Studio does not need a Plex token or API credentials.

## Database is missing tables
Verify the input is `com.plexapp.plugins.library.db...` and not `com.plexapp.plugins.library.blobs.db...`. Older or different Plex versions can vary.

## Fonts look different
Pillow uses an installed system font. Install DejaVu Sans on Linux or use default Windows/macOS fonts; the result may vary slightly.

## Template not found
Run `python rewind.py templates` from the repository root. Use a file path to load templates from another directory.

## My year is incomplete
The year-to-date stats only include data retained in the supplied snapshot. Run with a newer backup for later results.

## Can I export video?
Not in this MVP. It generates five PNGs; import those into Instagram, CapCut, DaVinci Resolve, or another video editor to animate them.
