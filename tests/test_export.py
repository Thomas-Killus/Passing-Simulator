import pytest

from sim.engine import simulate
from sim.export import to_json
from sim.notation import parse

SIX_CLUB = """
name: 6c 4-count
beat: 0.35
jugglers:
  A at (0, 1.75)
  B at (0, -1.75)
start:
  A: R=2 L=1
  B: R=2 L=1
loop:
  A: 3pB 3 3 3
  B: 3pA 3 3 3
"""


@pytest.fixture
def doc():
    return to_json(simulate(parse(SIX_CLUB), beats=32))


def test_top_level_shape(doc):
    assert doc["name"] == "6c 4-count"
    assert doc["beat"] == 0.35
    assert doc["period"] == 4
    assert doc["gravity"] == pytest.approx(9.81 * 0.35 ** 2)
    assert doc["report"]["ok"] is True
    assert doc["report"]["clubs"] == 6


def test_jugglers_carry_positions_and_hand_points(doc):
    a = next(j for j in doc["jugglers"] if j["id"] == "A")
    assert len(a["pos"]) == 3
    assert len(a["facing"]) == 3
    assert len(a["hands"]["R"]["throw"]) == 3


def test_every_club_has_flights_with_endpoints_and_times(doc):
    assert len(doc["clubs"]) == 6
    flight = doc["clubs"][0]["flights"][0]
    assert flight["t1"] > flight["t0"]
    assert len(flight["from"]) == 3
    assert len(flight["to"]) == 3
    assert flight["kind"] in ("self", "pass", "zip", "hold")
    assert flight["apex"] >= flight["from"][2]


def test_a_pass_flight_ends_at_the_partners_catch_point(doc):
    a = next(j for j in doc["jugglers"] if j["id"] == "A")
    b = next(j for j in doc["jugglers"] if j["id"] == "B")
    passes = [f for c in doc["clubs"] for f in c["flights"] if f["kind"] == "pass"]
    first = min(passes, key=lambda f: f["t0"])
    assert first["from"] == a["hands"]["R"]["throw"]
    assert first["to"] == b["hands"]["L"]["catch"]


def test_events_are_json_safe_and_ordered(doc):
    beats = [e["beat"] for e in doc["events"]]
    assert beats == sorted(beats)
    first = doc["events"][0]
    assert set(first) == {"beat", "juggler", "hand", "throw", "height", "target",
                          "club", "land_beat", "land_juggler", "land_hand", "line"}
    assert first["throw"] == "3pB"


def test_causal_arrows_point_two_beats_before_the_catch(doc):
    arrow = next(a for a in doc["causal"] if a["from"] == ["A", 0])
    assert arrow["to"] == ["B", 1]


def test_document_serialises(doc):
    import json
    json.dumps(doc)


def test_clubs_waiting_in_a_hand_are_stacked_so_they_do_not_overlap(doc):
    a_right = [c for c in doc["clubs"] if c["start"] == ["A", "R"]]
    assert sorted(c["stack"] for c in a_right) == [0, 1]
    assert all(c["stack"] == 0 for c in doc["clubs"] if c["start"] == ["A", "L"])


def test_events_and_pass_flights_say_whether_they_were_line_or_cross(doc):
    first_pass = next(e for e in doc["events"] if e["target"])
    assert first_pass["line"] is True          # 6c 4-count passes R -> partner's L
    flight = next(f for c in doc["clubs"] for f in c["flights"] if f["kind"] == "pass")
    assert flight["line"] is True
    assert all(f["line"] is False for c in doc["clubs"]
               for f in c["flights"] if f["kind"] == "hold")
