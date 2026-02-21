---
title: Quickstart
---

# Quickstart

Verify the installation:

```bash
niobium -h
```

## Your first deck (directory of images)

```bash
niobium --directory /path/to/images --deck-name "My Study Deck"
```

Anki must be running with AnkiConnect enabled. Niobium creates the deck if it does not exist.

## Offline export (no Anki required)

```bash
niobium --directory /path/to/images --apkg-out /path/to/output
```

Import the resulting `.apkg` into Anki via File → Import.

## Process a PDF directly

```bash
niobium --single-pdf /path/to/lecture.pdf --apkg-out /path/to/output
```

## Smart mode (requires Anthropic API key)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
niobium --directory /path/to/images --apkg-out ./output --smart
```

Claude Vision will analyze each image, filter noise, correct OCR errors, and add study hints. See [Smart Filtering](docs/smart-filtering.md) for full details.

## Next steps

- [CLI Reference](docs/cli-reference.md):every flag documented
- [Configuration](docs/configuration.md):tuning OCR exclusion rules
- [Smart Filtering](docs/smart-filtering.md):Claude Vision integration
- [Common Workflows](docs/workflows.md):task-oriented examples
