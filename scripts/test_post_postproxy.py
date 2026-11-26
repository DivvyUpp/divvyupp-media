import io
import json

import pytest

import post_postproxy as pp
import post_tiktok

KEY = "pp_s3cret"
TT = "https://www.tiktok.com/@getdivvyupp/video/7712592763354762509"
YT = "https://www.youtube.com/watch?v=U82Qn1ZS-GU"


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_from(responses, seen):
    queue = list(responses)

    def _open(req, timeout):
        seen.append(req)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResp(json.dumps(item).encode())

    return _open


def post(tt=None, yt=None, pid="P1"):
    """tt / yt: (status, permalink, error) or None to leave the platform out."""
    plats = []
    for name, s in (("tiktok", tt), ("youtube", yt)):
        if s is not None:
            status, link, err = (tuple(s) + (None, None))[:3]
            plats.append({"platform": name, "status": status, "permalink": link, "error": err})
    return {"id": pid, "platforms": plats}


def entry(**kw):
    e = {"id": "r1", "kind": "main", "status": "approved", "file": "reels/r1.mp4",
         "hook": "Paying the minimum? (Study Reel S8 v2: tip #5)",
         "caption": "Same $10K.\n\nGet started at divvyupp.com"}
    e.update(kw)
    return e


def write_queue(tmp_path, entries, indent=1, newline=True):
    p = tmp_path / "queue.json"
    p.write_text(json.dumps(entries, indent=indent, ensure_ascii=False) + ("\n" if newline else ""))
    return p


def run(p, responses, entry_id="r1", **kw):
    seen, logs = [], []
    code = pp.run(entry_id, key=KEY, opener=opener_from(responses, seen), sleep=lambda s: None,
                  queue_path=str(p), log=logs.append, **kw)
    return code, seen, json.loads(p.read_text()), logs


def test_both_platforms_in_one_request(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, seen, q, _ = run(p, [post(("pending",), ("pending",)),
                               post(("published", TT), ("processing",)),
                               post(("published", TT), ("published", YT))])
    assert code == 0
    e = q[0]
    assert e["tiktok_id"] == "7712592763354762509" and e["tiktok_url"] == TT
    assert e["youtube_id"] == "U82Qn1ZS-GU" and e["youtube_url"] == YT
    assert e["tiktok_postproxy_id"] == e["youtube_postproxy_id"] == "P1"
    req = seen[0]
    body = json.loads(req.data)
    assert req.get_method() == "POST" and req.get_header("Authorization") == f"Bearer {KEY}"
    assert req.get_header("Idempotency-key") == "tiktok-youtube-r1"
    assert body["profiles"] == ["MZU39X", "rOUpVX"]
    assert body["media"] == ["https://divvyupp.github.io/divvyupp-media/reels/r1.mp4"]
    assert body["post"]["body"] == entry()["caption"]
    tt = body["platforms"]["tiktok"]
    assert tt["privacy_status"] == "PUBLIC_TO_EVERYONE"
    assert not (tt["disable_comment"] or tt["disable_duet"] or tt["disable_stitch"])
    assert body["platforms"]["youtube"] == {"title": "Paying the minimum?", "privacy_status": "public"}
    assert seen[1].get_method() == "GET" and seen[1].full_url.endswith("/api/posts/P1")


def test_already_live_platform_left_out(tmp_path):
    p = write_queue(tmp_path, [entry(tiktok_id="1")])
    code, seen, q, logs = run(p, [post(yt=("published", YT))])
    body = json.loads(seen[0].data)
    assert code == 0 and body["profiles"] == ["rOUpVX"] and "tiktok" not in body["platforms"]
    assert seen[0].get_header("Idempotency-key") == "youtube-r1"
    assert any("tiktok: already live" in m for m in logs)


def test_already_sent_platform_left_out(tmp_path):
    p = write_queue(tmp_path, [entry(youtube_postproxy_id="X")])
    code, seen, _, logs = run(p, [post(tt=("published", TT))])
    assert code == 0 and json.loads(seen[0].data)["profiles"] == ["MZU39X"]
    assert any("never re-post" in m for m in logs)


def test_nothing_left_refused(tmp_path):
    p = write_queue(tmp_path, [entry(tiktok_id="1", youtube_id="2")])
    with pytest.raises(pp.Refused, match="nothing left"):
        run(p, [])


def test_one_fails_other_recorded(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, _, q, logs = run(p, [post(("published", TT), ("failed", None, "quota"))])
    assert code == 1
    assert q[0]["tiktok_id"] and "youtube_id" not in q[0] and q[0]["youtube_postproxy_id"] == "P1"
    assert any("youtube: publish failed: quota" in m for m in logs)
    with pytest.raises(pp.Refused, match="nothing left"):
        run(p, [])


def test_timeout_returns_2(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "POLL_MAX", 2)
    p = write_queue(tmp_path, [entry()])
    code, seen, q, logs = run(p, [post(("published", TT), ("pending",)),
                                  post(yt=("processing",)), post(yt=("processing",))])
    assert code == 2 and q[0]["tiktok_id"] and "youtube_id" not in q[0]
    assert len(seen) == 3 and any("youtube: still 'processing'" in m for m in logs)


def test_timeout_with_a_failure_returns_1(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "POLL_MAX", 1)
    p = write_queue(tmp_path, [entry()])
    code, _, _, _ = run(p, [post(("failed",), ("pending",)), post(yt=("pending",))])
    assert code == 1


def test_published_without_permalink_keeps_waiting(tmp_path):
    p = write_queue(tmp_path, [entry()], indent=2)
    code, _, q, _ = run(p, [post(("published",), ("published",)),
                            post(("published", TT), ("published", YT))])
    assert code == 0 and q[0]["youtube_id"]


def test_only_flag_and_tiktok_wrapper(tmp_path, monkeypatch, capsys):
    p = write_queue(tmp_path, [entry()])
    monkeypatch.setattr(pp, "QUEUE", str(p))
    assert post_tiktok.main(["r1", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["profiles"] == ["MZU39X"]
    assert pp.main(["r1", "--only", "youtube", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["profiles"] == ["rOUpVX"]
    assert pp.main(["r1", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["profiles"] == ["MZU39X", "rOUpVX"]


@pytest.mark.parametrize("argv", [[], ["a", "b"], ["r1", "--only", "instagram"], ["r1", "--bogus"]])
def test_main_usage(argv):
    assert pp.main(argv) == 1


@pytest.mark.parametrize("cap,want", [
    ("Same $10K.\n\nGet started. Link in the comments.\n\n#money", "Same $10K.\n\nGet started.\n\n#money"),
    ("Hook.\n\nLink in the comments.\n\n#a #b", "Hook.\n\n#a #b"),
    ("Free in beta. Link in the comments. Terms apply.", "Free in beta. Terms apply."),
    ("No link line here.", "No link line here."),
])
def test_caption_drops_instagram_only_comment_line(cap, want):
    assert pp.caption(entry(caption=cap)) == want


def test_tiktok_caption_used_verbatim():
    assert pp.caption(entry(tiktok_caption="Link in the comments.")) == "Link in the comments."


def test_youtube_title_rules():
    assert pp.youtube_title(entry(hook="x" * 150)) == "x" * 100
    assert pp.youtube_title(entry(hook="Plain hook")) == "Plain hook"
    with pytest.raises(pp.Refused, match="no hook"):
        pp.youtube_title(entry(hook=" (note only)"))


@pytest.mark.parametrize("kw,msg", [
    ({"kind": "trial"}, "only main"),
    ({"status": "awaiting_review"}, "only approved"),
    ({"file": ""}, "no file"),
])
def test_refusals(tmp_path, kw, msg):
    p = write_queue(tmp_path, [entry(**kw)])
    with pytest.raises(pp.Refused, match=msg):
        run(p, [])


def test_posted_status_missing_kind_and_other_entries(tmp_path):
    e = entry(status="posted")
    del e["kind"]
    p = write_queue(tmp_path, [entry(id="other"), e], newline=False)
    code, _, q, _ = run(p, [post(("published", TT), ("published", YT))])
    assert code == 0 and "tiktok_id" not in q[0] and q[1]["youtube_id"]
    assert not p.read_text().endswith("\n")


def test_unknown_entry_and_missing_key(tmp_path):
    p = write_queue(tmp_path, [entry()])
    with pytest.raises(pp.Refused, match="no queue entry"):
        pp.run("nope", key=KEY, queue_path=str(p))
    with pytest.raises(pp.Refused, match="POSTPROXY_API_KEY"):
        pp.run("r1", key=None, queue_path=str(p))


def test_dry_run_sends_nothing(tmp_path):
    p = write_queue(tmp_path, [entry()])
    before = p.read_text()
    assert pp.run("r1", dry_run=True, queue_path=str(p),
                  opener=lambda *a, **k: pytest.fail("network used")) == 0
    assert p.read_text() == before


def test_platform_id():
    assert pp.platform_id("youtube", YT) == "U82Qn1ZS-GU"
    assert pp.platform_id("youtube", "https://youtube.com/shorts/abc_D-1") == "abc_D-1"
    assert pp.platform_id("youtube", "https://example.com/v/odd/") == "odd"
    assert pp.platform_id("tiktok", TT + "/") == "7712592763354762509"


def test_main_missing_key_and_http_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pp, "QUEUE", str(write_queue(tmp_path, [entry()])))
    monkeypatch.delenv("POSTPROXY_API_KEY", raising=False)
    assert pp.main(["r1"]) == 1
    assert "POSTPROXY_API_KEY" in capsys.readouterr().err
    err = pp.urllib.error.HTTPError("u", 422, "x", {}, io.BytesIO(b'{"error":"bad"}'))

    def boom(*a, **k):
        raise err

    monkeypatch.setenv("POSTPROXY_API_KEY", KEY)
    monkeypatch.setattr(pp.urllib.request, "urlopen", boom)
    assert pp.main(["r1"]) == 1
    out = capsys.readouterr().err
    assert "HTTP 422" in out and KEY not in out


def test_default_log_and_sleep(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pp, "QUEUE", str(write_queue(tmp_path, [entry()])))
    monkeypatch.setattr(pp.time, "sleep", lambda s: None)
    seen = []
    monkeypatch.setattr(pp.urllib.request, "urlopen",
                        opener_from([post(("pending",), ("pending",)),
                                     post(("published", TT), ("published", YT))], seen))
    assert pp.run("r1", key=KEY) == 0
    assert "sent to Postproxy" in capsys.readouterr().err
