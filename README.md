## NIOBIUM: Nadia's Image Occlusion Booster Is UnManned

NIOBIUM is a small CLI tool for extracting text and image-occlusion-style notes from images and PDFs, and for preparing Anki-compatible outputs (via AnkiConnect or by creating an .apkg). This README shows common usages and examples for the command-line interface.

### Trivia: What the actual heck is niobium?

Niobium is a stealthy gray metal that is absurdly strong, feather‑light and allergic to corrosion. Mostly mined in Brazil and Canada, it moonlights in super‑alloys for jet engines and superconducting MRI magnets. It even hides in the capacitors inside your phone and laptop. 

So next time you're on a flight, fiddling with your phone on the way to an MRI conference, tip your hat to niobium, OR just give this repo a ⭐️.


## Requirements

- Python 3.8+
- Install runtime requirements from the repository:

```bash
pip install -r requirements.txt
```

## Quick overview

The main entry point is the `niobium.py` script. It exposes a few mutually-exclusive input modes and a few mutually-exclusive output modes.

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

Run `python niobium.py -h` to see the help text with the current arguments.

## Examples

Below are some concrete example commands (assumes you're in the project root and using zsh/bash):

1) ⭐️ Run OCR and push image-occlusion notes to an Anki deck (via AnkiConnect)

This processes all images under a directory and pushes notes to the Anki deck named `MyStudyDeck`.

```bash
python niobium.py --directory /absolute/path/to/images --deck-name MyStudyDeck
```

Notes:
- You may specify a deck name that doesn't yet exist; you'll be prompted to create it.
- Anki must be running with the AnkiConnect add-on enabled.
- The tool will detect text and create image-occlusion notes from detected regions.

2) Extract images from a single PDF

This extracts embedded images from `lecture.pdf` into `./out_images`.

```bash
python niobium.py --single-pdf /absolute/path/to/lecture.pdf --pdf-img-out /absolute/path/to/out_images
```

Important: `--single-pdf` is required when using `--pdf-img-out`.


3) Produce an `.apkg` file (offline export, **NOT TESTED**)

This processes a directory and writes an `.apkg` bundle suitable for import into Anki without requiring AnkiConnect at runtime.

```bash
python niobium.py --directory /absolute/path/to/images --apkg-out /absolute/path/to/output_dir
```

Optional: include the Image Occlusion model id if you want the built-in model referenced in the package:

```bash
python niobium.py --directory /absolute/path/to/images --apkg-out /absolute/path/to/output_dir --io-model-id 12345
```

4) Create basic (front/back) Anki cards instead of image-occlusion notes

```bash
python niobium.py --directory /absolute/path/to/images --deck-name MyStudyDeck --basic-type True
```

This comes in handy when you have a bunch of images in a folder (may be extracted from a PDF, see (2) above), and would like to create Q&A for each one of them. 

5) Tweak rectangle merging and OCR languages

If bounding boxes are too fragmented, increase the merge thresholds. To OCR multiple languages, provide a comma-separated list.

```bash
python niobium.py --directory /absolute/path/to/images --deck-name MyStudyDeck --merge-lim-x 20 --merge-lim-y 20 --langs en,fr
```

Note: Rectangle merging and other heuristics are experimental. Nearby occlusion boxes may be merged unintentionally, or distinct boxes may remain separate. Adjust --merge-lim-x/--merge-lim-y or disable merging with --merge-rects to change the behavior.

If you come up with a more robust approach to this, feel free to send a PR!

6) GPU usage

Pass `--gpu 0` to attempt to use GPU 0. The default `-1` runs on CPU.

```bash
python niobium.py --directory /abs/path/to/images --deck-name MyStudyDeck --gpu 0
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

- Run `python niobium.py -h` to inspect arguments.
- The code lives in the `niobium/` package; `niobium/io.py` contains I/O helpers.

## Contributing

If you'd like to contribute, open an issue or submit a pull request. Add tests where practical.