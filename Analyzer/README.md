# bsky-autopsy

Forensic analysis of any public Bluesky account. Posting patterns, vocabulary fingerprints, circadian heatmap, engagement stats.

## Usage

**Step 1 — fetch posts**
```bash
python fetch_posts.py @handle.bsky.social
# options:
#   --days 0        look-back window in days, 0 = no limit (default: 0)
#   --max 0         post cap, 0 = no limit (default: 0)
#   --out scan.json output file (default: scan.json)
```

This writes `scan.json` into the same folder.

**Step 2 — score sentiment (optional)**
```bash
pip install vaderSentiment
python analyze_sentiment.py --in scan.json
```

Adds a `sentiment` field to each post and a `sentimentSummary` block to the file. Prints the most positive/negative posts to stdout.

**Step 3 — view the analysis**

Serve the folder with any static file server and open `index.html`:
```bash
python -m http.server 8080
# → http://localhost:8080/Analyzer/
```

`index.html` will auto-load `scan.json` on startup. You can also type a handle into the scan bar to fetch live (no `scan.json` needed for that).

## scan.json shape

```json
{
  "profile":      { ...AppView profile fields... },
  "posts":        [ { "uri", "createdAt", "text", "replyParentUri", "likeCount", "repostCount", "sentiment?" } ],
  "didHandleMap": { "did:plc:...": "handle.bsky.social" },
  "scannedAt":    "2025-01-01T00:00:00+00:00",
  "windowDays":   0,
  "sentimentSummary?": { "scored", "avgCompound", "positive", "neutral", "negative" }
}
```
