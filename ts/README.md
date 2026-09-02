# interview-k — TypeScript

A port of the Python half — no dependencies, no build step (Node ≥ 22.18 strips
the types itself).

## `show()` — ASCII scatter, no dependencies

```ts
import { show, TWENTY, DATASETS } from "./src/index.ts";

show({ points: TWENTY });                         // one group -> every point is '·'
show([left, right]);                              // one mark per group
show([left, right], C, { title: "k=2" });         // centroids as their group's digit
```

Same two call shapes as Python. The object form is what Python spells
`show(points=pts)` — TypeScript has no keyword arguments, so the single-group
call takes an object instead. Passing a bare list of points throws rather than
plotting nonsense.

A group is any `Iterable<Point>` — an array, a generator, whatever. `Iterable`
rather than `Array` is deliberate and the opposite of the k-means signature:
`show()` makes exactly one pass, so a generator is safe here in a way it is not
for a multi-pass algorithm.

Non-finite coordinates are dropped and counted rather than thrown on, so a
half-finished solution still draws something.

What doesn't survive the port is the `Point`/`Centroid` int/float split: both
are `[number, number]`, and the distinction is a comment.

## The datasets

Identical to Python's point for point, not merely similar — `src/random.ts`
reproduces CPython's Mersenne Twister, seeding and all, so `blobs(1)` is the
same 1000 points in both languages and the same answer key grades both.

```ts
import { BLOBS, DATASETS, TWENTY } from "./src/index.ts";
```

`test/parity.test.ts` enforces that against a fixture Python generates, down to
the byte-for-byte stdout of `show()`. `test/solutions.test.ts` holds `main.ts`
to the same answer key, which is what makes the port a port rather than a
lookalike.

## Development

```sh
npm ci
node --test test/*.test.ts   # the whole suite
npx tsc --noEmit
node src/show.ts             # the show() demo
```

The parity fixture is generated on the Python side: `uv run python -m tools.ts_fixture`
from `py/`.
