from __future__ import annotations

from typing import TYPE_CHECKING

from interview_k import Centroid, Point, show
from interview_k.data import DATASETS, TWENTY

if TYPE_CHECKING:
    import pytest

SQUARE = [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_single_group_is_unlabeled(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE, width=20, height=5)
    out = capsys.readouterr().out
    assert "·" in out
    assert "●" not in out


def test_groups_get_distinct_marks(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE[:2], SQUARE[2:], width=20, height=5)
    out = capsys.readouterr().out
    assert "●" in out and "▲" in out
    assert "·" not in out


def test_centroids_render_as_digits(capsys: pytest.CaptureFixture[str]) -> None:
    show(SQUARE[:2], SQUARE[2:], centroids=[(0, 0.5), (1, 0.5)], width=20, height=5)
    assert "0" in capsys.readouterr().out


def test_non_finite_is_counted_not_raised(capsys: pytest.CaptureFixture[str]) -> None:
    show([*SQUARE, (float("nan"), 0.0)], width=20, height=5)
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
    show([(2.0, 2.0)] * 5, width=20, height=5)  # zero span must not divide by zero
    assert "·" in capsys.readouterr().out


def test_point_is_a_tuple_and_unpacks() -> None:
    p = Point(1.5, -2.0)
    assert isinstance(p, tuple)
    assert tuple(p) == (1.5, -2.0)
    assert (p.x, p.y) == (1.5, -2.0)


def test_point_accepts_integer_coordinates() -> None:
    p = Point(3, 4)  # pixels/counts are ordinary input; the numeric tower allows it
    assert p.x == 3


def test_centroid_is_an_alias_of_point() -> None:
    assert Centroid is Point
    assert Point(1.0, 2.0) == Centroid(1.0, 2.0)


def test_show_accepts_named_tuples(capsys: pytest.CaptureFixture[str]) -> None:
    left = [Point(0, 0), Point(0, 1)]
    right = [Point(1, 0), Point(1, 1)]
    show(left, right, centroids=[Centroid(0.0, 0.5), Centroid(1.0, 0.5)], width=20, height=5)
    out = capsys.readouterr().out
    assert "●" in out and "▲" in out and "0" in out


def test_twenty_is_hand_checkable() -> None:
    assert len(TWENTY) == 20
    assert all(isinstance(p, Point) for p in TWENTY)
    assert all(float(p.x).is_integer() and float(p.y).is_integer() for p in TWENTY)


def test_every_dataset_is_1000_points_and_deterministic() -> None:
    for name, fn in DATASETS.items():
        pts = fn()
        assert len(pts) == 1000, name
        assert fn() == pts, f"{name} is not deterministic"


def test_datasets_have_distinct_shapes() -> None:
    spans = {}
    for name, fn in DATASETS.items():
        pts = fn()
        spans[name] = (max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts))
    assert spans["unscaled"][1] / spans["unscaled"][0] > 100  # y dwarfs x
    assert spans["tight"][0] < 10  # small integer range
    assert spans["elongated"][0] > spans["elongated"][1]  # wider than tall
