# Templates

A template recolors any style and can change its headline text. It's a small JSON file in this folder, for example `templates/my-server.json`:

```bash
python rewind.py templates
python rewind.py render --data examples/odyssey-2026.json --name "My Media Server" --style swiss --theme my-server --out output/my-server
```

You can also pass any file path: `--theme /path/to/theme.json`.

Copy `aurora.json` to start. Supported keys:

- `colors`: any of `bg` (background), `panel` (raised surfaces and bar tracks), `accent` (the one highlight color), `secondary` (labels and captions) and `fg` (main text), as hex values like `#1c2640`. Colors you leave out keep the style's own.
- `labels`: any of `cover_title`, `cover_subtitle`, `stats_title`, `titles_title`, `library_title`, `info_title`, `closing_title`, `closing_footer`, `cta_methods` (slash-separated, like `"Ko-fi / Venmo"`). Labels you leave out keep the defaults.

Check that text stays readable: `fg` and `secondary` on `bg` should have a contrast ratio of at least 4.5:1.

Templates are JSON only and can't run code. Layout and typography belong to the style; to change those, [make a style](../studio/styles/README.md).

Privacy: keep account names and licensed artwork out of templates you share. Templates should hold reusable design settings only.
