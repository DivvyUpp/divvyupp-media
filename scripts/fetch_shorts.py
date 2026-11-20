#!/usr/bin/env python3
"""Pull recent Shorts for each YouTube channel in research/watchlist.csv and flag outliers.

Usage: python3 scripts/fetch_shorts.py [--days 90] [--max 50] [--out research/shorts-<date>.csv]
Needs env YOUTUBE_API_KEY (YouTube Data API v3) and www.googleapis.com allowed. Never commit the key.

For each channel with a YouTube handle: take its last --max uploads, keep videos of 180 s or less (Shorts),
compute the median views of those, and mark each Short published in the last --days with views / median.
Outlier = 3x or more (the proof bar in runs/research.md).
"""
import argparse, csv, datetime as dt, json, os, re, statistics, sys, urllib.parse, urllib.request

API = "https://www.googleapis.com/youtube/v3/"


def get(endpoint, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def seconds(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def channel(handle):
    h = handle if handle.startswith("@") else "@" + handle
    items = get("channels", part="contentDetails,snippet,statistics", forHandle=h).get("items", [])
    return items[0] if items else None


def uploads(playlist, n):
    ids, token = [], None
    while len(ids) < n:
        p = dict(part="contentDetails", playlistId=playlist, maxResults=min(50, n - len(ids)))
        if token:
            p["pageToken"] = token
        res = get("playlistItems", **p)
        ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        token = res.get("nextPageToken")
        if not token:
            break
    return ids


def videos(ids):
    out = []
    for i in range(0, len(ids), 50):
        res = get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        out += res.get("items", [])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max", type=int, default=50)
    ap.add_argument("--watchlist", default="research/watchlist.csv")
    ap.add_argument("--out", default=f"research/shorts-{dt.date.today()}.csv")
    a = ap.parse_args()
    if not os.environ.get("YOUTUBE_API_KEY"):
        sys.exit("YOUTUBE_API_KEY is not set")
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    rows = []
    for w in csv.DictReader(open(a.watchlist)):
        if "youtube" not in (w.get("platform") or "").lower() or not w.get("handle"):
            continue
        try:
            ch = channel(w["handle"])
        except Exception as e:  # keep going; report the channel
            print(f"{w['account']}: error {e}", file=sys.stderr)
            continue
        if not ch:
            print(f"{w['account']}: handle {w['handle']} not found", file=sys.stderr)
            continue
        vids = videos(uploads(ch["contentDetails"]["relatedPlaylists"]["uploads"], a.max))
        shorts = [v for v in vids if (seconds(v["contentDetails"].get("duration")) or 999) <= 180]
        views = [int(v["statistics"].get("viewCount", 0)) for v in shorts]
        if len(views) < 5:
            print(f"{w['account']}: only {len(views)} Shorts in last {a.max} uploads, skipped", file=sys.stderr)
            continue
        med = statistics.median(views)
        for v in shorts:
            pub = dt.datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
            if pub < since:
                continue
            n = int(v["statistics"].get("viewCount", 0))
            rows.append(dict(list=w.get("list", ""), account=w["account"], handle=w["handle"],
                             published=pub.date().isoformat(), title=v["snippet"]["title"],
                             views=n, likes=v["statistics"].get("likeCount", ""),
                             comments=v["statistics"].get("commentCount", ""),
                             channel_median=int(med), multiple=round(n / med, 1) if med else "",
                             outlier="yes" if med and n >= 3 * med else "",
                             url=f"https://www.youtube.com/shorts/{v['id']}"))
        print(f"{w['account']}: {len(shorts)} Shorts, median {int(med):,}, "
              f"{sum(1 for r in rows if r['account'] == w['account'] and r['outlier'])} outliers in {a.days}d",
              file=sys.stderr)
    rows.sort(key=lambda r: -(r["multiple"] or 0))
    if rows:
        with open(a.out, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"wrote {len(rows)} rows to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
