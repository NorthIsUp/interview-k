"""Your solution. Press Run to execute this file."""

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from dataviz import show

Point = tuple[int, int]  # a data point: pixels, counts, ages
Centroid = tuple[float, float]  # a cluster center: a mean, so rarely integral

DATASETS: dict[str, list[Point]] = {
    name: [(x, y) for x, y in points] for name, points in json.loads(Path(__file__).with_name("data.json").read_text()).items()
}
BLOBS = DATASETS["BLOBS"]


def cluster(points: Sequence[Point], k: int, max_iter: int = 100) -> Iterable[tuple[Centroid, list[Point]]]:
    """Cluster points into k groups.

    k: number of clusters, 1 <= k <= len(points)

    Returns one (centroid, its points) pair per cluster.
    """
    ...


if __name__ == "__main__":
    show(points=BLOBS, title="the data")
    # once cluster works:  show(cluster(BLOBS, 3))
