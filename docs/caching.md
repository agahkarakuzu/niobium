---
title: Caching
---

# Caching

Niobium maintains a SQLite database at `~/.config/niobium/cache.db` to avoid reprocessing the same images across runs.

## What is cached

### Processed images

When an image is successfully converted into Anki cards, its SHA-256 content hash is stored in the `processed` table. On the next run, if the same file content is encountered in a batch, Niobium skips it.

Content-based hashing means the cache is tied to image content, not filenames. Renaming a file does not cause reprocessing. Changing the image content causes it to be treated as new.

### Claude responses (Smart mode)

When `--smart` is used, Claude's JSON response for each image is stored in the `claude_cache` table. The cache key is derived from:

- The image content hash
- The OCR text list
- The model name
- The `instructions` string from config

A cached response is reused only when all four components are identical. Changing the model or instructions triggers a fresh API call.

## Cache management

### Clear the cache

```bash
niobium --clear-cache
```

This prints statistics (how many entries are in each table) and then deletes everything.

:::{warning}
`--clear-cache` deletes all entries from both cache tables. This cannot be undone. On the next run, all images will be reprocessed.
:::

### Bypass the cache for one run

```bash
niobium --directory /path/to/images --apkg-out ./output --no-cache
```

`--no-cache` skips cache lookups but still writes results to the cache. This is useful when you want to force reprocessing without losing the cache for other runs.

## Cache location

```
~/.config/niobium/cache.db
```

The database is a standard SQLite3 file and can be inspected directly:

```bash
sqlite3 ~/.config/niobium/cache.db ".tables"
sqlite3 ~/.config/niobium/cache.db "SELECT COUNT(*) FROM processed;"
sqlite3 ~/.config/niobium/cache.db "SELECT COUNT(*) FROM claude_cache;"
```

## How it works in practice

1. Run Niobium on a directory of 50 images:all 50 are processed
2. Add 10 new images to the same directory and run again:only the 10 new images are processed
3. Run with `--smart`:Claude is called for each image, responses are cached
4. Run the same `--smart` command again:cached Claude responses are used, no API calls
5. Change `instructions` in your config:cache miss for Claude, fresh API calls (but images still skip OCR if already processed)
