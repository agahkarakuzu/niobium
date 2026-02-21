---
title: PDF Processing
---

# PDF Processing

Niobium uses [PyMuPDF](https://pymupdf.readthedocs.io/) to extract embedded images from PDF files.

## Extract images only

Export images from a PDF without creating any Anki cards:

```bash
niobium --single-pdf /path/to/lecture.pdf --pdf-img-out /path/to/output
```

Images are saved as numbered files in a timestamped subdirectory.

## Create cards directly from a PDF

Process a PDF and push cards to Anki in one step:

```bash
niobium --single-pdf /path/to/lecture.pdf --deck-name "Lecture 3"
```

Or export as `.apkg`:

```bash
niobium --single-pdf /path/to/lecture.pdf --apkg-out ./output
```

## Two-step workflow

For large PDFs, extract first to review images before processing:

```bash
# Step 1: extract
niobium --single-pdf /path/to/lecture.pdf --pdf-img-out /path/to/images

# Step 2: review, delete unwanted images, then process
niobium --directory /path/to/images --apkg-out ./output
```

This gives you the opportunity to delete irrelevant images (title slides, blank pages) before card creation.

:::{note}
Only raster images embedded inside the PDF are extracted. Pages containing only vector graphics or text rendered as outlines will not yield images.
:::

## Constraint

`--pdf-img-out` requires `--single-pdf` as the input source. You cannot use `--pdf-img-out` with `--image` or `--directory`.

## Smart mode with PDFs

Smart filtering works with PDFs just like with images:

```bash
niobium --single-pdf /path/to/lecture.pdf --apkg-out ./output --smart
```

Each extracted image is sent to Claude individually for semantic analysis.
