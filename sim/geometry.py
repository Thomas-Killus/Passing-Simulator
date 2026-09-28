"""Where jugglers stand, where their hands are, and how high a throw flies.

World axes: x and y are the ground plane (the plane pattern files write points
in), z is up. Times are in beats, distances in metres.
"""

import math
from dataclasses import dataclass

from .pattern import Pattern

G = 9.81                # m/s^2
HAND_HEIGHT = 1.10      # hands at rest, above the ground
THROW_OUT = 0.18        # throw point, sideways from the body centre
CATCH_OUT = 0.42        # catch point, sideways from the body centre
THROW_FORWARD = 0.28    # throw point, in front of the body
CATCH_FORWARD = 0.22    # catch point, in front of the body
THROW_DROP = 0.06       # throws leave the hand slightly below the catch height

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class Frame:
    """A juggler's place and orientation, with their four hand points."""

    id: str
    pos: Vec3
    facing: Vec3
    right: Vec3
    hands: dict[str, dict[str, Vec3]]


def layout(pattern: Pattern) -> dict[str, Frame]:
    return {jid: _frame(j) for jid, j in pattern.jugglers.items()}


def _frame(juggler) -> Frame:
    pos = (juggler.pos[0], juggler.pos[1], 0.0)
    dx = juggler.facing[0] - juggler.pos[0]
    dy = juggler.facing[1] - juggler.pos[1]
    length = math.hypot(dx, dy)
    facing = (dx / length, dy / length, 0.0)
    # z-up right-handed: right = facing x up
    right = (facing[1], -facing[0], 0.0)

    hands = {}
    for hand, side in (("R", 1.0), ("L", -1.0)):
        hands[hand] = {
            "throw": _offset(pos, right, facing, side * THROW_OUT,
                             THROW_FORWARD, HAND_HEIGHT - THROW_DROP),
            "catch": _offset(pos, right, facing, side * CATCH_OUT,
                             CATCH_FORWARD, HAND_HEIGHT),
        }
    return Frame(juggler.id, pos, facing, right, hands)


def _offset(pos, right, facing, sideways, forward, height) -> Vec3:
    return (pos[0] + right[0] * sideways + facing[0] * forward,
            pos[1] + right[1] * sideways + facing[1] * forward,
            height)


def gravity_per_beat(beat_seconds: float) -> float:
    """Real gravity, expressed in metres per beat squared."""
    return G * beat_seconds ** 2


def vertical_speed(p0: Vec3, p1: Vec3, duration: float, g: float) -> float:
    """Upward speed (m/beat) needed to fall from p0 to p1 in `duration` beats."""
    if duration <= 0:
        return 0.0
    return (p1[2] - p0[2]) / duration + 0.5 * g * duration


def apex_height(p0: Vec3, p1: Vec3, duration: float, g: float) -> float:
    """Highest point (z) of the flight; equals the launch height for a zip."""
    v = vertical_speed(p0, p1, duration, g)
    if v <= 0 or g <= 0:
        return max(p0[2], p1[2])
    return p0[2] + v * v / (2 * g)
