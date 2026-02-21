---
title: Contributing
---

# Contributing

## Development setup

```bash
git clone https://github.com/agahkarakuzu/niobium.git
cd niobium
pip install -e .
```

## Project structure

| Path | Purpose |
|------|---------|
| `anki_niobium/cli.py` | CLI entry point:argument parsing, banner display |
| `anki_niobium/io.py` | Core `niobium` class:OCR, merging, filtering, AnkiConnect, APKG export, PDF extraction |
| `anki_niobium/llm.py` | Claude Vision integration:`smart_filter_results()` |
| `anki_niobium/cache.py` | SQLite cache for processed images and Claude responses |
| `anki_niobium/default_config.json` | Bundled default configuration |
| `docs/` | MyST documentation source |
| `myst.yml` | MyST project configuration |

## Smoke test

```bash
# Verify CLI is available
niobium -h

# Verify import
python -c "from anki_niobium.cli import main; print('OK')"
```

## Building documentation locally

```bash
npm install -g mystmd
myst build --html
# Open ./_build/html/index.html in a browser
```

## Submitting changes

1. Open an issue to discuss the change.
2. Fork the repository and create a feature branch.
3. Submit a pull request against the `main` branch.
