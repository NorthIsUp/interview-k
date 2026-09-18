"""Generate common/data.json for the k-means interview. Stdlib only, deterministic, integer coordinates.

TWENTY is a literal you can read at a glance and check by hand: 20 integer points in
[0, 100], three obvious clusters of 7/6/7. The generated sets each break k-means a
different way, so they double as the failure-mode probes — 1000 points each except
uniform, which is 100:

Run this (`mise run sync kmeans`) to regenerate common/data.json, which is what everything else
reads. Nothing imports this module; the JSON is the interface.

    blobs       three well-separated clusters — easy, unless you seed with the first k points
    tight       same shape on a small integer range — int centroids truncate here
    lopsided    cluster sizes 700/250/50 and unequal spread — k-means likes them even
    elongated   anisotropic clusters — k-means carves spheres, so it splits them wrong
    unscaled    y spans 1000x x — Euclidean distance sees only one feature
    uniform     100 points, no clusters at all — k-means still returns k of them
"""

from __future__ import annotations

import json
import random

# spelled out rather than imported: common/ is language-neutral, so it does not reach into py/
Point = tuple[int, int]
Centroid = tuple[float, float]


TWENTY: list[Point] = [
    (10, 15),
    (14, 20),
    (9, 22),
    (15, 14),
    (11, 19),
    (16, 21),
    (8, 17),
    (80, 28),
    (85, 33),
    (78, 31),
    (84, 26),
    (88, 30),
    (81, 35),
    (45, 75),
    (50, 80),
    (47, 82),
    (52, 76),
    (44, 79),
    (51, 83),
    (48, 77),
]


def _blob(rng: random.Random, center: Centroid, n: int, spread: tuple[float, float]) -> list[Point]:
    cx, cy = center
    sx, sy = spread
    return [(round(cx + rng.gauss(0, sx)), round(cy + rng.gauss(0, sy))) for _ in range(n)]


# Every ordering holds the same 1000 points, so which three lead the list is free to choose —
# and this one puts all three inside the (80, 30) blob. Seeding with points[:k], which is the
# first thing anyone writes, then converges to a fixed point 24x worse in inertia: two centroids
# split that blob between them and the third swallows both of the others. Picked by shuffling
# with each seed in range(4000) and keeping the one whose points[:3] converged worst; it is
# stable to 500 iterations, and seeding by sampling across the data still finds the real answer
# ~77% of the time. A baseline that rewards a better init is worth more than one that cannot.
BLOB_ORDER = 288


def blobs(seed: int = 1) -> list[Point]:
    """Three well-separated round clusters. The baseline — shape is easy, the ordering is not."""
    r = random.Random(seed)
    pts = _blob(r, (20, 20), 334, (4, 4)) + _blob(r, (80, 30), 333, (4, 4)) + _blob(r, (50, 80), 333, (4, 4))
    random.Random(BLOB_ORDER).shuffle(pts)
    return pts


def tight(seed: int = 2) -> list[Point]:
    """Same shape, small integer range. Integer centroids quantize and it breaks."""
    r = random.Random(seed)
    pts = _blob(r, (0, 0), 334, (0.6, 0.6)) + _blob(r, (3, 3), 333, (0.6, 0.6)) + _blob(r, (0, 3), 333, (0.6, 0.6))
    r.shuffle(pts)
    return pts


def lopsided(seed: int = 3) -> list[Point]:
    """700/250/50 with unequal spread. k-means pulls boundaries toward the big one."""
    r = random.Random(seed)
    pts = _blob(r, (20, 20), 700, (6, 6)) + _blob(r, (60, 60), 250, (3, 3)) + _blob(r, (20, 70), 50, (1.5, 1.5))
    r.shuffle(pts)
    return pts


def elongated(seed: int = 4) -> list[Point]:
    """Anisotropic clusters. k-means fits spheres, so it cuts these the wrong way."""
    r = random.Random(seed)
    pts = _blob(r, (30, 20), 334, (25, 2)) + _blob(r, (30, 40), 333, (25, 2)) + _blob(r, (30, 60), 333, (25, 2))
    r.shuffle(pts)
    return pts


def unscaled(seed: int = 5) -> list[Point]:
    """y spans ~1000x x. Euclidean distance sees only y until you standardize."""
    r = random.Random(seed)
    pts = _blob(r, (2, 5000), 334, (0.5, 900)) + _blob(r, (5, 5000), 333, (0.5, 900)) + _blob(r, (8, 5000), 333, (0.5, 900))
    r.shuffle(pts)
    return pts


def uniform(seed: int = 6) -> list[Point]:
    """100 points spread evenly over [0, 100]^2. There is no cluster structure here.

    k-means has no way to say so: it returns k clusters, every point assigned, inertia
    dutifully minimized. Nothing in the output distinguishes this from real structure —
    which is the whole argument for looking at the data before trusting the answer.
    """
    r = random.Random(seed)
    return [(r.randint(0, 100), r.randint(0, 100)) for _ in range(100)]


DATASETS: dict[str, list[Point]] = {
    "TWENTY": TWENTY,
    "BLOBS": blobs(),
    "TIGHT": tight(),
    "LOPSIDED": lopsided(),
    "ELONGATED": elongated(),
    "UNSCALED": unscaled(),
    "UNIFORM": uniform(),
}


def main() -> None:
    # one line per dataset: a 1000-point list pretty-printed is 4000 unreadable lines, and
    # this still diffs per dataset when one of them changes
    body = ",\n".join(f'  "{name}": {json.dumps([list(p) for p in points])}' for name, points in DATASETS.items())
    print("{\n" + body + "\n}")


if __name__ == "__main__":
    main()
