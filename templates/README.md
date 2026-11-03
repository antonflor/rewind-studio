# Custom slide templates

Place a JSON theme file in this folder, for example `templates/my-server.json`. The renderer loads it by name:

```bash
python rewind.py templates
python rewind.py render --data examples/odyssey-2026.json --name "My Media Server" --theme my-server --cta none --out output/my-server
```

Or pass any file path: `--theme /path/to/theme.json`.

Copy `templates/aurora.json` to create your own. Supported keys:

- `extends`: built-in base theme, `odyssey` or `minimal`
- `colors`: `bg`, `panel`, `accent`, `secondary`, `fg` (CSS-style hex values)
- `labels`: `cover_title`, `cover_subtitle`, `cover_footer`, `stats_title`, `titles_title`, `library_title`, `closing_title`, `closing_subtitle`, `closing_footer`
- `background`: optional PNG/JPG file path **relative to the template JSON**. Images are cropped to fit and blended at 25% opacity to keep text legible.

**Limitations:** Custom templates change colors, labels, and background photography. They do **not yet** support arbitrary slide positioning, custom fonts, or per-slide layouts. These would need a future layout schema. Templates are JSON only and cannot execute arbitrary code.

Export size is 1080 × 1350 pixels (4:5); set your source image to that aspect ratio for best results.

Privacy: Keep user data and licensed posters out of the public template directory. Templates should contain reusable design settings, not real account identifiers.
