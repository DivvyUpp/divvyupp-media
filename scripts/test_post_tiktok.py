import io
import json

import pytest

import post_tiktok as pt

KEY = "pp_s3cret"
URL = "https://www.tiktok.com/@getdivvyupp/video/7712592763354762509"


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


def post(status, permalink=None, error=None, pid="J5tZXb3"):
    return {"id": pid, "platforms": [{"platform": "tiktok", "status": status,
                                      "permalink": permalink, "error": error}]}


def entry(**kw):
    e = {"id": "r1", "kind": "main", "status": "approved", "file": "reels/r1.mp4",
         "caption": "Same $10K.\n\nGet started at divvyupp.com"}
    e.update(kw)
    return e


def write_queue(tmp_path, entries, indent=1):
    p = tmp_path / "queue.json"
    p.write_text(json.dumps(entries, indent=indent, ensure_ascii=False) + "\n")
    return p


def run(p, responses, **kw):
    seen = []
    code = pt.run("r1", key=KEY, opener=opener_from(responses, seen), sleep=lambda s: None,
                  queue_path=str(p), log=lambda m: None, **kw)
    return code, seen, json.loads(p.read_text())


def test_publishes_and_records_ids(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, seen, q = run(p, [post("pending"), post("processing"), post("published", URL)])
    assert code == 0
    assert q[0]["tiktok_id"] == "7712592763354762509"
    assert q[0]["tiktok_url"] == URL
    assert q[0]["tiktok_postproxy_id"] == "J5tZXb3"
    body = json.loads(seen[0].data)
    assert seen[0].get_method() == "POST"
    assert seen[0].get_header("Idempotency-key") == "tiktok-r1"
    assert seen[0].get_header("Authorization") == f"Bearer {KEY}"
    assert body["profiles"] == [pt.PROFILE_ID]
    assert body["media"] == ["https://divvyupp.github.io/divvyupp-media/reels/r1.mp4"]
    assert body["post"]["body"] == entry()["caption"]
    tt = body["platforms"]["tiktok"]
    assert tt["privacy_status"] == "PUBLIC_TO_EVERYONE"
    assert not tt["disable_comment"] and not tt["disable_duet"] and not tt["disable_stitch"]
    assert seen[1].get_method() == "GET" and seen[1].full_url.endswith("/api/posts/J5tZXb3")


def test_tiktok_caption_wins(tmp_path):
    p = write_queue(tmp_path, [entry(tiktok_caption="TT only")])
    code, seen, _ = run(p, [post("published", URL)])
    assert code == 0 and json.loads(seen[0].data)["post"]["body"] == "TT only"


def test_keeps_file_formatting(tmp_path):
    p = write_queue(tmp_path, [entry(caption="Link in bio → divvyupp.com")], indent=1)
    run(p, [post("published", URL)])
    text = p.read_text()
    assert text.endswith("\n") and "→" in text and '\n {' in text


def test_two_space_indent_kept(tmp_path):
    p = write_queue(tmp_path, {"entries": [entry()]}, indent=2)
    code, _, q = run(p, [post("published", URL)])
    assert code == 0 and q["entries"][0]["tiktok_id"]
    assert '\n  "entries"' in p.read_text()


def test_failure_returns_1_and_blocks_repost(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, _, q = run(p, [post("failed", error="bad media")])
    assert code == 1
    assert q[0]["tiktok_postproxy_id"] == "J5tZXb3" and "tiktok_id" not in q[0]
    with pytest.raises(pt.Refused, match="already sent"):
        run(p, [])


def test_timeout_returns_2(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, "POLL_MAX", 2)
    p = write_queue(tmp_path, [entry()])
    code, seen, q = run(p, [post("pending"), post("processing"), post("processing")])
    assert code == 2 and q[0]["tiktok_postproxy_id"] == "J5tZXb3"
    assert len(seen) == 3


def test_published_without_permalink_keeps_waiting(tmp_path):
    p = write_queue(tmp_path, [entry()])
    code, _, _ = run(p, [post("published"), post("published", URL)])
    assert code == 0


@pytest.mark.parametrize("kw,msg", [
    ({"kind": "trial"}, "only main"),
    ({"status": "awaiting_review"}, "only approved"),
    ({"tiktok_id": "1"}, "already on TikTok"),
    ({"file": ""}, "no file"),
])
def test_refusals(tmp_path, kw, msg):
    p = write_queue(tmp_path, [entry(**kw)])
    with pytest.raises(pt.Refused, match=msg):
        run(p, [])


def test_posted_status_allowed_and_missing_kind_is_main(tmp_path):
    e = entry(status="posted")
    del e["kind"]
    p = write_queue(tmp_path, [e])
    code, _, _ = run(p, [post("published", URL)])
    assert code == 0


def test_unknown_entry(tmp_path):
    p = write_queue(tmp_path, [entry()])
    with pytest.raises(pt.Refused, match="no queue entry"):
        pt.run("nope", key=KEY, queue_path=str(p))


def test_missing_key(tmp_path):
    p = write_queue(tmp_path, [entry()])
    with pytest.raises(pt.Refused, match="POSTPROXY_API_KEY"):
        pt.run("r1", key=None, queue_path=str(p))


def test_dry_run_sends_nothing(tmp_path, capsys):
    p = write_queue(tmp_path, [entry()])
    before = p.read_text()
    assert pt.run("r1", dry_run=True, key=None, queue_path=str(p),
                  opener=lambda *a, **k: pytest.fail("network used")) == 0
    assert '"PUBLIC_TO_EVERYONE"' in capsys.readouterr().out
    assert p.read_text() == before


def test_no_tiktok_platform_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(pt, "POLL_MAX", 1)
    p = write_queue(tmp_path, [entry()])
    code, _, _ = run(p, [{"id": "X", "platforms": []}, {"id": "X", "platforms": []}])
    assert code == 2


def test_video_id_from():
    assert pt.video_id_from(URL + "/") == "7712592763354762509"
    assert pt.video_id_from(None) is None


def test_main_usage_and_errors(tmp_path, monkeypatch, capsys):
    assert pt.main([]) == 1
    monkeypatch.delenv("POSTPROXY_API_KEY", raising=False)
    monkeypatch.setattr(pt, "QUEUE", str(write_queue(tmp_path, [entry()])))
    assert pt.main(["r1"]) == 1
    assert "POSTPROXY_API_KEY" in capsys.readouterr().err
    assert pt.main(["r1", "--dry-run"]) == 0


def test_main_http_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pt, "QUEUE", str(write_queue(tmp_path, [entry()])))
    err = pt.urllib.error.HTTPError("u", 422, "x", {}, io.BytesIO(b'{"error":"bad"}'))

    def boom(*a, **k):
        raise err

    monkeypatch.setenv("POSTPROXY_API_KEY", KEY)
    monkeypatch.setattr(pt.urllib.request, "urlopen", boom)
    assert pt.main(["r1"]) == 1
    out = capsys.readouterr().err
    assert "HTTP 422" in out and KEY not in out


def test_default_log_and_sleep(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pt, "QUEUE", str(write_queue(tmp_path, [entry()])))
    monkeypatch.setattr(pt.time, "sleep", lambda s: None)
    seen = []
    monkeypatch.setattr(pt.urllib.request, "urlopen",
                        opener_from([post("pending"), post("published", URL)], seen))
    assert pt.run("r1", key=KEY) == 0
    assert "sent to Postproxy" in capsys.readouterr().err


def test_other_entries_and_platforms_are_skipped(tmp_path):
    p = write_queue(tmp_path, [entry(id="other"), entry()])
    both = {"id": "J5tZXb3", "platforms": [{"platform": "instagram", "status": "failed"},
                                         {"platform": "tiktok", "status": "published",
                                          "permalink": URL}]}
    code, _, q = run(p, [both])
    assert code == 0 and "tiktok_id" not in q[0] and q[1]["tiktok_id"]


def test_no_trailing_newline_kept(tmp_path):
    p = tmp_path / "queue.json"
    p.write_text(json.dumps([entry()], indent=1))
    code, _, _ = run(p, [post("published", URL)])
    assert code == 0 and not p.read_text().endswith("\n")
