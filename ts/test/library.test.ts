/** The TS twin of `py/tests/test_library.py`, test for test. */

import assert from "node:assert/strict";
import test from "node:test";

import { DATASETS, TWENTY, UNIFORM } from "../src/data.ts";
import { show, type Centroid, type Point } from "../src/show.ts";
import { capture } from "./capture.ts";

const SQUARE: Point[] = [
  [0, 0],
  [0, 1],
  [1, 0],
  [1, 1],
];

test("single group is unlabeled", () => {
  const out = capture(() => show([SQUARE], { width: 20, height: 5 }));
  assert.ok(out.includes("·"));
  assert.ok(!out.includes("●"));
});

test("groups get distinct marks", () => {
  const out = capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], { width: 20, height: 5 }));
  assert.ok(out.includes("●"));
  assert.ok(out.includes("▲"));
  assert.ok(!out.includes("·"));
});

test("centroids render as digits", () => {
  const centroids: Centroid[] = [
    [0, 0.5],
    [1, 0.5],
  ];
  assert.ok(capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], { centroids, width: 20, height: 5 })).includes("0"));
});

test("non-finite centroid is counted, not thrown", () => {
  // only a centroid can be NaN — it is a mean, and the mean of an empty cluster is NaN
  const out = capture(() => show([SQUARE], { centroids: [[NaN, 0]], width: 20, height: 5 }));
  assert.ok(out.includes("1 point(s) unusable"));
});

test("no points does not throw", () => {
  assert.ok(capture(() => show([], { width: 20, height: 5 })).includes("no points"));
});

test("accepts an iterator", () => {
  assert.ok(capture(() => show([SQUARE.values()], { width: 20, height: 5 })).includes("·"));
});

test("explicit size is honored", () => {
  const lines = capture(() => show([SQUARE], { width: 30, height: 7 })).trimEnd().split("\n");
  assert.equal(lines.length, 9); // 7 rows + 2 rules
  assert.ok(lines.every((line) => line.length >= 31));
});

test("degenerate: all points identical", () => {
  // zero span must not divide by zero
  const same = Array.from({ length: 5 }, () => [2, 2] as Point);
  assert.ok(capture(() => show([same], { width: 20, height: 5 })).includes("·"));
});

test("TWENTY is hand-checkable", () => {
  assert.equal(TWENTY.length, 20);
  assert.equal(new Set(TWENTY.map(String)).size, 20, "duplicates make hand-checking ambiguous");
  assert.ok(TWENTY.flat().every((v) => Number.isInteger(v) && v >= 0 && v <= 100));
});

test("datasets are the documented size", () => {
  const sizes: Record<string, number> = { blobs: 1000, tight: 1000, lopsided: 1000, elongated: 1000, unscaled: 1000, uniform: 100 };
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
  assert.ok(spans.unscaled![1] / spans.unscaled![0] > 100); // y dwarfs x
  assert.ok(spans.tight![0] < 10); // small integer range
  assert.ok(spans.elongated![0] > spans.elongated![1]); // wider than tall
});
