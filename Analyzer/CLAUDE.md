# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Fetch posts for a handle (writes scan.json by default; --days 0 / --max 0 = unlimited)
python fetch_posts.py @handle.bsky.social
python fetch_posts.py handle.bsky.social --days 180 --max 5000 --out data.json

# Score sentiment on an existing scan file (adds per-post `sentiment` + top-level `sentimentSummary`)
pip install vaderSentiment
python analyze_sentiment.py --in scan.json

# View the analysis UI — must be served, file:// will break the fetch('scan.json')
python -m http.server 8080
# → http://localhost:8080/Analyzer/
```

No test suite, no build step. `vaderSentiment` is the only non-stdlib Python dep; everything else is standard library or in-browser JS.

## Architecture

Three loosely-coupled pieces sharing one JSON schema:

1. **`fetch_posts.py`** — CLI scraper. Two-hop AT Protocol walk: AppView (`public.api.bsky.app`) for the profile and recent engagement, then resolve the user's PDS via `plc.directory` and page `com.atproto.repo.listRecords` for the full post history. Engagement counts only populate for posts that appear in the AppView's latest-100 author feed — older posts are stored with `likeCount: 0` even if they originally had engagement.

2. **`analyze_sentiment.py`** — Optional post-processing pass. Loads a scan file, runs VADER over each post's `text`, writes `sentiment: {compound, pos, neu, neg, label}` back onto each post and a `sentimentSummary` at the top level. Reads/writes the same file by default.

3. **`index.html`** — Single-file browser analyzer. On load it tries `fetch('scan.json')`; if that fails it falls back to seeded mock data and waits for the user to type a handle into the scan bar, at which point it re-runs the same AT Protocol walk as `fetch_posts.py` but directly from the browser. All rendering (heatmap, vocab, posting stats, engagement, interaction web, day drilldown) keys off the `posts` array plus `didHandleMap`.

The JSON contract between all three pieces is documented in [README.md](README.md) under "scan.json shape". If you change field names in one place, update all three.

## Gotchas

- **`plc.directory` is browser-hostile.** The Python CLI uses it to resolve DID→PDS and it works fine. Inside `index.html`, reverse DID→handle lookups intentionally go through AppView's `app.bsky.actor.getProfiles` instead because `plc.directory` fails silently in browsers. Don't "simplify" the browser code by switching it back.
- **File name drift.** `fetch_posts.py` defaults to `scan.json`, `index.html` auto-loads `scan.json`, but the working artifact in this folder is `data.json`. If auto-load stops working, check this first — either rename, symlink, or pass `--out scan.json`.
- **`--days 0` / `--max 0` mean unlimited** in `fetch_posts.py`. The loop short-circuits the cutoff/cap checks when either is non-positive.
- **Shared stylesheet.** `index.html` links `../styles.css` from the parent `TCG-collection/` site. Visual changes may bleed into other pages — scope new CSS inside the `<style>` block in `index.html` unless the change is intentionally site-wide.

Before telling me a fix is done, actually execute it (or compile-check it) and paste the output. If you can't run it, list the exact manual test I should perform.