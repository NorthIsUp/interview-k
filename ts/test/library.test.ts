/** The TS twin of `tests/test_library.py`, test for test. */

import assert from "node:assert/strict";
import test from "node:test";

import { show, type Centroid, type Point } from "../src/dataviz.ts";
import { capture } from "./capture.ts";

const SQUARE: Point[] = [
  [0, 0],
  [0, 1],
  [1, 0],
  [1, 1],
];

test("single group is unlabeled", () => {
  const out = capture(() => show({ points: SQUARE, width: 20, height: 5 }));
  assert.ok(out.includes("·"));
  assert.ok(!out.includes("●"));
});

test("groups get distinct marks", () => {
  const out = capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], undefined, { width: 20, height: 5 }));
  assert.ok(out.includes("●"));
  assert.ok(out.includes("▲"));
  assert.ok(!out.includes("·"));
});

test("centroids render as digits", () => {
  const centroids: Centroid[] = [
    [0, 0.5],
    [1, 0.5],
  ];
  assert.ok(capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], centroids, { width: 20, height: 5 })).includes("0"));
});

test("non-finite centroid is counted, not thrown", () => {
  // only a centroid can be NaN — it is a mean, and the mean of an empty cluster is NaN
  const out = capture(() => show([SQUARE], [[NaN, 0]], { width: 20, height: 5 }));
  assert.ok(out.includes("1 point(s) unusable"));
});

test("no points does not throw", () => {
  assert.ok(capture(() => show([], undefined, { width: 20, height: 5 })).includes("no points"));
});

test("accepts an iterator", () => {
  assert.ok(capture(() => show({ points: SQUARE.values(), width: 20, height: 5 })).includes("·"));
});

test("explicit size is honored", () => {
  const lines = capture(() => show({ points: SQUARE, width: 30, height: 7 })).trimEnd().split("\n");
  assert.equal(lines.length, 9); // 7 rows + 2 rules
  assert.ok(lines.every((line) => line.length >= 31));
});

test("degenerate: all points identical", () => {
  // zero span must not divide by zero
  const same = Array.from({ length: 5 }, () => [2, 2] as Point);
  assert.ok(capture(() => show({ points: same, width: 20, height: 5 })).includes("·"));
});

test("bare point list is rejected", () => {
  // show(SQUARE) reads as four clusters of two numbers — say so instead of plotting noise
  assert.throws(() => show(SQUARE as unknown as Point[][]), { name: "TypeError", message: /list of clusters/ });
});
