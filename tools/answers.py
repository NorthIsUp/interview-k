"""Generate the reference answers for the interview datasets.

Not for the candidate, and deliberately not in the public repo — this is the answer key.

k-means has no single "correct" output: different initialisations reach different local
minima. What is well defined is the *global* optimum, so this takes the best of many
k-means++ restarts by inertia. With fixed data and a fixed seed the result is reproducible,
which is what makes a candidate's output diffable against it.

    uv run python tools/answers.py > docs/answers.md
"""

from __future__ import annotations

import pathlib
import random

from interview_k.data import BLOBS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED
from interview_k.show import Centroid, Point, show

K = 3
N_INIT = 40
PER_ROW = 6  # points per line in the generated solutions.py
SEED = 0

_ALL: list[tuple[str, list[Point]]] = [
    ("TWENTY", TWENTY),
    ("BLOBS", BLOBS),
    ("TIGHT", TIGHT),
    ("LOPSIDED", LOPSIDED),
    ("ELONGATED", ELONGATED),
    ("UNSCALED", UNSCALED),
    ("UNIFORM", UNIFORM),
]


def _inertia(clusters: list[tuple[Centroid, list[Point]]]) -> float:
    return sum((x - cx) ** 2 + (y - cy) ** 2 for (cx, cy), pts in clusters for x, y in pts)


def _assign(points: list[Point], centers: list[Centroid]) -> list[list[Point]]:
    groups: list[list[Point]] = [[] for _ in centers]
    for x, y in points:
        best = min(range(len(centers)), key=lambda i: (x - centers[i][0]) ** 2 + (y - centers[i][1]) ** 2)
        groups[best].append((x, y))
    return groups


def _plus_plus(points: list[Point], k: int, rng: random.Random) -> list[Centroid]:
    centers: list[Centroid] = [rng.choice(points)]
    while len(centers) < k:
        d2 = [min((x - cx) ** 2 + (y - cy) ** 2 for cx, cy in centers) for x, y in points]
        total = sum(d2)
        centers.append(rng.choice(points) if total == 0 else rng.choices(points, weights=d2)[0])
    return centers


def _lloyd(points: list[Point], k: int, rng: random.Random) -> list[tuple[Centroid, list[Point]]]:
    centers = _plus_plus(points, k, rng)
    for _ in range(200):
        groups = _assign(points, centers)
        moved = [(sum(x for x, _ in g) / len(g), sum(y for _, y in g) / len(g)) if g else rng.choice(points) for g in groups]
        if moved == centers:
            break
        centers = moved
    return list(zip(centers, _assign(points, centers), strict=True))


def solve(points: list[Point], k: int) -> list[tuple[Centroid, list[Point]]]:
    """Best of N_INIT restarts by inertia — the global optimum, for practical purposes."""
    rng = random.Random(SEED)
    return min((_lloyd(points, k, rng) for _ in range(N_INIT)), key=_inertia)


def print_clusters(clusters: list[tuple[Centroid, list[Point]]]) -> None:
    for centroid, pts in sorted(clusters):
        coords = ",".join(f"({x:g},{y:g})" for x, y in sorted(pts))
        cx, cy = centroid
        print(f"({cx:.4g}, {cy:.4g}): {coords}")


READING = {
    "BLOBS": "Recovers the planted centres (20,20) (50,80) (80,30) and near-equal sizes. "
    "Anything else means a local minimum — ask for restarts.",
    "TIGHT": "**Centroids are not integers.** If a candidate returns whole numbers here, "
    "their centroid dtype was inherited from the integer data and truncated.",
    "LOPSIDED": "Recovers 700/250/50 exactly. k-means handles unequal sizes fine when the "
    "clusters are round and separated — this one is the control, not a failure.",
    "ELONGATED": "**The optimal answer is structurally wrong.** The data is three horizontal "
    "bars; the lowest-inertia partition cuts three vertical wedges, each spanning "
    "all three bars. No amount of restarting fixes it — k-means fits spheres.",
    "UNSCALED": "**All three centroids share x (4.88, 5.00, 5.23).** The planted structure was "
    "three bands at x=2,5,8; y spans ~1000x more, so Euclidean distance never saw x. "
    "Standardise first and the answer changes completely.",
    "UNIFORM": "No structure exists. Every partition below is 'correct' and none is meaningful.",
}


def _summary(name: str, points: list[Point], k: int) -> None:
    clusters = solve(points, k)
    print(f"### {name}  ·  k={k}  ·  n={len(points)}\n")
    print(f"inertia **{_inertia(clusters):.1f}**, sizes {sorted(len(p) for _, p in clusters)}\n")
    print("| centroid | size |")
    print("|---|---|")
    for centroid, pts in sorted(clusters):
        print(f"| ({centroid[0]:.4g}, {centroid[1]:.4g}) | {len(pts)} |")
    if name in READING:
        print(f"\n{READING[name]}")
    print()


def write_solutions(path: pathlib.Path) -> None:
    """Emit solutions.py — the expected kmeans() output per dataset, as checked-in data."""
    lines = [
        '"""Expected `kmeans(points, K)` output for each dataset.',
        "",
        "ANSWERS[name] has exactly the shape kmeans returns: one (centroid, its points) pair",
        "per cluster. Clusters are sorted by centroid and points within a cluster are sorted,",
        "so the data is stable across regenerations — ordering is not part of the contract.",
        "",
        "Generated by tools/answers.py — best of 40 k-means++ restarts, so these are global",
        "optima rather than one run's local minimum. Regenerate with:",
        "",
        "    uv run python tools/answers.py --write-solutions",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import TYPE_CHECKING",
        "",
        "if TYPE_CHECKING:",
        "    from interview_k.show import Centroid, Point",
        "",
        "K = 3",
        "",
        "ANSWERS: dict[str, list[tuple[Centroid, list[Point]]]] = {",
    ]
    for name, points in _ALL:
        lines.append(f"    {name!r}: [")
        for centroid, pts in sorted(solve(points, K)):
            lines.append(f"        (({centroid[0]!r}, {centroid[1]!r}), [")
            row: list[str] = []
            for point in sorted(pts):
                row.append(f"({point[0]}, {point[1]})")
                if len(row) == PER_ROW:
                    lines.append("            " + ", ".join(row) + ",")
                    row = []
            if row:
                lines.append("            " + ", ".join(row) + ",")
            lines.append("        ]),")
        lines.append("    ],")
    lines += ["}", ""]
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    import sys

    if "--write-solutions" in sys.argv:
        write_solutions(pathlib.Path(__file__).parent.parent / "solutions.py")
        print("wrote solutions.py")
        raise SystemExit(0)

    print("# Reference answers\n")
    print("Generated by `tools/answers.py` — best of", N_INIT, "k-means++ restarts, seed", SEED)
    print("\n**Answer key — do not share with candidates.**\n")

    print("## TWENTY — full expected output\n")
    print("```text")
    print_clusters(solve(TWENTY, 3))
    print("```\n")

    print("## Generated sets\n")
    print("Centroids only — the point lists are 1000 long. Compare these and the inertia.\n")
    for name, pts in (("BLOBS", BLOBS), ("TIGHT", TIGHT), ("LOPSIDED", LOPSIDED), ("ELONGATED", ELONGATED), ("UNSCALED", UNSCALED)):
        _summary(name, pts, 3)

    print("## ELONGATED — the failure, drawn\n")
    print("```text")
    elongated_answer = solve(ELONGATED, 3)
    show(
        *[pts for _, pts in elongated_answer],
        centroids=[c for c, _ in elongated_answer],
        width=56,
        height=12,
        title="lowest-inertia answer — three wedges, not three bars",
    )
    print("```\n")

    print("## UNIFORM — there is no right answer\n")
    print("Inertia falls monotonically with k on structureless data, so it cannot choose k.\n")
    for k in (2, 3, 5, 8):
        _summary("UNIFORM", UNIFORM, k)
