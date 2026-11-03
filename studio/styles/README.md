# Studio styles

A style is a folder with two files:

```text
studio/styles/<id>/
  style.json   name, description, fonts it uses, default palette
  style.css    every rule scoped under .style-<id>
```

`python rewind.py styles` lists them; `--style <id>` renders with one. Each style lays out the same
shared markup ([`../base.html`](../base.html)) and the same numbers, so adding a style never touches
Python.

## style.json

```json
{
  "name": "Editorial",
  "description": "One line shown by `rewind.py styles`.",
  "fonts": ["Archivo", "JetBrains Mono"],
  "palette": { "bg": "#12110f", "panel": "#1c1a17", "accent": "#e5a00d", "secondary": "#a39b8f", "fg": "#f2ede4" }
}
```

The palette keys match the classic `templates/*.json` colors, so `--theme aurora` recolors any style.
In CSS they arrive as `--bg`, `--panel`, `--accent`, `--muted` (from `secondary`) and `--fg`. Derive
anything else with `color-mix()` so a theme override still holds together.

## The markup

Six sections, each 1080 × 1350: `.s-cover`, `.s-numbers`, `.s-watched`, `.s-library`, `.s-closing`
and the single-page `.s-info`. Every section starts with a `.deco` element (four empty `<i>` children,
hidden by default) that a style can turn on for frames, stripes or texture, and a `.slate` header.

Useful hooks:

| Element | Holds |
|---|---|
| `.title`, `.range`, `.lede` | Headline, date range, one-sentence lead |
| `.year` | The year (cover) |
| `.hero .v` | Total plays (numbers slide, infographic) |
| `.stat`, `.kpi`, `.side-row` | Secondary figures, each `.v` + `.l` (+ `.n` note) |
| `.track`, `.track .fill`, `.tick`, `.busy-mark`, `.month` | Year-progress strip; positions come from `--l`, `--bw` |
| `.list .row` → `.rk .nm .pl .bar` | Ranked shows / movies; first row has `.lead` |
| `.count-item` | Library totals |
| `.share` → `.k .p .bar` | "Added this year" part-of-whole bars |
| `.thanks .t1 .t2`, `.message`, `.cta .methods .method` | Closing slide |

Bars: style `.bar` (the track) and `.bar > i` (the fill). The fill's width is
`calc(var(--w) * var(--grow))`: data sets `--w`, the video runtime animates `--grow`. Don't set the
width yourself.

Servers differ. Names run from "Jones" to "Movie Night at the Garcia House": anything that shows the
server name should keep one line and opt into shrink-to-fit with `--fit: 1` (the slate and the
infographic title and footer already do, in `runtime/base.css`). Parts of the data can be missing (no busiest month, no library size, `--cta none` has no payment
methods). The markup removes those elements, so check that a slide still reads well without them:
the test suite renders every style.

## Motion

Video export fades `[data-m]` elements up in document order, counts numbers up and grows bars.
A style can tune it on `.slide`:

```css
.style-terminal .slide { --m-mode: type; --m-step: .2; }  /* appear instantly, like terminal output */
```

`--m-step` (seconds between elements), `--m-rise` (px), `--m-fade` (seconds), `--m-mode` (`fade` or `type`).

## Fonts

Only the bundled fonts in [`../fonts/`](../fonts/) load (renders never touch the network). To add a
typeface, copy its latin `.woff2` and license into `studio/fonts/<family>/` and add an `@font-face` to
`fonts.css`. Use fonts whose license allows redistribution (SIL OFL is ideal).

## Rules of the house

- Every number on a card comes from the stats file or plain arithmetic on it. No decorative charts.
- No logos you don't own (Plex's included): name things in type.
- One accent doing one job per slide. No glow, glassmorphism or stock imagery.
- Text contrast at least 4.5:1 (3:1 for text 24px and up) against what it sits on.
