![PyPI - Version](https://img.shields.io/pypi/v/anki-niobium?style=flat&logo=python&logoColor=white&logoSize=8&labelColor=rgb(255%2C0%2C0)&color=white)

## NIOBIUM: Nadia's Image Occlusion Booster Is UnManned

NIOBIUM is a small CLI tool for extracting text and image-occlusion-style notes from images and PDFs, and for preparing Anki-compatible outputs (via AnkiConnect or by creating an .apkg). This README shows common usages and examples for the command-line interface.

### Trivia: What the actual heck is niobium?

Niobium is a stealthy gray metal that is absurdly strong, feather‑light and allergic to corrosion. Mostly mined in Brazil and Canada, it moonlights in super‑alloys for jet engines and superconducting MRI magnets. It even hides in the capacitors inside your phone and laptop.

So next time you're on a flight, fiddling with your phone on the way to an MRI conference, tip your hat to niobium, OR just give this repo a ⭐️.


## Installation

### Using pip

```bash
pip install anki-niobium
```

### Using uv (faster alternative)

```bash
uv pip install anki-niobium
```

### From source

```bash
git clone https://github.com/agahkarakuzu/niobium.git
cd niobium
pip install -e .
```

## Requirements

- Python 3.8 or higher
- All dependencies are automatically installed with the package

## Quick overview

The main entry point is the `niobium` command. It exposes a few mutually-exclusive input modes and a few mutually-exclusive output modes.

Inputs (one required):
- `-i, --image` — absolute path to a single image file
- `-dir, --directory` — directory containing multiple images
- `-pin, --single-pdf` — absolute path to a single PDF

Outputs (one required):
- `-deck, --deck-name` — name of the Anki deck where notes will be pushed (requires AnkiConnect)
- `-pout, --pdf-img-out` — output directory where images extracted from a PDF will be saved
- `-apkg, --apkg-out` — output directory where a generated `.apkg` will be saved

Other useful flags:
- `-ioid, --io-model-id` — ID of the built-in Image Occlusion model in Anki (optional, used with `--apkg-out`)
- `-m, --merge-rects` — whether to merge nearby detected rectangles (default: True)
- `-mx, --merge-lim-x` — horizontal merging threshold in pixels (default: 10)
- `-my, --merge-lim-y` — vertical merging threshold in pixels (default: 10)
- `-l, --langs` — comma-separated OCR languages (default: `en`)
- `-g, --gpu` — GPU index to use, or `-1` for CPU only (default: -1)
- `-hdr, --add-header` — add filename as a header (default: False)
- `-basic, --basic-type` — create basic Anki cards instead of image-occlusion notes (default: False)
- `-c, --config` — path to a custom config file (see [Configuration](#configuration) below)

Run `niobium -h` to see the help text with the current arguments.

## Configuration

Niobium uses a JSON config file to control how OCR results are filtered before creating Anki notes. Without any configuration, a sensible bundled default is used automatically.

### Getting started

Generate your own config file:

```bash
niobium --init-config
```

This copies the default template to `~/.config/niobium/config.json`. To open it in your editor:

```bash
niobium --edit-config
```

This creates the config if it doesn't exist yet, then opens it with `$EDITOR` (falls back to `vi`).

Niobium will tell you which config file it is using every time it runs.

### Config resolution order

1. `--config path/to/config.json` — explicit path passed via CLI (highest priority)
2. `~/.config/niobium/config.json` — user-level config
3. Bundled default inside the package (lowest priority)

### Config file format

```json
{
    "langs": "en",
    "gpu": -1,
    "merge": {
        "enabled": true,
        "limit_x": 10,
        "limit_y": 10
    },
    "exclude": {
        "exact": ["A", "B", "Reproductive system"],
        "regex": ["(Figure|Fig\\.|Fig\\:)\\s+(\\d+[-\\w]*).*"]
    },
    "extra": [
        {"Ductus deferens": "Ductus deferens is a.k.a <span style=\"color:red;\">Vas deferens</span>"}
    ]
}
```

| Key | What it does |
|-----|-------------|
| `langs` | Comma-separated OCR languages (default: `"en"`). E.g. `"en,fr"` for English and French. |
| `gpu` | GPU index to use for OCR, or `-1` for CPU only (default: `-1`). |
| `merge.enabled` | Whether to merge nearby OCR bounding boxes before creating occlusions (default: `true`). |
| `merge.limit_x` | Horizontal merge threshold in pixels — boxes closer than this are merged (default: `10`). |
| `merge.limit_y` | Vertical merge threshold in pixels — boxes closer than this are merged (default: `10`). |
| `exclude.exact` | OCR text matching any of these strings (case-insensitive) is discarded and won't become an occlusion. Useful for filtering out labels like "A", "B", or section headings that appear in images. |
| `exclude.regex` | OCR text matching any of these regular expressions is discarded. Useful for filtering out figure captions (e.g., "Figure 1", "Fig. 2a"). |
| `extra` | A list of key-value objects. When OCR detects text matching a key (case-insensitive), the corresponding value is appended to the note's "Back Extra" field as HTML. Useful for adding supplementary information to specific terms. |

CLI flags (`--langs`, `--gpu`, `--merge-rects`, `--merge-lim-x`, `--merge-lim-y`) override the config file values when provided.

## Examples

Below are some concrete example commands (assumes you're in the project root and using zsh/bash):

1) ⭐️ Run OCR and push image-occlusion notes to an Anki deck (via AnkiConnect)

This processes all images under a directory and pushes notes to the Anki deck named `MyStudyDeck`.

```bash
niobium --directory /absolute/path/to/images --deck-name MyStudyDeck
```

Notes:
- You may specify a deck name that doesn't yet exist; you'll be prompted to create it.
- Anki must be running with the AnkiConnect add-on enabled.
- The tool will detect text and create image-occlusion notes from detected regions.

2) Extract images from a single PDF

This extracts embedded images from `lecture.pdf` into `./out_images`.

```bash
niobium --single-pdf /absolute/path/to/lecture.pdf --pdf-img-out /absolute/path/to/out_images
```

Important: `--single-pdf` is required when using `--pdf-img-out`.


3) Produce an `.apkg` file (offline export, no AnkiConnect needed)

This processes a directory and writes an `.apkg` bundle suitable for import into Anki without requiring AnkiConnect at runtime. Uses `genanki` under the hood.

```bash
niobium --directory /absolute/path/to/images --apkg-out /absolute/path/to/output_dir
```

You can also use a single image or a PDF as input:

```bash
niobium --image /absolute/path/to/image.png --apkg-out /absolute/path/to/output_dir
niobium --single-pdf /absolute/path/to/lecture.pdf --apkg-out /absolute/path/to/output_dir
```

4) Create basic (front/back) Anki cards instead of image-occlusion notes

```bash
niobium --directory /absolute/path/to/images --deck-name MyStudyDeck --basic-type True
```

This comes in handy when you have a bunch of images in a folder (may be extracted from a PDF, see (2) above), and would like to create Q&A for each one of them. 

5) Tweak rectangle merging and OCR languages

If bounding boxes are too fragmented, increase the merge thresholds. To OCR multiple languages, provide a comma-separated list.

```bash
niobium --directory /absolute/path/to/images --deck-name MyStudyDeck --merge-lim-x 20 --merge-lim-y 20 --langs en,fr
```

Note: Rectangle merging and other heuristics are experimental. Nearby occlusion boxes may be merged unintentionally, or distinct boxes may remain separate. Adjust --merge-lim-x/--merge-lim-y or disable merging with --merge-rects to change the behavior.

If you come up with a more robust approach to this, feel free to send a PR!

6) GPU usage

Pass `--gpu 0` to attempt to use GPU 0. The default `-1` runs on CPU.

```bash
niobium --directory /abs/path/to/images --deck-name MyStudyDeck --gpu 0
```

## Common workflows

- Automatic creation of image-occlusion notes and push to Anki:
  - `--directory` + `--deck-name`  (Anki must be running with anki-connect installed)
  - `--single-pdf` + `--deck-name` (Anki must be running with anki-connect installed)
- Quick extraction from a PDF for manual review:
  - `--single-pdf` + `--pdf-img-out`

## Troubleshooting

- If AnkiConnect calls fail, confirm Anki is running and AnkiConnect is installed and enabled.
- If OCR quality is poor, try adding the proper language code with `--langs` (e.g., `en,es`) and ensure Tesseract language packs are installed.
- If many small boxes are produced, increase `--merge-lim-x`/`--merge-lim-y` or set `--merge-rects False` to disable merging.

## Development

### Setting up for development

```bash
git clone https://github.com/agahkarakuzu/niobium.git
cd niobium
pip install -e .
```

### Running tests

The package includes automated tests that run on each push via GitHub Actions. You can test locally:

```bash
# Test the CLI is available
niobium -h

# Test import
python -c "from niobium.cli import main; print('Import successful')"
```

### Project structure

- `niobium/cli.py` - Main CLI entry point with argument parsing
- `niobium/io.py` - Core I/O helpers and OCR functionality
- `pyproject.toml` - Package configuration and dependencies

## Contributing

If you'd like to contribute, open an issue or submit a pull request.