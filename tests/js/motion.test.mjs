import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { clubState, handPosition } from '../../viewer/motion.js';

const docs = {
  '6c 4-count': JSON.parse(readFileSync('/tmp/6c.json', 'utf8')),
  '7c async': JSON.parse(readFileSync('/tmp/7a.json', 'utf8')),
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
