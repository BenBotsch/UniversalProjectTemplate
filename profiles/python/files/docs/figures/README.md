# Figures

Figures of the README and the documentation live in this folder. They are drawn in the shared
style of [FigureKit](https://github.com/BenBotsch/FigureKit) and are generated, not edited by
hand. Keep one command that writes all of them, and commit its output.

## Drawing

The optional dependency group `figures` installs FigureKit with matplotlib:

```text
uv sync --group figures
uv run --group figures python -m <package>.figures
uv run --group figures figkit check docs/figures
```

FigureKit's style guide describes the themes, the colour order, `render` and the export formats.

## Naming

Every figure exists for a light and a dark page. Its background is transparent, so one file fits
every page colour of its mode.

```text
<name>.svg        light page, for the web and the README
<name>-dark.svg   dark page
<name>.png        light page, for slides and tools without SVG
<name>-dark.png   dark page
card.png          optional 1200 x 630 social preview, opaque
card-dark.png     the same on a dark background
```

Photographs and images with overlays are WebP, with a PNG copy, instead of SVG.

## Check

When this folder holds a figure, the `lint` job of CI runs `figkit check docs/figures`. It fails
on a missing light or dark file, an opaque chart, a chart off the shared canvas width and a file
above its size budget. A folder with only this guide is not checked.

The SVG files end lines with spaces. `.gitattributes` and `.editorconfig` in this folder and the
pre-commit hooks leave them unchanged, so a second run writes the same bytes.

## Embedding

A README on GitHub picks the file from the reader's colour scheme:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/<name>-dark.svg">
  <img src="docs/figures/<name>.svg" alt="<what the figure shows and its main finding>">
</picture>
```

## Alt Text and Sources

- The alt text states what the figure shows and its finding, with the numbers that matter, such
  as "Recall per class: every class above 80 % except scratches at 74 %." It does not start with
  "Image of".
- List every figure with its alt text in a table in this README, so pages and slides reuse the
  same text.
- A figure drawn from third-party data or showing third-party images names the source and its
  licence below the table. Figures with images whose licence forbids redistribution are not
  committed.
