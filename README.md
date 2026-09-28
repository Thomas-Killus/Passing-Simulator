# Passing Simulator

Write a club passing pattern in a few lines of text, watch it in 3D, and have the
engine tell you whether it is actually valid.

**[Open the patterns in your browser →](https://thomas-killus.github.io/Passing-Simulator/)**
No install needed; pick a pattern from the dropdown, drag to orbit.

```
python3 -m sim                          # build every pattern, serve, open browser
python3 -m sim patterns/6c-4count.txt   # simulate one, print a report, open it
python3 -m sim --build                  # re-render docs/ and exit
```

No dependencies: Python 3.10+ and a browser. three.js loads from a CDN.

## Pattern files

```
# 6 clubs, 2 people, 4-count.
name: 6c 4-count
beat: 0.35

jugglers:
  A at (0, 1.75)
  B at (0, -1.75)

start:
  A: R=2 L=1
  B: R=2 L=1

loop:
  A: 3pB 3 3 3
  B: 3pA 3 3 3
```

**`beat`** is the length of one beat in seconds — the tempo you throw at.

**`jugglers`** — one line per person:

```
  A at (0, 1.75)                 # a point on the ground, in metres
  A at 72deg                     # shorthand: on a circle, auto-sized
  A at (0, 1.75) facing (0, 0)   # look at a point
  A at (0, 1.75) facing B        # look at another juggler
  A at (0, 1.75) phase 0.5       # beats offset half a beat from everyone else
  A at (0, 1.75) start_hand L    # start on the left instead of the right
```

Facing defaults to the centroid of everyone, which is right for two people facing
off and for any circle. Lines, Y-shapes and roundabouts need `facing` spelled out.

**`start`** — how many clubs in each hand before the first throw. The totals decide
the club count, and the engine checks they actually sustain the loop.

**`loop`** — one throw per beat, repeating forever. Heights count beats:

| Token | Meaning |
|---|---|
| `1` | zip — hand across to the other hand |
| `2` | hold — the club stays in the hand |
| `3` | self, single spin |
| `4` | heff, double spin |
| `5` | triple self |
| `3pB` | single pass to B |
| `4pB` | double pass to B |
| `5pB` | triple pass to B |
| `3.5pB` | pass landing half a beat off your own grid (see phases) |
| `-` | no throw this beat (prelude only) |

Spin follows the height, so you never type it. Hands alternate automatically:
which hand throws on a beat, and which hand catches a given throw, both fall out
of the beat count. That means **you never say whether a pass crosses** — a 3 from
your right lands in your partner's left hand three beats later, which is the
ordinary straight pass, and a 4 lands in their right, which is the crossing one.

**`prelude`** (optional, between `start` and `loop`) — one-off throws before the
loop starts, for startups a loop rotation cannot express. Use `-` to wait a beat.

## What the engine checks

- a hand is never asked to throw a club it does not have
- two clubs never land in the same hand on the same beat
- a throw always lands on a beat the catcher's hand is actually there for
- the pattern returns to the same state after one period — the loop closes

A failure names the juggler, the hand and the beat. Off-grid landings say which
heights would work instead:

```
A beat 0: throw 3pB lands at beat 3, but B's hands are on beats 0.5, 1.5, ...
          Use 2.5 or 3.5.
```

## Phases, and why passes sometimes get halves

Everyone shares one beat grid. `phase 0.5` shifts a juggler's beats half a beat
later, which is what "asynchronous" passing means. A pass has to arrive when the
catching hand is there, so passing across a half-beat offset forces heights like
`3.5p`. That is the same fact prechac notation writes as 3.5.

Synchronous patterns stay in plain integers — see `patterns/7c-2count.txt`, which
is 7 clubs on one grid with everyone throwing on whole beats.

## Viewer

Mouse drags orbit, scroll zooms. Space plays and pauses, arrow keys step a beat.
The timeline underneath shows every juggler's throws against the beat, with the
causal diagram drawn over it: an arrow runs from each throw to the throw its catch
forces, two beats before it lands.

## Patterns included

| File | What it is |
|---|---|
| `6c-4count.txt` | 6 clubs, 2 people, single pass every 4th beat |
| `7c-2count.txt` | 7 clubs, 2 people, double passes thrown line, clubs split 4/3 |
| `7c-async.txt` | 7 clubs, 2 people, half-beat offset, every throw a 3.5 pass |
| `star-15c.txt` | the 5-person star, 15 clubs, 4-count |
| `star-17c.txt` | the star at 7-club density, 17 clubs, two people holding 4 |
| `star-18c.txt` | the star one club denser, 18 clubs, three people holding 4 |
| `star-15c-2count.txt` | the star passing twice as often, same 15 clubs |
| `star-17c-2count.txt` | 17 clubs and 2-count, every pass from the right, three different jobs |
| `star-17c-doubles.txt` | 17 clubs, everyone 2-counting double passes, every self a plain 3 |
| `7c-2count-cross.txt` | the same 7 clubs with the passes thrown cross |
| `star-17c-doubles-line.txt` | 17 clubs, four line doubles and one single, all from the right |
| `star-17c-all-doubles.txt` | 17 clubs, **all five** throwing line doubles, one juggler off the beat |
| `star-18c-travelling-zip.txt` | 18 clubs, all five on line doubles, the zip going round the circle |
| `star-17c-line.txt` | 17 clubs, line passes without anyone changing hand phase |
| `star-19c-line.txt` | 19 clubs, every pass line, four people on the long pass |
| `star-20c-2count.txt` | uniform heavy 2-count, 20 clubs, four each |

### Why the dense star is 17 or 18, never 17.5

Club count equals the sum of everyone's average throw height, so it is always a
whole number. 7 clubs per 2 people means 3.5 each, and five people at 3.5 is 17.5
— that pattern does not exist. 17 clubs (3.4 each) and 18 (3.6) are its
neighbours, and both need a 5-beat loop, since an average of 3.4 or 3.6 cannot
come out of a 4-beat one.

### Line or cross depends on flight time AND hand phase

A **line** pass goes right hand to your partner's left; a **cross** stays on a
side, right to right. Which one you get is not a free choice per throw — it falls
out of how long the club is in the air and whether the two of you alternate hands
in step:

| | even flight (a 4) | odd flight (a 3 or 5) |
|---|---|---|
| your hands in step | cross | line |
| partner's hands offset by a beat (`start_hand L`) | **line** | cross |

So a double pass is a line pass or a cross pass depending on the partner's hand
phase, not on the number. Giving one juggler `start_hand L` flips every pass
between them without touching a single height — compare `7c-2count.txt` with
`7c-2count-cross.txt`, which differ by exactly that one word, or
`star-17c-doubles-line.txt` with `star-17c-doubles.txt`, which have identical
loops.

**Spin is separate from all of this.** You can put two spins on any of these
heights; it changes how the club looks in the air and nothing about where it
lands. The viewer draws the conventional spin for each height (3 single, 4 double,
5 triple) purely as a visual.

### Saying which you meant

Mark a pass `line` or `cross` and the engine checks it:

```
loop:
  A: 4pB line 3
  B: 3 4pA line
```

It is an assertion, not an instruction — the engine works out where the club
really lands and complains if the file disagrees, naming both ways out:

```
A beat 0: 4pB is a CROSS pass (A.R -> B.R), but the file says line.
          Either give B `start_hand L`, or make it a 3pB.
```

The mark attaches to the throw *before* it, and only a pass can carry one.

### Relation to 4-handed siteswap and prechac

This engine writes juggler-local siteswap with pass markers, which assumes the
jugglers share a beat grid. On that clock passes are whole numbers: `3p` single,
`4p` double, `5p` triple.

Prechac and 4-handed siteswap assume the opposite — that the jugglers are half a
beat out of phase (hands in the order A.R, B.R, A.L, B.L). That is why their
passes are halves, and why in 4-handed siteswap every odd number is a pass:

| | single pass | double pass |
|---|---|---|
| here, juggler-local | `3p` | `4p` |
| prechac (local, fractional) | 3.5 | 4.5 |
| 4-handed (global) | 7 | 9 |

Global is prechac doubled. Same theory, different clock — and this engine speaks
the other dialect too: give a juggler `phase 0.5` and use fractional heights.
`patterns/7c-async.txt` is exactly that, `3.5p` throughout.

### Why one person in the star has to throw a single

A double pass leaves your right hand and lands in your partner's **right**; a
single leaves your right and lands in their **left**. So a double flips which
hand your partner passes from, and a single leaves it alone.

The star's passing chain closes on itself after five people:

```
A -> C -> E -> B -> D -> A
```

Five doubles would flip the hand five times and leave A passing from the hand
opposite the one it started on — a contradiction. The number of doubles has to be
even, and five is odd. Four doubles and one single is the most you can have, and
it comes out at exactly 17 clubs. `star-17c-doubles.txt` is that pattern; the
test suite checks that no arrangement of five doubles works.

Note the chain is the **pentagram**, not the seating order. Alternating roles
round the circle A, B, C, D, E puts A and C on the same beats, and A passes to C —
two clubs into one hand.

### Getting all five to throw doubles

The even-doubles rule only binds while everybody shares one beat grid. Stand one
juggler **half a beat off** and it lifts: the two passes touching them stretch from
a 4 to a **4.5** to reach a hand that now arrives half a beat later. That is the
ordinary double pass of asynchronous passing — prechac writes it 4.5 for exactly
this reason — and it peaks about 40 cm higher than a 4, floatier but the same
throw. `star-17c-all-doubles.txt` is that pattern: five doubles, three 4s and two
4.5s, every one line and from the right hand.

Five doubles carry 18 clubs with plain 3s for selfs. Swapping one self for a
**zip** takes a club back out and lands it on 17; two zips gives 16, and so on.
A zip does not change any of the parity arguments above — a 1 is odd, like a 3 —
it only moves the club count.

### Why the zip cannot be shared out

Over ten beats a juggler passing every other beat throws five selfs, and only
three totals are throwable: **5, 15 or 25**. Fifteen is the ordinary case — five
3s, or any mix that keeps the total, like `5 1 3 3 3`. Thirteen (four 3s and a
zip) is not a pattern at all.

That decides everything about the zip:

- **17 clubs** needs one juggler down at a self-total of 5, and the only five
  selfs adding to 5 are **five zips**. So somebody zips on every self beat,
  permanently, and the job cannot move. A longer period does not help — the same
  arithmetic returns.
- **18 clubs** puts everyone at 15, where a `5 1` pair substitutes for `3 3`
  without changing the club count. Drop one into each person's ten beats at a
  rotating position and the zip ripples round the circle. The cost is the 5: a
  triple-height self, about 3.4 m, thrown to buy the time the zip gives back.

`star-17c-all-doubles.txt` is the first; `star-18c-travelling-zip.txt` the second.

### Why five identical jugglers can only hold a multiple of five clubs

Club count is five times the loop average. A 2-beat loop averages a whole or half
number, so five identical people total either a non-whole number of clubs (3.5
each would be 17.5) or a multiple of five — 15, 20, never 17 or 18. So of these
three you can have any two, never all three:

- 17 or 18 clubs
- 2-count: every pass from the right hand
- everybody throwing the same thing

`star-17c.txt` drops the second (5-beat loop, passes alternate hands),
`star-17c-2count.txt` drops the third (three different jobs), and
`star-15c-2count.txt` / `star-20c-2count.txt` drop the first.

Both 5-beat stars also need the loop **staggered** round the circle: each person starts the
same sequence one beat after the last. Everyone passing on the same beat, the way
the 15-club star does, has no valid solution at 17 clubs — the engine rejects
every one. The stagger turns the five simultaneous passes into a wave with
exactly one club crossing the star per beat.

## Sharing a pattern

Every pattern has its own link. Take the id from the dropdown and put it after
`?p=`:

```
https://thomas-killus.github.io/Passing-Simulator/?p=star-17c-all-doubles
```

Send that to whoever you are passing with — they need nothing installed.

### How the hosting works

The engine is a **build-time** tool. `python3 -m sim --build` runs it over every
file in `patterns/` and writes `docs/patterns/<id>.json` plus an `index.json` the
dropdown reads. What gets published is `docs/` — the viewer's five files and one
JSON per pattern, about 40 KB of code. No Python runs for a visitor, which is why
this can sit on free static hosting.

GitHub Pages is set to serve `main` / `docs`. The local server serves the very
same folder, so what you see while working is what visitors get.

### Adding a pattern

```
vim patterns/my-idea.txt
python3 -m sim patterns/my-idea.txt   # check it, watch it
python3 -m sim --build                # re-render docs/
git add -A && git commit && git push  # live in a minute or so
```

Committing `docs/patterns/` is deliberate — it keeps the site a pure static
build with no CI needed. A test fails if you forget to rerun `--build`, so a
stale site cannot ship.

## Tests

```
python3 -m pytest tests/       # engine, notation, geometry, export, build, CLI
node --test tests/js/          # the viewer's flight and spin maths
```

The node tests read the built files in `docs/patterns/`, so run
`python3 -m sim --build` first if you have just changed a pattern.
