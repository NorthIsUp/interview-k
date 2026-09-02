"""Reference solution — what a candidate should end up with. NOT for the candidate."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

Point = tuple[int, int]
Centroid = tuple[float, float]

N_INIT = 10


def _d2(a: Sequence[float], b: Sequence[float]) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _assign(points: Sequence[Point], centers: list[Centroid]) -> list[list[Point]]:
    groups: list[list[Point]] = [[] for _ in centers]
    for point in points:
        groups[min(range(len(centers)), key=lambda i: _d2(point, centers[i]))].append(point)
    return groups


def _once(points: Sequence[Point], k: int, rng: random.Random) -> list[tuple[Centroid, list[Point]]]:
    # k-means++: seed each new centre far from the ones already chosen
    centers: list[Centroid] = [rng.choice(points)]
    while len(centers) < k:
        weights = [min(_d2(p, c) for c in centers) for p in points]
        centers.append(rng.choice(points) if sum(weights) == 0 else rng.choices(points, weights)[0])

    for _ in range(300):
        groups = _assign(points, centers)
        # float division, so the centre is a mean even when every point is integral
        moved = [(sum(x for x, _ in g) / len(g), sum(y for _, y in g) / len(g)) if g else rng.choice(points) for g in groups]
        if moved == centers:
            break
        centers = moved
    return list(zip(centers, _assign(points, centers), strict=True))


def kmeans(points: Sequence[Point], k: int) -> list[tuple[Centroid, list[Point]]]:
    """Cluster points into k groups. Best of N_INIT restarts by inertia."""
    rng = random.Random(0)
    return min(
        (_once(points, k, rng) for _ in range(N_INIT)),
        key=lambda cl: sum(_d2(p, c) for c, pts in cl for p in pts),
    )
