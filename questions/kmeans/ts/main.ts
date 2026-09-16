/**
 * Reference solution — what a candidate should end up with. NOT for the candidate.
 *
 * A port of `py/main.py`. It does not reproduce CPython's random number stream — the two
 * languages seed k-means++ differently and converge on the same optimum anyway, which is
 * what `test/solutions.test.ts` checks against the answer key.
 */

import type { Centroid, Point } from "../../../ts/src/dataviz.ts";

/**
 * Deterministic and tiny: a 32-bit LCG (Numerical Recipes), enough to seed k-means++.
 *
 * The restarts, not the generator, are what make the answer good — see kmeans() below.
 */
class Rng {
  #state: number;
  constructor(seed: number) {
    this.#state = seed >>> 0;
  }
  #next(): number {
    this.#state = (Math.imul(this.#state, 1664525) + 1013904223) >>> 0;
    return this.#state / 2 ** 32;
  }
  choice<T>(items: readonly T[]): T {
    return items[Math.floor(this.#next() * items.length)]!;
  }
  /** One draw weighted by `weights` — the slice of Python's `random.choices` we use. */
  choices<T>(items: readonly T[], weights: readonly number[]): T[] {
    const total = weights.reduce((a, b) => a + b, 0);
    let target = this.#next() * total;
    for (let i = 0; i < items.length; i++) {
      target -= weights[i]!;
      if (target <= 0) return [items[i]!];
    }
    return [items[items.length - 1]!];
  }
}

const N_INIT = 10;

export type Cluster = [Centroid, Point[]];

const d2 = (a: readonly [number, number], b: readonly [number, number]): number =>
  (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;

function assign(points: readonly Point[], centers: readonly Centroid[]): Point[][] {
  const groups: Point[][] = centers.map(() => []);
  for (const point of points) {
    let best = 0;
    let bestD = d2(point, centers[0]!);
    for (let i = 1; i < centers.length; i++) {
      // strictly-less keeps the first of a tie, which is what Python's min() does
      const candidate = d2(point, centers[i]!);
      if (candidate < bestD) {
        best = i;
        bestD = candidate;
      }
    }
    groups[best]!.push(point);
  }
  return groups;
}

function once(points: readonly Point[], k: number, rng: Rng): Cluster[] {
  // k-means++: seed each new centre far from the ones already chosen
  const centers: Centroid[] = [rng.choice(points)];
  while (centers.length < k) {
    const weights = points.map((p) => Math.min(...centers.map((c) => d2(p, c))));
    const total = weights.reduce((a, b) => a + b, 0);
    centers.push(total === 0 ? rng.choice(points) : rng.choices(points, weights)[0]!);
  }

  for (let iteration = 0; iteration < 300; iteration++) {
    const groups = assign(points, centers);
    // float division, so the centre is a mean even when every point is integral
    const moved: Centroid[] = groups.map((g) =>
      g.length === 0
        ? rng.choice(points)
        : [g.reduce((s, [x]) => s + x, 0) / g.length, g.reduce((s, [, y]) => s + y, 0) / g.length],
    );
    if (moved.every((c, i) => c[0] === centers[i]![0] && c[1] === centers[i]![1])) break;
    centers.splice(0, centers.length, ...moved);
  }
  return assign(points, centers).map((group, i) => [centers[i]!, group]);
}

const inertia = (clusters: readonly Cluster[]): number =>
  clusters.reduce((sum, [c, pts]) => sum + pts.reduce((s, p) => s + d2(p, c), 0), 0);

/** Cluster points into k groups. Best of N_INIT restarts by inertia. */
export function kmeans(points: readonly Point[], k: number): Cluster[] {
  const rng = new Rng(0);
  let best: Cluster[] | null = null;
  for (let i = 0; i < N_INIT; i++) {
    const candidate = once(points, k, rng);
    // strictly-less again: on a tie Python's min() keeps the earlier restart
    if (best === null || inertia(candidate) < inertia(best)) best = candidate;
  }
  return best!;
}
