"""The static site build — what GitHub Pages publishes."""

import json

from sim.build import build


def test_build_writes_one_json_per_pattern_plus_an_index(tmp_path):
    assert build(out=tmp_path) == []
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index) >= 10
    for entry in index:
        assert (tmp_path / f"{entry['id']}.json").exists()
        assert entry["clubs"] > 0 and entry["jugglers"] > 0
        assert entry["summary"]


def test_every_published_pattern_is_playable(tmp_path):
    build(out=tmp_path)
    for path in tmp_path.glob("*.json"):
        if path.stem == "index":
            continue
        doc = json.loads(path.read_text())
        assert doc["report"]["ok"], path.stem
        assert doc["clubs"] and doc["jugglers"] and doc["events"]


def test_build_removes_json_for_patterns_that_no_longer_exist(tmp_path):
    (tmp_path / "ghost.json").write_text("{}")
    build(out=tmp_path)
    assert not (tmp_path / "ghost.json").exists()


def test_the_committed_site_is_up_to_date(tmp_path):
    """docs/patterns is committed, so a stale build would ship a stale site."""
    from pathlib import Path
    build(out=tmp_path)
    live = Path("docs/patterns")
    fresh = {p.name for p in tmp_path.glob("*.json")}
    assert fresh == {p.name for p in live.glob("*.json")}
    assert json.loads((live / "index.json").read_text()) == \
           json.loads((tmp_path / "index.json").read_text())
