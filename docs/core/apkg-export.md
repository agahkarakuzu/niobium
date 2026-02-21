---
title: APKG Export
---

# APKG Export

The `-apkg` flag exports cards as a standard `.apkg` file using [genanki](https://github.com/kerrickstaley/genanki). No Anki instance or AnkiConnect add-on is required at export time.

## Basic usage

```bash
niobium -dir /path/to/images -apkg ./output
```

The `.apkg` file is written to the specified directory. The filename is derived from the input (e.g., `slides.apkg` for a directory named `slides`).

### Default output

When `-apkg` is used without a path, or no output flag is given at all, Niobium saves to `{work_dir}/outputs` (default: `~/niobium_work/outputs`).

```bash
# All of these save to ~/niobium_work/outputs/
niobium -dir /path/to/images -apkg
niobium -dir /path/to/images
niobium -pin lecture.pdf
```

## Supported inputs

All three input modes work with APKG export:

```bash
# Single image
niobium -i /path/to/diagram.png -apkg ./output

# Directory of images
niobium -dir /path/to/images -apkg ./output

# PDF
niobium -pin /path/to/lecture.pdf -apkg ./output
```

## Importing into Anki

1. Open Anki.
2. Go to File -> Import.
3. Select the `.apkg` file.

All images are bundled inside the package — no external files needed.

## Card model

Exported cards use a custom Image Occlusion cloze model with these fields:

| Field | Purpose |
|-------|---------|
| Occlusion | Cloze-formatted occlusion coordinates |
| Image | The source image (embedded) |
| Header | Filename header (populated when `--add-header` is used) |
| Back Extra | Supplementary HTML: hints from Smart mode, extra annotations, or image context |
| Comments | Reserved for future use |

The front template shows the cloze occlusion overlaid on the image. The back template reveals the answer and displays the Back Extra content.

When AI generation mode is used (`--smart --generate` or `--smart --page`), the export can also contain Cloze and Basic card models in addition to Image Occlusion.

## With Smart mode

```bash
niobium -dir /path/to/images -apkg ./output --smart
```

When combined with `--smart`, the Back Extra field is populated with Claude-generated hints, OCR corrections, and image context descriptions. See [AI Features](docs/ai/overview.md).
