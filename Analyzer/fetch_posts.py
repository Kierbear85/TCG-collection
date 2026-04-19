#!/usr/bin/env python3
"""
Fetch posts from a Bluesky PDS and save to scan.json (or a custom output file).
Usage:
    python fetch_posts.py @handle.bsky.social
    python fetch_posts.py handle.bsky.social --days 180 --max 5000 --out data.json
"""

import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone

APPVIEW = 'https://public.api.bsky.app/xrpc'
PLC_DIR = 'https://plc.directory'


def fetch_json(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_profile(handle):
    url = f'{APPVIEW}/app.bsky.actor.getProfile?actor={urllib.parse.quote(handle)}'
    return fetch_json(url)


def resolve_pds(did):
    if did.startswith('did:web:'):
        return 'https://' + did[len('did:web:'):]
    doc = fetch_json(f'{PLC_DIR}/{urllib.parse.quote(did)}')
    for svc in (doc.get('service') or []):
        if svc.get('type') == 'AtprotoPersonalDataServer':
            return svc['serviceEndpoint'].rstrip('/')
    raise ValueError('no PDS found in DID document')


def list_pds_posts(pds, did, window_days, max_posts):
    records = []
    unlimited_days = window_days is None or window_days <= 0
    unlimited_max = max_posts is None or max_posts <= 0
    cutoff_ms = None if unlimited_days else (datetime.now(timezone.utc).timestamp() - window_days * 86400) * 1000
    cursor = None

    while unlimited_max or len(records) < max_posts:
        params = {'repo': did, 'collection': 'app.bsky.feed.post', 'limit': '100'}
        if cursor:
            params['cursor'] = cursor
        url = f'{pds}/xrpc/com.atproto.repo.listRecords?{urllib.parse.urlencode(params)}'
        try:
            body = fetch_json(url)
        except Exception as e:
            print(f'\n  PDS request failed: {e}')
            break

        batch = body.get('records', [])
        if not batch:
            break

        done = False
        for rec in batch:
            created_at = rec.get('value', {}).get('createdAt', '')
            try:
                ts = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp() * 1000
            except Exception:
                done = True
                break
            if cutoff_ms is not None and ts < cutoff_ms:
                done = True
                break
            records.append(rec)
            if not unlimited_max and len(records) >= max_posts:
                done = True
                break

        print(f'  {len(records)} records fetched...', end='\r', flush=True)
        if done or not body.get('cursor'):
            break
        cursor = body['cursor']

    print()
    return records


def get_engagement_map(handle):
    url = f'{APPVIEW}/app.bsky.feed.getAuthorFeed?actor={urllib.parse.quote(handle)}&limit=100'
    try:
        body = fetch_json(url)
    except Exception:
        return {}
    result = {}
    for item in body.get('feed', []):
        post = item.get('post', {})
        uri = post.get('uri')
        if uri:
            result[uri] = {
                'likeCount': post.get('likeCount', 0),
                'repostCount': post.get('repostCount', 0),
            }
    return result


def resolve_did_handles(dids):
    result = {}
    for i in range(0, len(dids), 25):
        chunk = dids[i:i + 25]
        params = '&'.join(f'actors[]={urllib.parse.quote(d)}' for d in chunk)
        url = f'{APPVIEW}/app.bsky.actor.getProfiles?{params}'
        try:
            body = fetch_json(url)
            for p in body.get('profiles', []):
                result[p['did']] = p['handle']
        except Exception:
            pass
    return result


def did_from_uri(uri):
    if not uri:
        return None
    parts = uri.split('/')
    return parts[2] if len(parts) > 2 else None


def normalize_posts(records, engagement_map):
    posts = []
    for rec in records:
        val = rec.get('value', {})
        uri = rec['uri']
        eng = engagement_map.get(uri, {})
        reply = val.get('reply') or {}
        reply_parent = (reply.get('parent') or {}).get('uri')
        posts.append({
            'uri': uri,
            'createdAt': val.get('createdAt', ''),
            'text': val.get('text', ''),
            'replyParentUri': reply_parent,
            'likeCount': eng.get('likeCount', 0),
            'repostCount': eng.get('repostCount', 0),
        })
    return posts


def main():
    parser = argparse.ArgumentParser(description='Fetch Bluesky posts and save to scan.json')
    parser.add_argument('handle', help='Bluesky handle (e.g. @user.bsky.social or user.bsky.social)')
    parser.add_argument('--days', type=int, default=0, help='Days to look back (0 = no limit, default: 0)')
    parser.add_argument('--max', type=int, default=0, help='Max posts to fetch (0 = no limit, default: 0)')
    parser.add_argument('--out', default='scan.json', help='Output file (default: scan.json)')
    args = parser.parse_args()

    handle = args.handle.lstrip('@')

    print(f'[1/5] Fetching profile for {handle}...')
    try:
        profile = get_profile(handle)
    except Exception as e:
        print(f'  Error: {e}', file=sys.stderr)
        sys.exit(1)
    did = profile['did']
    print(f'      DID: {did}')
    print(f'      Display name: {profile.get("displayName") or handle}')

    print(f'[2/5] Resolving PDS...')
    try:
        pds = resolve_pds(did)
    except Exception as e:
        print(f'  Error: {e}', file=sys.stderr)
        sys.exit(1)
    print(f'      PDS: {pds}')

    print(f'[3/5] Fetching engagement data (latest 100 posts)...')
    engagement_map = get_engagement_map(profile['handle'])
    print(f'      {len(engagement_map)} posts with engagement data')

    days_desc = 'all time' if args.days <= 0 else f'last {args.days} days'
    max_desc = 'unlimited' if args.max <= 0 else f'max {args.max}'
    print(f'[4/5] Streaming posts from PDS ({days_desc}, {max_desc})...')
    records = list_pds_posts(pds, did, args.days, args.max)
    posts = normalize_posts(records, engagement_map)
    print(f'      {len(posts)} posts')

    print(f'[5/5] Resolving reply-target handles...')
    did_freq: dict[str, int] = {}
    for p in posts:
        d = did_from_uri(p.get('replyParentUri'))
        if d:
            did_freq[d] = did_freq.get(d, 0) + 1
    top_dids = sorted(did_freq, key=lambda d: did_freq[d], reverse=True)[:25]
    did_handle_map = resolve_did_handles(top_dids)
    print(f'      {len(did_handle_map)} handles resolved')

    scan = {
        'profile': profile,
        'posts': posts,
        'didHandleMap': did_handle_map,
        'scannedAt': datetime.now(timezone.utc).isoformat(),
        'windowDays': args.days,
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(scan, f, ensure_ascii=False, indent=2)

    size_kb = round(len(json.dumps(scan, ensure_ascii=False)) / 1024)
    print(f'\nDone. Saved {len(posts)} posts to {args.out} ({size_kb} KB)')
    print(f'Open index.html in a local server to view the analysis.')


if __name__ == '__main__':
    main()
