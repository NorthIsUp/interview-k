/**
 * ASCII scatter plot for the k-means interview. No dependencies.
 *
 *     show({ points })                     -> every point is '·'
 *     show(clusters)                       -> one mark per group, in list order
 *     show(clusters, centroids)            -> centroids overlaid as their group's digit
 *
 * `clusters` is a list of groups, so a single group is `show({ points })` — passing one
 * bare list of points is the easy mistake and throws rather than plotting nonsense. The
 * object form is what Python spells `show(points=pts)`; TypeScript has no keyword args.
 *
 * A group is any `Iterable<Point>` — an array, a generator, whatever. `Iterable` rather
 * than `Array` is deliberate and the opposite of kmeans(): show() makes exactly one pass
 * and materializes, so a generator is safe here in a way it is not for a multi-pass
 * algorithm.
 *
 * Non-finite coordinates are dropped and counted rather than thrown on, so a half-broken
 * solution still draws something.
 *
 * width/height of 0 mean auto: both come from the terminal, leaving room for the borders
 * and the prompt. The data is then stretched to fill that box on each axis independently,
 * so the result is a topology view rather than a scale drawing. Pass them explicitly for
 * a fixed size.
 *
 * Ported from `py/src/interview_k/show.py`. The one thing the port cannot carry over is
 * the Point/Centroid int/float split: it is documentation only, TypeScript has one number
 * type.
 */

import { round } from "./random.ts";

export const MARKS = "●▲■◆★✚✦❖"; // if your terminal misaligns these, use "oxv+*#@%"
const UNLABELED = "·";
const BLANK = " ";

/** Data points are integral (pixels, counts, ages) — by convention, not by type. */
export type Point = readonly [number, number];
/** A centroid is a mean, and rarely integral. */
export type Centroid = readonly [number, number];

/** (row, col) into the character grid, flattened to `row * width + col`. */
type Cell = number;

export interface ShowBox {
  height?: number;
  width?: number;
  title?: string;
}

/** The single-group call: `show({ points })`, TypeScript's stand-in for a keyword arg. */
export interface ShowSpec extends ShowBox {
  points: Iterable<Point>;
  centroids?: Iterable<Centroid>;
}

/** Split points into the plottable ones and a count of the rest. */
function finite(points: Iterable<Centroid>): [Centroid[], number] {
  const usable: Centroid[] = [];
  let dropped = 0;
  for (const [x, y] of points) {
    if (Number.isFinite(x) && Number.isFinite(y)) usable.push([x, y]);
    else dropped++;
  }
  return [usable, dropped];
}

/** Grid size, defaulting to the terminal with room for borders and the prompt. */
function terminalBox(width: number, height: number): [number, number] {
  const cols = process.stdout.columns || 80;
  const rows = process.stdout.rows || 24;
  return [
    width || Math.max(20, Math.min(120, cols - 2)), // 2 columns for the │ borders
    height || Math.max(5, Math.min(60, rows - 4)), // 2 rules, a title, a prompt
  ];
}

/** Map data coordinates onto grid cells, stretching each axis to fill the box. */
function projection(points: Centroid[], width: number, height: number): (point: Centroid) => Cell {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = Math.min(...ys);
  const y1 = Math.max(...ys);
  const spanX = x1 - x0 || 1;
  const spanY = y1 - y0 || 1;

  return ([x, y]) => {
    const col = round(((x - x0) / spanX) * (width - 1));
    const row = round(((y1 - y) / spanY) * (height - 1)); // flip y: row 0 is the top
    return Math.max(0, Math.min(height - 1, row)) * width + Math.max(0, Math.min(width - 1, col));
  };
}

/** Catch the call that would otherwise plot nonsense: one bare list of points as clusters. */
function checked(clusters: Iterable<Point>[]): Iterable<Point>[] {
  const head = clusters[0];
  if (Array.isArray(head) && typeof head[0] === "number") {
    throw new TypeError("show() takes a list of clusters — use show({ points }) for one group, show([a, b]) for several");
  }
  return clusters;
}

export function show(clusters: Iterable<Point>[], centroids?: Iterable<Centroid>, box?: ShowBox): void;
export function show(spec: ShowSpec): void;

/** Print an ASCII scatter, one mark per group. See the module docstring. */
export function show(first: Iterable<Point>[] | ShowSpec = [], centroids?: Iterable<Centroid>, box: ShowBox = {}): void {
  const spec = Array.isArray(first) ? null : first;
  const opts = spec ?? { ...box, centroids };

  const groups = (spec ? [spec.points] : checked(first as Iterable<Point>[])).map(finite);
  const [centers, centroidsDropped] = finite(opts.centroids ?? []);
  const dropped = centroidsDropped + groups.reduce((sum, [, n]) => sum + n, 0);
  const plotted = groups.flatMap(([group]) => group);

  if (plotted.length === 0 && centers.length === 0) {
    console.log(dropped ? `(nothing to plot — ${dropped} unusable)` : "(no points)");
    return;
  }

  const [width, height] = terminalBox(opts.width ?? 0, opts.height ?? 0);
  const cellOf = projection([...plotted, ...centers], width, height);

  // Groups overlap, so tally every mark landing in a cell and let the majority hold it.
  // Insertion order breaks ties, which is how Python's Counter.most_common(1) breaks them.
  const marks = groups.length === 1 ? UNLABELED : MARKS;
  const tally = new Map<Cell, Map<string, number>>();
  groups.forEach(([group], index) => {
    const mark = marks[index % marks.length]!;
    for (const point of group) {
      const cell = cellOf(point);
      const here = tally.get(cell) ?? new Map<string, number>();
      here.set(mark, (here.get(mark) ?? 0) + 1);
      tally.set(cell, here);
    }
  });

  const grid = Array.from({ length: height }, () => new Array<string>(width).fill(BLANK));
  for (const [cell, here] of tally) {
    let best = BLANK;
    let bestCount = 0;
    for (const [mark, count] of here) {
      if (count > bestCount) [best, bestCount] = [mark, count];
    }
    grid[Math.floor(cell / width)]![cell % width] = best;
  }
  centers.forEach((center, index) => {
    // drawn last, so a centroid wins its cell
    const cell = cellOf(center);
    grid[Math.floor(cell / width)]![cell % width] = String(index % 10);
  });

  const rule = "─".repeat(width);
  const notes = [opts.title ?? "", dropped ? `${dropped} point(s) unusable` : ""].filter(Boolean);
  console.log(`┌${rule}`);
  console.log(grid.map((row) => "│" + row.join("")).join("\n"));
  console.log(`└${rule}  ` + notes.join("  ·  "));
}

/** Self-test: the input shapes show() accepts. */
export function demo(): void {
  const quad: Point[] = Array.from({ length: 41 }, (_, i) => {
    const x = i - 20;
    return [x, Math.floor((x * x) / 8) - 40];
  });
  const left = quad.filter(([x]) => x < 0);
  const right = quad.filter(([x]) => x >= 0);

  show({ points: quad, width: 44, height: 8, title: "one group -> unlabeled" });
  const halves: Centroid[] = [
    [-10, -20],
    [10, -20],
  ];
  show([left, right], halves, { width: 44, height: 8, title: "two groups + centroids" });
  show([left.values(), right.values()], undefined, { width: 44, height: 8, title: "iterators — safe, show() is single-pass" });
  show([quad], [[0, NaN]], { width: 44, height: 8, title: "NaN centroid does not crash" });
  show([], undefined, { width: 44 });
}

if (import.meta.main) demo();
