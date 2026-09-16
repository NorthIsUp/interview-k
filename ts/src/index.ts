/**
 * The plotting helpers. Question-agnostic — the datasets live with the question that uses
 * them, in `questions/<name>/ts/datasets.ts`.
 */

export { MARKS, printClusters, show } from "./dataviz.ts";
export type { Centroid, Cluster, Point, ShowBox, ShowSpec } from "./dataviz.ts";
