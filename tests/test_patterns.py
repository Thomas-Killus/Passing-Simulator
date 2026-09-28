"""The shipped pattern files must actually be valid patterns."""

from pathlib import Path

import pytest

from sim.engine import simulate
from sim.notation import parse

PATTERNS = sorted((Path(__file__).parent.parent / "patterns").glob("*.txt"))


@pytest.mark.parametrize("path", PATTERNS, ids=lambda p: p.stem)
def test_pattern_file_simulates_without_errors(path):
    result = simulate(parse(path.read_text()), beats=48)
    assert result.errors == [], result.errors
    assert result.loop_closes, result.warnings


def test_six_club_four_count_uses_six_clubs():
    p = parse((Path("patterns/6c-4count.txt")).read_text())
    assert p.club_count == 6


def test_seven_club_two_count_splits_four_three():
    p = parse((Path("patterns/7c-2count.txt")).read_text())
    assert p.club_count == 7
    assert sorted(j.club_count for j in p.jugglers.values()) == [3, 4]


def test_the_cross_seven_club_opens_with_b_throwing_the_double():
    p = parse((Path("patterns/7c-2count-cross.txt")).read_text())
    result = simulate(p, beats=16)
    opening = [e for e in result.events if e.beat == 0]
    by_juggler = {e.juggler: e for e in opening}
    assert by_juggler["B"].throw.height == 4 and by_juggler["B"].throw.is_pass
    assert by_juggler["A"].throw.height == 3 and not by_juggler["A"].throw.is_pass
    a_second = next(e for e in result.events if e.juggler == "A" and e.beat == 1)
    assert a_second.throw.height == 4 and a_second.throw.is_pass


def test_async_pattern_needs_fractional_heights():
    p = parse((Path("patterns/7c-async.txt")).read_text())
    assert p.jugglers["B"].phase == 0.5
    assert all(t.height % 1 == 0.5 for t in p.jugglers["A"].loop)


def test_dense_stars_have_the_club_counts_their_comments_claim():
    counts = {}
    for name in ("star-15c", "star-17c", "star-18c"):
        p = parse(Path(f"patterns/{name}.txt").read_text())
        counts[name] = (p.club_count, sorted(j.club_count for j in p.jugglers.values()))
    assert counts["star-15c"] == (15, [3, 3, 3, 3, 3])
    assert counts["star-17c"] == (17, [3, 3, 3, 4, 4])
    assert counts["star-18c"] == (18, [3, 3, 4, 4, 4])


def test_the_dense_star_puts_exactly_one_pass_in_the_air_on_every_beat():
    result = simulate(parse(Path("patterns/star-17c.txt").read_text()), beats=40)
    passes = [e for e in result.events if e.throw.is_pass and e.beat < 20]
    by_beat = {}
    for e in passes:
        by_beat.setdefault(e.beat, []).append(e)
    assert sorted(by_beat) == [float(b) for b in range(20)]
    assert all(len(v) == 1 for v in by_beat.values())


def test_a_dense_star_cannot_have_everyone_passing_on_the_same_beat():
    """The 15-club star has all five pass together; at 17 clubs that breaks.

    Same loop for everyone with no stagger, the way the 15-club star is written.
    """
    ids = "ABCDE"
    lines = "\n".join(
        f"  {j}: 3p{ids[(i + 2) % 5]} 3 3 4 4" for i, j in enumerate(ids))
    starts = "\n".join(f"  {j}: R=2 L={2 if j in 'AB' else 1}" for j in ids)
    places = "\n".join(f"  {j} at {i * 72}deg" for i, j in enumerate(ids))
    result = simulate(parse(
        f"name: unstaggered\nbeat: 0.33\njugglers:\n{places}\n"
        f"start:\n{starts}\nloop:\n{lines}\n"), beats=40)
    assert not result.ok


def test_two_count_stars_pass_from_the_right_hand_on_every_even_beat():
    for name in ("star-15c-2count", "star-17c-2count", "star-20c-2count"):
        result = simulate(parse(Path(f"patterns/{name}.txt").read_text()), beats=24)
        passes = [e for e in result.events if e.throw.is_pass]
        assert {e.hand for e in passes} == {"R"}, name
        assert {e.beat % 2 for e in passes} == {0.0}, name
        # all five throw their pass together
        by_beat = {}
        for e in passes:
            by_beat.setdefault(e.beat, []).append(e)
        assert all(len(v) == 5 for v in by_beat.values()), name


def test_no_uniform_two_count_star_can_hold_seventeen_or_eighteen_clubs():
    """Five identical jugglers on a 2-beat loop total a multiple of five.

    Club count is 5 x the loop average, and a 2-beat loop averages a whole or
    half number, so the total is either not a whole number of clubs at all
    (3.5 each would be 17.5) or a multiple of five. This is why
    star-17c-2count.txt has to give its jugglers three different jobs.
    """
    reachable = set()
    for pass_height in range(1, 8):
        for self_height in range(1, 8):
            total = 5 * (pass_height + self_height) / 2
            if total == int(total):
                reachable.add(int(total))
    assert 17 not in reachable
    assert 18 not in reachable
    assert reachable and all(t % 5 == 0 for t in reachable)


def test_the_doubles_star_has_no_heffs_holds_or_zips():
    p = parse(Path("patterns/star-17c-doubles.txt").read_text())
    selfs = [t for j in p.jugglers.values() for t in j.loop if not t.is_pass]
    assert {t.height for t in selfs} == {3.0}
    passes = [t for j in p.jugglers.values() for t in j.loop if t.is_pass]
    assert sorted(t.height for t in passes) == [3.0, 4.0, 4.0, 4.0, 4.0]
    assert p.club_count == 17


def test_an_odd_passing_chain_needs_an_even_number_of_double_passes():
    """A double flips which hand your partner passes from; a single does not.

    The star's passing chain A->C->E->B->D->A closes after five people, so the
    flips must cancel: the number of doubles must be even. Five doubles is
    therefore impossible, four is the most you can have.
    """
    ids = "ABCDE"
    places = "\n".join(f"  {j} at {i * 72}deg" for i, j in enumerate(ids))
    starts = "\n".join(f"  {j}: R=2 L=2" for j in ids)

    def star(heights, pass_first):
        loops = []
        for i, j in enumerate(ids):
            throw = f"{heights[i]}p{ids[(i + 2) % 5]}"
            loops.append(f"  {j}: " + (f"{throw} 3" if pass_first[i] else f"3 {throw}"))
        return parse(f"name: t\nbeat: 0.33\njugglers:\n{places}\n"
                     f"start:\n{starts}\nloop:\n" + "\n".join(loops) + "\n")

    # five doubles, every arrangement of which hand each person passes from
    for bits in range(32):
        first = [bool(bits >> k & 1) for k in range(5)]
        assert not simulate(star([4] * 5, first), beats=40).ok

    # four doubles and one single does work
    assert simulate(star([4, 4, 4, 4, 3], [True, True, False, False, True]),
                    beats=40).errors == []


def test_the_line_stars_never_cross_a_pass():
    for name in ("star-17c-line", "star-19c-line"):
        result = simulate(parse(Path(f"patterns/{name}.txt").read_text()), beats=40)
        passes = [e for e in result.events if e.throw.is_pass]
        assert passes
        for e in passes:
            assert e.hand == "R" and e.land_hand == "L", (name, e)


def test_whether_a_pass_is_line_or_cross_depends_on_relative_hand_phase():
    """A 4 is NOT always a crossing pass.

    Which hand catches is fixed by the landing beat and that juggler's start_hand.
    If the two jugglers alternate hands in step, a 4 lands in the partner's right
    (cross) and a 3 in their left (line). If one of them starts on the other hand,
    it is the other way round — which is how most people throw 7-club 2-count.
    """
    def pair(height, partner_start_hand):
        return simulate(parse(f"""
name: t
beat: 0.32
jugglers:
  A at (0, 1.75)
  B at (0, -1.75) start_hand {partner_start_hand}
start:
  A: R=2 L=2
  B: R=2 L=2
loop:
  A: {height}pB 3
  B: 3 {height}pA
"""), beats=12)

    def landing_hands(result):
        return {(e.hand, e.land_hand) for e in result.events
                if e.throw.is_pass and e.juggler == "A"}

    # hands in step: 4 crosses, 3 goes line
    assert landing_hands(pair(4, "R")) == {("R", "R")}
    assert landing_hands(pair(3, "R")) == {("R", "L")}
    # partner's hands offset by one beat: exactly the other way round
    assert landing_hands(pair(4, "L")) == {("R", "L")}
    assert landing_hands(pair(3, "L")) == {("R", "R")}


def test_all_line_star_club_count_is_fifteen_plus_the_long_passes():
    counts = {}
    for name in ("star-15c-2count", "star-17c-line", "star-19c-line"):
        p = parse(Path(f"patterns/{name}.txt").read_text())
        longs = sum(1 for j in p.jugglers.values()
                    for t in j.loop if t.is_pass and t.height == 5)
        counts[name] = (p.club_count, longs)
    for name, (clubs, longs) in counts.items():
        assert clubs == 15 + longs, (name, clubs, longs)


def test_the_seven_club_two_count_is_thrown_line_as_most_people_do():
    p = parse(Path("patterns/7c-2count.txt").read_text())
    assert p.jugglers["A"].start_clubs == {"R": 2, "L": 2}
    assert p.jugglers["B"].start_clubs == {"R": 1, "L": 2}
    assert p.jugglers["B"].start_hand == "L"

    result = simulate(p, beats=24)
    passes = [e for e in result.events if e.throw.is_pass]
    assert passes
    for e in passes:
        assert e.hand == "R" and e.is_line, e
        assert e.throw.height == 4

    opening = {e.juggler: e for e in result.events if e.beat == 0}
    assert opening["A"].throw.is_pass and opening["A"].hand == "R"
    assert not opening["B"].throw.is_pass and opening["B"].hand == "L"


def test_the_cross_variant_differs_only_in_hand_phase():
    line = parse(Path("patterns/7c-2count.txt").read_text())
    cross = parse(Path("patterns/7c-2count-cross.txt").read_text())
    assert line.club_count == cross.club_count == 7
    crossed = [e for e in simulate(cross, beats=24).events if e.throw.is_pass]
    assert all(not e.is_line for e in crossed)


def test_the_line_doubles_star_matches_the_cross_one_throw_for_throw():
    line = parse(Path("patterns/star-17c-doubles-line.txt").read_text())
    cross = parse(Path("patterns/star-17c-doubles.txt").read_text())
    for jid, juggler in line.jugglers.items():
        assert [(t.height, t.target) for t in juggler.loop] == \
               [(t.height, t.target) for t in cross.jugglers[jid].loop], jid
    assert line.club_count == 17
    assert {j.start_hand for j in line.jugglers.values()} == {"R", "L"}

    result = simulate(line, beats=24)
    assert result.errors == []
    passes = [e for e in result.events if e.throw.is_pass]
    assert all(e.is_line and e.hand == "R" for e in passes)
    assert {t.height for j in line.jugglers.values()
            for t in j.loop if not t.is_pass} == {3.0}


def test_even_doubles_rule_holds_however_the_hands_are_phased():
    """The rule I had right: five doubles round the star never works.

    Re-checked with start_hand free, which is the freedom I originally missed.
    """
    ids = "ABCDE"
    starts = "\n".join(f"  {j}: R=2 L=2" for j in ids)
    for hands in range(32):                      # who starts on the left
        places = "\n".join(
            f"  {j} at {i * 72}deg" + (" start_hand L" if hands >> i & 1 else "")
            for i, j in enumerate(ids))
        for firsts in range(32):                 # who passes on their even beat
            loops = []
            for i, j in enumerate(ids):
                throw = f"4p{ids[(i + 2) % 5]}"
                loops.append(f"  {j}: " + (f"{throw} 3" if firsts >> i & 1
                                           else f"3 {throw}"))
            result = simulate(parse(
                f"name: t\nbeat: 0.33\njugglers:\n{places}\n"
                f"start:\n{starts}\nloop:\n" + "\n".join(loops) + "\n"), beats=30)
            assert not result.ok, (hands, firsts)


def test_all_five_throw_a_double_in_the_all_doubles_star():
    p = parse(Path("patterns/star-17c-all-doubles.txt").read_text())
    assert p.club_count == 17
    passes = [t for j in p.jugglers.values() for t in j.loop if t.is_pass]
    assert len(passes) == 5
    assert all(t.height in (4.0, 4.5) for t in passes), [t.height for t in passes]
    assert p.jugglers["E"].phase == 0.5
    assert [t.height for t in p.jugglers["E"].loop if not t.is_pass] == [1.0]

    result = simulate(p, beats=40)
    assert result.errors == []
    thrown = [e for e in result.events if e.throw.is_pass]
    assert all(e.is_line and e.hand == "R" for e in thrown)


def test_only_the_passes_touching_the_offset_juggler_are_four_and_a_half():
    p = parse(Path("patterns/star-17c-all-doubles.txt").read_text())
    halves = {jid for jid, j in p.jugglers.items()
              for t in j.loop if t.is_pass and t.height == 4.5}
    # E throws one, and whoever passes to E throws the other
    feeders = {jid for jid, j in p.jugglers.items()
               for t in j.loop if t.target == "E"}
    assert halves == {"E"} | feeders


def test_zips_alone_cannot_buy_a_fifth_double_on_one_beat_grid():
    """A zip is a 1 — odd, like a 3 — so it moves the club count, not the parity.

    Five doubles needs somebody off the beat; no choice of self height helps.
    """
    ids = "ABCDE"
    starts = "\n".join(f"  {j}: R=2 L=2" for j in ids)
    for selfs in ((1, 3, 3, 3, 3), (1, 1, 3, 3, 3), (1, 1, 1, 1, 1), (3, 3, 3, 3, 1)):
        for hands in range(32):
            places = "\n".join(
                f"  {j} at {i * 72}deg" + (" start_hand L" if hands >> i & 1 else "")
                for i, j in enumerate(ids))
            loops = "\n".join(
                f"  {j}: 4p{ids[(i + 2) % 5]} {selfs[i]}" for i, j in enumerate(ids))
            result = simulate(parse(
                f"name: t\nbeat: 0.3\njugglers:\n{places}\n"
                f"start:\n{starts}\nloop:\n{loops}\n"), beats=30)
            assert not result.ok, (selfs, hands)


def test_the_zip_travels_round_the_circle():
    p = parse(Path("patterns/star-18c-travelling-zip.txt").read_text())
    assert p.club_count == 18
    # every juggler throws exactly one zip per ten beats
    for jid, juggler in p.jugglers.items():
        assert [t.height for t in juggler.loop].count(1.0) == 1, jid
    result = simulate(p, beats=40)
    assert result.errors == []
    assert all(e.is_line and e.hand == "R"
               for e in result.events if e.throw.is_pass)
    order = [e.juggler for e in sorted(
        (e for e in result.events if e.throw.height == 1 and e.beat < 10),
        key=lambda e: e.beat)]
    assert len(order) == 5 and len(set(order)) == 5, order


def test_a_juggler_passing_every_other_beat_can_only_total_5_15_or_25_in_selfs():
    """Why the zip cannot be shared out at 17 clubs.

    Over ten beats a juggler throws five selfs, and only totals of 5, 15 and 25
    are throwable. 17 clubs needs one juggler down at 5, and five selfs adding to
    5 can only be five zips — so that juggler zips every time, permanently.
    """
    ids = "ABCDE"
    places = "\n".join(f"  {j} at {i * 72}deg" for i, j in enumerate(ids))
    starts = "\n".join(f"  {j}: R=2 L=2" for j in ids)

    def totals(selfs):
        loops = "\n".join(
            "  " + j + ": " + " ".join(
                f"3p{ids[(i + 2) % 5]} {s}" for s in selfs)
            for i, j in enumerate(ids))
        return simulate(parse(f"name: t\nbeat: 0.3\njugglers:\n{places}\n"
                              f"start:\n{starts}\nloop:\n{loops}\n"), beats=60)

    assert totals((3, 3, 3, 3, 3)).ok            # sums to 15
    assert totals((5, 1, 3, 3, 3)).ok            # also 15 — the travelling zip
    assert totals((1, 1, 1, 1, 1)).ok            # sums to 5 — the permanent zip
    assert not totals((3, 3, 3, 3, 1)).ok        # sums to 13 — not throwable
    assert not totals((3, 3, 3, 1, 1)).ok        # sums to 11 — not throwable
