---
title: APKG Export
---

# APKG Export

The `--apkg-out` flag exports cards as a standard `.apkg` file using [genanki](https://github.com/kerrickstaley/genanki). No Anki instance or AnkiConnect add-on is required at export time.

## Basic usage

```bash
niobium --directory /path/to/images --apkg-out /path/to/output
```

The `.apkg` file is written to the specified directory.

## Supported inputs

All three input modes work with APKG export:

```bash
# Single image
niobium --image /path/to/diagram.png --apkg-out ./output

# Directory of images
niobium --directory /path/to/images --apkg-out ./output

# PDF
niobium --single-pdf /path/to/lecture.pdf --apkg-out ./output
```

## Importing into Anki

1. Open Anki.
2. Go to File → Import.
3. Select the `.apkg` file.

All images are bundled inside the package:no external files needed.

## Card model

Exported cards use a custom Image Occlusion cloze model with these fields:

| Field | Purpose |
|-------|---------|
| Occlusion | Cloze-formatted occlusion coordinates |
| Image | The source image (embedded) |
| Header | Filename header (populated when `--add-header` is used) |
| Back Extra | Supplementary HTML:hints from Smart mode, extra annotations, or image context |
| Comments | Reserved for future use |

The front template shows the cloze occlusion overlaid on the image. The back template reveals the answer and displays the Back Extra content.

## With Smart mode

```bash
niobium --directory /path/to/images --apkg-out ./output --smart
```

When combined with `--smart`, the Back Extra field is populated with Claude-generated hints, OCR corrections, and image context descriptions.
