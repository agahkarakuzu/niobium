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

## Output (mutually exclusive, one required)

| Flag | Short | Description |
|------|-------|-------------|
| `--deck-name NAME` | `-deck` | Anki deck to push notes into (requires AnkiConnect) |
| `--pdf-img-out PATH` | `-pout` | Directory to save images extracted from a PDF |
| `--apkg-out PATH` | `-apkg` | Directory to write the exported `.apkg` file |

## Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--smart` |:| `False` | Enable Claude Vision smart filtering |
| `--add-header` | `-hdr` | `False` | Add the filename as a card header |
| `--basic-type` | `-basic` | `False` | Create basic front/back cards instead of image occlusion |
| `--config PATH` | `-c` | auto | Path to a custom `config.json` |

## Config management

These flags run their action and exit immediately:they do not process images.

| Flag | Description |
|------|-------------|
| `--init-config` | Copy the default config to `~/.config/niobium/config.json` |
| `--edit-config` | Open the config directory in the system file manager |
| `--clear-cache` | Delete all entries from the SQLite processing cache and exit |

## Config-managed flags (advanced)

These flags are accepted by the CLI but hidden from `--help` because they are easier to set persistently in your [config file](docs/configuration.md). They can always be passed on the command line to override the config for a single run.

| Flag | Short | Config key | Description |
|------|-------|------------|-------------|
| `--merge-rects` | `-m` | `merge.enabled` | Merge nearby OCR bounding boxes |
| `--merge-lim-x N` | `-mx` | `merge.limit_x` | Horizontal merge threshold (pixels) |
| `--merge-lim-y N` | `-my` | `merge.limit_y` | Vertical merge threshold (pixels) |
| `--langs LANGS` | `-l` | `langs` | Comma-separated OCR language codes |
| `--gpu N` | `-g` | `gpu` | GPU index (`-1` for CPU) |
| `--no-cache` |:|:| Ignore the processing cache for this run |

## Constraint rules

- `--pdf-img-out` requires `--single-pdf` as the input.
- `--deck-name` requires Anki to be running with AnkiConnect.
- `--smart` requires an Anthropic API key (see [Smart Filtering](docs/smart-filtering.md)).
- `--basic-type` requires `--directory` as the input.
