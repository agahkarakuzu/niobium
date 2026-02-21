---
title: Troubleshooting
---

# Troubleshooting

## AnkiConnect errors

**Symptom:** Connection error when trying to push cards.

**Cause:** Anki is not running, or AnkiConnect is not installed.

**Fix:**
1. Open Anki.
2. Confirm AnkiConnect is installed (Tools → Add-ons).
3. Verify it is listening: open `http://localhost:8765` in a browser.

## Poor OCR quality

**Symptom:** Incorrect text, garbled labels, or missed regions.

**Fixes:**
- Add the correct language code: `--langs en,es` for Spanish images.
- Use `--smart` to let Claude correct OCR errors automatically.
- Ensure the source image is high resolution:OCR quality drops significantly on low-res images.

## Too many small occlusion boxes

**Symptom:** Every word becomes a separate occlusion; boxes are not grouped.

**Fix:** Increase merge thresholds in your config or via CLI:

```bash
niobium --directory ./images --deck-name MyDeck --merge-lim-x 20 --merge-lim-y 20
```

Or set higher values in `config.json`:

```json
"merge": {
    "enabled": true,
    "limit_x": 20,
    "limit_y": 20
}
```

## Smart mode falls back to rule-based filtering

**Symptom:** Niobium prints "Falling back to rule-based filtering."

| Cause | Fix |
|-------|-----|
| No API key | Set `ANTHROPIC_API_KEY` env var or add `api_key` to `llm` config |
| API error or timeout | Check your network; the run completes using rule-based filtering |
| Malformed Claude response | Usually transient; retry the run |

## No images extracted from PDF

**Symptom:** Zero images extracted from a PDF.

**Cause:** The PDF pages contain only vector graphics or text rendered as outlines:not embedded raster images.

**Fix:** Convert PDF pages to raster images using an external tool (e.g., `pdftoppm`) and then use `--directory` mode.

## Cache not working

**Symptom:** Images that were already processed are being reprocessed.

**Possible causes:**
- `--no-cache` is set on the command line
- The image file was modified (changes its content hash)
- The cache was cleared with `--clear-cache`

**Fix:** Remove `--no-cache` if present. If the file content changed, Niobium correctly treats it as a new image.

## EasyOCR first-run download

**Symptom:** First run takes several minutes before processing starts.

**Cause:** EasyOCR downloads PyTorch and language model weights on first use.

**Fix:** This is expected. Subsequent runs use the cached models and start much faster.
