import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { clubState, handPosition } from '../../docs/motion.js';

// the same files the site publishes; regenerate with `python3 -m sim --build`
const docs = {
  '6c 4-count': JSON.parse(readFileSync('docs/patterns/6c-4count.json', 'utf8')),
  '17c one zip': JSON.parse(
    readFileSync('docs/patterns/star-17c-one-zip.json', 'utf8')),
};

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const byId = (doc) => Object.fromEntries(doc.jugglers.map((j) => [j.id, j]));

for (const [name, doc] of Object.entries(docs)) {
  const jugglers = byId(doc);

  test(`${name}: club paths are continuous`, () => {
    for (const club of doc.clubs) {
      let previous = null;
      for (let t = 0; t < doc.horizon - 1; t += 0.02) {
        const p = clubState(club, t, doc.gravity, jugglers).pos;
        if (previous) assert.ok(dist(p, previous) < 0.25,
          `club ${club.id} jumped ${dist(p, previous).toFixed(2)}m at beat ${t.toFixed(2)}`);
        previous = p;
      }
    }
  });

  test(`${name}: a club is at the throwing hand when it is thrown`, () => {
    for (const e of doc.events) {
      if (e.beat > doc.horizon - 2) continue;
      const club = doc.clubs[e.club];
      const p = clubState(club, e.beat, doc.gravity, jugglers).pos;
      const hand = jugglers[e.juggler].hands[e.hand].throw;
      assert.ok(dist(p, hand) < 0.06,
        `club ${e.club} was ${dist(p, hand).toFixed(3)}m from ${e.juggler}.${e.hand} at beat ${e.beat}`);
    }
  });

  test(`${name}: a club arrives at the catching hand`, () => {
    for (const e of doc.events) {
      if (e.land_beat > doc.horizon - 2 || e.height === 2) continue;
      const club = doc.clubs[e.club];
      const arrive = e.land_beat - 0.4;
      const p = clubState(club, arrive, doc.gravity, jugglers).pos;
      const hand = jugglers[e.land_juggler].hands[e.land_hand].catch;
      assert.ok(dist(p, hand) < 0.06,
        `club ${e.club} was ${dist(p, hand).toFixed(3)}m from ${e.land_juggler}.${e.land_hand}`);
    }
  });

  test(`${name}: hands are at the throw point exactly on their throw beats`, () => {
    for (const e of doc.events) {
      const p = handPosition(jugglers[e.juggler], e.hand, e.beat);
      const hand = jugglers[e.juggler].hands[e.hand].throw;
      assert.ok(dist(p, hand) < 1e-6,
        `${e.juggler}.${e.hand} was ${dist(p, hand).toFixed(3)}m off at beat ${e.beat}`);
    }
  });

  test(`${name}: clubs never go below the ground`, () => {
    for (const club of doc.clubs) {
      for (let t = 0; t < doc.horizon - 1; t += 0.05) {
        const z = clubState(club, t, doc.gravity, jugglers).pos[2];
        assert.ok(z > 0.4, `club ${club.id} at z=${z.toFixed(2)} on beat ${t.toFixed(2)}`);
      }
    }
  });
}

import { clubSpin, bulbDirection } from '../../docs/motion.js';

// A club tumbles handle-first: the handle leads over the top and drops down into
// the catching hand. So the head (bulb) tips AGAINST the direction of travel —
// backspin, not topspin. Topspin would sweep the handle backwards out of the
// catcher's hand at the moment of the catch.
const FLIGHT = { from: [0, 2, 1.1], to: [0, -2, 1.1], spin: 2 };   // travelling -y

test('the club head tips against the direction of travel just after release', () => {
  const bulb = bulbDirection(FLIGHT, 0.05);
  const travel = [0, -1];
  const along = bulb[0] * travel[0] + bulb[1] * travel[1];
  assert.ok(along < -0.05,
    `bulb leans ${along.toFixed(3)} along travel; expected it to lean backwards`);
});

test('the club head still tips backwards on a throw going the other way', () => {
  const back = { from: [0, -2, 1.1], to: [0, 2, 1.1], spin: 2 };
  const bulb = bulbDirection(back, 0.05);
  assert.ok(bulb[1] < -0.05, `bulb y=${bulb[1].toFixed(3)}, expected negative`);
});

test('a whole number of spins brings the club back upright', () => {
  const bulb = bulbDirection(FLIGHT, 1);            // spin: 2, so two full turns
  assert.ok(Math.abs(bulb[2] - 1) < 1e-9, `bulb z=${bulb[2]}`);
});

test('the spin axis lies flat and across the flight', () => {
  const { axis } = clubSpin(FLIGHT, 0.5);
  assert.equal(axis[2], 0);
  assert.ok(Math.abs(Math.hypot(axis[0], axis[1]) - 1) < 1e-9);
  assert.equal(axis[0] * 0 + axis[1] * -1, 0);      // perpendicular to travel
});
