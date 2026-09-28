"""Turns a Pattern into throw/catch events and club flights, and validates it.

Knows nothing about geometry or drawing: flights refer to hands by name, and
export.py turns those into positions. Times are in beats throughout.
"""

from dataclasses import dataclass, field

from .pattern import Juggler, Pattern, Throw

# Fraction of a beat a club spends in the hand between catch and next throw.
DWELL = 0.4
EPS = 1e-9


@dataclass(frozen=True)
class Event:
    beat: float
    local_beat: int
    juggler: str
    hand: str
    throw: Throw
    club: int
    land_beat: float
    land_juggler: str
    land_hand: str

    @property
    def is_line(self) -> bool:
        """A line pass goes right-to-left (or left-to-right); a cross stays on a side."""
        return self.hand != self.land_hand


@dataclass(frozen=True)
class Flight:
    club: int
    t0: float           # leaves the hand
    t1: float           # arrives in the catching hand
    t_throw_next: float # when the catching hand throws it on (t0 + height)
    src: tuple[str, str]
    dst: tuple[str, str]
    kind: str
    spin: int
    height: float
    line: bool


@dataclass
class Club:
    id: int
    start: tuple[str, str]
    stack: int = 0   # position in the starting hand, so the viewer can splay them
    flights: list[Flight] = field(default_factory=list)


@dataclass
class Result:
    pattern: Pattern
    events: list[Event]
    clubs: list[Club]
    errors: list[str]
    warnings: list[str]
    loop_closes: bool
    horizon: float

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def club_count(self) -> int:
        return len(self.clubs)


def simulate(pattern: Pattern, beats: float = 32) -> Result:
    errors: list[str] = []
    warnings: list[str] = []
    events: list[Event] = []

    clubs, hands = _deal(pattern)
    steps = _beat_steps(pattern, beats)
    pending: dict[float, list[tuple[int, str, str, str]]] = {}
    signatures: dict[float, tuple] = {}

    for t, beats_now in steps:
        _deliver(pending.pop(_key(t), []), hands, t, errors)
        signatures[_key(t)] = _signature(hands, pending, t)

        for jid, local_beat in beats_now:
            juggler = pattern.jugglers[jid]
            throw = juggler.throw_at(local_beat)
            if throw is None:
                continue
            hand = juggler.hand_at(local_beat)
            queue = hands[(jid, hand)]
            if not queue:
                errors.append(
                    f"{jid}.{hand} beat {t:g}: nothing to throw "
                    f"(pattern says {throw}), hand is empty")
                continue

            landing = _landing(pattern, juggler, t, throw, errors)
            if landing is None:
                continue
            land_beat, land_jid, land_hand = landing
            _check_handedness(juggler, t, throw, hand, land_jid, land_hand,
                              pattern, errors)

            club = queue.pop(0)
            events.append(Event(t, local_beat, jid, hand, throw, club,
                                land_beat, land_jid, land_hand))
            clubs[club].flights.append(
                _flight(club, t, throw, (jid, hand), (land_jid, land_hand)))
            pending.setdefault(_key(land_beat), []).append(
                (club, land_jid, land_hand, f"{jid}.{hand} beat {t:g}"))

    loop_closes = _loop_closes(pattern, signatures, warnings, bool(errors))
    return Result(pattern, events, list(clubs.values()), errors, warnings,
                  loop_closes, beats)


def _deal(pattern: Pattern) -> tuple[dict[int, Club], dict[tuple[str, str], list[int]]]:
    clubs: dict[int, Club] = {}
    hands: dict[tuple[str, str], list[int]] = {}
    for jid, juggler in pattern.jugglers.items():
        for hand in ("R", "L"):
            hands[(jid, hand)] = []
            for stack in range(juggler.start_clubs[hand]):
                club = Club(id=len(clubs), start=(jid, hand), stack=stack)
                clubs[club.id] = club
                hands[(jid, hand)].append(club.id)
    return clubs, hands


def _beat_steps(pattern: Pattern, horizon: float):
    """All juggler beats up to the horizon, grouped by global time, in order."""
    grouped: dict[float, list[tuple[str, int]]] = {}
    for jid, juggler in pattern.jugglers.items():
        local = 0
        while juggler.phase + local < horizon - EPS:
            grouped.setdefault(_key(juggler.phase + local), []).append((jid, local))
            local += 1
    return [(t, sorted(v)) for t, v in sorted(grouped.items())]


def _deliver(arrivals, hands, t, errors) -> None:
    seen: dict[tuple[str, str], str] = {}
    for club, jid, hand, source in arrivals:
        if (jid, hand) in seen:
            errors.append(
                f"two clubs land in {jid}.{hand} at beat {t:g} "
                f"(from {seen[(jid, hand)]} and {source})")
            continue
        seen[(jid, hand)] = source
        hands[(jid, hand)].append(club)


def _landing(pattern: Pattern, juggler: Juggler, t: float, throw: Throw, errors):
    target = pattern.jugglers[throw.target] if throw.is_pass else juggler
    land_beat = t + throw.height
    local = land_beat - target.phase
    offset = local - round(local)
    if abs(offset) > 1e-6:
        frac = local % 1.0
        errors.append(
            f"{juggler.id} beat {t:g}: throw {throw} lands at beat {land_beat:g}, "
            f"but {target.id}'s hands are on beats "
            f"{target.phase % 1.0:g}, {target.phase % 1.0 + 1:g}, ... "
            f"Use {throw.height - frac:g} or {throw.height + (1 - frac):g}.")
        return None
    return land_beat, target.id, target.hand_at(int(round(local)))


def _check_handedness(juggler, t, throw, hand, land_jid, land_hand, pattern, errors):
    """Verify a `line`/`cross` annotation against where the club actually lands."""
    if throw.want is None:
        return
    actual = "line" if hand != land_hand else "cross"
    if actual == throw.want:
        return
    target = pattern.jugglers[land_jid]
    other_hand = "L" if target.start_hand == "R" else "R"
    errors.append(
        f"{juggler.id} beat {t:g}: {throw} is a {actual.upper()} pass "
        f"({juggler.id}.{hand} -> {land_jid}.{land_hand}), but the file says "
        f"{throw.want}. Either give {land_jid} `start_hand {other_hand}`, "
        f"or make it a {throw.height - 1:g}p{land_jid}.")


def _flight(club: int, t: float, throw: Throw, src, dst) -> Flight:
    arrives = t + throw.height if throw.kind == "hold" else t + throw.height - DWELL
    return Flight(club=club, t0=t, t1=arrives, t_throw_next=t + throw.height,
                  src=src, dst=dst, kind=throw.kind, spin=throw.spin,
                  height=throw.height, line=src[1] != dst[1])


def _signature(hands, pending, now) -> tuple:
    held = tuple(sorted((k, len(v)) for k, v in hands.items()))
    flying = tuple(sorted(
        (jid, hand, round(land - now, 6))
        for land, arrivals in pending.items()
        for _, jid, hand, _ in arrivals
        if land >= now - EPS))
    return held, flying


def _loop_closes(pattern, signatures, warnings, had_errors) -> bool:
    """Steady state, not cold start: compare the last two loop boundaries.

    The first few beats are always transient while the start distribution drains
    into the air, so comparing beat 0 with beat `period` proves nothing.
    """
    if had_errors:
        return False
    period = pattern.period
    boundaries = sorted(t for t in signatures
                        if t >= pattern.loop_start - EPS
                        and abs((t - pattern.loop_start) % period) < 1e-6)
    if len(boundaries) < 2:
        warnings.append(
            f"simulated too few beats to check loop closure "
            f"(need at least {pattern.loop_start + 2 * period:g})")
        return False
    before, after = signatures[boundaries[-2]], signatures[boundaries[-1]]
    if before == after:
        return True
    warnings.append(
        f"pattern does not repeat after {period} beats: "
        f"{_describe_drift(before, after)}")
    return False


def _describe_drift(before, after) -> str:
    held_a, held_b = dict(before[0]), dict(after[0])
    drifted = [f"{jid}.{hand} {held_a[(jid, hand)]}->{held_b[(jid, hand)]}"
               for (jid, hand) in held_a if held_a[(jid, hand)] != held_b[(jid, hand)]]
    return ", ".join(drifted) if drifted else "clubs are in flight differently"


def _key(t: float) -> float:
    return round(t, 6)
