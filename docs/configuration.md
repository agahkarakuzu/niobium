---
title: Configuration
---

# Configuration

Niobium uses a JSON config file to control OCR filtering behaviour. Without any configuration, the bundled default is used automatically.

## Quick setup

```bash
# Create user config from the bundled default
niobium --init-config

# Open the config directory in your file manager
niobium --edit-config
```

The user config lives at `~/.config/niobium/config.json`.

## Config resolution order

When Niobium starts, it looks for a config file in this priority order:

1. `--config path/to/config.json` passed on the command line (highest priority)
2. `~/.config/niobium/config.json` (user-level config)
3. The bundled `default_config.json` inside the package (lowest priority)

Niobium prints the path of the config it is using at startup.

## Full config reference

```json
{
    "langs": "en",
    "gpu": -1,
    "qc": false,
    "merge": {
        "enabled": true,
        "limit_x": 10,
        "limit_y": 10
    },
    "exclude": {
        "exact": ["A", "B", "Figure 1"],
        "regex": ["(Figure|Fig\\.|Fig\\:)\\s+(\\d+[-\\w]*).*"]
    },
    "extra": [
        {"Ductus deferens": "Ductus deferens a.k.a <span style=\"color:red;\">Vas deferens</span>"}
    ],
    "llm": {
        "api_key": null,
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "temperature": 0.2,
        "instructions": null
    }
}
```

### `langs`

Comma-separated [EasyOCR language codes](https://www.jaided.ai/easyocr/). Default: `"en"`. Example for English and French: `"en,fr"`.

### `gpu`

GPU device index for EasyOCR. Use `-1` (default) to run on CPU. Use `0` for the first GPU.

### `qc`

Save quality-control images with OCR bounding boxes drawn on them. Default: `false`. When enabled, debug images are saved to a `niobium-io/` subdirectory next to the processed images.

### `merge`

Controls whether nearby OCR bounding boxes are merged before creating occlusions.

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `true` | Enable/disable box merging |
| `limit_x` | `10` | Horizontal proximity threshold in pixels |
| `limit_y` | `10` | Vertical proximity threshold in pixels |

Increase `limit_x` and `limit_y` if OCR produces too many fragmented boxes. Decrease them if unrelated labels are being merged together.

### `exclude`

Filtering rules applied to OCR text before creating occlusions.

| Key | Description |
|-----|-------------|
| `exact` | Case-insensitive exact string matches to discard |
| `regex` | Python regex patterns; matching text is discarded |

:::{tip}
Use `exclude.exact` for fixed labels ("A", "B", system headings). Use `exclude.regex` for patterns like figure captions that follow a predictable format.
:::

### `extra`

A list of `{"key": "html_value"}` objects. When OCR detects text matching a key (case-insensitive), the HTML value is appended to the card's Back Extra field.

```json
"extra": [
    {"Mitral valve": "Also called the <b>bicuspid valve</b>; left heart only"}
]
```

### `llm`

Controls [Smart Filtering](docs/smart-filtering.md) behaviour.

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | `null` | Anthropic API key (falls back to `ANTHROPIC_API_KEY` env var) |
| `model` | `"claude-sonnet-4-6"` | Claude model identifier |
| `max_tokens` | `1024` | Maximum tokens in Claude's response |
| `temperature` | `0.2` | Response variability (lower = more consistent) |
| `instructions` | `null` | Custom instructions appended to the built-in prompt |

See the [Smart Filtering](docs/smart-filtering.md) page for details on `instructions` examples and API key setup.

## CLI overrides

CLI flags always take priority over config values. For example:

```bash
# Config says langs="en", but this run uses French too
niobium --directory ./slides --deck-name Anatomy --langs en,fr
```

The flags `--merge-rects`, `--merge-lim-x`, `--merge-lim-y`, `--langs`, and `--gpu` are hidden from `--help` since they are config-managed, but they are always accepted on the command line.
