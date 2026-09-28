"""Parser for the pattern text format.

    name: 6c 4-count
    beat: 0.35

    jugglers:
      A at (0, 1.75)
      B at 180deg facing A phase 0.5 start_hand L

    start:
      A: R=2 L=1

    prelude:        # optional
      A: 3 -

    loop:
      A: 3pB 3 3 3
"""

import math
import re

from .pattern import Juggler, Pattern, Throw

BLOCKS = ("jugglers", "start", "prelude", "loop")
DEFAULT_RADIUS = 1.75
DEFAULT_BEAT = 0.35

_POINT = re.compile(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")
_DEGREES = re.compile(r"^(-?[\d.]+)deg$")
_THROW = re.compile(r"^(\d+(?:\.\d+)?)(?:p([A-Za-z_]\w*))?$")
_CLUBS = re.compile(r"^([RL])=(\d+)$")
HANDEDNESS = ("line", "cross")


class NotationError(Exception):
    pass


def _fail(lineno: int, message: str) -> None:
    raise NotationError(f"line {lineno}: {message}")


def _strip(raw: str) -> str:
    return raw.split("#", 1)[0].rstrip()


def parse(text: str) -> Pattern:
    name = "untitled"
    beat = DEFAULT_BEAT
    block = None
    # juggler id -> (lineno, placement tokens); parsed after all ids are known
    placements: dict[str, tuple[int, list[str]]] = {}
    rows: dict[str, dict[str, tuple[int, list[str]]]] = {b: {} for b in BLOCKS[1:]}

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = _strip(raw)
        if not line.strip():
            continue

        bare = line.strip()
        if bare.rstrip(":") in BLOCKS and bare.endswith(":"):
            block = bare.rstrip(":")
            continue

        if block is None:
            key, _, value = bare.partition(":")
            key, value = key.strip().lower(), value.strip()
            if key == "name":
                name = value
            elif key == "beat":
                try:
                    beat = float(value)
                except ValueError:
                    _fail(lineno, f"beat must be a number, got {value!r}")
            else:
                _fail(lineno, f"unknown header {key!r}")
            continue

        if block == "jugglers":
            tokens = bare.split()
            jid = tokens[0]
            if jid in placements:
                _fail(lineno, f"juggler {jid!r} declared twice")
            if len(tokens) < 2:
                _fail(lineno, f"juggler {jid!r} needs a position, e.g. 'at (0, 1.75)'")
            placements[jid] = (lineno, tokens[1:])
            continue

        jid, sep, rest = bare.partition(":")
        jid = jid.strip()
        if not sep:
            _fail(lineno, f"expected '<juggler>: ...' in {block} block, got {bare!r}")
        if jid in rows[block]:
            _fail(lineno, f"juggler {jid!r} listed twice in {block} block")
        rows[block][jid] = (lineno, rest.split())

    if not placements:
        raise NotationError("no jugglers declared")

    jugglers = {jid: Juggler(id=jid, pos=(0.0, 0.0)) for jid in placements}
    _place(jugglers, placements)
    _apply_rows(jugglers, rows)
    return Pattern(name=name, beat=beat, jugglers=jugglers)


def _place(jugglers: dict[str, Juggler], placements) -> None:
    """Resolve positions first, then facings (which may reference other jugglers)."""
    radius = DEFAULT_RADIUS if len(jugglers) <= 2 else _circle_radius(len(jugglers))
    facing_specs: dict[str, tuple[int, str | None]] = {}

    for jid, (lineno, tokens) in placements.items():
        pos = None
        facing = None
        i = 0
        while i < len(tokens):
            word = tokens[i]
            if word == "at":
                pos, i = _read_point(tokens, i + 1, lineno, radius)
            elif word == "facing":
                if i + 1 >= len(tokens):
                    _fail(lineno, "'facing' needs a point or a juggler name")
                if tokens[i + 1].startswith("("):
                    facing, i = _read_point(tokens, i + 1, lineno, radius)
                    facing_specs[jid] = (lineno, None)
                    jugglers[jid].facing = facing
                else:
                    facing_specs[jid] = (lineno, tokens[i + 1])
                    i += 2
            elif word == "phase":
                jugglers[jid].phase = _read_float(tokens, i + 1, lineno, "phase")
                i += 2
            elif word == "start_hand":
                hand = tokens[i + 1] if i + 1 < len(tokens) else ""
                if hand not in ("R", "L"):
                    _fail(lineno, f"start_hand must be R or L, got {hand!r}")
                jugglers[jid].start_hand = hand
                i += 2
            else:
                _fail(lineno, f"unexpected {word!r} in juggler declaration")
        if pos is None:
            _fail(lineno, f"juggler {jid!r} has no 'at' position")
        jugglers[jid].pos = pos

    centroid = _centroid([j.pos for j in jugglers.values()])
    for jid, juggler in jugglers.items():
        lineno, target = facing_specs.get(jid, (0, "__centroid__"))
        if target == "__centroid__":
            # a lone juggler is their own centroid; point them down -y instead
            juggler.facing = centroid if centroid != juggler.pos else (
                juggler.pos[0], juggler.pos[1] - 1.0)
        elif target is not None:
            if target not in jugglers:
                _fail(lineno, f"juggler {jid!r} faces unknown juggler {target!r}")
            juggler.facing = jugglers[target].pos
        if juggler.facing == juggler.pos:
            _fail(lineno, f"juggler {jid!r} cannot face its own position")


def _circle_radius(n: int) -> float:
    """Keep neighbours a comfortable passing distance apart as the circle grows."""
    return max(DEFAULT_RADIUS, 1.75 / math.sin(math.pi / n))


def _read_point(tokens, i, lineno, radius) -> tuple[tuple[float, float], int]:
    if i >= len(tokens):
        _fail(lineno, "expected a position")
    deg = _DEGREES.match(tokens[i])
    if deg:
        angle = math.radians(float(deg.group(1)))
        return (round(radius * math.sin(angle), 10),
                round(radius * math.cos(angle), 10)), i + 1
    # a point may be split across tokens: "(0," "1.75)"
    for width in (1, 2, 3):
        if i + width > len(tokens):
            break
        joined = "".join(tokens[i:i + width])
        match = _POINT.fullmatch(joined)
        if match:
            return (float(match.group(1)), float(match.group(2))), i + width
    _fail(lineno, f"expected (x, y) or <n>deg, got {tokens[i]!r}")


def _read_float(tokens, i, lineno, what) -> float:
    if i >= len(tokens):
        _fail(lineno, f"{what} needs a number")
    try:
        return float(tokens[i])
    except ValueError:
        _fail(lineno, f"{what} must be a number, got {tokens[i]!r}")


def _centroid(points) -> tuple[float, float]:
    return (round(sum(p[0] for p in points) / len(points), 10),
            round(sum(p[1] for p in points) / len(points), 10))


def _apply_rows(jugglers: dict[str, Juggler], rows) -> None:
    for block in ("start", "prelude", "loop"):
        for jid, (lineno, tokens) in rows[block].items():
            if jid not in jugglers:
                _fail(lineno, f"{block} block names unknown juggler {jid!r}")
            if block == "start":
                jugglers[jid].start_clubs = _parse_clubs(tokens, lineno)
            else:
                setattr(jugglers[jid], block,
                        _parse_throws(tokens, lineno, jugglers))

    for jid, juggler in jugglers.items():
        if jid not in rows["start"]:
            raise NotationError(f"juggler {jid!r} has no start: line")
        if not juggler.loop:
            raise NotationError(f"juggler {jid!r} has no loop: line")


def _parse_clubs(tokens, lineno) -> dict[str, int]:
    clubs = {"R": 0, "L": 0}
    if not tokens:
        _fail(lineno, "start line needs club counts, e.g. 'R=2 L=1'")
    for token in tokens:
        match = _CLUBS.fullmatch(token)
        if not match:
            _fail(lineno, f"start line expects R=<n> L=<n>, got {token!r}")
        clubs[match.group(1)] = int(match.group(2))
    return clubs


def _parse_throws(tokens, lineno, jugglers) -> list[Throw | None]:
    """Throws, with a bare 'line'/'cross' attaching to the throw before it."""
    throws: list[Throw | None] = []
    for token in tokens:
        if token not in HANDEDNESS:
            throws.append(_parse_throw(token, lineno, jugglers))
            continue
        if not throws or throws[-1] is None:
            _fail(lineno, f"{token!r} must follow a pass, e.g. '4pB {token}'")
        previous = throws[-1]
        if not previous.is_pass:
            _fail(lineno, f"{token!r} follows {previous}, which is a self — "
                          f"only a pass can be line or cross")
        if previous.want is not None:
            _fail(lineno, f"{previous} is already marked {previous.want!r}")
        throws[-1] = Throw(previous.height, previous.target, token)
    return throws


def _parse_throw(token, lineno, jugglers) -> Throw | None:
    if token == "-":
        return None
    match = _THROW.fullmatch(token)
    if not match:
        _fail(lineno, f"{token!r} is not a throw (expected e.g. 3, 4pB, 3.5pB or -)")
    target = match.group(2)
    if target is not None and target not in jugglers:
        _fail(lineno, f"throw {token!r} passes to unknown juggler {target!r}")
    return Throw(float(match.group(1)), target)
