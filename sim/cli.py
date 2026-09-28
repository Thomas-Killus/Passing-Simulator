"""`python -m sim patterns/6c-4count.txt` - simulate, report, serve, open browser."""

import argparse
import json
import sys
from pathlib import Path

from .engine import simulate
from .export import to_json
from .notation import NotationError, parse
from .server import serve


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        pattern = parse(Path(args.pattern).read_text())
    except NotationError as error:
        print(f"{args.pattern}: {error}")
        return 1
    except OSError as error:
        print(error)
        return 1

    beats = args.beats or _default_beats(pattern)
    result = simulate(pattern, beats=beats)
    doc = to_json(result)
    _report(pattern, result, beats)

    if args.json:
        Path(args.json).write_text(json.dumps(doc, indent=2))
        print(f"wrote {args.json}")

    if not result.ok:
        return 1
    if not args.no_serve:
        serve(doc, port=args.port, open_browser=not args.no_open)
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="sim", description=__doc__)
    parser.add_argument("pattern", help="pattern file to simulate")
    parser.add_argument("--beats", type=float, default=None,
                        help="how many beats to simulate (default: several loops)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--json", metavar="PATH", help="also write the JSON document")
    parser.add_argument("--no-serve", action="store_true",
                        help="simulate and report only")
    parser.add_argument("--no-open", action="store_true",
                        help="serve but do not open a browser")
    return parser.parse_args(argv)


def _default_beats(pattern) -> float:
    """Enough loops to be watchable, and enough to judge loop closure."""
    return max(48, pattern.loop_start + pattern.period * 8)


def _report(pattern, result, beats) -> None:
    print(f"{pattern.name}: {pattern.club_count} clubs, "
          f"{len(pattern.jugglers)} jugglers, period {pattern.period}, "
          f"{beats:g} beats simulated")
    handedness = _handedness(result)
    for jid, juggler in pattern.jugglers.items():
        loop = " ".join(str(t) if t else "-" for t in juggler.loop)
        print(f"  {jid}: {juggler.club_count} clubs "
              f"(R={juggler.start_clubs['R']} L={juggler.start_clubs['L']})"
              f"{'  start ' + juggler.start_hand if juggler.start_hand != 'R' else ''}"
              f"{'  phase ' + format(juggler.phase, 'g') if juggler.phase else ''}"
              f"   loop: {loop}"
              f"{'   ' + handedness[jid] if jid in handedness else ''}")
    _print_capped(result.errors, "ERROR")
    _print_capped(result.warnings, "warn ")
    if result.ok:
        print(f"  ok, loop {'closes' if result.loop_closes else 'DOES NOT close'}")


def _handedness(result) -> dict[str, str]:
    """How each juggler's passes land, e.g. 'LINE  R->L'."""
    out = {}
    for e in result.events:
        if not e.throw.is_pass or e.juggler in out:
            continue
        out[e.juggler] = (f"{'LINE ' if e.is_line else 'CROSS'} "
                          f"{e.hand}->{e.land_juggler}.{e.land_hand}")
    return out


def _print_capped(messages, label, limit=6) -> None:
    """One broken hand fails on every beat; show the first few, count the rest."""
    for message in messages[:limit]:
        print(f"  {label}  {message}")
    if len(messages) > limit:
        print(f"  {label}  ... and {len(messages) - limit} more")


if __name__ == "__main__":
    sys.exit(main())
