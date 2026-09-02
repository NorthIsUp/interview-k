/**
 * Reference solution — what a candidate should end up with. NOT for the candidate.
 *
 * A port of `py/main.py`, down to the order it draws random numbers in. `Random` is
 * CPython's MT19937 bit-for-bit, so seeding both with 0 makes the two languages take the
 * same k-means++ seeds and land on the same clusters — `test/solutions.test.ts` checks
 * that against the answer key rather than trusting the claim.
 */

import { Random } from "./src/random.ts";
import type { Centroid, Point } from "./src/show.ts";

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

function once(points: readonly Point[], k: number, rng: Random): Cluster[] {
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
  const rng = new Random(0);
  let best: Cluster[] | null = null;
  for (let i = 0; i < N_INIT; i++) {
    const candidate = once(points, k, rng);
    // strictly-less again: on a tie Python's min() keeps the earlier restart
    if (best === null || inertia(candidate) < inertia(best)) best = candidate;
  }
  return best!;
}
