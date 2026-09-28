"""Plain data describing a passing pattern. No logic lives here."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Throw:
    """A single throw. `height` counts global beats; `target` is None for a self.

    `want` is an optional "line"/"cross" assertion about where the pass lands. It
    is checked, not obeyed: which hand catches follows from the flight time and the
    two jugglers' start_hand, so the engine errors if the file disagrees.
    """

    height: float
    target: str | None = None
    want: str | None = None

    @property
    def is_pass(self) -> bool:
        return self.target is not None

    @property
    def kind(self) -> str:
        if self.height == 1:
            return "zip"
        if self.height == 2:
            return "hold"
        if self.is_pass:
            return "pass"
        return "self"

    @property
    def spin(self) -> int:
        """Club spins, derived from height: 1-2 none, 3 single, 4 double, 5 triple."""
        return max(0, int(self.height) - 2)

    def __str__(self) -> str:
        h = f"{self.height:g}"
        return f"{h}p{self.target}" if self.is_pass else h


@dataclass
class Juggler:
    id: str
    pos: tuple[float, float]
    facing: tuple[float, float] = (0.0, 0.0)
    phase: float = 0.0
    start_hand: str = "R"
    start_clubs: dict[str, int] = field(default_factory=lambda: {"R": 0, "L": 0})
    prelude: list[Throw | None] = field(default_factory=list)
    loop: list[Throw | None] = field(default_factory=list)

    @property
    def club_count(self) -> int:
        return self.start_clubs["R"] + self.start_clubs["L"]

    def hand_at(self, local_beat: int) -> str:
        """Hands alternate by local beat parity."""
        other = "L" if self.start_hand == "R" else "R"
        return self.start_hand if local_beat % 2 == 0 else other

    def throw_at(self, local_beat: int) -> Throw | None:
        """Prelude first, then the loop repeating forever."""
        if local_beat < len(self.prelude):
            return self.prelude[local_beat]
        return self.loop[(local_beat - len(self.prelude)) % len(self.loop)]


@dataclass
class Pattern:
    name: str
    beat: float
    jugglers: dict[str, Juggler]

    @property
    def club_count(self) -> int:
        return sum(j.club_count for j in self.jugglers.values())

    @property
    def period(self) -> int:
        """Beats before every juggler's loop realigns."""
        import math

        period = 1
        for j in self.jugglers.values():
            period = math.lcm(period, len(j.loop))
        # hands must realign too, so the period must be even
        return period if period % 2 == 0 else period * 2

    @property
    def loop_start(self) -> int:
        return max((len(j.prelude) for j in self.jugglers.values()), default=0)
