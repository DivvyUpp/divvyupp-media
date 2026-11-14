#!/usr/bin/env python3
"""Fetch last week's DivvyUpp funnel (instagram + all sources) into funnel/.

Called by .github/workflows/funnel-weekly.yml. Stdlib only.

Env:
  FUNNEL_EXPORT_TOKEN  required. Bearer token for GET /api/export/funnel/daily. Never printed.
  FUNNEL_API_BASE      optional. Defaults to the production App Runner URL.
  FROM_DATE, TO_DATE   optional YYYY-MM-DD (manual runs). Both or neither.

Writes funnel/<ISO-year>-W<ISO-week>.json for the default (previous Mon-Sun ET)
range, or funnel/custom-<from>_<to>.json for a custom range. Nothing is written
unless BOTH requests return 200. Exit 0 = written or unchanged, 1 = failure.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

DEFAULT_API_BASE = "https://pbnxfbfpmw.us-east-1.awsapprunner.com"
ET = ZoneInfo("America/New_York")
TIMEOUT_S = 20
MAX_RETRIES = 2


class FetchError(Exception):
    pass


def previous_week(today: dt.date):
    """Monday..Sunday of the week before the one containing `today` (ET date)."""
    this_monday = today - dt.timedelta(days=today.weekday())
    start = this_monday - dt.timedelta(days=7)
    return start, start + dt.timedelta(days=6)


def output_path(root: str, start: dt.date, end: dt.date, custom: bool) -> str:
    if custom:
        return os.path.join(root, "funnel", f"custom-{start.isoformat()}_{end.isoformat()}.json")
    year, week, _ = start.isocalendar()
    return os.path.join(root, "funnel", f"{year}-W{week:02d}.json")


def _retry_after(err: urllib.error.HTTPError, attempt: int) -> float:
    try:
        return max(0.0, float(err.headers.get("Retry-After", "")))
    except (TypeError, ValueError):
        return float(2 ** attempt)


def fetch(base, token, start, end, source=None, opener=urllib.request.urlopen, sleep=time.sleep):
    q = {"from": start.isoformat(), "to": end.isoformat()}
    if source:
        q["source"] = source
    url = f"{base.rstrip('/')}/api/export/funnel/daily?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    for attempt in range(MAX_RETRIES + 1):
        try:
            with opener(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            retryable = e.code == 429 or e.code >= 500
            if not retryable or attempt == MAX_RETRIES:
                raise FetchError(f"{source or 'all sources'}: HTTP {e.code}") from None
            sleep(_retry_after(e, attempt))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == MAX_RETRIES:
                raise FetchError(f"{source or 'all sources'}: network error ({type(e).__name__})") from None
            sleep(float(2 ** attempt))
    raise FetchError("unreachable")  # pragma: no cover


def run(env, root, today, opener=urllib.request.urlopen, sleep=time.sleep, now=None):
    token = env.get("FUNNEL_EXPORT_TOKEN", "")
    if not token:
        print("FUNNEL_EXPORT_TOKEN is not set", file=sys.stderr)
        return 1
    base = env.get("FUNNEL_API_BASE") or DEFAULT_API_BASE
    f, t = env.get("FROM_DATE", ""), env.get("TO_DATE", "")
    if bool(f) != bool(t):
        print("Set both FROM_DATE and TO_DATE, or neither", file=sys.stderr)
        return 1
    custom = bool(f)
    try:
        start, end = (dt.date.fromisoformat(f), dt.date.fromisoformat(t)) if custom else previous_week(today)
    except ValueError:
        print("FROM_DATE/TO_DATE must be YYYY-MM-DD", file=sys.stderr)
        return 1

    try:
        instagram = fetch(base, token, start, end, "instagram", opener, sleep)
        all_sources = fetch(base, token, start, end, None, opener, sleep)
    except FetchError as e:
        print(f"funnel fetch failed: {e}; nothing written", file=sys.stderr)
        return 1

    year, week, _ = start.isocalendar()
    doc = {
        "week": f"{year}-W{week:02d}",
        "fetched_at": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from": start.isoformat(),
        "to": end.isoformat(),
        "instagram": instagram,
        "all_sources": all_sources,
    }
    path = output_path(root, start, end, custom)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
        if {k: v for k, v in old.items() if k != "fetched_at"} == {k: v for k, v in doc.items() if k != "fetched_at"}:
            print(f"{path} unchanged")
            return 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(run(dict(os.environ), root, dt.datetime.now(ET).date()))
