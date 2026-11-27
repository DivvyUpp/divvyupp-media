#!/usr/bin/env python3
"""Publish one approved queue entry to @getdivvyupp on TikTok AND YouTube (Shorts) through Postproxy.

Called by the Post run (runs/post.md step 3b) right after the entry posts on Instagram, for that same
entry only. One Postproxy request carries both platforms, so it counts as ONE post on Postproxy's plan.
Stdlib only. Tested by hand on 2026-11-26: TikTok (same-10k v12 -> 7712592763354762509) and YouTube
(S8 minimum -> U82Qn1ZS-GU).

Usage:  python3 scripts/post_postproxy.py <entry_id> [--only tiktok|youtube] [--dry-run]

Env:
  POSTPROXY_API_KEY  required. Bearer token for https://api.postproxy.dev. Never printed.

What it does:
  * refuses unless the entry is "kind": "main" (or no kind) with status "approved" or "posted";
  * leaves out any platform the entry already went to (`<platform>_id`) or was already sent to
    (`<platform>_postproxy_id`), so nothing is ever posted twice; refuses if none is left;
  * caption (TikTok caption and YouTube description) = entry.tiktok_caption, else entry.caption with
    only the "Link in the comments." sentence removed (that first comment exists on Instagram only);
  * YouTube title = entry.hook without a trailing "(...)" note, cut to 100 characters;
  * video = https://divvyupp.github.io/divvyupp-media/<entry.file> (Postproxy downloads it);
  * cover (TikTok cover, YouTube thumbnail) = entry.cover or reels/<video>_cover.jpg when rendered;
  * both public; TikTok comments / Duet / Stitch on; posted now; an Idempotency-Key per entry and
    platform set, so a re-sent request cannot make a second post;
  * waits for every platform, then writes `<platform>_id`, `<platform>_url` and
    `<platform>_postproxy_id` onto the entry in queue.json (same formatting as the file).

Exit 0 = every platform published (or --dry-run), 1 = refused or a platform failed (reason on
stderr; platforms that did publish are still recorded), 2 = a platform was still processing when
the wait ran out (its postproxy id is saved: check it, never re-post).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.postproxy.dev"
PROFILES = {"tiktok": "MZU39X", "youtube": "rOUpVX"}  # @getdivvyupp (GET /api/profiles)
PLATFORMS = ("tiktok", "youtube")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# YouTube custom thumbnails need a phone-verified channel; not confirmed yet (2026-11-27). Set True once Srini confirms
# Studio > Settings > Channel > Feature eligibility shows "Features that require phone verification: Enabled".
YOUTUBE_THUMBNAIL = False
PAGES = "https://divvyupp.github.io/divvyupp-media/"
QUEUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "queue.json")
TIMEOUT_S = 30
POLL_EVERY_S = 15
POLL_MAX = 40  # ~10 minutes


class Refused(Exception):
    pass


def entries(queue):
    return queue if isinstance(queue, list) else queue.get("entries", queue.get("queue", []))


def find_entry(queue, entry_id):
    for e in entries(queue):
        if e.get("id") == entry_id:
            return e
    raise Refused(f"no queue entry with id {entry_id!r}")


def check_postable(e):
    if e.get("kind", "main") != "main":
        raise Refused(f"{e['id']} is a {e.get('kind')} entry; only main Reels are cross-posted")
    if e.get("status") not in ("approved", "posted"):
        raise Refused(f"{e['id']} has status {e.get('status')!r}; only approved Reels may be posted")
    if not e.get("file"):
        raise Refused(f"{e['id']} has no file")


def platforms_to_post(e, wanted, log):
    todo = []
    for p in wanted:
        if e.get(f"{p}_id"):
            log(f"{p}: already live ({e[f'{p}_id']}), left out")
        elif e.get(f"{p}_postproxy_id"):
            log(f"{p}: already sent to Postproxy ({e[f'{p}_postproxy_id']}); check that post, never re-post")
        else:
            todo.append(p)
    if not todo:
        raise Refused(f"{e['id']} has nothing left to post on {', '.join(wanted)}")
    return todo


def caption(e):
    """entry.tiktok_caption, else entry.caption minus "Link in the comments." (Instagram-only comment)."""
    if e.get("tiktok_caption"):
        return e["tiktok_caption"]
    cap = re.sub(r"[ \t]*Link in the comments\.?[ \t]*", " ", e["caption"])
    cap = re.sub(r" *\n *", "\n", cap)
    cap = re.sub(r"\n{3,}", "\n\n", cap)
    return re.sub(r" {2,}", " ", cap).strip()


def youtube_title(e):
    title = re.sub(r"\s*\([^)]*\)\s*$", "", e.get("hook") or "").strip()
    if not title:
        raise Refused(f"{e['id']} has no hook to use as the YouTube title")
    return title[:100]


def cover_path(e):
    """entry.cover, else reels/<video name>_cover.jpg next to the video if it exists in the repo; None otherwise.
    Sent as the cover on Instagram, TikTok and YouTube (2026-11-27: Srini stopped setting covers by hand)."""
    if e.get("cover"):
        return e["cover"]
    stem, _ = os.path.splitext(e["file"])
    guess = stem + "_cover.jpg"
    return guess if os.path.exists(os.path.join(ROOT, guess)) else None


def build_payload(e, todo):
    params = {}
    cover = cover_path(e)
    if "tiktok" in todo:
        params["tiktok"] = {
            "format": "video",
            "privacy_status": "PUBLIC_TO_EVERYONE",
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
        }
        if cover:
            params["tiktok"]["cover_url"] = PAGES + cover
    if "youtube" in todo:
        params["youtube"] = {"title": youtube_title(e), "privacy_status": "public"}
        if cover and YOUTUBE_THUMBNAIL:
            params["youtube"]["cover_url"] = PAGES + cover          # custom thumbnail (verified channel)
    return {
        "post": {"body": caption(e)},
        "profiles": [PROFILES[p] for p in todo],
        "media": [PAGES + e["file"]],
        "platforms": params,
    }


def request(method, path, key, body=None, extra_headers=None, opener=urllib.request.urlopen):
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    headers.update(extra_headers or {})
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    with opener(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def states(post):
    return {p.get("platform"): p for p in post.get("platforms", [])}


def platform_id(platform, permalink):
    if platform == "youtube":
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]+)", permalink)
        if m:
            return m.group(1)
    return permalink.rstrip("/").rsplit("/", 1)[-1]


def save_queue(path, queue, raw):
    indent = 1 if "\n \"" in raw[:400] or "\n {" in raw[:400] else 2
    out = json.dumps(queue, indent=indent, ensure_ascii=False)
    if raw.endswith("\n"):
        out += "\n"
    with open(path, "w") as f:
        f.write(out)


def run(entry_id, platforms=PLATFORMS, dry_run=False, key=None, opener=None, sleep=None,
        queue_path=None, log=None):
    opener = opener or urllib.request.urlopen
    sleep = sleep or time.sleep
    queue_path = queue_path or QUEUE
    log = log or (lambda m: print(m, file=sys.stderr))
    with open(queue_path) as f:
        raw = f.read()
    queue = json.loads(raw)
    e = find_entry(queue, entry_id)
    check_postable(e)
    todo = platforms_to_post(e, platforms, log)
    payload = build_payload(e, todo)
    if dry_run:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
        return 0
    if not key:
        raise Refused("POSTPROXY_API_KEY is not set")

    post = request("POST", "/api/posts", key, payload,
                   {"Idempotency-Key": f"{'-'.join(todo)}-{entry_id}"}, opener=opener)
    for p in todo:
        e[f"{p}_postproxy_id"] = post["id"]
    save_queue(queue_path, queue, raw)  # saved first: a crash past here can't lead to a re-post
    log(f"sent to Postproxy as {post['id']} ({', '.join(todo)})")

    pending = list(todo)
    failed = []
    for _ in range(POLL_MAX):
        st = states(post)
        for p in list(pending):
            s = st.get(p, {})
            if s.get("status") == "published" and s.get("permalink"):
                e[f"{p}_url"] = s["permalink"]
                e[f"{p}_id"] = platform_id(p, s["permalink"])
                save_queue(queue_path, queue, raw)
                print(f"{p}: {s['permalink']}")
                pending.remove(p)
            elif s.get("status") == "failed":
                log(f"{p}: publish failed: {s.get('error')}")
                failed.append(p)
                pending.remove(p)
        if not pending:
            return 1 if failed else 0
        sleep(POLL_EVERY_S)
        post = request("GET", f"/api/posts/{post['id']}", key, opener=opener)
    for p in pending:
        log(f"{p}: still {states(post).get(p, {}).get('status')!r} after the wait; Postproxy post {post['id']}")
    return 1 if failed else 2


def main(argv, platforms=PLATFORMS):
    args, only, i = [], None, 0
    while i < len(argv):
        if argv[i] == "--only" and i + 1 < len(argv) and argv[i + 1] in PLATFORMS:
            only = (argv[i + 1],)
            i += 2
            continue
        if not argv[i].startswith("--"):
            args.append(argv[i])
        elif argv[i] != "--dry-run":
            args = []
            break
        i += 1
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        return run(args[0], platforms=only or platforms, dry_run="--dry-run" in argv,
                   key=os.environ.get("POSTPROXY_API_KEY"))
    except Refused as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as err:
        print(f"Postproxy HTTP {err.code}: {err.read().decode(errors='replace')[:500]}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
