/**
 * Datasets for the k-means interview. No dependencies, deterministic, integer coordinates
 * throughout — and identical, point for point, to the Python sets in
 * `py/src/interview_k/data.py`, because `random.ts` reproduces CPython's Mersenne Twister.
 *
 * TWENTY is a literal you can read at a glance and check by hand: 20 integer points in
 * [0, 100], three obvious clusters of 7/6/7. The generated sets each break k-means a
 * different way, so they double as the failure-mode probes — 1000 points each except
 * uniform, which is 100:
 *
 * Each is generated once at import and exported as a constant: BLOBS, TIGHT, and so on.
 * The functions remain if you want a different seed.
 *
 *     blobs       three well-separated clusters — the baseline that should just work
 *     tight       same shape on a small integer range — int centroids truncate here
 *     lopsided    cluster sizes 700/250/50 and unequal spread — k-means likes them even
 *     elongated   anisotropic clusters — k-means carves spheres, so it splits them wrong
 *     unscaled    y spans 1000x x — Euclidean distance sees only one feature
 *     uniform     100 points, no clusters at all — k-means still returns k of them
 */

import { Random, round } from "./random.ts";
import type { Centroid, Point } from "./show.ts";

export const TWENTY: Point[] = [
  [10, 15],
  [14, 20],
  [9, 22],
  [15, 14],
  [11, 19],
  [16, 21],
  [8, 17],
  [80, 28],
  [85, 33],
  [78, 31],
  [84, 26],
  [88, 30],
  [81, 35],
  [45, 75],
  [50, 80],
  [47, 82],
  [52, 76],
  [44, 79],
  [51, 83],
  [48, 77],
];

function blob(rng: Random, center: Centroid, n: number, spread: readonly [number, number]): Point[] {
  const [cx, cy] = center;
  const [sx, sy] = spread;
  // x before y: the draw order is part of the seed contract with the Python original.
  return Array.from({ length: n }, () => [round(cx + rng.gauss(0, sx)), round(cy + rng.gauss(0, sy))] as Point);
}

/** Three well-separated round clusters. The baseline. */
export function blobs(seed = 1): Point[] {
  const r = new Random(seed);
  const pts = [...blob(r, [20, 20], 334, [4, 4]), ...blob(r, [80, 30], 333, [4, 4]), ...blob(r, [50, 80], 333, [4, 4])];
  r.shuffle(pts);
  return pts;
}

/** Same shape, small integer range. Integer centroids quantize and it breaks. */
export function tight(seed = 2): Point[] {
  const r = new Random(seed);
  const pts = [...blob(r, [0, 0], 334, [0.6, 0.6]), ...blob(r, [3, 3], 333, [0.6, 0.6]), ...blob(r, [0, 3], 333, [0.6, 0.6])];
  r.shuffle(pts);
  return pts;
}

/** 700/250/50 with unequal spread. k-means pulls boundaries toward the big one. */
export function lopsided(seed = 3): Point[] {
  const r = new Random(seed);
  const pts = [...blob(r, [20, 20], 700, [6, 6]), ...blob(r, [60, 60], 250, [3, 3]), ...blob(r, [20, 70], 50, [1.5, 1.5])];
  r.shuffle(pts);
  return pts;
}

/** Anisotropic clusters. k-means fits spheres, so it cuts these the wrong way. */
export function elongated(seed = 4): Point[] {
  const r = new Random(seed);
  const pts = [...blob(r, [30, 20], 334, [25, 2]), ...blob(r, [30, 40], 333, [25, 2]), ...blob(r, [30, 60], 333, [25, 2])];
  r.shuffle(pts);
  return pts;
}

/** y spans ~1000x x. Euclidean distance sees only y until you standardize. */
export function unscaled(seed = 5): Point[] {
  const r = new Random(seed);
  const pts = [
    ...blob(r, [2, 5000], 334, [0.5, 900]),
    ...blob(r, [5, 5000], 333, [0.5, 900]),
    ...blob(r, [8, 5000], 333, [0.5, 900]),
  ];
  r.shuffle(pts);
  return pts;
}

/**
 * 100 points spread evenly over [0, 100]^2. There is no cluster structure here.
 *
 * k-means has no way to say so: it returns k clusters, every point assigned, inertia
 * dutifully minimized. Nothing in the output distinguishes this from real structure —
 * which is the whole argument for looking at the data before trusting the answer.
 */
export function uniform(seed = 6): Point[] {
  const r = new Random(seed);
  return Array.from({ length: 100 }, () => [r.randint(0, 100), r.randint(0, 100)] as Point);
}

export const BLOBS = blobs();
export const TIGHT = tight();
export const LOPSIDED = lopsided();
export const ELONGATED = elongated();
export const UNSCALED = unscaled();
export const UNIFORM = uniform();

/** Derived, for tours and tests. The constants above are the normal way in. */
export const DATASETS: Record<string, Point[]> = {
  blobs: BLOBS,
  tight: TIGHT,
  lopsided: LOPSIDED,
  elongated: ELONGATED,
  unscaled: UNSCALED,
  uniform: UNIFORM,
};
