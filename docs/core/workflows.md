---
title: Core Workflows
---

# Core Workflows

Everything on this page works **without an API key or internet connection**. Niobium uses local OCR to detect text regions and creates image occlusion flashcards automatically.

## From a directory of images

The most common workflow. Point Niobium at a folder of screenshots, slides, or diagrams.

### Push to Anki directly

Requires Anki to be open with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) installed.

```bash
niobium -dir /path/to/images -deck "Anatomy 2025"
```

Niobium creates the deck if it does not exist.

### Export as .apkg (no Anki needed)

```bash
niobium -dir /path/to/images -apkg ./output
```

Import the `.apkg` into Anki with File -> Import. See [APKG Export](apkg-export.md) for details.

## From a single image

```bash
# Push to Anki
niobium -i /path/to/diagram.png -deck "Anatomy 2025"

# Export as .apkg
niobium -i /path/to/diagram.png -apkg ./output
```

## From a PDF

Niobium extracts embedded images from the PDF and processes each one.

```bash
# Push to Anki
niobium -pin /path/to/lecture.pdf -deck "Lecture 3"

# Export as .apkg
niobium -pin /path/to/lecture.pdf -apkg ./output

# Process only specific pages
niobium -pin /path/to/lecture.pdf --page 5-10 -apkg ./output
```

See [PDF Processing](pdf-processing.md) for more details.

## Extract images from a PDF (without creating cards)

Useful for reviewing what's inside a PDF before making cards.

```bash
niobium -pin /path/to/lecture.pdf -pout /path/to/images
```

Images are saved as numbered files in a timestamped subdirectory.

## Two-step PDF workflow

For large PDFs, extract first, review, then process:

```bash
# Step 1: extract all images
niobium -pin /path/to/lecture.pdf -pout /path/to/images

# Step 2: delete unwanted images (title slides, blank pages, etc.)
# ... manually review the folder ...

# Step 3: create cards from the curated set
niobium -dir /path/to/images -apkg ./output
```

This gives you full control over which images become flashcards.

## Create basic front/back cards

Each image becomes a single card with the image as the front and an empty back. Useful for quick visual review decks.

```bash
niobium -dir /path/to/images -deck "Quick Review" -basic True
```

## Tune OCR behavior

### Change languages

```bash
niobium -dir /path/to/images -deck "My Deck" --langs en,fr
```

### Adjust box merging

If OCR creates too many fragmented boxes:

```bash
niobium -dir /path/to/images -deck "My Deck" --merge-lim-x 20 --merge-lim-y 20
```

### GPU acceleration

```bash
niobium -dir /path/to/images -deck "My Deck" --gpu 0
```

All of these can also be set persistently in your [config file](docs/reference/configuration.md).

## Re-running on the same directory

Niobium tracks processed images via a local cache. If you add new images to a directory and re-run, only the new images are processed. See [Caching](docs/reference/caching.md).

## Default output directory

When no output flag is given, Niobium saves `.apkg` files to `{work_dir}/outputs` (default: `~/niobium_work/outputs`). The filename is derived from your input (e.g., `lecture.apkg` for `lecture.pdf`).

```bash
# These all save to ~/niobium_work/outputs/
niobium -dir ./slides
niobium -pin lecture.pdf
niobium -i diagram.png
```
