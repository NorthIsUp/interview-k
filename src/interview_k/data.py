"""Datasets for the k-means interview. Stdlib only, deterministic.

TWENTY is a literal you can read at a glance and check by hand: 20 integer points
in [0, 100], three obvious clusters of 7/6/7. The five 1000-point
sets each break k-means a different way, so they double as the §5 failure-mode probes:

    blobs       three well-separated clusters — the baseline that should just work
    tight       same shape on a small integer range — int centroids truncate here
    lopsided    cluster sizes 700/250/50 and unequal spread — k-means likes them even
    elongated   anisotropic clusters — k-means carves spheres, so it splits them wrong
    unscaled    y spans 1000x x — Euclidean distance sees only one feature
    uniform     100 points, no clusters at all — k-means still returns k of them
"""

from __future__ import annotations

import random

from interview_k.show import Point

TWENTY: list[Point] = [
    Point(10, 15),
    Point(14, 20),
    Point(9, 22),
    Point(15, 14),
    Point(11, 19),
    Point(16, 21),
    Point(8, 17),
    Point(80, 28),
    Point(85, 33),
    Point(78, 31),
    Point(84, 26),
    Point(88, 30),
    Point(81, 35),
    Point(45, 75),
    Point(50, 80),
    Point(47, 82),
    Point(52, 76),
    Point(44, 79),
    Point(51, 83),
    Point(48, 77),
]


def _blob(rng: random.Random, center: Point, n: int, spread: Point) -> list[Point]:
    return [Point(center.x + rng.gauss(0, spread.x), center.y + rng.gauss(0, spread.y)) for _ in range(n)]


def blobs(seed: int = 1) -> list[Point]:
    """Three well-separated round clusters. The baseline."""
    r = random.Random(seed)
    pts = _blob(r, Point(20, 20), 334, Point(4, 4)) + _blob(r, Point(80, 30), 333, Point(4, 4)) + _blob(r, Point(50, 80), 333, Point(4, 4))
    r.shuffle(pts)
    return pts


def tight(seed: int = 2) -> list[Point]:
    """Same shape, small integer range. Integer centroids quantize and it breaks."""
    r = random.Random(seed)
    pts = (
        _blob(r, Point(0, 0), 334, Point(0.6, 0.6))
        + _blob(r, Point(3, 3), 333, Point(0.6, 0.6))
        + _blob(r, Point(0, 3), 333, Point(0.6, 0.6))
    )
    r.shuffle(pts)
    return [Point(round(p.x), round(p.y)) for p in pts]


def lopsided(seed: int = 3) -> list[Point]:
    """700/250/50 with unequal spread. k-means pulls boundaries toward the big one."""
    r = random.Random(seed)
    pts = (
        _blob(r, Point(20, 20), 700, Point(6, 6)) + _blob(r, Point(60, 60), 250, Point(3, 3)) + _blob(r, Point(20, 70), 50, Point(1.5, 1.5))
    )
    r.shuffle(pts)
    return pts


def elongated(seed: int = 4) -> list[Point]:
    """Anisotropic clusters. k-means fits spheres, so it cuts these the wrong way."""
    r = random.Random(seed)
    pts = (
        _blob(r, Point(30, 20), 334, Point(25, 2)) + _blob(r, Point(30, 40), 333, Point(25, 2)) + _blob(r, Point(30, 60), 333, Point(25, 2))
    )
    r.shuffle(pts)
    return pts


def unscaled(seed: int = 5) -> list[Point]:
    """y spans ~1000x x. Euclidean distance sees only y until you standardize."""
    r = random.Random(seed)
    pts = (
        _blob(r, Point(2, 5000), 334, Point(0.5, 900))
        + _blob(r, Point(5, 5000), 333, Point(0.5, 900))
        + _blob(r, Point(8, 5000), 333, Point(0.5, 900))
    )
    r.shuffle(pts)
    return pts


def uniform(seed: int = 6) -> list[Point]:
    """100 points spread evenly over [0, 100]^2. There is no cluster structure here.

    k-means has no way to say so: it returns k clusters, every point assigned, inertia
    dutifully minimized. Nothing in the output distinguishes this from real structure —
    which is the whole argument for looking at the data before trusting the answer.
    """
    r = random.Random(seed)
    return [Point(r.uniform(0, 100), r.uniform(0, 100)) for _ in range(100)]


DATASETS = {f.__name__: f for f in (blobs, tight, lopsided, elongated, unscaled, uniform)}
