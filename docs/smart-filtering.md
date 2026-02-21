---
title: Smart Filtering
---

# Smart Filtering

The `--smart` flag activates Claude Vision integration. Instead of relying solely on rule-based exclusion patterns, Claude analyzes each image semantically and decides what is worth studying.

## Pipeline comparison

**Without `--smart`:**

```
Image → EasyOCR → Rule-based filter (exclude.exact / exclude.regex) → Anki card
```

**With `--smart`:**

```
Image → EasyOCR → Claude Vision (semantic curation + OCR correction) → Anki card
```

OCR handles precise bounding box coordinates (its strength). Claude handles semantic understanding (its strength).

## What Claude does

For each image, Claude:

- **Decides what to occlude**:key terms, anatomical labels, drug names, disease names, important numerical values
- **Decides what to skip**:figure labels (A, B, Fig. 1), publisher info, copyright notices, page numbers, OCR noise
- **Corrects OCR errors**:compares garbled OCR text against what it actually sees in the image (e.g., "Glcmerulus" → "Glomerulus")
- **Generates study hints**:clinical correlations, functional notes, alternative names, mnemonics:added to the Back Extra field
- **Describes the image**:a one-line context description appears at the top of Back Extra

## Usage

Add `--smart` to any existing Niobium command:

```bash
# Single image
niobium --image /path/to/anatomy.png --apkg-out ./output --smart

# Directory of images
niobium --directory /path/to/slides --deck-name Pharmacology --smart

# PDF
niobium --single-pdf /path/to/lecture.pdf --apkg-out ./output --smart
```

Without `--smart`, Niobium works exactly as before:pure OCR with rule-based filtering.

## API key setup

An Anthropic API key is required. Provide it in one of two ways:

**Environment variable (recommended):**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Config file:**

```json
"llm": {
    "api_key": "sk-ant-..."
}
```

The config file value takes priority over the environment variable. If no key is found, Niobium falls back to rule-based filtering with a warning.

## Configuration

The `llm` section in your config file controls Smart mode:

```json
{
    "llm": {
        "api_key": null,
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "temperature": 0.2,
        "instructions": null
    }
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | `null` | Anthropic API key |
| `model` | `"claude-sonnet-4-6"` | Claude model identifier |
| `max_tokens` | `1024` | Maximum response tokens |
| `temperature` | `0.2` | Response variability (lower = more consistent) |
| `instructions` | `null` | Custom prompt addition (see below) |

## Custom instructions

The `instructions` field is the most powerful configuration option. It appends text to the built-in system prompt, letting you steer Claude's decisions for a specific study context.

**Pharmacology:**
```json
"instructions": "I'm studying pharmacology. Prioritize drug names, drug classes, mechanisms of action, receptor types, and side effects. Add hints about drug interactions and clinical indications."
```

**Histology:**
```json
"instructions": "These are histology slides. Occlude tissue types, cell types, staining characteristics, and structural features. Add hints about how to distinguish similar-looking tissues."
```

**Pathology:**
```json
"instructions": "Focus on pathological findings. Occlude disease names, morphological descriptions, and diagnostic features. Add hints about epidemiology and clinical presentation."
```

**USMLE Step 1:**
```json
"instructions": "I'm preparing for USMLE Step 1. Add high-yield clinical correlations and First Aid-style memory aids in the hints."
```

**Text-heavy slides:**
```json
"instructions": "These images contain mostly text paragraphs. Occlude only the most important medical terms, numerical values, and key facts. Skip filler words and context sentences."
```

Set `instructions` to `null` (or remove it) to use the default general-purpose behaviour.

## Cost

Claude Sonnet processes each image for approximately \$0.005–\$0.01 depending on image size and number of text regions. A batch of 50 images costs approximately \$0.25–\$0.50.

## Fallback behaviour

If anything goes wrong during a Smart mode run (API error, network timeout, malformed response), Niobium automatically falls back to rule-based filtering for that image and continues processing. You always get your cards.

## Caching

Claude responses are cached in `~/.config/niobium/cache.db` so the same image is never sent to the API twice. The cache key is derived from the image content, the OCR text list, the model name, and the `instructions` string. Changing any of these causes a fresh API call. See [Caching](docs/caching.md) for details.
