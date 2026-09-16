"""The datasets are what every other check here rests on, so their shape is asserted.

Sizes, ranges and spans — not the points themselves, which are `datasets.json`. A failure
here means `datasets.py` drifted from what packet.md tells the interviewer to expect.
"""

from __future__ import annotations

import json
from pathlib import Path

Point = tuple[int, int]

DATASETS: dict[str, list[Point]] = {
    name: [(x, y) for x, y in points] for name, points in json.loads((Path(__file__).parent.parent / "datasets.json").read_text()).items()
}
TWENTY = DATASETS["TWENTY"]
UNIFORM = DATASETS["UNIFORM"]


def test_twenty_is_hand_checkable() -> None:
    assert len(TWENTY) == 20
    assert len(set(TWENTY)) == 20, "duplicates make hand-checking ambiguous"
    assert all(float(v).is_integer() for p in TWENTY for v in p)
    assert all(0 <= v <= 100 for p in TWENTY for v in p)


def test_datasets_are_the_documented_size() -> None:
    sizes = {"TWENTY": 20, "BLOBS": 1000, "TIGHT": 1000, "LOPSIDED": 1000, "ELONGATED": 1000, "UNSCALED": 1000, "UNIFORM": 100}
    assert sizes.keys() == DATASETS.keys()
    for name, points in DATASETS.items():
        assert len(points) == sizes[name], name


def test_uniform_has_no_cluster_structure() -> None:
    points = UNIFORM
    assert all(0 <= v <= 100 for p in points for v in p)
    # evenly spread: each quadrant holds roughly a quarter of the points
    quadrants = [sum(1 for x, y in points if (x > 50) == right and (y > 50) == top) for right in (False, True) for top in (False, True)]
    assert all(15 <= q <= 35 for q in quadrants), quadrants


def test_datasets_have_distinct_shapes() -> None:
    spans = {}
    for name, points in DATASETS.items():
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        spans[name] = (max(xs) - min(xs), max(ys) - min(ys))
    assert spans["UNSCALED"][1] / spans["UNSCALED"][0] > 100  # y dwarfs x
    assert spans["TIGHT"][0] < 10  # small integer range
    assert spans["ELONGATED"][0] > spans["ELONGATED"][1]  # wider than tall
