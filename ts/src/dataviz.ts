/**
 * Looking at an answer: the scatter plot and the one-line-per-cluster dump.
 *
 * `show()` lives in show.ts and is re-exported here, so a candidate has one place to import
 * from — `dataviz` is the name the brief gives them, and the pad puts this module beside their
 * solution rather than pasting it into it.
 *
 * Ported from `py/src/interview_k/dataviz.py`; `test/parity.test.ts` holds the output to
 * Python's byte for byte.
 */

import { MARKS, show, type Centroid, type Point } from "./show.ts";

export { MARKS, show };

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
