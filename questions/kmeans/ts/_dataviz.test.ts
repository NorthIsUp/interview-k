/** The TS twin of `_dataviz_test.py`, test for test. */

import assert from "node:assert/strict";
import test from "node:test";

import { MARKS, show, type Centroid, type Point } from "./dataviz.ts";
import { capture } from "./_capture.ts";

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

test("bare point list is one group", () => {
  // the shape a candidate reaches for first, and it used to throw
  assert.ok(capture(() => show(SQUARE, { width: 20, height: 5 })).includes("·"));
});

test("pairs carry their own centroids", () => {
  // cluster() output goes straight in: the centroids come from the pairs, not a second argument
  const out = capture(() => show([[[0, 0.5], SQUARE.slice(0, 2)], [[1, 0.5], SQUARE.slice(2)]], { width: 20, height: 5 }));
  assert.ok(out.includes("0") && out.includes("1"));
});

test("map form is centroid to points", () => {
  const groups = new Map<Centroid, Point[]>([
    [[0, 0.5], SQUARE.slice(0, 2)],
    [[1, 0.5], SQUARE.slice(2)],
  ]);
  const out = capture(() => show(groups, { width: 20, height: 5 }));
  assert.ok(out.includes("0") && out.includes("1"));
});

test("a two-point group is not a pair", () => {
  // [[a, b], [c, d]] is two groups, though each group is shaped exactly like a pair
  const out = capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], { width: 20, height: 5 }));
  assert.ok(out.includes(MARKS[0]!) && out.includes(MARKS[1]!), "read as pairs instead of groups");
});

test("centroids get a legend", () => {
  const out = capture(() => show([SQUARE.slice(0, 2), SQUARE.slice(2)], [[0, 0.5], [1, 0.5]], { width: 40, height: 5 }));
  const footer = out.trimEnd().split("\n").at(-1)!;
  assert.ok(footer.includes(`(0, 0.5): 0${MARKS[0]}`));
  assert.ok(footer.includes(`(1, 0.5): 1${MARKS[1]}`));
});

test("no centroids means no legend", () => {
  const out = capture(() => show({ points: SQUARE, width: 40, height: 5, title: "just points" }));
  assert.ok(out.trimEnd().split("\n").at(-1)!.endsWith("just points"));
});

test("a centroid past the last group has no mark", () => {
  const out = capture(() => show([SQUARE.slice(0, 2)], [[0, 0.5], [1, 0.5]], { width: 40, height: 5 }));
  assert.ok(out.trimEnd().split("\n").at(-1)!.endsWith("(1, 0.5): 1"));
});
