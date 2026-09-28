import pytest

from sim.engine import simulate
from sim.notation import parse

SOLO = """
name: 3 club cascade
beat: 0.35
jugglers:
  A at (0, 0)
start:
  A: R=2 L=1
loop:
  A: 3
"""

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


def run(text, beats=32):
    return simulate(parse(text), beats=beats)


def throws_by(result, juggler):
    return [e for e in result.events if e.juggler == juggler]


def test_solo_cascade_is_valid():
    r = run(SOLO)
    assert r.errors == []
    assert r.ok


def test_solo_cascade_alternates_hands_every_beat():
    r = run(SOLO, beats=6)
    assert [e.hand for e in throws_by(r, "A")] == ["R", "L", "R", "L", "R", "L"]


def test_solo_cascade_throw_lands_three_beats_later_in_the_other_hand():
    first = throws_by(run(SOLO), "A")[0]
    assert first.beat == 0
    assert first.hand == "R"
    assert first.land_beat == 3
    assert first.land_hand == "L"


def test_solo_cascade_rethrows_the_club_it_just_caught():
    r = run(SOLO, beats=8)
    thrown_at_0 = throws_by(r, "A")[0].club
    thrown_at_3 = throws_by(r, "A")[3].club
    assert thrown_at_0 == thrown_at_3


def test_six_club_four_count_is_valid():
    r = run(SIX_CLUB)
    assert r.errors == []
    assert r.ok


def test_six_club_four_count_passes_only_on_every_fourth_beat_from_the_right():
    r = run(SIX_CLUB, beats=16)
    passes = [e for e in throws_by(r, "A") if e.throw.is_pass]
    assert [e.beat for e in passes] == [0, 4, 8, 12]
    assert {e.hand for e in passes} == {"R"}


def test_passes_are_straight_right_hand_to_partners_left():
    r = run(SIX_CLUB, beats=8)
    first_pass = next(e for e in throws_by(r, "A") if e.throw.is_pass)
    assert first_pass.land_juggler == "B"
    assert first_pass.land_hand == "L"
    assert first_pass.land_beat == 3


def test_club_count_is_conserved():
    r = run(SIX_CLUB)
    assert r.club_count == 6
    assert len(r.clubs) == 6


def test_every_club_is_thrown_at_least_once():
    r = run(SIX_CLUB)
    thrown = {e.club for e in r.events}
    assert thrown == set(range(6))


def test_throwing_from_an_empty_hand_is_an_error_naming_hand_and_beat():
    r = run("""
name: too few clubs
beat: 0.35
jugglers:
  A at (0, 0)
start:
  A: R=1 L=0
loop:
  A: 3
""")
    assert not r.ok
    assert any("A" in e and "L" in e and "beat 1" in e for e in r.errors)


def test_two_clubs_landing_in_one_hand_on_one_beat_is_an_error():
    r = run("""
name: colliding doubles
beat: 0.35
jugglers:
  A at (0, 1.75)
  B at (0, -1.75)
start:
  A: R=2 L=1
  B: R=2 L=2
loop:
  A: 4pB 3
  B: 4pA 3
""")
    assert not r.ok
    assert any("two clubs" in e.lower() for e in r.errors)


def test_landing_off_the_targets_beat_grid_is_an_error_listing_valid_heights():
    r = run("""
name: phase mismatch
beat: 0.35
jugglers:
  A at (0, 1.75)
  B at (0, -1.75) phase 0.5
start:
  A: R=2 L=1
  B: R=2 L=1
loop:
  A: 3pB 3 3 3
  B: 3pA 3 3 3
""")
    assert not r.ok
    assert any("2.5" in e and "3.5" in e for e in r.errors)


def test_loop_closure_is_reported_for_a_good_pattern():
    assert run(SIX_CLUB).loop_closes


def test_flights_cover_every_club_continuously():
    r = run(SIX_CLUB, beats=16)
    for club in r.clubs:
        for earlier, later in zip(club.flights, club.flights[1:]):
            assert later.t0 >= earlier.t1 - 1e-9


def test_a_hold_keeps_the_club_in_the_same_hand():
    r = run("""
name: hold test
beat: 0.35
jugglers:
  A at (0, 0)
start:
  A: R=2 L=1
loop:
  A: 3 3 3 3 3 2
""", beats=24)
    hold = next(e for e in r.events if e.throw.height == 2)
    assert hold.land_hand == hold.hand
    assert hold.land_juggler == hold.juggler


def test_a_zip_moves_the_club_to_the_other_hand_one_beat_later():
    r = run("""
name: zip test
beat: 0.35
jugglers:
  A at (0, 0)
start:
  A: R=2 L=1
loop:
  A: 5 1 3 3 3 3
""", beats=24)
    zip_throw = next(e for e in r.events if e.throw.height == 1)
    assert zip_throw.land_hand != zip_throw.hand
    assert zip_throw.land_beat == zip_throw.beat + 1


PAIR = """
name: annotated
beat: 0.32
jugglers:
  A at (0, 1.75)
  B at (0, -1.75) start_hand {hand}
start:
  A: R=2 L=2
  B: R=1 L=2
loop:
  A: 4pB {want} 3
  B: 3 4pA
"""


def test_an_event_knows_whether_it_was_line_or_cross():
    r = run(SIX_CLUB, beats=8)
    first_pass = next(e for e in r.events if e.throw.is_pass)
    assert first_pass.hand == "R" and first_pass.land_hand == "L"
    assert first_pass.is_line


def test_a_correct_line_annotation_passes_validation():
    r = simulate(parse(PAIR.format(hand="L", want="line")), beats=24)
    assert r.errors == []
    assert all(e.is_line for e in r.events if e.throw.is_pass)


def test_a_wrong_annotation_is_an_error_naming_both_fixes():
    r = simulate(parse(PAIR.format(hand="R", want="line")), beats=24)
    assert not r.ok
    message = next(e for e in r.errors if "line" in e)
    assert "cross" in message.lower()
    assert "start_hand" in message          # flip the partner's hand phase
    assert "3pB" in message                 # or change the height parity


def test_a_correct_cross_annotation_passes_validation():
    r = simulate(parse(PAIR.format(hand="R", want="cross")), beats=24)
    assert [e for e in r.errors if "cross" in e] == []
