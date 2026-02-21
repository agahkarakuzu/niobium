---
title: CLI Reference
---

# CLI Reference

```
niobium [options] <input> <output>
```

Run `niobium -h` to see the built-in help text.

## Input (mutually exclusive, one required)

| Flag | Short | Description |
|------|-------|-------------|
| `--image PATH` | `-i` | Absolute path to a single image file |
| `--directory PATH` | `-dir` | Directory containing multiple images |
| `--single-pdf PATH` | `-pin` | Absolute path to a PDF file |

## Output (mutually exclusive)

| Flag | Short | Description |
|------|-------|-------------|
| `--deck-name NAME` | `-deck` | Anki deck to push notes into (requires AnkiConnect) |
| `--pdf-img-out PATH` | `-pout` | Directory to save images extracted from a PDF |
| `--apkg-out [PATH]` | `-apkg` | Directory to write the exported `.apkg` file |

When no output flag is given, or `-apkg` is used without a path, Niobium defaults to `{work_dir}/outputs` (see [work_dir](docs/reference/configuration.md#work_dir) config). If `work_dir` is not set either, an error is raised.

## Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--smart` |:| `False` | Enable Claude AI — [filters OCR results](docs/ai/smart-filtering.md) by default, [generates cards from scratch](docs/ai/smart-generation.md) with `--generate` or `--page` |
| `--generate` | `-gen` | `False` | Generation-first mode: Claude sees the full image and generates cards from scratch (requires `--smart`) |
| `--page RANGE` |:| `None` | Page or page range for PDF input, e.g. `5` or `5-10` (requires `-pin`) |
| `--max-cards N` |:| `None` | Max cards to generate per item (requires `--smart` with `--page` or `--generate`) |
| `--card-type TYPE` |:| `None` | Force card type: `cloze`, `basic`, or `image_occlusion` (requires `--smart` with `--page` or `--generate`) |
| `--add-header` | `-hdr` | `False` | Add the filename as a card header |
| `--basic-type` | `-basic` | `False` | Create basic front/back cards instead of image occlusion |
| `--no-cache` |:| `False` | Skip the cache for this run (does not clear existing cache) |
| `--config PATH` | `-c` | auto | Path to a custom config file |

## Config management

These flags run their action and exit immediately — they do not process images.

| Flag | Description |
|------|-------------|
| `--init-config` | Copy the default config to `~/.config/niobium/config.yaml` |
| `--edit-config` | Open the config directory in the system file manager |
| `--clear-cache` | Delete all entries from the SQLite processing cache and exit |

## Config-managed flags (advanced)

These flags are accepted by the CLI but hidden from `--help` because they are easier to set persistently in your [config file](docs/reference/configuration.md). They can always be passed on the command line to override the config for a single run.

| Flag | Short | Config key | Description |
|------|-------|------------|-------------|
| `--merge-rects` | `-m` | `merge.enabled` | Merge nearby OCR bounding boxes |
| `--merge-lim-x N` | `-mx` | `merge.limit_x` | Horizontal merge threshold (pixels) |
| `--merge-lim-y N` | `-my` | `merge.limit_y` | Vertical merge threshold (pixels) |
| `--langs LANGS` | `-l` | `langs` | Comma-separated OCR language codes |
| `--gpu N` | `-g` | `gpu` | GPU index (`-1` for CPU) |

## Smart mode behavior

`--smart` behaves differently depending on the input and flags:

| Input + flags | Behavior | Card types |
|---|---|---|
| `-i` or `-dir` with `--smart` | [Smart Filtering](docs/ai/smart-filtering.md) — OCR runs first, Claude filters regions | Image occlusion only |
| `-i` or `-dir` with `--smart --generate` | [Smart Generation](docs/ai/smart-generation.md) — Claude sees the full image and generates cards from scratch | Image occlusion, cloze, basic |
| `-pin` with `--smart` (no `--page`) | Smart Filtering applied to images extracted from the PDF | Image occlusion only |
| `-pin --page` with `--smart` | [Smart Generation](docs/ai/smart-generation.md) — Claude sees the full page and generates cards from scratch | Image occlusion, cloze, basic |

When `--smart` is used, Niobium displays a summary panel showing the pipeline, input, output, model, and instructions before processing. This lets you verify the configuration before spending API credits.

## Constraint rules

- `--pdf-img-out` requires `--single-pdf` as the input.
- `--deck-name` requires Anki to be running with AnkiConnect.
- `--smart` requires an Anthropic API key (see [Smart Filtering](docs/ai/smart-filtering.md)).
- `--generate` requires `--smart`.
- `--generate` with `-pin` requires `--page`.
- `--page` requires `--single-pdf` as the input.
- `--max-cards` and `--card-type` require `--smart` with either `--page` or `--generate`.
- `--basic-type` requires `--directory` as the input.
