---
title: Smart Generation
---

# Smart Generation

Smart Generation is a **generation-first** pipeline. Instead of the usual OCR-then-filter approach, Claude sees the **full content** and generates the best card type(s) from scratch — including cloze, basic, and image occlusion cards.

This is fundamentally different from [Smart Filtering](docs/ai/smart-filtering.md), which is OCR-first and limited to image occlusion cards.

## How it differs from Smart Filtering

| | Smart Filtering (`--smart`) | Smart Generation (`--smart --generate` or `--smart --page`) |
|---|---|---|
| **Pipeline** | OCR first, Claude filters | Claude generates from scratch |
| **Input to Claude** | Image + OCR text regions | Full image, page render, or extracted text |
| **What Claude does** | Classifies existing OCR regions as keep/skip | Generates cards from scratch |
| **Card types** | Image occlusion only | Image occlusion, cloze, and basic |

## When to use which

- **Smart Filtering** (`--smart`): You have labeled diagrams/figures and want OCR-based image occlusion cards with smart curation. Works with any input type.
- **Smart Generation** (`--smart --generate` or `--smart --page`): You want Claude to analyze the full content and decide the best card types. Use `--generate` for image inputs, `--page` for PDF pages.

## Pipeline

### Image inputs (`-i` or `-dir` with `--smart --generate`)

```
Image ──(send full image)──> Claude Vision ──> mixed card types
```

Claude sees the entire image and decides what cards to create. No OCR step — Claude handles everything.

### PDF pages (`-pin --page` with `--smart`)

Niobium automatically detects whether each page contains images or is text-only, and uses the cheapest approach for each:

```
PDF page with images:
  ──(render at 200 dpi)──> page image ──(Claude Vision)──> mixed card types

PDF page without images:
  ──(extract text)──> page text ──(Claude text-only)──> cloze & basic cards
```

Text-only pages skip the expensive image rendering and Vision API call entirely, sending just the extracted text to Claude. Image occlusion cards are automatically excluded for text-only pages since there is nothing to occlude.

## Usage

### Image inputs

```bash
# Single image — Claude generates cards from scratch
niobium -i anatomy.png --smart --generate -apkg ./output

# Directory of images
niobium -dir ./slides --smart --generate -deck "Pharmacology"

# With constraints
niobium -dir ./slides --smart --generate --max-cards 3 --card-type cloze -apkg
```

### PDF pages

```bash
# Single page — outputs to work_dir/outputs by default
niobium -pin lecture.pdf --page 5 --smart

# Page range
niobium -pin lecture.pdf --page 3-8 --smart

# Explicit output directory
niobium -pin lecture.pdf --page 5 --smart -apkg ./my_output

# Push to Anki instead
niobium -pin lecture.pdf --page 3-8 --smart -deck "Anatomy"
```

For PDFs, `--smart --page` implies generation mode — no need to add `--generate`.

When no output flag is given, the `.apkg` file is saved to `{work_dir}/outputs` (default `~/niobium_work/outputs`). The filename is derived from the input (e.g., `lecture.apkg` for `lecture.pdf`).

### Limit the number of cards

```bash
# Per page
niobium -pin lecture.pdf --page 1-10 --smart --max-cards 3

# Per image
niobium -dir ./slides --smart --generate --max-cards 5 -apkg
```

You can also set a default in your config:

```yaml
llm:
  max_cards: 5
```

The `--max-cards` CLI flag overrides the config value for a single run.

### Force a specific card type

```bash
# Only cloze cards
niobium -pin lecture.pdf --page 1-5 --smart --card-type cloze

# Only basic Q&A cards from images
niobium -dir ./slides --smart --generate --card-type basic -apkg

# Only image occlusion
niobium -i figure.png --smart --generate --card-type image_occlusion -deck "Anatomy"
```

### Combine constraints

```bash
niobium -pin lecture.pdf --page 1-20 --smart --card-type cloze --max-cards 5
niobium -dir ./slides --smart --generate --card-type basic --max-cards 3 -apkg
```

## Card types Claude can generate

### Image occlusion
Best for diagrams, labeled figures, and annotated images. Claude provides rectangular coordinates for regions to hide, and the student recalls what is underneath.

### Cloze
Best for factual statements and definitions. Claude writes fill-in-the-blank sentences using Anki's cloze syntax (`{{c1::answer}}`).

### Basic
Best for conceptual questions. Claude writes a question for the front and an answer for the back.

When no `--card-type` is specified, Claude decides the best mix based on the content. A labeled diagram will get occlusion cards; text-heavy content will get cloze and basic cards; mixed content may get all three.

## Page selection (`--page`)

The `--page` flag works with any PDF workflow, not just smart mode:

```bash
# Smart page generation (outputs to work_dir/outputs)
niobium -pin notes.pdf --page 5-10 --smart

# Standard OCR pipeline, limited to specific pages
niobium -pin notes.pdf --page 3 -deck "Default"

# Image extraction from specific pages
niobium -pin notes.pdf --page 1-5 -pout ./images
```

Pages are 1-indexed. `--page 1` is the first page. `--page 3-7` processes pages 3 through 7 inclusive.

## Confirmation panel

When `--smart` is used, Niobium displays a summary panel before processing that shows:

- **Pipeline**: what will happen (filtering vs generation)
- **Input**: what's being processed
- **Output**: where results will be saved
- **Card types**: what types of cards can be created
- **Model and instructions**: which Claude model and custom instructions are active
- **Constraints**: max cards, forced card type, cache status

This lets you verify the full configuration before spending API credits.

## Configuration

Smart generation uses the same `llm` config section as smart filtering, plus additional keys:

```yaml
llm:
  api_key: null
  model: claude-sonnet-4-6
  max_tokens: 1024
  max_tokens_generate: 4096
  temperature: 0.2
  max_cards: null
  instructions: null

work_dir: ~/niobium_work
```

| Key | Default | Description |
|-----|---------|-------------|
| `llm.max_tokens_generate` | `4096` | Max response tokens for card generation (higher than filtering because Claude produces full card content) |
| `llm.max_cards` | `null` | Default max cards per page/image; overridden by `--max-cards` |
| `work_dir` | `~/niobium_work` | Base directory for outputs and artifacts (set to `null` to disable) |

The `instructions` field works here too. For example:

```yaml
instructions: >-
  I'm studying pharmacology. Generate cloze cards for drug mechanisms
  and basic cards for clinical indications.
```

## Caching

Responses are cached per content + constraint combination. Changing `--max-cards`, `--card-type`, or the input content produces a different cache key, so you can experiment freely without stale results. Use `--no-cache` to force fresh API calls.

## Cost

- **Images**: approximately $0.005-$0.02 per image depending on size (Claude Vision)
- **PDF pages with images**: approximately $0.01-$0.02 per page (rendered and sent via Vision API)
- **Text-only PDF pages**: approximately $0.001-$0.003 per page (text extraction only, no Vision)

A directory of 30 images costs roughly $0.15-$0.60. A 20-page PDF where half the pages are text-only costs roughly $0.10-$0.25.
