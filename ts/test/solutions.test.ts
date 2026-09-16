/**
 * Grade `main.ts` against the Python answer key.
 *
 * Not point for point: the two languages no longer share a random number stream, so they
 * reach different — equally converged — local minima. What is checked is what is actually
 * claimed, and it is what `py/tests/test_solutions.py` checks of a candidate: every point
 * assigned once, no empty cluster, each centroid the mean of its own points, and a cost
 * within 1.25x of the reference optimum.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { kmeans } from "../main.ts";
import { DATASETS } from "../src/index.ts";
import type { Centroid, Point } from "../src/dataviz.ts";

interface Fixture {
  k: number;
  answers: Record<string, { inertia: number; centroids: [number, number][] }>;
}

const fixture: Fixture = JSON.parse(readFileSync(new URL("./parity.json", import.meta.url), "utf8"));
const all: Record<string, Point[]> = DATASETS;

const d2 = (a: readonly [number, number], b: readonly [number, number]): number => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;

const inertia = (clusters: readonly [Centroid, Point[]][]): number =>
  clusters.reduce((sum, [c, pts]) => sum + pts.reduce((s, p) => s + d2(p, c), 0), 0);

const TOLERANCE = 1.25;

for (const [name, answer] of Object.entries(fixture.answers)) {
  test(`main.ts converges as well as the Python answer for ${name}`, () => {
    const points = all[name]!;
    const clusters = kmeans(points, fixture.k);

    assert.equal(clusters.length, fixture.k, `${name}: wrong cluster count`);
    assert.equal(
      clusters.reduce((n, [, pts]) => n + pts.length, 0),
      points.length,
      `${name}: points dropped or duplicated`,
    );
    for (const [centroid, pts] of clusters) {
      assert.ok(pts.length > 0, `${name}: empty cluster`);
      const mean = [pts.reduce((s, [x]) => s + x, 0) / pts.length, pts.reduce((s, [, y]) => s + y, 0) / pts.length];
      assert.ok(Math.abs(centroid[0] - mean[0]!) < 1e-9 && Math.abs(centroid[1] - mean[1]!) < 1e-9, `${name}: centroid is not the mean`);
    }
    // every point nearest its own centroid — the other half of the k-means fixed point
    for (const [centroid, pts] of clusters) {
      for (const point of pts) {
        const nearest = Math.min(...clusters.map(([c]) => d2(point, c)));
        assert.ok(d2(point, centroid) <= nearest + 1e-9, `${name}: ${point} is nearer another centroid`);
      }
    }
    assert.ok(inertia(clusters) <= answer.inertia * TOLERANCE, `${name}: inertia ${inertia(clusters)} vs reference ${answer.inertia}`);
  });
}
