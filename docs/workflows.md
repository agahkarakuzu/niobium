---
title: Common Workflows
---

# Common Workflows

## Push cards to Anki directly

Requires Anki to be open with AnkiConnect installed.

```bash
# From a directory of images
niobium --directory /path/to/images --deck-name "Anatomy 2025"

# From a single image
niobium --image /path/to/diagram.png --deck-name "Anatomy 2025"

# From a PDF
niobium --single-pdf /path/to/lecture.pdf --deck-name "Anatomy 2025"
```

Niobium creates the deck if it does not exist. You will be prompted to confirm.

## Create an offline .apkg file

No Anki or AnkiConnect needed at creation time.

```bash
niobium --directory /path/to/images --apkg-out ./output
niobium --image /path/to/diagram.png --apkg-out ./output
niobium --single-pdf /path/to/lecture.pdf --apkg-out ./output
```

Import the `.apkg` into Anki with File → Import.

## Extract images from a PDF (without creating cards)

```bash
niobium --single-pdf /path/to/lecture.pdf --pdf-img-out /path/to/images
```

Useful for reviewing extracted images before processing them.

## Two-step PDF workflow

For large PDFs, extract first, review, then process:

```bash
# Step 1: extract images
niobium --single-pdf /path/to/lecture.pdf --pdf-img-out /path/to/images

# Step 2: delete unwanted images, then create cards
niobium --directory /path/to/images --apkg-out ./output
```

## Create basic front/back cards

Each image becomes a single card with the image as the front.

```bash
niobium --directory /path/to/images --deck-name "Quick Review" --basic-type True
```

## Add Smart mode to any workflow

```bash
export ANTHROPIC_API_KEY=sk-ant-...
niobium --directory /path/to/images --apkg-out ./output --smart
```

See [Smart Filtering](docs/smart-filtering.md) for configuration and custom instructions.

## Tweak OCR merging and languages

```bash
niobium --directory /path/to/images --deck-name "Pharmacology" \
  --merge-lim-x 20 --merge-lim-y 20 --langs en,fr
```

## GPU acceleration

```bash
niobium --directory /path/to/images --deck-name "My Deck" --gpu 0
```

## Re-running on the same directory

Niobium tracks processed images via a SQLite cache. If you add new images to a directory and re-run, only the new images are processed. See [Caching](docs/caching.md) for details.
