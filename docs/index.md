---
title: Niobium (Nb41) ANKI
---

:::{image} logo.png
:::

**Putting AI back in [Anki](https://apps.ankiweb.net/). Because making flashcards by hand was never high-yield.**

::::{dropdown} ⚛️ Why Nb41?
:color: info

Nb41 is [niobium](https://en.wikipedia.org/wiki/Niobium): element 41 on the periodic table. A stealthy gray metal that is absurdly strong, feather-light, and allergic to corrosion. Mostly mined in Brazil and Canada, it moonlights in super-alloys for jet engines and superconducting MRI magnets. It even hides in the capacitors inside your phone and laptop.

This tool was built by an MRI scientist who kept watching a med student named Nadia spend hours manually creating anatomy flashcards. That's where the backronym comes from: **N**adia's **I**mage **O**cclusion **B**ooster **I**s **U**n**M**anned. 

It grew from a quick OCR script into a full pipeline with AI-powered filtering, PDF support, and offline export. The name stuck, and so did the element: niobium is essential to the superconducting magnets inside every MRI scanner.

:::{image} https://cdn.britannica.com/59/22359-050-715B20E2/Niobium-niobium-symbol-square-Nb-properties-some.jpg
:::
::::

:::{card}
Niobium is a free, open-source CLI that turns your lecture slides, textbook screenshots, and PDFs into image occlusion flashcards (and more) automatically. 
:::

Point it at an image and it detects every label, term, and annotation via OCR. Turn on `--smart` mode and Claude Vision steps in: filtering noise, correcting OCR mistakes, and writing study hints that actually help you recall. 

::::{grid} 1 2 2 3

:::{grid-item-card} 🧿 OCR + AI Vision
EasyOCR finds every label. Claude Vision decides what's worth studying and fixes the mistakes OCR missed.
:::

:::{grid-item-card} ⭐️ Anki Native
Push cards to a live Anki deck via AnkiConnect, or export a portable `.apkg` without Anki running.
:::

:::{grid-item-card} 🧵 Tailored to Your Needs
Tell the AI what you're studying (pharmacology, histology, pathology, USMLE prep) and it adapts its hints and corrections to match.
:::

:::{grid-item-card} 📄 PDF Pipeline
Extract images from lecture PDFs and turn them into flashcards in one step. Or extract first, review, then process.
:::

:::{grid-item-card} 🗃️ Smart Caching
Already processed a folder of 50 images? Add 10 more and only the new ones get processed. Claude API responses are cached too.
:::

:::{grid-item-card} 🔓 Free & Open Source
GPL-3.0 licensed. No accounts, no subscriptions, no lock-in. Bring your own API key for Smart mode.
:::
::::

## Key features

- **OCR-powered occlusion**: text detection via [EasyOCR](https://github.com/JaidedAI/EasyOCR) with bounding box merging
- **Smart filtering**: Claude Vision analyzes images semantically, corrects OCR errors, and generates study hints (`--smart`)
- **Live push to Anki**: create decks and push notes in real time via [AnkiConnect](https://foosoft.net/projects/anki-connect/)
- **Offline `.apkg` export**: generate importable Anki packages without running Anki
- **PDF pipeline**: extract images from PDFs and process them directly

## Navigation

- New to Niobium? Start with [Installation](docs/installation.md) then [Quickstart](docs/quickstart.md).
- Looking for a specific flag? See the [CLI Reference](docs/cli-reference.md).
- Want AI-powered filtering? Read about [Smart Filtering](docs/smart-filtering.md).
- Need to tune OCR behaviour? Check [Configuration](docs/configuration.md).

:::{card} Give Niobium a star on GitHub
:link: https://github.com/agahkarakuzu/niobium

If you find this tool useful, please give the repo a star.
:::