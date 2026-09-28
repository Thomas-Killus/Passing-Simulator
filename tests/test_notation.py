import math
import pytest

from sim.notation import NotationError, parse
from sim.pattern import Throw


SIX_CLUB = """
# 6 clubs, 2 people, 4-count
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


def test_parses_header():
    p = parse(SIX_CLUB)
    assert p.name == "6c 4-count"
    assert p.beat == 0.35


def test_parses_juggler_positions():
    p = parse(SIX_CLUB)
    assert list(p.jugglers) == ["A", "B"]
    assert p.jugglers["A"].pos == (0.0, 1.75)
    assert p.jugglers["B"].pos == (0.0, -1.75)


def test_facing_defaults_to_centroid_of_all_jugglers():
    p = parse(SIX_CLUB)
    assert p.jugglers["A"].facing == (0.0, 0.0)
    assert p.jugglers["B"].facing == (0.0, 0.0)


def test_parses_start_club_counts():
    p = parse(SIX_CLUB)
    assert p.jugglers["A"].start_clubs == {"R": 2, "L": 1}


def test_parses_loop_throws_with_pass_targets():
    p = parse(SIX_CLUB)
    assert p.jugglers["A"].loop == [Throw(3.0, "B"), Throw(3.0, None),
                                    Throw(3.0, None), Throw(3.0, None)]


def test_defaults_phase_and_start_hand():
    p = parse(SIX_CLUB)
    assert p.jugglers["A"].phase == 0.0
    assert p.jugglers["A"].start_hand == "R"
    assert p.jugglers["A"].prelude == []


def test_degree_placement_puts_jugglers_on_a_circle():
    p = parse("""
name: star
beat: 0.35
jugglers:
  A at 0deg
  B at 72deg
  C at 144deg
  D at 216deg
  E at 288deg
start:
  A: R=2 L=1
  B: R=2 L=1
  C: R=2 L=1
  D: R=2 L=1
  E: R=2 L=1
loop:
  A: 3pC 3 3 3
  B: 3pD 3 3 3
  C: 3pE 3 3 3
  D: 3pA 3 3 3
  E: 3pB 3 3 3
""")
    radii = {round(math.hypot(*j.pos), 6) for j in p.jugglers.values()}
    assert len(radii) == 1
    assert p.jugglers["A"].facing == pytest.approx((0.0, 0.0), abs=1e-9)


def test_explicit_facing_point_and_facing_juggler():
    p = parse("""
name: line
beat: 0.35
jugglers:
  A at (0, 0) facing (0, 1)
  B at (2, 0) facing A
start:
  A: R=2 L=1
  B: R=2 L=1
loop:
  A: 3 3
  B: 3 3
""")
    assert p.jugglers["A"].facing == (0.0, 1.0)
    assert p.jugglers["B"].facing == (0.0, 0.0)


def test_phase_and_start_hand_modifiers():
    p = parse("""
name: async
beat: 0.35
jugglers:
  A at (0, 1) phase 0.0
  B at (0, -1) phase 0.5 start_hand L
start:
  A: R=2 L=1
  B: R=2 L=2
loop:
  A: 3.5pB 3
  B: 3.5pA 3
""")
    assert p.jugglers["B"].phase == 0.5
    assert p.jugglers["B"].start_hand == "L"
    assert p.jugglers["A"].loop[0] == Throw(3.5, "B")


def test_prelude_block_and_rest_token():
    p = parse("""
name: prelude test
beat: 0.35
jugglers:
  A at (0, 1)
  B at (0, -1)
start:
  A: R=2 L=1
  B: R=2 L=2
prelude:
  A: 3 -
  B: 4pA
loop:
  A: 3pB 3
  B: 3pA 3
""")
    assert p.jugglers["A"].prelude == [Throw(3.0, None), None]
    assert p.jugglers["B"].prelude == [Throw(4.0, "A")]


def test_unknown_pass_target_is_an_error_naming_the_line():
    with pytest.raises(NotationError) as e:
        parse("""
name: bad
beat: 0.35
jugglers:
  A at (0, 1)
start:
  A: R=2 L=1
loop:
  A: 3pZ 3
""")
    assert "Z" in str(e.value)
    assert "line 9" in str(e.value)


def test_malformed_height_is_an_error():
    with pytest.raises(NotationError) as e:
        parse("""
name: bad
beat: 0.35
jugglers:
  A at (0, 1)
start:
  A: R=2 L=1
loop:
  A: high 3
""")
    assert "high" in str(e.value)


def test_bad_start_line_is_an_error():
    with pytest.raises(NotationError) as e:
        parse("""
name: bad
beat: 0.35
jugglers:
  A at (0, 1)
start:
  A: 3 clubs
loop:
  A: 3 3
""")
    assert "start" in str(e.value).lower()


def test_juggler_without_start_or_loop_is_an_error():
    with pytest.raises(NotationError) as e:
        parse("""
name: bad
beat: 0.35
jugglers:
  A at (0, 1)
  B at (0, -1)
start:
  A: R=2 L=1
loop:
  A: 3 3
  B: 3 3
""")
    assert "B" in str(e.value)


LINE_PAIR = """
name: line pair
beat: 0.32
jugglers:
  A at (0, 1.75)
  B at (0, -1.75) start_hand L
start:
  A: R=2 L=2
  B: R=1 L=2
loop:
  A: 4pB {a} 3
  B: 3 4pA {b}
"""


def test_a_pass_can_be_annotated_line_or_cross():
    p = parse(LINE_PAIR.format(a="line", b="cross"))
    assert p.jugglers["A"].loop[0].want == "line"
    assert p.jugglers["B"].loop[1].want == "cross"


def test_an_unannotated_throw_wants_nothing():
    p = parse(LINE_PAIR.format(a="", b=""))
    assert p.jugglers["A"].loop[0].want is None


def test_the_annotation_does_not_change_how_a_throw_prints():
    p = parse(LINE_PAIR.format(a="line", b="line"))
    assert str(p.jugglers["A"].loop[0]) == "4pB"


def test_annotating_a_self_is_an_error():
    with pytest.raises(NotationError) as e:
        parse(LINE_PAIR.format(a="", b="") .replace("A: 4pB  3", "A: 4pB 3 line"))
    assert "self" in str(e.value).lower()


def test_an_annotation_with_no_throw_before_it_is_an_error():
    with pytest.raises(NotationError) as e:
        parse(LINE_PAIR.replace("  A: 4pB {a} 3", "  A: line 4pB 3")
                       .replace("{b}", ""))
    assert "must follow a pass" in str(e.value)


def test_a_doubled_annotation_is_an_error():
    with pytest.raises(NotationError) as e:
        parse(LINE_PAIR.format(a="line cross", b=""))
    assert "already" in str(e.value).lower()
