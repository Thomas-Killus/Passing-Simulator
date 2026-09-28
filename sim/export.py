"""Joins engine events with geometry into the single JSON document the viewer eats.

All times in the document are beats, so the viewer's speed slider never needs the
engine to re-run.
"""

from .engine import Result
from .geometry import apex_height, gravity_per_beat, layout


def to_json(result: Result) -> dict:
    pattern = result.pattern
    frames = layout(pattern)
    g = gravity_per_beat(pattern.beat)

    return {
        "name": pattern.name,
        "beat": pattern.beat,
        "period": pattern.period,
        "loop_start": pattern.loop_start,
        "horizon": result.horizon,
        "gravity": g,
        "jugglers": [_juggler(frames[jid], pattern.jugglers[jid])
                     for jid in pattern.jugglers],
        "clubs": [_club(club, frames, g) for club in result.clubs],
        "events": [_event(e) for e in sorted(result.events, key=lambda e: e.beat)],
        "causal": [{"from": [e.juggler, e.beat],
                    "to": [e.land_juggler, e.land_beat - 2]}
                   for e in result.events],
        "report": {
            "ok": result.ok,
            "clubs": result.club_count,
            "loop_closes": result.loop_closes,
            "errors": result.errors,
            "warnings": result.warnings,
        },
    }


def _juggler(frame, juggler) -> dict:
    return {
        "id": frame.id,
        "pos": list(frame.pos),
        "facing": list(frame.facing),
        "right": list(frame.right),
        "phase": juggler.phase,
        "start_hand": juggler.start_hand,
        "clubs": juggler.club_count,
        "hands": {hand: {point: list(xyz) for point, xyz in points.items()}
                  for hand, points in frame.hands.items()},
    }


def _club(club, frames, g) -> dict:
    return {
        "id": club.id,
        "start": list(club.start),
        "stack": club.stack,
        "rest": list(frames[club.start[0]].hands[club.start[1]]["catch"]),
        "flights": [_flight(f, frames, g) for f in club.flights],
    }


def _flight(flight, frames, g) -> dict:
    src = frames[flight.src[0]].hands[flight.src[1]]["throw"]
    dst = frames[flight.dst[0]].hands[flight.dst[1]]["catch"]
    if flight.kind == "hold":
        src = dst = frames[flight.src[0]].hands[flight.src[1]]["catch"]
    duration = flight.t1 - flight.t0
    return {
        "club": flight.club,
        "t0": flight.t0,
        "t1": flight.t1,
        "t_throw_next": flight.t_throw_next,
        "from": list(src),
        "to": list(dst),
        "apex": apex_height(src, dst, duration, g),
        "kind": flight.kind,
        "line": flight.line if flight.kind == "pass" else False,
        "spin": flight.spin,
        "height": flight.height,
        "src": list(flight.src),
        "dst": list(flight.dst),
    }


def _event(e) -> dict:
    return {
        "beat": e.beat,
        "juggler": e.juggler,
        "hand": e.hand,
        "throw": str(e.throw),
        "height": e.throw.height,
        "target": e.throw.target,
        "club": e.club,
        "land_beat": e.land_beat,
        "land_juggler": e.land_juggler,
        "land_hand": e.land_hand,
        "line": e.is_line,
    }
