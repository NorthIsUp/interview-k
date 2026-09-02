/**
 * Grade `main.ts` against the Python answer key.
 *
 * `Random` is CPython's MT19937 bit-for-bit, so the two solutions draw the same k-means++
 * seeds and must land on the same clusters — not merely on a converged answer of their own.
 * A failure here means the port drifted, or a restart loop went missing.
 *
 * The partition is compared as a digest and the centroids to a tolerance, the same split
 * `py/tests/test_solutions.py` makes. Both sides normalise ordering away first, by the same
 * rule, because it is not part of the contract.
 */

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";

import { kmeans } from "../main.ts";
import { DATASETS, TWENTY } from "../src/data.ts";
import type { Centroid, Point } from "../src/show.ts";

interface Fixture {
  k: number;
  answers: Record<string, { partition: string; centroids: [number, number][] }>;
}

const fixture: Fixture = JSON.parse(readFileSync(new URL("./parity.json", import.meta.url), "utf8"));
const all: Record<string, Point[]> = { twenty: TWENTY, ...DATASETS };

const sha256 = (s: string): string => createHash("sha256").update(s).digest("hex");
const join = (points: readonly Point[]): string => points.map(([x, y]) => `${x},${y}`).join(";");

/** Lexicographic over flattened coordinates — for equal-length pairs, Python's tuple order. */
const cmp = (a: readonly number[], b: readonly number[]): number => {
  for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] !== b[i]) return a[i]! - b[i]!;
  return a.length - b.length;
};

function normalise(clusters: readonly [Centroid, Point[]][]): { centroids: Centroid[]; partition: string } {
  const groups = clusters
    .map(([centroid, points]) => ({ centroid, points: [...points].sort((p, q) => cmp(p, q)) }))
    .sort((a, b) => cmp(a.points.flat(), b.points.flat()));
  return {
    centroids: groups.map((g) => g.centroid),
    partition: sha256(groups.map((g) => sha256(join(g.points))).join("|")),
  };
}

for (const [name, answer] of Object.entries(fixture.answers)) {
  test(`main.ts reaches the Python answer for ${name}`, () => {
    const got = normalise(kmeans(all[name]!, fixture.k));

    assert.equal(got.partition, answer.partition, `${name}: different partition`);
    assert.equal(got.centroids.length, answer.centroids.length, `${name}: wrong cluster count`);
    got.centroids.forEach((centroid, i) => {
      assert.ok(Math.abs(centroid[0] - answer.centroids[i]![0]) < 1e-4, `${name}: centroid ${i} x drifted`);
      assert.ok(Math.abs(centroid[1] - answer.centroids[i]![1]) < 1e-4, `${name}: centroid ${i} y drifted`);
    });
  });
}
