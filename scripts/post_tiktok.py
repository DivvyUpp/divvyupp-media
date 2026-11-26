#!/usr/bin/env python3
"""Publish one approved queue entry to @getdivvyupp on TikTok through Postproxy.

Called by the Post run (runs/post.md step 3c) right after the entry posts on Instagram.
Stdlib only. First used by hand on 2026-11-26 (same-10k v12, TikTok id 7712592763354762509).

Usage:  python3 scripts/post_tiktok.py <entry_id> [--dry-run]

Env:
  POSTPROXY_API_KEY  required. Bearer token for https://api.postproxy.dev. Never printed.

What it does:
  * refuses unless the entry is "kind": "main" (or no kind), status "approved" or "posted",
    and has no tiktok_id (never posts twice);
  * caption = entry.tiktok_caption, else entry.caption (exactly; never edited);
  * video  = https://divvyupp.github.io/divvyupp-media/<entry.file> (Postproxy downloads it);
  * public, comments / Duet / Stitch on, posted now; an Idempotency-Key per entry id, so a
    re-sent request cannot make a second post;
  * waits until TikTok reports published or failed, then writes tiktok_id, tiktok_url and
    tiktok_postproxy_id onto the entry in queue.json (same formatting as the file).

Exit 0 = published (or --dry-run), 1 = failed or refused (reason on stderr), 2 = still
processing when the wait ran out (tiktok_postproxy_id is saved: check it, never re-post).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.postproxy.dev"
PROFILE_ID = "MZU39X"  # @getdivvyupp on TikTok (GET /api/profiles)
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
        raise Refused(f"{e['id']} is a {e.get('kind')} entry; only main Reels go to TikTok")
    if e.get("status") not in ("approved", "posted"):
        raise Refused(f"{e['id']} has status {e.get('status')!r}; only approved Reels may be posted")
    if e.get("tiktok_id"):
        raise Refused(f"{e['id']} is already on TikTok ({e['tiktok_id']})")
    if e.get("tiktok_postproxy_id"):
        raise Refused(
            f"{e['id']} was already sent to Postproxy ({e['tiktok_postproxy_id']}); "
            "check that post's status instead of posting again"
        )
    if not e.get("file"):
        raise Refused(f"{e['id']} has no file")


def build_payload(e):
    caption = e.get("tiktok_caption") or e["caption"]
    return {
        "post": {"body": caption},
        "profiles": [PROFILE_ID],
        "media": [PAGES + e["file"]],
        "platforms": {
            "tiktok": {
                "format": "video",
                "privacy_status": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            }
        },
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


def tiktok_state(post):
    for p in post.get("platforms", []):
        if p.get("platform") == "tiktok":
            return p
    return {}


def video_id_from(permalink):
    return permalink.rstrip("/").rsplit("/", 1)[-1] if permalink else None


def save_queue(path, queue, raw):
    indent = 1 if "\n \"" in raw[:400] or "\n {" in raw[:400] else 2
    out = json.dumps(queue, indent=indent, ensure_ascii=False)
    if raw.endswith("\n"):
        out += "\n"
    with open(path, "w") as f:
        f.write(out)


def run(entry_id, dry_run=False, key=None, opener=None, sleep=None, queue_path=None, log=None):
    opener = opener or urllib.request.urlopen
    sleep = sleep or time.sleep
    queue_path = queue_path or QUEUE
    log = log or (lambda m: print(m, file=sys.stderr))
    with open(queue_path) as f:
        raw = f.read()
    queue = json.loads(raw)
    e = find_entry(queue, entry_id)
    check_postable(e)
    payload = build_payload(e)
    if dry_run:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
        return 0
    if not key:
        raise Refused("POSTPROXY_API_KEY is not set")

    post = request("POST", "/api/posts", key, payload,
                   {"Idempotency-Key": f"tiktok-{entry_id}"}, opener=opener)
    e["tiktok_postproxy_id"] = post["id"]
    save_queue(queue_path, queue, raw)  # saved first: a crash past here can't lead to a re-post
    log(f"sent to Postproxy as {post['id']}")

    for _ in range(POLL_MAX):
        state = tiktok_state(post)
        status = state.get("status")
        if status == "published" and state.get("permalink"):
            e["tiktok_url"] = state["permalink"]
            e["tiktok_id"] = video_id_from(state["permalink"])
            save_queue(queue_path, queue, raw)
            print(e["tiktok_url"])
            return 0
        if status == "failed":
            log(f"TikTok publish failed: {state.get('error')}")
            return 1
        sleep(POLL_EVERY_S)
        post = request("GET", f"/api/posts/{post['id']}", key, opener=opener)
    log(f"still {tiktok_state(post).get('status')!r} after the wait; Postproxy post {post['id']}")
    return 2


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 1
    try:
        return run(args[0], dry_run="--dry-run" in argv, key=os.environ.get("POSTPROXY_API_KEY"))
    except Refused as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as err:
        print(f"Postproxy HTTP {err.code}: {err.read().decode(errors='replace')[:500]}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
