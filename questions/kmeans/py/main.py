"""Your solution. Press Run to execute this file."""

from collections.abc import Sequence
from pathlib import Path

from dataviz import show
from pydantic import RootModel

Point = tuple[int, int]  # a data point: pixels, counts, ages
Centroid = tuple[float, float]  # a cluster center: a mean, so rarely integral


class Datasets(RootModel[dict[str, list[Point]]]):
    """data.json is a bare {name: points} mapping, so the model is that mapping itself.

    Validating into `Point` is what turns json's lists into tuples, which a solution
    reaching for `set(points)` or `{point: label}` needs — a list is not hashable.
    """

    @classmethod
    def load(cls, path: Path) -> dict[str, list[Point]]:
        return cls.model_validate_json(path.read_text()).root


def cluster(points: Sequence[Point], k: int = 3, max_iter: int = 20) -> Sequence[tuple[Centroid, list[Point]]]:
    """Cluster points into k groups.

    k: number of clusters, 1 <= k <= len(points)

    Returns one (centroid, its points) pair per cluster.
    """
    return []  # your clusters go here — Run draws whatever this returns


if __name__ == "__main__":
    DATASETS = Datasets.load(Path(__file__).with_name("data.json"))

    # a small dataset for testing
    TWENTY = DATASETS["TWENTY"]

    # the larger dataset we want to cluster
    BLOBS = DATASETS["BLOBS"]

    # visualize the dataset first
    show(points=TWENTY, title="the data")
