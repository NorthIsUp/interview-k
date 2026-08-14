from __future__ import annotations

from typing import TYPE_CHECKING

from interview_k import Centroid, Point, show
from interview_k.data import DATASETS, TWENTY

if TYPE_CHECKING:
    import pytest

SQUARE: list[Point] = [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_point_and_centroid_are_plain_tuples() -> None:
    p: Point = (1, -2)  # data points are integral
    c: Centroid = (1.5, -2.5)  # a centroid is a mean
    assert (p, c) == ((1, -2), (1.5, -2.5))
    accepts_centroid: Centroid = p  # a Point flows into a Centroid, not the reverse
    assert accepts_centroid == p


def test_single_group_is_unlabeled(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE, width=20, height=5)
    out = capsys.readouterr().out
    assert "·" in out
    assert "●" not in out


def test_groups_get_distinct_marks(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE[:2], SQUARE[2:], width=20, height=5)
    out = capsys.readouterr().out
    assert "●" in out
    assert "▲" in out
    assert "·" not in out


def test_centroids_render_as_digits(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE[:2], SQUARE[2:], centroids=[(0, 0.5), (1, 0.5)], width=20, height=5)
    assert "0" in capsys.readouterr().out


def test_non_finite_centroid_is_counted_not_raised(capsys: pytest.CaptureFixture[str]) -> None:
    # only a centroid can be nan — it is a mean, and mean() of an empty cluster is nan
    show(SQUARE, centroids=[(float("nan"), 0.0)], width=20, height=5)
    assert "1 point(s) unusable" in capsys.readouterr().out


def test_no_points_does_not_raise(capsys: pytest.CaptureFixture[str]) -> None:
    show(width=20, height=5)
    assert "no points" in capsys.readouterr().out


def test_accepts_a_generator(capsys: pytest.CaptureFixture[str]) -> None:
    show((p for p in SQUARE), width=20, height=5)
    assert "·" in capsys.readouterr().out


def test_explicit_size_is_honored(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE, width=30, height=7)
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 9  # 7 rows + 2 rules
    assert all(len(line) >= 31 for line in lines)


def test_degenerate_all_points_identical(capsys: pytest.CaptureFixture[str]) -> None:
    show([(2, 2)] * 5, width=20, height=5)  # zero span must not divide by zero
    assert "·" in capsys.readouterr().out


def test_twenty_is_hand_checkable() -> None:
    assert len(TWENTY) == 20
    assert len(set(TWENTY)) == 20, "duplicates make hand-checking ambiguous"
    assert all(float(v).is_integer() for p in TWENTY for v in p)
    assert all(0 <= v <= 100 for p in TWENTY for v in p)


def test_datasets_are_the_documented_size() -> None:
    sizes = {"blobs": 1000, "tight": 1000, "lopsided": 1000, "elongated": 1000, "unscaled": 1000, "uniform": 100}
    assert sizes.keys() == DATASETS.keys()
    for name, points in DATASETS.items():
        assert len(points) == sizes[name], name


def test_uniform_has_no_cluster_structure() -> None:
    points = DATASETS["uniform"]
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
    assert spans["unscaled"][1] / spans["unscaled"][0] > 100  # y dwarfs x
    assert spans["tight"][0] < 10  # small integer range
    assert spans["elongated"][0] > spans["elongated"][1]  # wider than tall
