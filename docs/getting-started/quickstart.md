---
title: Quickstart
---

# Quickstart

Verify the installation:

```bash
niobium -h
```

## Create cards without AI (free, no API key)

### From a directory of images

```bash
# Push to Anki (requires AnkiConnect)
niobium -dir /path/to/images -deck "My Study Deck"

# Or export .apkg (no Anki needed)
niobium -dir /path/to/images -apkg ./output
```

### From a PDF

```bash
niobium -pin /path/to/lecture.pdf -apkg ./output
```

### Extract images from a PDF first, then create cards

```bash
# Step 1: extract images for review
niobium -pin /path/to/lecture.pdf -pout /path/to/images

# Step 2: delete unwanted images, then process
niobium -dir /path/to/images -apkg ./output
```

Import the resulting `.apkg` into Anki via File -> Import.

## Add AI features (requires Anthropic API key)

### Smart Filtering — AI curates your OCR results

```bash
export ANTHROPIC_API_KEY=sk-ant-...
niobium -dir /path/to/images -apkg ./output --smart
```

Claude filters noise, corrects OCR errors, and adds study hints. Output: image occlusion cards.

### Smart Generation — AI creates cards from scratch

```bash
# From images: Claude sees the full image
niobium -i /path/to/diagram.png --smart --generate -apkg ./output

# From PDF pages: Claude sees the full page
niobium -pin /path/to/lecture.pdf --page 1-5 --smart -apkg
```

Claude generates the best card types (cloze, basic, image occlusion) based on the content.

## Next steps

- [Core Workflows](docs/core/workflows.md): all non-AI workflows documented
- [AI Features](docs/ai/overview.md): what AI adds, costs, and setup
- [CLI Reference](docs/reference/cli.md): every flag documented
- [Configuration](docs/reference/configuration.md): tuning OCR and AI behavior
