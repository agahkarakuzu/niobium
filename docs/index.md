---
title: Niobium (Nb41) ANKI
---

:::{image} logo.png
:::

**Putting AI back in [Anki](https://apps.ankiweb.net/). Because making flashcards by hand was never high-yield.**

::::{dropdown} Why Nb41?
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

Point it at an image and it detects every label, term, and annotation via OCR. Turn on `--smart` mode and Claude AI steps in: filtering noise, correcting OCR mistakes, writing study hints, and even generating cloze and basic cards from scratch.

::::{grid} 1 2 2 3

:::{grid-item-card} OCR + Image Occlusion
Fully free, no API key needed. EasyOCR finds every label, Niobium turns them into image occlusion flashcards.
:::

:::{grid-item-card} Anki Native
Push cards to a live Anki deck via AnkiConnect, or export a portable `.apkg` without Anki running.
:::

:::{grid-item-card} PDF Pipeline
Extract images from lecture PDFs, select specific pages, and turn them into flashcards in one step.
:::

:::{grid-item-card} AI Smart Filtering
Optional: Claude AI curates OCR results, corrects errors, and adds study hints to your cards.
:::

:::{grid-item-card} AI Card Generation
Optional: Claude sees the full page and generates cloze, basic, and image occlusion cards from scratch.
:::

:::{grid-item-card} Free & Open Source
GPL-3.0 licensed. No accounts, no subscriptions, no lock-in. AI features are optional — bring your own API key.
:::
::::

## Works without AI

Niobium's core features work entirely offline with no API key:

- **OCR-powered image occlusion**: text detection via [EasyOCR](https://github.com/JaidedAI/EasyOCR) with bounding box merging
- **PDF image extraction**: pull embedded images from PDFs, optionally selecting specific pages
- **Live push to Anki**: create decks and push notes in real time via [AnkiConnect](https://foosoft.net/projects/anki-connect/)
- **Offline `.apkg` export**: generate importable Anki packages without running Anki
- **Smart caching**: already processed a folder of 50 images? Add 10 more and only the new ones get processed

See [Core Workflows](docs/core/workflows.md) to get started.

## Optional AI features

Add `--smart` and an Anthropic API key to unlock:

- **Smart Filtering**: Claude curates OCR results, corrects misread text, and generates study hints
- **Smart Generation**: Claude sees the full content and generates cloze, basic, and image occlusion cards from scratch (`--generate` for images, `--page` for PDFs)

See [AI Features Overview](docs/ai/overview.md) for setup, costs, and details.

## Navigation

- New to Niobium? Start with [Installation](docs/getting-started/installation.md) then [Quickstart](docs/getting-started/quickstart.md).
- Want to create cards without AI? See [Core Workflows](docs/core/workflows.md).
- Want AI-powered cards? Read [AI Features Overview](docs/ai/overview.md).
- Looking for a specific flag? See the [CLI Reference](docs/reference/cli.md).
- Need to tune OCR behaviour? Check [Configuration](docs/reference/configuration.md).

:::{card} Give Niobium a star on GitHub
:link: https://github.com/agahkarakuzu/niobium

If you find this tool useful, please give the repo a star.
:::
