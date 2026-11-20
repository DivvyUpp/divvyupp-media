#!/usr/bin/env python3
"""Find and vet YouTube channels for research/watchlist.csv against the entry bar in runs/research.md.

Usage: python3 scripts/vet_channels.py --names "Caleb Hammer" "Rachel Cruze" --queries "budgeting tips" ...
Needs env YOUTUBE_API_KEY. Prints one JSON line per channel with the numbers the entry bar uses:
subscribers, country, Shorts posted in the last 90 days, median Shorts views, last Short date.
"""
import argparse, datetime as dt, json, os, re, statistics, sys, urllib.parse, urllib.request

API = "https://www.googleapis.com/youtube/v3/"


def get(endpoint, **p):
    p["key"] = os.environ["YOUTUBE_API_KEY"]
    with urllib.request.urlopen(API + endpoint + "?" + urllib.parse.urlencode(p), timeout=30) as r:
        return json.load(r)


def secs(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 999
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def find(term, n):
    res = get("search", part="snippet", type="channel", q=term, maxResults=n, regionCode="US",
              relevanceLanguage="en")
    return [i["snippet"]["channelId"] for i in res.get("items", [])]


def vet(cid, since):
    ch = get("channels", part="snippet,statistics,contentDetails", id=cid)["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           get("playlistItems", part="contentDetails", playlistId=up, maxResults=50).get("items", [])]
    vids = get("videos", part="snippet,statistics,contentDetails", id=",".join(ids)).get("items", []) if ids else []
    shorts = [v for v in vids if secs(v["contentDetails"].get("duration")) <= 180]
    recent = [v for v in shorts if v["snippet"]["publishedAt"][:10] >= since]
    views = [int(v["statistics"].get("viewCount", 0)) for v in shorts]
    return dict(
        id=cid, title=ch["snippet"]["title"], handle=ch["snippet"].get("customUrl", ""),
        country=ch["snippet"].get("country", ""), subs=int(ch["statistics"].get("subscriberCount", 0) or 0),
        uploads_checked=len(vids), shorts_in_last50=len(shorts), shorts_90d=len(recent),
        median_short_views=int(statistics.median(views)) if views else 0,
        last_short=max((v["snippet"]["publishedAt"][:10] for v in shorts), default=""),
        sample_titles=[v["snippet"]["title"][:70] for v in shorts[:5]],
        url=f"https://www.youtube.com/{ch['snippet'].get('customUrl') or 'channel/' + cid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", nargs="*", default=[])
    ap.add_argument("--queries", nargs="*", default=[])
    ap.add_argument("--per_query", type=int, default=8)
    a = ap.parse_args()
    since = (dt.date.today() - dt.timedelta(days=90)).isoformat()
    seen = set()
    for term, n in [(x, 1) for x in a.names] + [(q, a.per_query) for q in a.queries]:
        try:
            ids = find(term, n)
        except Exception as e:
            print(json.dumps(dict(search=term, error=str(e))), flush=True)
            continue
        for cid in ids:
            if cid in seen:
                continue
            seen.add(cid)
            try:
                r = vet(cid, since)
                r["found_by"] = term
                print(json.dumps(r), flush=True)
            except Exception as e:
                print(json.dumps(dict(id=cid, found_by=term, error=str(e))), flush=True)


if __name__ == "__main__":
    main()
