# bsky-autopsy

Forensic analysis of any public Bluesky account. Posting patterns, vocabulary fingerprints, circadian heatmap, engagement stats.

## Usage

**Step 1 — fetch posts**
```bash
python fetch_posts.py @handle.bsky.social
# options:
#   --days 90       look-back window (default: 90)
#   --max 10000     post cap (default: 10000)
#   --out scan.json output file (default: scan.json)
```

This writes `scan.json` into the same folder.

**Step 2 — view the analysis**

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
  "posts":        [ { "uri", "createdAt", "text", "replyParentUri", "likeCount", "repostCount" } ],
  "didHandleMap": { "did:plc:...": "handle.bsky.social" },
  "scannedAt":    "2025-01-01T00:00:00+00:00",
  "windowDays":   90
}
```
