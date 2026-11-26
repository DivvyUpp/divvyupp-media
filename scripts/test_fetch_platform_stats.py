import datetime as dt
import io
import json
import urllib.error
import urllib.parse

import pytest

import fetch_platform_stats as fps

KEY = "pp_s3cret"
TT_LINK = "https://www.tiktok.com/@getdivvyupp/video/111"
YT_LINK = "https://www.youtube.com/watch?v=abc_D-1&t=1"


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def router(routes, seen=None):
    """routes: {(path, frozenset of query keys we match on) or path: response-or-callable}."""
    def _open(req, timeout):
        u = urllib.parse.urlparse(req.full_url)
        q = dict(urllib.parse.parse_qsl(u.query))
        if seen is not None:
            seen.append((u.path, q, req.get_header("Authorization")))
        h = routes[u.path]
        body = h(q) if callable(h) else h
        if isinstance(body, Exception):
            raise body
        return FakeResp(json.dumps(body).encode())
    return _open


def post(pid, created, platform, link):
    return {"id": pid, "created_at": created,
            "platforms": [{"platform": platform, "permalink": link}]}


def list_posts(q):
    if q["profile_id"] == "MZU39X":
        return {"data": [post("T1", "2026-11-26T21:18:00Z", "tiktok", TT_LINK),
                         post("T0", "2026-06-21T21:52:00Z", "tiktok", TT_LINK + "0"),
                         {"id": "T2", "created_at": "2026-11-26T22:00:00Z",
                          "platforms": [{"platform": "tiktok", "permalink": None}]}]}
    return {"data": [post("Y1", "2026-11-26T22:04:00Z", "youtube", YT_LINK),
                     post("Y2", "2026-11-26T20:14:00Z", "youtube", "https://www.youtube.com/shorts/zz9")]}


STATS = {"data": {
    "T1": {"platforms": [{"platform": "tiktok", "records": [
        {"stats": {"reach": 0}, "raw_stats": {}, "recorded_at": "old"},
        {"stats": {"reach": 50, "shares": 9}, "raw_stats": {
            "view_count": 7, "average_time_watched": 28.02, "total_time_watched": 196,
            "full_video_watched_rate": 0.1429, "duration": 52.667, "like_count": 1,
            "comment_count": 2, "share_count": 3}, "recorded_at": "2026-11-26T22:19:18Z"}]}]},
    "Y1": {"platforms": [{"platform": "youtube", "records": []}]},
    "Y2": {"platforms": [{"platform": "instagram", "records": [{"stats": {}}]},
                        {"platform": "youtube", "records": [
                            {"stats": {"impressions": 7, "likes": 0, "comments": 0}, "raw_stats": None,
                             "recorded_at": "2026-11-26T22:03:12Z"}]}]},
}}


def profile_stats(platform):
    if platform == "tiktok":
        return {"data": {"records": [{"stats": {"follower_count": 1}, "recorded_at": "r1"}]}}
    return {"data": {"records": [{"stats": {"subscriberCount": 0, "views_7d": 5, "averageViewDuration_7d": 12,
                                            "averageViewPercentage_7d": 40.5, "estimatedMinutesWatched_7d": 3},
                                  "recorded_at": "r2"}]}}


def routes(**over):
    r = {"/api/posts": list_posts, "/api/posts/stats": STATS,
         "/api/profiles/MZU39X/stats": profile_stats("tiktok"),
         "/api/profiles/rOUpVX/stats": profile_stats("youtube")}
    r.update(over)
    return r


def setup(tmp_path, metrics=None, queue=None):
    q = queue if queue is not None else [
        {"id": "reel-a", "hook": "Hook A", "post_date": "2026-11-20", "media_id": "IG1",
         "tiktok_id": "111", "youtube_id": "abc_D-1"},
        {"id": "reel-b", "hook": "Hook B", "post_date": "2026-11-26", "youtube_id": "zz9"},
        {"id": "reel-c", "post_date": "2026-11-18", "media_id": "IG3"},
    ]
    (tmp_path / "queue.json").write_text(json.dumps(q))
    if metrics is not None:
        (tmp_path / "metrics").mkdir()
        (tmp_path / "metrics" / "2026-11-26.json").write_text(json.dumps(metrics))
    return tmp_path


NOW = dt.datetime(2026, 11, 27, 5, 55, tzinfo=fps.ET)


def test_full_pull_merges_into_instagram_file(tmp_path):
    ig = {"date": "2026-11-26", "followers_count": 3,
          "reels": [{"media_id": "IG1", "views": 114}, {"media_id": "IG3", "views": 6},
                    {"media_id": "UNKNOWN", "views": 1}]}
    root = setup(tmp_path, metrics=ig)
    seen = []
    m = fps.run("2026-11-26", key=KEY, opener=router(routes(), seen), root=str(root), now=NOW)
    saved = json.loads((root / "metrics" / "2026-11-26.json").read_text())
    assert saved == m
    assert saved["followers_count"] == 3 and saved["reels"] == ig["reels"]
    assert saved["platforms_pulled_at"] == "2026-11-27T05:55:00-05:00"
    tt = saved["tiktok"]
    assert tt["followers_count"] == 1 and tt["recorded_at"] == "r1"
    assert [v["tiktok_id"] for v in tt["videos"]] == ["111"]
    v = tt["videos"][0]
    assert v == {"tiktok_id": "111", "queue_id": "reel-a", "permalink": TT_LINK, "posted": "2026-11-26",
                 "views": 7, "reach": 50, "avg_watch_s": 28.02, "total_watch_s": 196,
                 "full_watch_rate": 0.1429, "duration_s": 52.667, "likes": 1, "comments": 2, "shares": 3,
                 "sends_per_1k": 60.0, "recorded_at": "2026-11-26T22:19:18Z"}
    yt = saved["youtube"]
    assert yt["subscribers"] == 0 and yt["channel_views_7d"] == 5 and yt["channel_avg_view_s_7d"] == 12
    assert yt["channel_avg_view_pct_7d"] == 40.5 and yt["channel_minutes_watched_7d"] == 3
    y1, y2 = yt["videos"]
    assert y1["youtube_id"] == "abc_D-1" and y1["queue_id"] == "reel-a" and y1["views"] is None
    assert y2["youtube_id"] == "zz9" and y2["queue_id"] == "reel-b" and y2["views"] == 7
    comb = {r["queue_id"]: r for r in saved["combined"]}
    assert [r["queue_id"] for r in saved["combined"]] == ["reel-c", "reel-a", "reel-b"]
    assert comb["reel-a"] == {"queue_id": "reel-a", "hook": "Hook A", "posted": "2026-11-20",
                              "instagram_views": 114, "tiktok_views": 7, "youtube_views": None,
                              "total_views": 121, "on": ["instagram", "tiktok"]}
    assert comb["reel-b"]["total_views"] == 7 and comb["reel-b"]["on"] == ["youtube"]
    assert all(a == f"Bearer {KEY}" for _, _, a in seen)
    assert any(p == "/api/posts/stats" and q["post_ids"] == "T1" for p, q, _ in seen)


def test_creates_file_when_instagram_step_missing(tmp_path):
    root = setup(tmp_path)
    m = fps.run("2026-11-26", key=KEY, opener=router(routes()), root=str(root), now=NOW)
    assert m["date"] == "2026-11-26" and "reels" not in m
    assert json.loads((root / "metrics" / "2026-11-26.json").read_text())["tiktok"]["videos"]


def test_no_recent_posts_and_no_profile_records(tmp_path):
    root = setup(tmp_path, queue={"entries": [{"id": "x", "tiktok_id": "9"}]})
    m = fps.run("2026-11-26", key=KEY, root=str(root), now=NOW, opener=router(routes(**{
        "/api/posts": {"data": []},
        "/api/posts/stats": lambda q: pytest.fail("stats called with no posts"),
        "/api/profiles/MZU39X/stats": {"data": {"records": []}},
        "/api/profiles/rOUpVX/stats": {}})))
    assert m["tiktok"] == {"followers_count": None, "recorded_at": None, "videos": []}
    assert m["youtube"]["subscribers"] is None and m["combined"] == []


def test_pagination_and_stats_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(fps, "PER_PAGE", 2)
    monkeypatch.setattr(fps, "STATS_BATCH", 1)
    pages = {"1": [post("A", "2026-11-25T12:00:00Z", "tiktok", TT_LINK + "a"),
                   post("B", "2026-11-25T12:00:00Z", "tiktok", TT_LINK + "b")],
             "2": [post("C", "2026-11-25T12:00:00Z", "tiktok", TT_LINK + "c")]}
    seen = []
    root = setup(tmp_path, queue=[])
    m = fps.run("2026-11-26", key=KEY, root=str(root), now=NOW, opener=router(routes(**{
        "/api/posts": lambda q: {"data": pages.get(q["page"], []) if q["profile_id"] == "MZU39X" else []},
        "/api/posts/stats": {"data": {}}}), seen))
    assert [v["tiktok_id"] for v in m["tiktok"]["videos"]] == ["111a", "111b", "111c"]
    assert all(v["views"] is None and v["queue_id"] is None for v in m["tiktok"]["videos"])
    assert sum(1 for p, _, _ in seen if p == "/api/posts/stats") == 3


def test_tiktok_falls_back_to_normalised_stats(tmp_path):
    rec = {"stats": {"reach": 0, "likes": 4, "comments": 5, "shares": 6},
           "raw_stats": {"video_views": 8, "video_duration": 30}, "recorded_at": "t"}
    row = fps.tiktok_row(rec)
    assert row["views"] == 8 and row["duration_s"] == 30 and row["likes"] == 4
    assert row["comments"] == 5 and row["shares"] == 6 and row["sends_per_1k"] is None


def test_per_1k():
    assert fps.per_1k(3, 50) == 60.0
    assert fps.per_1k(None, 50) is None and fps.per_1k(3, 0) is None and fps.per_1k(3, None) is None


def test_platform_id():
    assert fps.platform_id("youtube", YT_LINK) == "abc_D-1"
    assert fps.platform_id("youtube", "https://youtube.com/shorts/zz9/") == "zz9"
    assert fps.platform_id("tiktok", TT_LINK) == "111"


def test_missing_key(tmp_path):
    with pytest.raises(fps.Failed, match="POSTPROXY_API_KEY"):
        fps.run("2026-11-26", key=None, root=str(tmp_path))


def test_http_and_network_errors_write_nothing(tmp_path):
    root = setup(tmp_path)
    err = urllib.error.HTTPError("u", 500, "x", {}, io.BytesIO(b"boom"))
    with pytest.raises(fps.Failed, match="HTTP 500: boom"):
        fps.run("2026-11-26", key=KEY, root=str(root), opener=router(routes(**{"/api/posts": err})))
    with pytest.raises(fps.Failed, match="unreachable"):
        fps.run("2026-11-26", key=KEY, root=str(root),
                opener=router(routes(**{"/api/posts": urllib.error.URLError("dns")})))
    assert not (root / "metrics").exists()


def test_main(tmp_path, monkeypatch, capsys):
    root = setup(tmp_path)
    monkeypatch.setattr(fps, "ROOT", str(root))
    monkeypatch.setattr(fps.urllib.request, "urlopen", router(routes()))
    monkeypatch.setenv("POSTPROXY_API_KEY", KEY)
    assert fps.main(["--date", "2026-11-26", "--days", "8"]) == 0
    out = capsys.readouterr()
    assert "tiktok: 1 videos, 1 followers" in out.out and KEY not in out.out + out.err
    monkeypatch.delenv("POSTPROXY_API_KEY")
    assert fps.main([]) == 1
    assert "POSTPROXY_API_KEY" in capsys.readouterr().err
    assert fps.main(["--bogus"]) == 1
    assert fps.main(["--date"]) == 1


def test_default_opener_and_root(tmp_path, monkeypatch):
    root = setup(tmp_path)
    monkeypatch.setattr(fps, "ROOT", str(root))
    monkeypatch.setattr(fps.urllib.request, "urlopen", router(routes()))
    m = fps.run("2026-11-26", key=KEY)
    assert m["tiktok"]["videos"] and "platforms_pulled_at" in m
