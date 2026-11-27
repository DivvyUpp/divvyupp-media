#!/usr/bin/env python3
"""Publish one approved queue entry to @getdivvyupp on Instagram, then TikTok + YouTube, all through Postproxy.

Called by the Post run (runs/post.md step 3) for the ONE entry that slot posts. Replaces the Windsor
`create_video_post` / `create_comment` calls (Srini, 2026-11-27: all three channels on Postproxy).
Stdlib only.

Usage:  python3 scripts/post_reel.py <entry_id> [--dry-run]

Env:
  POSTPROXY_API_KEY  required. Bearer token for https://api.postproxy.dev. Never printed.

What it does:
  1. Instagram (Postproxy profile 6lUEBB = account 17841422626862357), as its own Postproxy post because
     Instagram keeps the FULL caption (with "Link in the comments.") while TikTok/YouTube drop that line:
     * refuses unless status is "approved" (or "posted" with Instagram already live, to finish the
       other platforms), and the entry has a file and a caption;
     * main entry -> Reel, share_to_feed on, `first_comment` = entry.first_comment (if set and no
       first_comment_id yet); trial entry -> Reel with trial_strategy MANUAL (no first comment);
     * skipped when Instagram is already live (`media_id` / `instagram_id`) or already sent
       (`instagram_postproxy_id`: check that post, never re-post);
     * refuses if any recent Postproxy post already sent this same video file to Instagram;
     * saves `instagram_postproxy_id` BEFORE waiting, so a crash can't lead to a second post;
     * once published writes `instagram_url`, `instagram_id` (the permalink shortcode), `status`
       "posted", `posted_at` (ET, ISO) and, when Postproxy shows the first comment,
       `first_comment_id` (Instagram's comment id). The numeric Graph `media_id` is NOT known here:
       the Metrics pull fills it in from Windsor by matching the shortcode.
  2. TikTok + YouTube (main entries only, and only if Instagram is live): scripts/post_postproxy.py
     for the same entry, in one Postproxy request.

Exit 0 = everything published (or --dry-run). 1 = refused or a platform failed (reason on stderr;
whatever did publish is recorded). 2 = a platform was still processing when the wait ran out (its
postproxy id is saved: check it, never re-post). If Instagram does not publish, nothing else is sent.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

import post_postproxy as pp

IG_PROFILE = "6lUEBB"  # @getdivvyupp Instagram (GET /api/profiles; platform_id 17841422626862357)
ET = ZoneInfo("America/New_York")
RECENT_POSTS = 20  # Postproxy posts checked for an earlier send of the same file


def ig_state(e):
    """'live', 'sent' or None."""
    if e.get("media_id") or e.get("instagram_id"):
        return "live"
    if e.get("instagram_postproxy_id"):
        return "sent"
    return None


def check_postable(e):
    kind = e.get("kind", "main")
    if kind not in ("main", "trial"):
        raise pp.Refused(f"{e['id']} is a {kind!r} entry; only main and trial Reels are posted")
    state = ig_state(e)
    if e.get("status") == "posted" and state == "live":
        if kind == "trial":
            raise pp.Refused(f"{e['id']} is a trial already on Instagram; trials go nowhere else")
    elif e.get("status") != "approved":
        raise pp.Refused(f"{e['id']} has status {e.get('status')!r}; only approved Reels may be posted")
    if not e.get("file"):
        raise pp.Refused(f"{e['id']} has no file")
    if not e.get("caption"):
        raise pp.Refused(f"{e['id']} has no caption")
    if state == "sent":
        raise pp.Refused(f"{e['id']} was already sent to Instagram as Postproxy post "
                         f"{e['instagram_postproxy_id']}; check that post, never re-post")


def ig_payload(e):
    ig = {"format": "reel"}
    if e.get("kind", "main") == "trial":
        ig["trial_strategy"] = "MANUAL"
    else:
        ig["share_to_feed"] = True
        if e.get("first_comment") and not e.get("first_comment_id"):
            ig["first_comment"] = e["first_comment"]
    return {
        "post": {"body": e["caption"]},
        "profiles": [IG_PROFILE],
        "media": [pp.PAGES + e["file"]],
        "platforms": {"instagram": ig},
    }


def already_sent_elsewhere(e, key, opener):
    """True if a recent Postproxy post already carried this file to Instagram."""
    url = pp.PAGES + e["file"]
    resp = pp.request("GET", f"/api/posts?per_page={RECENT_POSTS}&profiles=instagram", key, opener=opener)
    for p in resp.get("data", []):
        if (any(m.get("source_url") == url for m in p.get("media", []))
                and "instagram" in pp.states(p)):
            return p["id"]
    return None


def shortcode(permalink):
    m = re.search(r"instagram\.com/(?:p|reel|reels)/([\w-]+)", permalink)
    return m.group(1) if m else permalink.rstrip("/").rsplit("/", 1)[-1]


def find_first_comment(e, post_id, key, opener, log):
    """Record Instagram's id for the first comment if Postproxy already shows it; never fails the run."""
    try:
        resp = pp.request("GET", f"/api/posts/{post_id}/comments?profile_id={IG_PROFILE}", key,
                          opener=opener)
    except (urllib.error.URLError, ValueError) as err:
        log(f"instagram: first comment sent with the post; couldn't read comments back ({err})")
        return
    rows = resp if isinstance(resp, list) else resp.get("data", [])
    for c in rows:
        if c.get("body") == e["first_comment"] and c.get("external_id"):
            e["first_comment_id"] = c["external_id"]
            return
    log("instagram: first comment sent with the post; not listed by Postproxy yet: check the Reel")


def post_instagram(e, queue, raw, queue_path, key, opener, sleep, log, now):
    earlier = already_sent_elsewhere(e, key, opener)
    if earlier:
        raise pp.Refused(f"Postproxy post {earlier} already sent {e['file']} to Instagram; "
                         "check it, never re-post")
    payload = ig_payload(e)
    post = pp.request("POST", "/api/posts", key, payload,
                      {"Idempotency-Key": f"instagram-{e['id']}"}, opener=opener)
    e["instagram_postproxy_id"] = post["id"]
    pp.save_queue(queue_path, queue, raw)  # saved first: a crash past here can't lead to a re-post
    log(f"sent to Postproxy as {post['id']} (instagram)")
    for _ in range(pp.POLL_MAX):
        s = pp.states(post).get("instagram", {})
        if s.get("status") == "published" and s.get("permalink"):
            e["instagram_url"] = s["permalink"]
            e["instagram_id"] = shortcode(s["permalink"])
            e["status"] = "posted"
            e["posted_at"] = now().astimezone(ET).replace(microsecond=0).isoformat()
            if "first_comment" in payload["platforms"]["instagram"]:
                find_first_comment(e, post["id"], key, opener, log)
            pp.save_queue(queue_path, queue, raw)
            print(f"instagram: {s['permalink']}")
            return 0
        if s.get("status") == "failed":
            log(f"instagram: publish failed: {s.get('error')}")
            return 1
        sleep(pp.POLL_EVERY_S)
        post = pp.request("GET", f"/api/posts/{post['id']}", key, opener=opener)
    log(f"instagram: still {pp.states(post).get('instagram', {}).get('status')!r} after the wait; "
        f"Postproxy post {post['id']}")
    return 2


def run(entry_id, dry_run=False, key=None, opener=None, sleep=None, queue_path=None, log=None,
        now=None):
    opener = opener or urllib.request.urlopen
    sleep = sleep or time.sleep
    queue_path = queue_path or pp.QUEUE
    log = log or (lambda m: print(m, file=sys.stderr))
    now = now or (lambda: datetime.datetime.now(datetime.timezone.utc))
    with open(queue_path) as f:
        raw = f.read()
    queue = json.loads(raw)
    e = pp.find_entry(queue, entry_id)
    check_postable(e)
    main_entry = e.get("kind", "main") == "main"
    if dry_run:
        out = {"instagram": None if ig_state(e) else ig_payload(e)}
        if main_entry:
            todo = [p for p in pp.PLATFORMS if not (e.get(f"{p}_id") or e.get(f"{p}_postproxy_id"))]
            out["tiktok_youtube"] = pp.build_payload(e, todo) if todo else None
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    if not key:
        raise pp.Refused("POSTPROXY_API_KEY is not set")

    if ig_state(e) == "live":
        log(f"instagram: already live ({e.get('instagram_id') or e.get('media_id')}), left out")
    else:
        code = post_instagram(e, queue, raw, queue_path, key, opener, sleep, log, now)
        if code:
            log("tiktok/youtube: not sent, because Instagram is not live")
            return code
    if not main_entry:
        return 0
    try:
        return pp.run(entry_id, key=key, opener=opener, sleep=sleep, queue_path=queue_path, log=log)
    except pp.Refused as err:
        if "nothing left" in str(err):
            log(f"tiktok/youtube: {err}")
            return 0
        raise


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = [a for a in argv if a.startswith("--")]
    if len(args) != 1 or any(f != "--dry-run" for f in flags):
        print(__doc__, file=sys.stderr)
        return 1
    try:
        return run(args[0], dry_run="--dry-run" in flags, key=os.environ.get("POSTPROXY_API_KEY"))
    except pp.Refused as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as err:
        print(f"Postproxy HTTP {err.code}: {err.read().decode(errors='replace')[:500]}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
