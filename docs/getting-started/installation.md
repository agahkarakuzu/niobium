---
title: Installation
---

# Installation

## Python package

### pip

```bash
pip install nb41
```

### uv (faster alternative)

```bash
uv pip install nb41
```

### From source

```bash
git clone https://github.com/agahkarakuzu/niobium.git
cd niobium
pip install -e .
```

## Requirements

- Python 3.8 or higher
- All Python dependencies are installed automatically

:::{note}
EasyOCR downloads PyTorch and language model weights on first use. First startup may take a few minutes while these are cached locally.
:::

## Anki setup (for live push)

To push cards directly into a running Anki instance:

1. Install [AnkiConnect](https://ankiweb.net/shared/info/2055492159) from the Anki add-on browser.
2. Restart Anki.
3. Confirm AnkiConnect is active at `http://localhost:8765`.

:::{tip}
Offline `.apkg` export does not require Anki or AnkiConnect. See [APKG Export](docs/core/apkg-export.md) for details.
:::
