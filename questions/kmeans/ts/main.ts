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
function cluster(points: Point[], k = 3, maxIter = 20): [Centroid, Point[]][] {
  return []; // your clusters go here — Run draws whatever this returns
}

show({ points: BLOBS, title: "the data" });
show(cluster(BLOBS, 3));
