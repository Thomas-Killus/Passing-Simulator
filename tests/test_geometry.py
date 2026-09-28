import math

import pytest

from sim.geometry import apex_height, gravity_per_beat, layout
from sim.notation import parse

FACING = """
name: pair
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


def dist(a, b):
    return math.dist(a, b)


def test_facing_vector_points_from_the_juggler_at_their_facing_target():
    frames = layout(parse(FACING))
    assert frames["A"].facing == pytest.approx((0.0, -1.0, 0.0))
    assert frames["B"].facing == pytest.approx((0.0, 1.0, 0.0))


def test_right_vector_is_perpendicular_to_facing_and_horizontal():
    a = layout(parse(FACING))["A"]
    assert sum(f * r for f, r in zip(a.facing, a.right)) == pytest.approx(0.0)
    assert a.right[2] == pytest.approx(0.0)
    assert math.hypot(*a.right[:2]) == pytest.approx(1.0)


def test_facing_minus_y_puts_the_right_hand_toward_minus_x():
    a = layout(parse(FACING))["A"]
    assert a.right == pytest.approx((-1.0, 0.0, 0.0))


def test_a_straight_pass_right_to_partners_left_is_shorter_than_right_to_right():
    f = layout(parse(FACING))
    straight = dist(f["A"].hands["R"]["throw"], f["B"].hands["L"]["catch"])
    crossing = dist(f["A"].hands["R"]["throw"], f["B"].hands["R"]["catch"])
    assert straight < crossing


def test_hands_are_at_a_plausible_height_above_the_ground():
    a = layout(parse(FACING))["A"]
    for hand in ("R", "L"):
        for point in ("throw", "catch"):
            assert 0.8 < a.hands[hand][point][2] < 1.4


def test_catch_point_is_further_out_to_the_side_than_the_throw_point():
    a = layout(parse(FACING))["A"]
    def sideways(point):
        return abs(sum((p - c) * r for p, c, r in zip(point, a.pos, a.right)))
    assert sideways(a.hands["R"]["catch"]) > sideways(a.hands["R"]["throw"])


def test_five_jugglers_are_evenly_spaced_on_a_circle_all_facing_the_middle():
    frames = layout(parse("""
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
"""))
    for frame in frames.values():
        to_middle = (-frame.pos[0], -frame.pos[1])
        length = math.hypot(*to_middle)
        assert frame.facing[:2] == pytest.approx(
            (to_middle[0] / length, to_middle[1] / length))


def test_gravity_in_metres_per_beat_squared_matches_real_gravity():
    assert gravity_per_beat(0.35) == pytest.approx(9.81 * 0.35 ** 2)
    assert gravity_per_beat(1.0) == pytest.approx(9.81)


def test_apex_rises_with_flight_duration():
    g = gravity_per_beat(0.35)
    single = apex_height((0, 0, 1.0), (0, 0, 1.0), 2.6, g)
    double = apex_height((0, 0, 1.0), (0, 0, 1.0), 3.6, g)
    assert single < double


def test_a_single_self_throw_peaks_about_a_metre_above_the_hands():
    g = gravity_per_beat(0.35)
    peak = apex_height((0, 0, 1.1), (0, 0, 1.1), 2.6, g)
    assert 1.9 < peak < 2.3


def test_a_zip_barely_leaves_the_hand():
    g = gravity_per_beat(0.35)
    peak = apex_height((0, 0, 1.1), (0.4, 0, 1.1), 0.6, g)
    assert peak - 1.1 < 0.1
