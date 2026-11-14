import datetime as dt
import io
import json
import os
import urllib.error

import pytest

import fetch_funnel as ff

TOKEN = "tok_s3cret_value"


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("u", code, "x", headers, None)


def opener_from(responses, seen=None):
    """responses: list consumed in order; each a dict (200 body) or an exception."""
    queue = list(responses)

    def _open(req, timeout):
        if seen is not None:
            seen.append(req)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResp(json.dumps(item).encode())

    return _open


BODY_IG = {"timezone": "America/New_York", "source_filter": "instagram", "days": []}
BODY_ALL = {"timezone": "America/New_York", "source_filter": None, "days": []}
ENV = {"FUNNEL_EXPORT_TOKEN": TOKEN}
MONDAY = dt.date(2026, 11, 16)
NOW = dt.datetime(2026, 11, 16, 10, 40, tzinfo=dt.timezone.utc)


def test_previous_week_is_prior_monday_to_sunday():
    assert ff.previous_week(MONDAY) == (dt.date(2026, 11, 9), dt.date(2026, 11, 15))
    assert ff.previous_week(dt.date(2026, 11, 22)) == (dt.date(2026, 11, 9), dt.date(2026, 11, 15))


def test_iso_week_filename_at_year_boundary(tmp_path):
    # Mon 28 Dec 2026 starts ISO week 2026-W53; Mon 4 Jan 2027 is 2027-W01.
    assert ff.output_path(str(tmp_path), dt.date(2026, 12, 28), dt.date(2027, 1, 3), False).endswith("funnel/2026-W53.json")
    assert ff.output_path(str(tmp_path), dt.date(2027, 1, 4), dt.date(2027, 1, 10), False).endswith("funnel/2027-W01.json")


def test_success_writes_documented_shape(tmp_path, capsys):
    seen = []
    rc = ff.run(ENV, str(tmp_path), MONDAY, opener_from([BODY_IG, BODY_ALL], seen), sleep=lambda s: None, now=NOW)
    assert rc == 0
    doc = json.loads((tmp_path / "funnel" / "2026-W46.json").read_text())
    assert set(doc) == {"week", "fetched_at", "from", "to", "instagram", "all_sources"}
    assert doc["week"] == "2026-W46" and doc["from"] == "2026-11-09" and doc["to"] == "2026-11-15"
    assert doc["instagram"] == BODY_IG and doc["all_sources"] == BODY_ALL
    assert "source=instagram" in seen[0].full_url and "source" not in seen[1].full_url
    assert seen[0].get_header("Authorization") == f"Bearer {TOKEN}"
    out = capsys.readouterr()
    assert TOKEN not in out.out and TOKEN not in out.err


@pytest.mark.parametrize("second", [http_error(403), http_error(500), http_error(500), urllib.error.URLError("down")])
def test_one_failed_fetch_writes_nothing(tmp_path, capsys, second):
    responses = [BODY_IG] + [second] * (ff.MAX_RETRIES + 1)
    rc = ff.run(ENV, str(tmp_path), MONDAY, opener_from(responses), sleep=lambda s: None, now=NOW)
    assert rc == 1
    assert not (tmp_path / "funnel").exists() or not os.listdir(tmp_path / "funnel")
    assert TOKEN not in capsys.readouterr().err


def test_429_honours_retry_after_then_succeeds(tmp_path):
    slept = []
    responses = [http_error(429, "7"), BODY_IG, BODY_ALL]
    rc = ff.run(ENV, str(tmp_path), MONDAY, opener_from(responses), sleep=slept.append, now=NOW)
    assert rc == 0 and slept == [7.0]


def test_401_is_not_retried(tmp_path):
    slept = []
    rc = ff.run(ENV, str(tmp_path), MONDAY, opener_from([http_error(401)]), sleep=slept.append, now=NOW)
    assert rc == 1 and slept == []


def test_unchanged_content_is_not_rewritten(tmp_path, capsys):
    ff.run(ENV, str(tmp_path), MONDAY, opener_from([BODY_IG, BODY_ALL]), sleep=lambda s: None, now=NOW)
    p = tmp_path / "funnel" / "2026-W46.json"
    before = p.read_text()
    later = NOW + dt.timedelta(hours=1)
    rc = ff.run(ENV, str(tmp_path), MONDAY, opener_from([BODY_IG, BODY_ALL]), sleep=lambda s: None, now=later)
    assert rc == 0 and p.read_text() == before
    assert "unchanged" in capsys.readouterr().out


def test_custom_range_writes_custom_file(tmp_path):
    env = dict(ENV, FROM_DATE="2026-11-01", TO_DATE="2026-11-03")
    rc = ff.run(env, str(tmp_path), MONDAY, opener_from([BODY_IG, BODY_ALL]), sleep=lambda s: None, now=NOW)
    assert rc == 0
    assert os.listdir(tmp_path / "funnel") == ["custom-2026-11-01_2026-11-03.json"]


@pytest.mark.parametrize("env", [
    {},
    {"FUNNEL_EXPORT_TOKEN": TOKEN, "FROM_DATE": "2026-11-01"},
    {"FUNNEL_EXPORT_TOKEN": TOKEN, "FROM_DATE": "nope", "TO_DATE": "2026-11-03"},
])
def test_bad_configuration_fails_without_requests(tmp_path, env):
    rc = ff.run(env, str(tmp_path), MONDAY, opener_from([]), sleep=lambda s: None, now=NOW)
    assert rc == 1
