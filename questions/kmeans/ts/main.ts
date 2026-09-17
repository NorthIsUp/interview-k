/** Your solution. Press Run to execute this file. */

import { readFileSync } from "node:fs";

import { show } from "./dataviz.ts";

type Point = [number, number];
type Centroid = [number, number];

const { BLOBS } = JSON.parse(readFileSync("src/data.json", "utf8")) as { BLOBS: Point[] };

/**
 * Cluster points into k groups.
 *
 * k: number of clusters, 1 <= k <= points.length
 *
 * Returns one [centroid, its points] pair per cluster.
 */
function cluster(points: Point[], k: number, maxIter = 100): [Centroid, Point[]][] {
  throw new Error("not implemented");
}

show({ points: BLOBS, title: "the data" });
// once cluster works:  show(cluster(BLOBS, 3));
