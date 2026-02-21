---
title: PDF Processing
---

# PDF Processing

Niobium uses [PyMuPDF](https://pymupdf.readthedocs.io/) to extract embedded images from PDF files. All PDF processing works without an API key.

## Extract images only

Export images from a PDF without creating any Anki cards:

```bash
niobium -pin /path/to/lecture.pdf -pout /path/to/output
```

Images are saved as numbered files in a timestamped subdirectory.

### Extract from specific pages

```bash
niobium -pin /path/to/lecture.pdf --page 5-10 -pout /path/to/output
```

Pages are 1-indexed. `--page 1` is the first page. `--page 3-7` processes pages 3 through 7 inclusive.

## Create cards directly from a PDF

Process a PDF and push cards to Anki in one step:

```bash
niobium -pin /path/to/lecture.pdf -deck "Lecture 3"
```

Or export as `.apkg`:

```bash
niobium -pin /path/to/lecture.pdf -apkg ./output
```

Or from specific pages:

```bash
niobium -pin /path/to/lecture.pdf --page 5-10 -apkg ./output
```

## Two-step workflow

For large PDFs, extract first to review images before processing:

```bash
# Step 1: extract
niobium -pin /path/to/lecture.pdf -pout /path/to/images

# Step 2: review, delete unwanted images, then process
niobium -dir /path/to/images -apkg ./output
```

This gives you the opportunity to delete irrelevant images (title slides, blank pages) before card creation.

:::{note}
Only raster images embedded inside the PDF are extracted. Pages containing only vector graphics or text rendered as outlines will not yield images.
:::

## Page selection (`--page`)

The `--page` flag limits which pages are processed:

```bash
# Single page
niobium -pin notes.pdf --page 5 -apkg ./output

# Page range
niobium -pin notes.pdf --page 3-7 -apkg ./output
```

This works with all PDF workflows: image extraction (`-pout`), card creation (`-deck`, `-apkg`), and AI modes (`--smart`).

## AI-powered PDF processing

When combined with `--smart --page`, Niobium enters a generation-first pipeline where Claude sees the full rendered page and creates cards from scratch (cloze, basic, and image occlusion). See [Smart Generation](docs/ai/smart-generation.md).

```bash
niobium -pin lecture.pdf --page 1-10 --smart -apkg
```
