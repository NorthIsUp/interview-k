"""Grade a solution against every dataset.

    uv run pytest tests/test_solutions.py                     # grades reference/main.py
    KMEANS_SOLUTION=/path/to/their/main.py uv run pytest tests/test_solutions.py

The module under test must define:

    kmeans(points: Sequence[Point], k: int) -> list[tuple[Centroid, list[Point]]]

Most of these assert the k-means fixed-point conditions rather than an expected answer,
because there is no single right answer — different initialisations reach different local
minima, and all of them are legitimate. A result that satisfies all of them has genuinely
converged. Only the last test compares against the reference optimum, and it is a warning
about quality rather than a statement about correctness.
"""

from __future__ import annotations

import importlib.util
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from interview_k.data import BLOBS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

    from interview_k.show import Centroid, Point

Clusters = list[tuple["Centroid", list["Point"]]]

K = 3
ROOT = Path(__file__).parent.parent
DATASETS: dict[str, list[Point]] = {
    "TWENTY": TWENTY,
    "BLOBS": BLOBS,
    "TIGHT": TIGHT,
    "LOPSIDED": LOPSIDED,
    "ELONGATED": ELONGATED,
    "UNSCALED": UNSCALED,
    "UNIFORM": UNIFORM,
}


class KMeans(Protocol):
    def __call__(self, points: Sequence[Point], k: int, /) -> Clusters: ...


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_path = Path(os.environ.get("KMEANS_SOLUTION", ROOT / "reference" / "main.py"))
if not _path.exists():
    pytest.skip(f"no solution at {_path}", allow_module_level=True)
kmeans = cast("KMeans", _load("solution_under_test", _path).kmeans)


def _d2(a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _inertia(clusters: Clusters) -> float:
    return sum(_d2(p, c) for c, pts in clusters for p in pts)


@pytest.fixture(scope="module", params=list(DATASETS.items()), ids=list(DATASETS))
def solved(request: pytest.FixtureRequest) -> tuple[str, list[Point], Clusters]:
    name, points = cast("tuple[str, list[Point]]", request.param)
    return name, points, kmeans(points, K)


def test_returns_one_pair_per_cluster(solved: tuple[str, list[Point], Clusters]) -> None:
    _, _, clusters = solved
    assert len(clusters) == K
    for centroid, points in clusters:
        assert len(centroid) == 2
        assert isinstance(points, list)


def test_every_point_assigned_exactly_once(solved: tuple[str, list[Point], Clusters]) -> None:
    """A partition: nothing dropped, nothing duplicated, nothing invented."""
    _, points, clusters = solved
    assigned = [p for _, pts in clusters for p in pts]
    assert len(assigned) == len(points), "point count changed"
    assert sorted(assigned) == sorted(points), "the assigned points are not the input points"


def test_no_cluster_is_empty(solved: tuple[str, list[Point], Clusters]) -> None:
    _, _, clusters = solved
    empty = [i for i, (_, pts) in enumerate(clusters) if not pts]
    assert not empty, f"clusters {empty} are empty — an empty cluster's mean is nan"


def test_centroid_is_the_mean_of_its_points(solved: tuple[str, list[Point], Clusters]) -> None:
    """Catches integer truncation: a mean stored in an int is not the mean."""
    _, _, clusters = solved
    for centroid, points in clusters:
        mean_x = sum(x for x, _ in points) / len(points)
        mean_y = sum(y for _, y in points) / len(points)
        assert math.isclose(centroid[0], mean_x, abs_tol=1e-6), f"x: got {centroid[0]}, mean is {mean_x}"
        assert math.isclose(centroid[1], mean_y, abs_tol=1e-6), f"y: got {centroid[1]}, mean is {mean_y}"


def test_every_point_is_nearest_its_own_centroid(solved: tuple[str, list[Point], Clusters]) -> None:
    """The other half of convergence: no point would rather be somewhere else."""
    _, _, clusters = solved
    centroids = [c for c, _ in clusters]
    for own, points in clusters:
        for point in points:
            nearest = min(_d2(point, c) for c in centroids)
            assert math.isclose(_d2(point, own), nearest, rel_tol=1e-9), (
                f"{point} sits in the cluster at {own} but is closer to another centroid"
            )


def test_inertia_is_close_to_the_reference_optimum(solved: tuple[str, list[Point], Clusters]) -> None:
    """Quality, not correctness — a local minimum is still a converged answer.

    Note what this cannot do: it does not detect a missing restart loop. With k-means++
    init a single run lands near the optimum roughly 97% of the time, so a no-restart
    solution usually passes. Verified — a deliberately restart-free variant passed every
    check. Ask about restarts in the interview; the harness will not raise it for you.
    """
    solver = _load("reference_solver", ROOT / "tools" / "answers.py")
    name, points, clusters = solved
    best = cast("float", solver._inertia(solver.solve(points, K)))
    got = _inertia(clusters)
    assert got <= best * 1.25 + 1e-9, f"{name}: inertia {got:.1f} vs reference {best:.1f} — add restarts"
