// Where a club is at a given beat. Pure maths, no three.js.

export const DWELL = 0.4;
const HAND_CYCLE = 2;   // a hand throws every other beat

// Upward speed (metres per beat) needed to fall from z0 to z1 in `duration`.
export function verticalSpeed(z0, z1, duration, g) {
  if (duration <= 0) return 0;
  return (z1 - z0) / duration + 0.5 * g * duration;
}

// The flight governing a club at beat t, or null before its first throw.
export function flightAt(club, t) {
  let current = null;
  for (const f of club.flights) {
    if (f.t0 > t) break;
    current = f;
  }
  return current;
}

export function lerp3(a, b, u) {
  return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
}

// A hand swings out to catch and back in to throw, on its own two-beat cycle.
export function handPosition(juggler, hand, t) {
  const points = juggler.hands[hand];
  const offset = juggler.start_hand === hand ? 0 : 1;
  const local = t - juggler.phase;
  const nextThrow = Math.ceil((local - offset) / HAND_CYCLE) * HAND_CYCLE + offset;
  const untilThrow = nextThrow - local;
  if (untilThrow <= DWELL) {
    return lerp3(points.catch, points.throw, 1 - untilThrow / DWELL);
  }
  const u = 1 - (untilThrow - DWELL) / (HAND_CYCLE - DWELL);
  return lerp3(points.throw, points.catch, u);
}

// Position of a club at beat t. `jugglers` maps id -> juggler document entry.
export function clubState(club, t, g, jugglers) {
  const f = flightAt(club, t);
  if (!f) {
    // not thrown yet: ride the hand, splayed a little so a loaded hand reads
    // as more than one club, and closing that splay just before the first throw
    const [jid, hand] = club.start;
    const pos = handPosition(jugglers[jid], hand, t);
    const first = club.flights[0];
    const fade = first ? Math.min(1, Math.max(0, (first.t0 - t) / DWELL)) : 1;
    const splay = club.stack * 0.055 * fade;
    return {
      pos: [pos[0], pos[1], pos[2] + splay],
      flight: null, progress: 0, inHand: true,
    };
  }

  if (f.kind === 'hold') {
    const [jid, hand] = f.dst;
    return { pos: handPosition(jugglers[jid], hand, t), flight: f, progress: 0, inHand: true };
  }

  if (t >= f.t1) {
    // caught: riding the hand from the catch point round to the throw point
    const [jid, hand] = f.dst;
    return { pos: handPosition(jugglers[jid], hand, t), flight: f, progress: 1, inHand: true };
  }

  const duration = f.t1 - f.t0;
  const u = (t - f.t0) / duration;
  const v = verticalSpeed(f.from[2], f.to[2], duration, g);
  const dt = t - f.t0;
  return {
    pos: [
      f.from[0] + (f.to[0] - f.from[0]) * u,
      f.from[1] + (f.to[1] - f.from[1]) * u,
      f.from[2] + v * dt - 0.5 * g * dt * dt,
    ],
    flight: f,
    progress: u,
    inHand: false,
  };
}
