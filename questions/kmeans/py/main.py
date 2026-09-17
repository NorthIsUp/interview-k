"""Your solution. Press Run to execute this file."""

import json
from collections.abc import Sequence
from pathlib import Path

from dataviz import show

Point = tuple[int, int]  # a data point: pixels, counts, ages
Centroid = tuple[float, float]  # a cluster center: a mean, so rarely integral


def load_datasets() -> dict[str, list[Point]]:
    raw_data = json.loads(Path(__file__).with_name("data.json").read_text())
    return {
        name: [(int(x), int(y)) for x, y in points]  # points are tuples, but load as lists
        for name, points in raw_data.items()  # loads the JSON data from the file
    }


DATASETS = load_datasets()
BLOBS = DATASETS["BLOBS"]


def cluster(points: Sequence[Point], k: int = 3, max_iter: int = 20) -> Sequence[tuple[Centroid, list[Point]]]:
    """Cluster points into k groups.

    k: number of clusters, 1 <= k <= len(points)

    Returns one (centroid, its points) pair per cluster.
    """
    return []  # your clusters go here — Run draws whatever this returns


if __name__ == "__main__":
    show(points=BLOBS, title="the data")
    show(cluster(BLOBS, 3))
