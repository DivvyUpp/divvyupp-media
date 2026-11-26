#!/usr/bin/env python3
"""Add TikTok and YouTube numbers (from Postproxy) to today's metrics file, plus a combined per-Reel view.

Called by the Metrics pull (runs/metrics.md step 2b) after the Instagram numbers are written. Stdlib only.

Usage:  python3 scripts/fetch_platform_stats.py [--date YYYY-MM-DD] [--days 8]

Env:
  POSTPROXY_API_KEY  required. Bearer token for https://api.postproxy.dev. Never printed.

Writes into metrics/<date>.json (creates it if the Instagram step didn't), leaving every Instagram field as is:
  "tiktok":  {"followers_count", "recorded_at", "videos": [{tiktok_id, queue_id, permalink, posted, views,
              reach, avg_watch_s, total_watch_s, full_watch_rate, duration_s, likes, comments, shares,
              sends_per_1k, recorded_at}]}
  "youtube": {"subscribers", "channel_views_7d", "channel_avg_view_s_7d", "channel_avg_view_pct_7d",
              "channel_minutes_watched_7d", "recorded_at", "videos": [{youtube_id, queue_id, permalink,
              posted, views, likes, comments, recorded_at}]}
  "combined": [{queue_id, hook, posted, instagram_views, tiktok_views, youtube_views, total_views, on}]
Every number is exactly what Postproxy returns; null where it returns nothing. Never estimated. YouTube
per-Short watch time is not available here (only channel-level 7-day figures). TikTok's view count can
lag its watch-time numbers by hours; both are written as returned.

Exit 0 = written, 1 = failed (nothing written; reason on stderr).
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

API = "https://api.postproxy.dev"
PROFILES = {"tiktok": "MZU39X", "youtube": "rOUpVX"}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ET = ZoneInfo("America/New_York")
TIMEOUT_S = 30
PER_PAGE = 100
STATS_BATCH = 50


class Failed(Exception):
    pass


def get(path, key, params=None, opener=urllib.request.urlopen):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with opener(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def recent_posts(platform, key, since, opener):
    """Postproxy posts on this profile (made here or imported) that went live on or after `since` (ET date)."""
    out, page = [], 1
    while True:
        d = get("/api/posts", key, {"profile_id": PROFILES[platform], "per_page": PER_PAGE, "page": page},
                opener)
        rows = d.get("data", [])
        for p in rows:
            live = dt.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ET).date()
            plat = next((x for x in p.get("platforms", []) if x.get("platform") == platform), None)
            if live >= since and plat and plat.get("permalink"):
                out.append({"post_id": p["id"], "posted": live.isoformat(), "permalink": plat["permalink"]})
        if len(rows) < PER_PAGE:
            return out
        page += 1


def latest_stats(post_ids, platform, key, opener):
    latest = {}
    for i in range(0, len(post_ids), STATS_BATCH):
        d = get("/api/posts/stats", key, {"post_ids": ",".join(post_ids[i:i + STATS_BATCH])}, opener)
        for pid, v in d.get("data", {}).items():
            for p in v.get("platforms", []):
                if p.get("platform") == platform and p.get("records"):
                    latest[pid] = p["records"][-1]
    return latest


def profile_stats(platform, key, opener):
    recs = get(f"/api/profiles/{PROFILES[platform]}/stats", key, opener=opener).get("data", {}).get("records", [])
    return recs[-1] if recs else {}


def platform_id(platform, permalink):
    if platform == "youtube" and "v=" in permalink:
        return permalink.split("v=", 1)[1].split("&", 1)[0]
    return permalink.rstrip("/").rsplit("/", 1)[-1]


def per_1k(num, den):
    return round(num / den * 1000, 1) if isinstance(num, (int, float)) and den else None


def tiktok_row(rec):
    raw, st = rec.get("raw_stats") or {}, rec.get("stats") or {}
    views = raw.get("view_count", raw.get("video_views"))
    reach = st.get("reach", raw.get("reach"))
    shares = raw.get("share_count", st.get("shares"))
    return {"views": views, "reach": reach, "avg_watch_s": raw.get("average_time_watched"),
            "total_watch_s": raw.get("total_time_watched"), "full_watch_rate": raw.get("full_video_watched_rate"),
            "duration_s": raw.get("duration", raw.get("video_duration")), "likes": raw.get("like_count", st.get("likes")),
            "comments": raw.get("comment_count", st.get("comments")), "shares": shares,
            "sends_per_1k": per_1k(shares, reach), "recorded_at": rec.get("recorded_at")}


def youtube_row(rec):
    raw, st = rec.get("raw_stats") or {}, rec.get("stats") or {}
    return {"views": raw.get("view_count", st.get("impressions")), "likes": raw.get("like_count", st.get("likes")),
            "comments": raw.get("comment_count", st.get("comments")), "recorded_at": rec.get("recorded_at")}


def empty_row(platform):
    keys = tiktok_row({}) if platform == "tiktok" else youtube_row({})
    return {k: None for k in keys}


def collect(platform, key, since, by_id, opener):
    posts = recent_posts(platform, key, since, opener)
    stats = latest_stats([p["post_id"] for p in posts], platform, key, opener) if posts else {}
    videos = []
    for p in posts:
        vid = platform_id(platform, p["permalink"])
        rec = stats.get(p["post_id"])
        row = (tiktok_row if platform == "tiktok" else youtube_row)(rec) if rec else empty_row(platform)
        videos.append({f"{platform}_id": vid, "queue_id": by_id.get((platform, vid)),
                       "permalink": p["permalink"], "posted": p["posted"], **row})
    prof = profile_stats(platform, key, opener)
    ps = prof.get("stats") or {}
    if platform == "tiktok":
        return {"followers_count": ps.get("follower_count"), "recorded_at": prof.get("recorded_at"),
                "videos": videos}
    return {"subscribers": ps.get("subscriberCount"), "channel_views_7d": ps.get("views_7d"),
            "channel_avg_view_s_7d": ps.get("averageViewDuration_7d"),
            "channel_avg_view_pct_7d": ps.get("averageViewPercentage_7d"),
            "channel_minutes_watched_7d": ps.get("estimatedMinutesWatched_7d"),
            "recorded_at": prof.get("recorded_at"), "videos": videos}


def combine(metrics, queue):
    by_media = {e.get("media_id"): e for e in queue if e.get("media_id")}
    by_qid = {e["id"]: e for e in queue if e.get("id")}
    rows = {}

    def row(qid):
        e = by_qid.get(qid, {})
        return rows.setdefault(qid, {"queue_id": qid, "hook": e.get("hook"), "posted": e.get("post_date"),
                                     "instagram_views": None, "tiktok_views": None, "youtube_views": None})

    for r in metrics.get("reels", []):
        e = by_media.get(r.get("media_id"))
        if e:
            row(e["id"])["instagram_views"] = r.get("views")
    for platform in ("tiktok", "youtube"):
        for v in metrics.get(platform, {}).get("videos", []):
            if v.get("queue_id"):
                row(v["queue_id"])[f"{platform}_views"] = v.get("views")
    out = []
    for r in rows.values():
        on = [p for p in ("instagram", "tiktok", "youtube") if r[f"{p}_views"] is not None]
        r["total_views"] = sum(r[f"{p}_views"] for p in on) if on else None
        r["on"] = on
        out.append(r)
    return sorted(out, key=lambda r: (r["posted"] or "", r["queue_id"]))


def run(date, days=8, key=None, opener=None, root=None, now=None):
    if not key:
        raise Failed("POSTPROXY_API_KEY is not set")
    opener = opener or urllib.request.urlopen
    root = root or ROOT
    with open(os.path.join(root, "queue.json")) as f:
        queue = json.load(f)
    queue = queue if isinstance(queue, list) else queue.get("entries", queue.get("queue", []))
    by_id = {}
    for e in queue:
        for p in ("tiktok", "youtube"):
            if e.get(f"{p}_id"):
                by_id[(p, str(e[f"{p}_id"]))] = e["id"]
    since = dt.date.fromisoformat(date) - dt.timedelta(days=days)
    try:
        blocks = {p: collect(p, key, since, by_id, opener) for p in ("tiktok", "youtube")}
    except urllib.error.HTTPError as err:
        raise Failed(f"Postproxy HTTP {err.code}: {err.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as err:
        raise Failed(f"Postproxy unreachable: {err.reason}")

    path = os.path.join(root, "metrics", f"{date}.json")
    metrics = {"date": date}
    if os.path.exists(path):
        with open(path) as f:
            metrics = json.load(f)
    metrics.update(blocks)
    metrics["platforms_pulled_at"] = (now or dt.datetime.now(ET)).isoformat(timespec="seconds")
    metrics["combined"] = combine(metrics, queue)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return metrics


def main(argv):
    date, days = dt.datetime.now(ET).date().isoformat(), 8
    i = 0
    while i < len(argv):
        if argv[i] in ("--date", "--days") and i + 1 < len(argv):
            if argv[i] == "--date":
                date = argv[i + 1]
            else:
                days = int(argv[i + 1])
            i += 2
            continue
        print(__doc__, file=sys.stderr)
        return 1
    try:
        m = run(date, days, key=os.environ.get("POSTPROXY_API_KEY"))
    except Failed as err:
        print(f"failed: {err}", file=sys.stderr)
        return 1
    print(f"tiktok: {len(m['tiktok']['videos'])} videos, {m['tiktok']['followers_count']} followers; "
          f"youtube: {len(m['youtube']['videos'])} videos, {m['youtube']['subscribers']} subscribers; "
          f"combined: {len(m['combined'])} Reels")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
