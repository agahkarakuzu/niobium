---
title: AI Features Overview
---

# AI Features Overview

Niobium works fully without any AI or API key — OCR-based image occlusion is completely free. The `--smart` flag is an **optional upgrade** that adds Claude AI for smarter cards.

## What AI adds

| | Without AI | With AI (`--smart`) |
|---|---|---|
| **Text detection** | EasyOCR | EasyOCR (or skipped entirely in generation mode) |
| **Filtering** | Rule-based (exact + regex patterns) | Claude decides what's worth studying |
| **OCR correction** | None | Claude fixes misread text by comparing against the image |
| **Study hints** | None | Claude generates clinical correlations, mnemonics, and context |
| **Card types** | Image occlusion only | Image occlusion, cloze, and basic (in generation mode) |

## Two AI modes

### Smart Filtering (`--smart`)

OCR runs first, then Claude filters the results. Best for labeled diagrams and figures.

```bash
niobium -i anatomy.png --smart -apkg ./output
```

See [Smart Filtering](smart-filtering.md) for details.

### Smart Generation (`--smart --generate` or `--smart --page`)

Claude sees the full content and generates cards from scratch. Supports cloze, basic, and image occlusion cards.

```bash
# Image input
niobium -i anatomy.png --smart --generate -apkg ./output

# PDF pages
niobium -pin lecture.pdf --page 1-10 --smart -apkg
```

See [Smart Generation](smart-generation.md) for details.

## API key setup

An [Anthropic API key](https://console.anthropic.com/) is required. Provide it in one of two ways:

**Environment variable (recommended):**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Config file:**

```yaml
llm:
  api_key: sk-ant-...
```

The config value takes priority over the environment variable. If no key is found, Niobium falls back to rule-based filtering with a warning.

## Cost

All costs are approximate and depend on image size and content density.

| Mode | Cost per item | Notes |
|---|---|---|
| Smart Filtering | ~$0.005-$0.01 per image | Image + OCR text sent to Claude |
| Smart Generation (image) | ~$0.005-$0.02 per image | Full image sent via Vision API |
| Smart Generation (PDF page with images) | ~$0.01-$0.02 per page | Page rendered and sent via Vision API |
| Smart Generation (text-only PDF page) | ~$0.001-$0.003 per page | Only extracted text sent, no Vision |

**Example costs:**
- 50 images with Smart Filtering: ~$0.25-$0.50
- 20-page PDF (half text-only) with Smart Generation: ~$0.10-$0.25

## Confirmation panel

When `--smart` is used, Niobium displays a summary panel before processing:

```
╭──────────── Smart Generation ────────────╮
│                                          │
│  Pipeline: Claude sees full content and  │
│            generates cards from scratch   │
│  Input: PDF pages from lecture.pdf       │
│         (page 1-10)                      │
│  Output: APKG: ~/niobium_work/outputs    │
│  Card types: image occlusion, cloze,     │
│              basic                       │
│  Model: claude-sonnet-4-6               │
│  Instructions: Focus on pharmacology...  │
│                                          │
╰──────────────────────────────────────────╯
Proceed? [Y/n]:
```

This lets you verify the configuration before spending API credits.

## Custom instructions

The `instructions` field in your config lets you steer Claude's behavior:

```yaml
llm:
  instructions: >-
    I'm studying pharmacology. Prioritize drug names, mechanisms
    of action, and side effects.
```

Instructions work with both Smart Filtering and Smart Generation. See [Configuration](docs/reference/configuration.md) for more examples.

## Caching

All Claude API responses are cached locally. The same input is never sent to the API twice unless you use `--no-cache`. See [Caching](docs/reference/caching.md).
