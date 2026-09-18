/**
 * Looking at an answer: the ASCII scatter plot and the one-line-per-cluster dump.
 *
 * `dataviz` is the name the brief gives the candidate, and the pad puts this module beside
 * their solution rather than pasting it into it.
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
 * Ported from `py/dataviz.py`. The one thing the port cannot carry over is
 * the Point/Centroid int/float split: it is documentation only, TypeScript has one number
 * type.
 */

/** Python's `round`: half-to-even, unlike JS's half-up `Math.round`. */
function round(x: number): number {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac > 0.5) return floor + 1;
  if (frac < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

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

const XY = 2; // a Point, a Centroid and a Pair are all 2-arrays; only their contents differ

/** A cluster as cluster() returns it: its centroid, then its points. */
export type Pair = [Centroid, Iterable<Point>];

/**
 * Every shape the first argument may take. A group is Iterable rather than Array on purpose —
 * show() makes exactly one pass, so a generator is safe here.
 */
export type Clusters = Map<Centroid, Iterable<Point>> | Point[] | Iterable<Point>[] | Pair[];

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
  // one pass rather than Math.min(...xs): spreading an array of arguments throws RangeError
  // past ~65k of them, and Python's min() over a generator has no such ceiling to match.
  let x0 = Infinity;
  let x1 = -Infinity;
  let y0 = Infinity;
  let y1 = -Infinity;
  for (const [x, y] of points) {
    if (x < x0) x0 = x;
    if (x > x1) x1 = x;
    if (y < y0) y0 = y;
    if (y > y1) y1 = y;
  }
  const spanX = x1 - x0 || 1;
  const spanY = y1 - y0 || 1;

  return ([x, y]) => {
    const col = round(((x - x0) / spanX) * (width - 1));
    const row = round(((y1 - y) / spanY) * (height - 1)); // flip y: row 0 is the top
    return Math.max(0, Math.min(height - 1, row)) * width + Math.max(0, Math.min(width - 1, col));
  };
}

const isPoint = (value: unknown): value is Point =>
  Array.isArray(value) && value.length === XY && value.every((v) => typeof v === "number");

/** A [centroid, its points] pair — what cluster() returns, one per cluster. */
const isPair = (value: unknown): value is Pair =>
  Array.isArray(value) && value.length === XY && isPoint(value[0]) && !isPoint(value[1]);

/**
 * Work out which call shape this is. See the module docstring for all of them.
 *
 * Each is told apart by its first element and they cannot collide: a Point is a 2-array of
 * numbers, a pair is a 2-array whose first element is one, and a group of points is neither.
 */
function resolve(first: Clusters, centroids: Iterable<Centroid> | undefined): [Iterable<Point>[], Iterable<Centroid>] {
  if (first instanceof Map) return [[...first.values()], [...first.keys()]];

  const items = [...first];
  if (items.length === 0) return [[], centroids ?? []];
  if (isPoint(items[0])) return [[items as Point[]], centroids ?? []]; // one bare group
  if (isPair(items[0])) {
    const pairs = items as Pair[];
    return [pairs.map(([, pts]) => pts), pairs.map(([centroid]) => centroid)];
  }
  return [items as Iterable<Point>[], centroids ?? []];
}

/**
 * Which digit on the plot is which centroid, and the mark of the group it belongs to.
 *
 * A centroid past the last group gets no mark: the pairing is positional, so there is
 * nothing for it to name.
 */
function legend(centers: Centroid[], marks: string, groups: number): string {
  return centers
    .map(([cx, cy], index) => `(${g(cx, 4)}, ${g(cy, 4)}): ${index % 10}${index < groups ? marks[index % marks.length] : ""}`)
    .join("  ");
}

export function show(clusters: Map<Centroid, Iterable<Point>>, box?: ShowBox): void;
export function show(clusters: Pair[], box?: ShowBox): void;
export function show(points: Point[], box?: ShowBox): void;
export function show(clusters: Iterable<Point>[], centroids?: Iterable<Centroid>, box?: ShowBox): void;
// after the centroids form, so `show(groups, C)` still picks that one — a box is not iterable
export function show(clusters: Iterable<Point>[], box?: ShowBox): void;
export function show(spec: ShowSpec): void;

/** Print an ASCII scatter, one mark per group. See the module docstring. */
export function show(
  first: Clusters | ShowSpec = [],
  centroids?: Iterable<Centroid> | ShowBox,
  box: ShowBox = {},
): void {
  const spec = Array.isArray(first) || first instanceof Map ? null : first;
  // the 2-arg overloads pass a box where the 3-arg one passes centroids
  const asBox = centroids !== undefined && !(Symbol.iterator in Object(centroids)) ? (centroids as ShowBox) : undefined;
  const given = asBox ? undefined : (centroids as Iterable<Centroid> | undefined);
  const opts = spec ?? { ...(asBox ?? box) };

  const [resolved, found] = spec ? [[spec.points], spec.centroids ?? []] : resolve(first as Clusters, given);
  const groups = resolved.map(finite);
  const [centers, centroidsDropped] = finite(found);
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
  if (centers.length) notes.push(legend(centers, marks, groups.length));
  console.log(`┌${rule}`);
  console.log(grid.map((row) => "│" + row.join("")).join("\n"));
  console.log(`└${rule}  ` + notes.join("  ·  "));
}

export type Cluster = [Centroid, Point[]];

/** Significant digits with trailing zeros dropped — Python's `%g` / `%.4g`. */
const g = (value: number, digits: number): string => String(Number(value.toPrecision(digits)));

const byValue = (a: readonly [number, number], b: readonly [number, number]): number => a[0] - b[0] || a[1] - b[1];

/**
 * One line per cluster: `centroid: points`.
 *
 * Sorted so two runs are diffable — cluster order and point order are not part of the
 * contract, and sorting inside kmeans() would be a misread of it.
 */
export function printClusters(clusters: readonly Cluster[]): void {
  for (const [centroid, points] of [...clusters].sort(([a], [b]) => byValue(a, b))) {
    const coords = [...points]
      .sort(byValue)
      .map(([x, y]) => `(${g(x, 6)},${g(y, 6)})`)
      .join(",");
    console.log(`(${g(centroid[0], 4)}, ${g(centroid[1], 4)}): ${coords}`);
  }
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
