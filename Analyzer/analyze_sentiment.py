#!/usr/bin/env python3
"""
Score sentiment for every post in a scan JSON file using VADER.
Usage:
    pip install vaderSentiment
    python analyze_sentiment.py                 # reads data.json, writes data.json
    python analyze_sentiment.py --in scan.json --out scored.json
"""

import sys
import json
import argparse
from statistics import mean

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    print('Missing dependency. Install with:  pip install vaderSentiment', file=sys.stderr)
    sys.exit(1)


def classify(compound):
    if compound >= 0.05:
        return 'positive'
    if compound <= -0.05:
        return 'negative'
    return 'neutral'


def main():
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure:
        reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description='Add VADER sentiment scores to posts in a scan JSON file.')
    parser.add_argument('--in', dest='inp', default='scan.json',
                        help='Input JSON (default: scan.json)')
    parser.add_argument('--out', default=None,
                        help='Output JSON (default: overwrite input)')
    parser.add_argument('--top', type=int, default=5,
                        help='How many top/bottom posts to print (default: 5)')
    args = parser.parse_args()

    out_path = args.out or args.inp

    with open(args.inp, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = data.get('posts', [])
    analyzer = SentimentIntensityAnalyzer()

    scored = 0
    skipped_replies = 0
    for p in posts:
        if p.get('replyParentUri'):
            p['sentiment'] = None
            skipped_replies += 1
            continue
        text = (p.get('text') or '').strip()
        if not text:
            p['sentiment'] = None
            continue
        s = analyzer.polarity_scores(text)
        p['sentiment'] = {
            'compound': s['compound'],
            'pos': s['pos'],
            'neu': s['neu'],
            'neg': s['neg'],
            'label': classify(s['compound']),
        }
        scored += 1

    compounds = [p['sentiment']['compound']
                 for p in posts if p.get('sentiment')]
    labels = [p['sentiment']['label'] for p in posts if p.get('sentiment')]
    summary = {
        'scored': scored,
        'avgCompound': round(mean(compounds), 4) if compounds else 0,
        'positive': labels.count('positive'),
        'neutral': labels.count('neutral'),
        'negative': labels.count('negative'),
    }
    data['sentimentSummary'] = summary

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        f'Scored {scored}/{len(posts)} posts (skipped {skipped_replies} replies). Average compound: {summary["avgCompound"]}')
    print(
        f'  positive: {summary["positive"]}   neutral: {summary["neutral"]}   negative: {summary["negative"]}')

    ranked = sorted(
        (p for p in posts if p.get('sentiment')),
        key=lambda p: p['sentiment']['compound'],
    )
    n = args.top
    if ranked and n > 0:
        print(f'\nMost negative ({min(n, len(ranked))}):')
        for p in ranked[:n]:
            snippet = p['text'].replace('\n', ' ')[:100]
            print(f'  [{p["sentiment"]["compound"]:+.3f}] {snippet}')
        print(f'\nMost positive ({min(n, len(ranked))}):')
        for p in reversed(ranked[-n:]):
            snippet = p['text'].replace('\n', ' ')[:100]
            print(f'  [{p["sentiment"]["compound"]:+.3f}] {snippet}')

    print(f'\nSaved to {out_path}')


if __name__ == '__main__':
    main()
