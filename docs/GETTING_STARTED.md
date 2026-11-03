# Getting started

Rewind Studio is a **command-line program**, not a website. It turns your Plex server's stats into five 1080 × 1350 slides, a single-page infographic and/or an animated video, ready to post on Instagram. This guide starts with the bundled sample before touching your Plex database.

## 1. Install prerequisites

Install [Python 3.10+](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads/). On Windows, check **Add Python to PATH** during installation. For video, also install [ffmpeg](https://ffmpeg.org/download.html): `winget install ffmpeg` (Windows), `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Debian/Ubuntu).

Open PowerShell (Windows) or Terminal (macOS/Linux):

| Platform | Check Python | Check Git |
|---|---|---|
| Windows | `py --version` | `git --version` |
| macOS | `python3 --version` | `git --version` |
| Linux | `python3 --version` | `git --version` |

Commands below use `python`. On Windows substitute `py`, and on macOS/Linux substitute `python3` if needed.

## 2. Download and install

```bash
git clone https://github.com/antonflor/rewind-studio.git
cd rewind-studio
python -m venv .venv
```

Activate your environment:

- **Windows PowerShell:** `.venv\Scripts\Activate.ps1` (if blocked, use `.venv\Scripts\python.exe` directly)
- **Windows Command Prompt:** `.venv\Scripts\activate.bat`
- **macOS/Linux:** `source .venv/bin/activate`

Then install the dependencies and the headless browser Rewind Studio renders with:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python rewind.py --help
```

On a Linux server without a desktop, use `python -m playwright install --with-deps chromium`. Already have Chrome or Chromium? Skip the download and set `REWIND_CHROMIUM` to the browser's executable path instead.

## 3. Generate an example, no Plex server required

```bash
python rewind.py render --data examples/odyssey-2026.json --name "My Media Server" --format both --out output/demo
```

Look in `output/demo/` for `slide-1.png` through `slide-5.png` and `infographic.png`. Run `python rewind.py styles` to see the seven styles and try another with `--style`, for example `--style ticket`.

## 4. Find your own Plex library backup

Rewind Studio does **not** assume a fixed installation location. You must choose a **complete, standalone backup** of `com.plexapp.plugins.library.db`, often with a dated suffix. Do **not** point it at the active, changing Plex database. Never use the `blobs.db` file.

Common locations:

| Installation | Typical data location (varies) |
|---|---|
| Windows | `%LOCALAPPDATA%\Plex Media Server\Plug-in Support\Databases` |
| macOS | `~/Library/Application Support/Plex Media Server/Plug-in Support/Databases` |
| Linux | `/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases` |
| Docker | Host folder bound to Plex `/config`, followed by its library data path |
| NAS / seedbox | Vendor-specific application data directory |

Linux example (only if those paths exist):

```bash
find "$HOME" /var/lib/plexmediaserver -type f -name 'com.plexapp.plugins.library.db-20*' 2>/dev/null
```

For Windows, open File Explorer, paste `%LOCALAPPDATA%\Plex Media Server\Plug-in Support\Databases` into the address bar, and inspect the dated backup files. Copy the backup to your computer if the server is remote. The exact filename varies with Plex version and backup schedule.

## 5. Extract data safely

Use **your** database backup path:

```bash
python rewind.py extract --db "/full/path/to/your/plex-backup.db" --year 2026 --out stats.json
```

For Windows PowerShell, for example:

```powershell
py rewind.py extract --db "C:\Users\YourName\Downloads\plex-backup.db" --year 2026 --out stats.json
```

`stats.json` stores aggregated counts and top titles; it does **not** include account names or individual account playback rows. It may still reveal information about your media library, so inspect it before sharing.

Optional: edit `stats.json` to set `"library_size_label": "~10 TiB"`, which Plex's database does not determine.

## 6. Generate your recap

```bash
python rewind.py render --data stats.json --name "The Vault" --style editorial --format all --out output/the-vault
```

`--format all` writes the five slides, `infographic.png` and `rewind.mp4`. Use `slides`, `infographic`, `both` or `video` for less. The video takes about 30 seconds to render; add `--no-sound` for a silent one.

Name the server anything. Long names shrink to fit, and anything your stats don't include, like a busiest month or a music library, is left out. **Odyssey is example data, not a requirement.**

### The closing slide

| Option | Result |
|---|---|
| `--cta none` | A simple "That's a wrap" (default) |
| `--cta thanks` | A thank-you to everyone who watched |
| `--cta donation` | A thank-you plus how to chip in for next year |
| `--cta-text "…"` | Your own closing message |
| `--cta-methods "Ko-fi / Venmo"` | The donation options to list (default: PayPal / Zelle / DM) |

## 7. Recolor a style with a template

`python rewind.py templates` lists the templates in `templates/`. A template gives any style new colors and, optionally, new headline text:

```bash
python rewind.py render --data stats.json --name "The Vault" --style swiss --theme aurora --out output/aurora
```

Copy `templates/aurora.json` to `templates/my-theme.json` and edit it to make your own, or pass a path: `--theme "/path/to/my-theme.json"`. See the [template reference](../templates/README.md).

## 8. Post to Instagram

Upload the five slides as a carousel (keep their order), **or** `infographic.png` as one feed post, **or** `rewind.mp4` as a video post. Everything is 1080 × 1350 (4:5), Instagram's portrait feed size. When posting the video, choose a cover frame in Instagram's *Edit cover* step, because the video opens on a dark frame.

Stats extracted with this version include a monthly breakdown, so the cards can name the busiest month. Older `stats.json` files still work; that line is just left out.

## Common problems

See [Troubleshooting](TROUBLESHOOTING.md). `python rewind.py render --help` lists every option.
