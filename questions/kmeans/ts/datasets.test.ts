/**
 * The datasets are what every other check here rests on, so their shape is asserted.
 *
 * Sizes, ranges and spans — not the points themselves, which are `datasets.json`. The
 * Python side asserts the same things in `py/test_datasets.py`, over the same file.
 */

import assert from "node:assert/strict";
import test from "node:test";

import type { Point } from "../../../ts/src/dataviz.ts";
import { DATASETS, TWENTY, UNIFORM } from "./datasets.ts";

test("TWENTY is hand-checkable", () => {
  assert.equal(TWENTY.length, 20);
  assert.equal(new Set(TWENTY.map(String)).size, 20, "duplicates make hand-checking ambiguous");
  assert.ok(TWENTY.flat().every((v) => Number.isInteger(v) && v >= 0 && v <= 100));
});

test("datasets are the documented size", () => {
  const sizes: Record<string, number> = { TWENTY: 20, BLOBS: 1000, TIGHT: 1000, LOPSIDED: 1000, ELONGATED: 1000, UNSCALED: 1000, UNIFORM: 100 };
  assert.deepEqual(Object.keys(DATASETS).sort(), Object.keys(sizes).sort());
  for (const [name, points] of Object.entries(DATASETS)) assert.equal(points.length, sizes[name], name);
});

test("uniform has no cluster structure", () => {
  assert.ok(UNIFORM.flat().every((v) => v >= 0 && v <= 100));
  // evenly spread: each quadrant holds roughly a quarter of the points
  const quadrants = [true, false].flatMap((right) =>
    [true, false].map((top) => UNIFORM.filter(([x, y]) => x > 50 === right && y > 50 === top).length),
  );
  assert.ok(
    quadrants.every((q) => q >= 15 && q <= 35),
    String(quadrants),
  );
});

test("datasets have distinct shapes", () => {
  const span = (points: Point[]): [number, number] => {
    const xs = points.map(([x]) => x);
    const ys = points.map(([, y]) => y);
    return [Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
  };
  const spans = Object.fromEntries(Object.entries(DATASETS).map(([name, points]) => [name, span(points)]));
  assert.ok(spans.UNSCALED![1] / spans.UNSCALED![0] > 100); // y dwarfs x
  assert.ok(spans.TIGHT![0] < 10); // small integer range
  assert.ok(spans.ELONGATED![0] > spans.ELONGATED![1]); // wider than tall
});
