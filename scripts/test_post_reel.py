import datetime
import io
import json

import pytest

import post_postproxy as pp
import post_reel as pr
from test_post_postproxy import KEY, TT, YT, FakeResp, entry, opener_from, post, write_queue

IG = "https://www.instagram.com/reel/DgOZaYIIR81/"
NOW = datetime.datetime(2026, 11, 27, 16, 58, 5, 123, tzinfo=datetime.timezone.utc)
FILE_URL = "https://divvyupp.github.io/divvyupp-media/reels/r1.mp4"


def ig(status, link=None, err=None, pid="I1"):
    return {"id": pid, "platforms": [{"platform": "instagram", "status": status, "permalink": link,
                                      "error": err}]}


def recent(*posts):
    return {"data": list(posts)}


def comments(*rows):
    return {"data": list(rows)}


@pytest.fixture(autouse=True)
def _no_repo_covers(tmp_path_factory, monkeypatch):
    monkeypatch.setattr(pr, "ROOT", str(tmp_path_factory.mktemp("root")))


def run(p, responses, entry_id="r1", **kw):
    seen, logs = [], []
    code = pr.run(entry_id, key=KEY, opener=opener_from(responses, seen), sleep=lambda s: None,
                  queue_path=str(p), log=logs.append, now=lambda: NOW, **kw)
    return code, seen, json.loads(p.read_text()), logs


def test_all_three_platforms(tmp_path, capsys):
    p = write_queue(tmp_path, [entry(first_comment="Start at divvyupp.com")])
    code, seen, q, logs = run(p, [
        recent(),
        ig("processing"), ig("published", IG),
        comments({"body": "someone else", "external_id": "9"},
                 {"body": "Start at divvyupp.com", "external_id": "18001"}),
        post(("pending",), ("pending",), pid="P2"), post(("published", TT), ("published", YT), pid="P2"),
    ])
    assert code == 0
    e = q[0]
    assert e["status"] == "posted" and e["posted_at"] == "2026-11-27T11:58:05-05:00"
    assert e["instagram_postproxy_id"] == "I1" and e["instagram_url"] == IG
    assert e["instagram_id"] == "DgOZaYIIR81" and e["first_comment_id"] == "18001"
    assert "media_id" not in e
    assert e["tiktok_postproxy_id"] == e["youtube_postproxy_id"] == "P2"
    assert e["tiktok_url"] == TT and e["youtube_url"] == YT
    assert seen[0].get_method() == "GET" and "profiles=instagram" in seen[0].full_url
    body = json.loads(seen[1].data)
    assert seen[1].get_header("Idempotency-key") == "instagram-r1"
    assert body == {"post": {"body": entry()["caption"]}, "profiles": ["6lUEBB"], "media": [FILE_URL],
                    "platforms": {"instagram": {"format": "reel", "share_to_feed": True,
                                                "first_comment": "Start at divvyupp.com"}}}
    assert seen[2].full_url.endswith("/api/posts/I1")
    assert seen[3].full_url.endswith("/api/posts/I1/comments?profile_id=6lUEBB")
    assert json.loads(seen[4].data)["profiles"] == ["MZU39X", "rOUpVX"]
    assert f"instagram: {IG}" in capsys.readouterr().out


def test_no_first_comment_skips_comment_lookup(tmp_path):
    p = write_queue(tmp_path, [entry(first_comment="hi", first_comment_id="old")])
    code, seen, q, _ = run(p, [recent(), ig("published", IG), post(("published", TT), ("published", YT))])
    assert code == 0 and "first_comment" not in json.loads(seen[1].data)["platforms"]["instagram"]
    assert q[0]["first_comment_id"] == "old" and len(seen) == 3


def test_first_comment_not_listed_yet(tmp_path):
    p = write_queue(tmp_path, [entry(first_comment="hi")])
    code, _, q, logs = run(p, [recent(), ig("published", IG), [{"body": "hi", "external_id": None}],
                               post(("published", TT), ("published", YT))])
    assert code == 0 and "first_comment_id" not in q[0]
    assert any("not listed by Postproxy yet" in m for m in logs)


def test_first_comment_lookup_error_never_fails(tmp_path):
    p = write_queue(tmp_path, [entry(first_comment="hi")])
    err = pp.urllib.error.HTTPError("u", 500, "x", {}, io.BytesIO(b""))
    code, _, q, logs = run(p, [recent(), ig("published", IG), err,
                               post(("published", TT), ("published", YT))])
    assert code == 0 and q[0]["status"] == "posted"
    assert any("couldn't read comments back" in m for m in logs)


def test_instagram_fails_nothing_else_sent(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, seen, q, logs = run(p, [recent(), ig("failed", err="aspect ratio")])
    assert code == 1 and len(seen) == 2
    assert q[0]["status"] == "approved" and q[0]["instagram_postproxy_id"] == "I1"
    assert "tiktok_postproxy_id" not in q[0]
    assert any("instagram: publish failed: aspect ratio" in m for m in logs)
    assert any("not sent, because Instagram is not live" in m for m in logs)
    with pytest.raises(pp.Refused, match="never re-post"):
        run(p, [])


def test_instagram_timeout_returns_2(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "POLL_MAX", 2)
    p = write_queue(tmp_path, [entry()])
    code, seen, q, logs = run(p, [recent(), ig("processing"), ig("processing"), ig("processing")])
    assert code == 2 and len(seen) == 4 and q[0]["status"] == "approved"
    assert any("instagram: still 'processing'" in m and "I1" in m for m in logs)


def test_published_without_permalink_keeps_waiting(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, _, q, _ = run(p, [recent(), ig("published"), ig("published", "https://instagram.com/p/AbC_1"),
                            post(("published", TT), ("published", YT))])
    assert code == 0 and q[0]["instagram_id"] == "AbC_1"


def test_earlier_send_of_same_file_refused(tmp_path):
    p = write_queue(tmp_path, [entry()])
    other = {"id": "OLD", "media": [{"source_url": "https://divvyupp.github.io/divvyupp-media/x.mp4"}],
             "platforms": [{"platform": "instagram"}]}
    tt_only = {"id": "TTONLY", "media": [{"source_url": FILE_URL}], "platforms": [{"platform": "tiktok"}]}
    dup = {"id": "DUP", "media": [{"source_url": FILE_URL}], "platforms": [{"platform": "instagram"}]}
    with pytest.raises(pp.Refused, match="DUP already sent"):
        run(p, [recent(other, tt_only, dup)])
    assert "instagram_postproxy_id" not in json.loads(p.read_text())[0]


def test_trial_goes_to_instagram_only(tmp_path):
    p = write_queue(tmp_path, [entry(kind="trial", first_comment="no")])
    code, seen, q, _ = run(p, [recent(), ig("published", IG)])
    assert code == 0 and len(seen) == 2 and q[0]["status"] == "posted"
    assert json.loads(seen[1].data)["platforms"]["instagram"] == {"format": "reel", "trial_strategy": "MANUAL"}


def test_instagram_live_finishes_other_platforms(tmp_path):
    e = entry(status="posted", media_id="17954745858342945")
    del e["kind"]
    p = write_queue(tmp_path, [e])
    code, seen, q, logs = run(p, [post(("published", TT), ("published", YT))])
    assert code == 0 and len(seen) == 1 and q[0]["tiktok_id"]
    assert any("instagram: already live (17954745858342945)" in m for m in logs)


def test_everything_already_live(tmp_path):
    p = write_queue(tmp_path, [entry(status="posted", instagram_id="X", tiktok_id="1", youtube_id="2")])
    code, seen, _, logs = run(p, [])
    assert code == 0 and seen == [] and any("tiktok/youtube: " in m and "nothing left" in m for m in logs)


def test_tiktok_youtube_refusal_propagates(tmp_path):
    p = write_queue(tmp_path, [entry(status="posted", instagram_id="X", hook=" (note)")])
    with pytest.raises(pp.Refused, match="no hook"):
        run(p, [])


@pytest.mark.parametrize("kw,msg", [
    ({"kind": "story"}, "only main and trial"),
    ({"status": "awaiting_review"}, "only approved"),
    ({"status": "posted"}, "only approved"),
    ({"kind": "trial", "status": "posted", "instagram_id": "X"}, "trials go nowhere else"),
    ({"file": ""}, "no file"),
    ({"caption": ""}, "no caption"),
    ({"instagram_postproxy_id": "I9"}, "I9; check that post"),
])
def test_refusals(tmp_path, kw, msg):
    p = write_queue(tmp_path, [entry(**kw)])
    with pytest.raises(pp.Refused, match=msg):
        run(p, [])


def test_missing_key(tmp_path):
    p = write_queue(tmp_path, [entry()])
    with pytest.raises(pp.Refused, match="POSTPROXY_API_KEY"):
        pr.run("r1", key=None, queue_path=str(p))


def test_dry_run_sends_nothing(tmp_path, capsys):
    p = write_queue(tmp_path, [entry(), entry(id="t", kind="trial"),
                               entry(id="done", status="posted", media_id="1", tiktok_id="1", youtube_id="2")])
    before = p.read_text()
    no_net = lambda *a, **k: pytest.fail("network used")  # noqa: E731
    assert pr.run("r1", dry_run=True, queue_path=str(p), opener=no_net) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["instagram"]["profiles"] == ["6lUEBB"]
    assert out["tiktok_youtube"]["profiles"] == ["MZU39X", "rOUpVX"]
    assert pr.run("t", dry_run=True, queue_path=str(p), opener=no_net) == 0
    assert "tiktok_youtube" not in json.loads(capsys.readouterr().out)
    assert pr.run("done", dry_run=True, queue_path=str(p), opener=no_net) == 0
    assert json.loads(capsys.readouterr().out) == {"instagram": None, "tiktok_youtube": None}
    assert p.read_text() == before


def test_shortcode():
    assert pr.shortcode("https://www.instagram.com/p/DgOZaYIIR81") == "DgOZaYIIR81"
    assert pr.shortcode("https://instagram.com/reels/a-B_c/") == "a-B_c"
    assert pr.shortcode("https://example.com/odd/") == "odd"


@pytest.mark.parametrize("argv", [[], ["a", "b"], ["r1", "--bogus"]])
def test_main_usage(argv):
    assert pr.main(argv) == 1


def test_main_dry_run_refusal_and_http_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pp, "QUEUE", str(write_queue(tmp_path, [entry()])))
    assert pr.main(["r1", "--dry-run"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("POSTPROXY_API_KEY", raising=False)
    assert pr.main(["r1"]) == 1
    assert "POSTPROXY_API_KEY" in capsys.readouterr().err
    err = pp.urllib.error.HTTPError("u", 422, "x", {}, io.BytesIO(b'{"error":"bad"}'))

    def boom(*a, **k):
        raise err

    monkeypatch.setenv("POSTPROXY_API_KEY", KEY)
    monkeypatch.setattr(pr.urllib.request, "urlopen", boom)
    assert pr.main(["r1"]) == 1
    out = capsys.readouterr().err
    assert "HTTP 422" in out and KEY not in out


def test_defaults(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pp, "QUEUE", str(write_queue(tmp_path, [entry()])))
    monkeypatch.setattr(pr.time, "sleep", lambda s: None)
    seen = []
    monkeypatch.setattr(pr.urllib.request, "urlopen",
                        opener_from([recent(), ig("pending"), ig("published", IG),
                                     post(("published", TT), ("published", YT))], seen))
    assert pr.run("r1", key=KEY) == 0
    q = json.loads(open(pp.QUEUE).read())
    assert q[0]["posted_at"].endswith(("-05:00", "-04:00"))
    assert "sent to Postproxy as I1" in capsys.readouterr().err


def test_fake_resp_reexport():
    assert FakeResp(b"{}").read() == b"{}"


def test_cover_from_entry_and_from_rendered_file(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "ROOT", str(tmp_path))
    assert pr.ig_payload(entry(cover="reels/x.jpg"))["platforms"]["instagram"]["cover_url"] == \
        "https://divvyupp.github.io/divvyupp-media/reels/x.jpg"
    assert "cover_url" not in pr.ig_payload(entry())["platforms"]["instagram"]
    (tmp_path / "reels").mkdir(); (tmp_path / "reels" / "r1_cover.jpg").write_bytes(b"jpg")
    assert pr.ig_payload(entry())["platforms"]["instagram"]["cover_url"] == \
        "https://divvyupp.github.io/divvyupp-media/reels/r1_cover.jpg"
    assert pr.ig_payload(entry(kind="trial"))["platforms"]["instagram"]["cover_url"].endswith("r1_cover.jpg")
