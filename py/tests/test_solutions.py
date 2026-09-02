"""Grade main.py against every dataset.

    uv run pytest tests/test_solutions.py

Drop a candidate's solution in as main.py to grade theirs instead. It must define:

    kmeans(points: Sequence[Point], k: int) -> list[tuple[Centroid, list[Point]]]

Most of these assert the k-means fixed-point conditions rather than an expected answer,
because there is no single right answer — different initialisations reach different local
minima, and all of them are legitimate. A result that satisfies all of them has genuinely
converged. Only the last test compares against the reference optimum, and it is a warning
about quality rather than a statement about correctness.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from interview_k.data import BLOBS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED
from main import kmeans
from solutions import ANSWERS, K

if TYPE_CHECKING:
    from interview_k.show import Centroid, Point

Clusters = list[tuple["Centroid", list["Point"]]]
Solved = tuple[str, list["Point"], Clusters]


DATASETS: dict[str, list[Point]] = {
    "TWENTY": TWENTY,
    "BLOBS": BLOBS,
    "TIGHT": TIGHT,
    "LOPSIDED": LOPSIDED,
    "ELONGATED": ELONGATED,
    "UNSCALED": UNSCALED,
    "UNIFORM": UNIFORM,
}


def _d2(a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _inertia(clusters: Clusters) -> float:
    return sum(_d2(p, c) for c, pts in clusters for p in pts)


@pytest.fixture(scope="module", params=list(DATASETS.items()), ids=list(DATASETS))
def solved(request: pytest.FixtureRequest) -> Solved:
    name, points = request.param
    return name, points, kmeans(points, K)


def test_returns_one_pair_per_cluster(solved: Solved) -> None:
    _, _, clusters = solved
    assert len(clusters) == K
    for centroid, points in clusters:
        assert len(centroid) == 2
        assert isinstance(points, list)


def test_every_point_assigned_exactly_once(solved: Solved) -> None:
    """A partition: nothing dropped, nothing duplicated, nothing invented."""
    _, points, clusters = solved
    assigned = [p for _, pts in clusters for p in pts]
    assert len(assigned) == len(points), "point count changed"
    assert sorted(assigned) == sorted(points), "the assigned points are not the input points"


def test_no_cluster_is_empty(solved: Solved) -> None:
    _, _, clusters = solved
    empty = [i for i, (_, pts) in enumerate(clusters) if not pts]
    assert not empty, f"clusters {empty} are empty — an empty cluster's mean is nan"


def test_centroid_is_the_mean_of_its_points(solved: Solved) -> None:
    """Catches integer truncation: a mean stored in an int is not the mean."""
    _, _, clusters = solved
    for centroid, points in clusters:
        mean_x = sum(x for x, _ in points) / len(points)
        mean_y = sum(y for _, y in points) / len(points)
        assert math.isclose(centroid[0], mean_x, abs_tol=1e-6), f"x: got {centroid[0]}, mean is {mean_x}"
        assert math.isclose(centroid[1], mean_y, abs_tol=1e-6), f"y: got {centroid[1]}, mean is {mean_y}"


def test_every_point_is_nearest_its_own_centroid(solved: Solved) -> None:
    """The other half of convergence: no point would rather be somewhere else."""
    _, _, clusters = solved
    centroids = [c for c, _ in clusters]
    for own, points in clusters:
        for point in points:
            nearest = min(_d2(point, c) for c in centroids)
            assert math.isclose(_d2(point, own), nearest, rel_tol=1e-9), (
                f"{point} sits in the cluster at {own} but is closer to another centroid"
            )


def test_inertia_is_close_to_the_reference_optimum(solved: Solved) -> None:
    """Quality, not correctness — a local minimum is still a converged answer.

    The soft version of the check below: it passes a solution that converged somewhere
    reasonable and fails one that converged badly.
    """
    name, _, clusters = solved
    best = _inertia(ANSWERS[name])
    got = _inertia(clusters)
    assert got <= best * 1.25, f"{name}: inertia {got:.1f} vs reference {best:.1f} — add restarts"


def test_matches_the_reference_answer(solved: Solved) -> None:
    """The whole expected output, compared against solutions.py.

    Stricter than correctness: a converged local minimum passes every test above and
    fails this one. That is the intended reading — it is the "did the restarts work"
    signal, not a bug. Ordering is normalised first, since it is not part of the contract.

    It also cannot detect a missing restart loop on its own: with k-means++ a single run
    lands on the optimum roughly 97% of the time. Ask about restarts in the interview.
    """
    name, _, clusters = solved
    got = sorted((tuple(round(v, 6) for v in c), sorted(pts)) for c, pts in clusters)
    want = sorted((tuple(round(v, 6) for v in c), sorted(pts)) for c, pts in ANSWERS[name])

    assert [pts for _, pts in got] == [pts for _, pts in want], f"{name}: different partition"
    for (gc, _), (wc, _) in zip(got, want, strict=True):
        assert gc == pytest.approx(wc, abs=1e-4), f"{name}: centroid {gc} != {wc}"
