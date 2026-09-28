"""Pre-render every pattern to JSON so docs/ can be served as a plain static site.

GitHub Pages (or any static host) then needs no Python at all — the engine is a
build-time tool, and what gets published is the viewer plus one JSON per pattern.
"""

import json
from pathlib import Path

from .engine import simulate
from .export import to_json
from .notation import NotationError, parse

ROOT = Path(__file__).parent.parent
PATTERNS = ROOT / "patterns"
SITE = ROOT / "docs"
OUT = SITE / "patterns"


def default_beats(pattern) -> float:
    """Enough loops to be watchable, and enough to judge loop closure."""
    return max(48, pattern.loop_start + pattern.period * 8)


def build(out: Path = OUT, beats: float | None = None) -> list[str]:
    """Write one JSON per pattern plus an index. Returns any problems found."""
    out.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    problems: list[str] = []

    for path in sorted(PATTERNS.glob("*.txt")):
        try:
            pattern = parse(path.read_text())
        except NotationError as error:
            problems.append(f"{path.name}: {error}")
            continue
        result = simulate(pattern, beats=beats or default_beats(pattern))
        doc = _trim(to_json(result))
        (out / f"{path.stem}.json").write_text(json.dumps(doc))
        index.append({
            "id": path.stem,
            "name": pattern.name,
            "clubs": pattern.club_count,
            "jugglers": len(pattern.jugglers),
            "summary": _summary(pattern, result),
        })
        if not result.ok:
            problems.append(f"{path.name}: {result.errors[0]}")

    (out / "index.json").write_text(json.dumps(index, indent=2))

    known = {entry["id"] for entry in index}
    for stale in out.glob("*.json"):
        if stale.stem != "index" and stale.stem not in known:
            stale.unlink()

    return problems


def _trim(value, places: int = 4):
    """Round the float noise away — these files live in git and cross the wire."""
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, list):
        return [_trim(v, places) for v in value]
    if isinstance(value, dict):
        return {k: _trim(v, places) for k, v in value.items()}
    return value


def _summary(pattern, result) -> str:
    passes = [e for e in result.events if e.throw.is_pass]
    if not passes:
        return "no passes"
    line = sum(1 for e in passes if e.is_line)
    handedness = ("all line" if line == len(passes)
                  else "all cross" if line == 0
                  else f"{line}/{len(passes)} line")
    heights = sorted({f"{e.throw.height:g}" for e in passes})
    return f"passes {'/'.join(heights)}, {handedness}"
