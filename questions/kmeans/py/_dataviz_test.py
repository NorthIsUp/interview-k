from __future__ import annotations

import pytest

from questions.kmeans.py.dataviz import MARKS, Centroid, Point, show

# show() is question-agnostic, so these exercise it on shapes of their own — no question data
SQUARE: list[Point] = [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_point_and_centroid_are_plain_tuples() -> None:
    p: Point = (1, -2)  # data points are integral
    c: Centroid = (1.5, -2.5)  # a centroid is a mean
    assert (p, c) == ((1, -2), (1.5, -2.5))
    accepts_centroid: Centroid = p  # a Point flows into a Centroid, not the reverse
    assert accepts_centroid == p


def test_single_group_is_unlabeled(capsys: pytest.CaptureFixture[str]) -> None:
    show(points=SQUARE, width=20, height=5)
    out = capsys.readouterr().out
    assert "·" in out
    assert "●" not in out


def test_groups_get_distinct_marks(capsys: pytest.CaptureFixture[str]) -> None:
    show([SQUARE[:2], SQUARE[2:]], width=20, height=5)
    out = capsys.readouterr().out
    assert "●" in out
    assert "▲" in out
    assert "·" not in out


def test_centroids_render_as_digits(capsys: pytest.CaptureFixture[str]) -> None:
    show([SQUARE[:2], SQUARE[2:]], [(0, 0.5), (1, 0.5)], width=20, height=5)
    assert "0" in capsys.readouterr().out


def test_non_finite_centroid_is_counted_not_raised(capsys: pytest.CaptureFixture[str]) -> None:
    # only a centroid can be nan — it is a mean, and mean() of an empty cluster is nan
    show([SQUARE], [(float("nan"), 0.0)], width=20, height=5)
    assert "1 point(s) unusable" in capsys.readouterr().out


def test_no_points_does_not_raise(capsys: pytest.CaptureFixture[str]) -> None:
    show(width=20, height=5)
    assert "no points" in capsys.readouterr().out


def test_accepts_a_generator(capsys: pytest.CaptureFixture[str]) -> None:
    show(points=(p for p in SQUARE), width=20, height=5)
    assert "·" in capsys.readouterr().out


def test_explicit_size_is_honored(capsys: pytest.CaptureFixture[str]) -> None:
    show(points=SQUARE, width=30, height=7)
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 9  # 7 rows + 2 rules
    assert all(len(line) >= 31 for line in lines)


def test_degenerate_all_points_identical(capsys: pytest.CaptureFixture[str]) -> None:
    show(points=[(2, 2)] * 5, width=20, height=5)  # zero span must not divide by zero
    assert "·" in capsys.readouterr().out


def test_bare_point_list_is_one_group(capsys: pytest.CaptureFixture[str]) -> None:
    """The shape a candidate reaches for first, and it used to raise."""
    show(SQUARE, width=20, height=5)
    assert "·" in capsys.readouterr().out


def test_pairs_carry_their_own_centroids(capsys: pytest.CaptureFixture[str]) -> None:
    """kmeans() output goes straight in: the centroids come from the pairs, not a second arg."""
    show([((0.0, 0.5), SQUARE[:2]), ((1.0, 0.5), SQUARE[2:])], width=20, height=5)
    out = capsys.readouterr().out
    assert "0" in out and "1" in out


def test_mapping_form_is_centroid_to_points(capsys: pytest.CaptureFixture[str]) -> None:
    """`show({centroid: cluster, ...})` — the form the candidate brief promises."""
    show({(0.0, 0.5): SQUARE[:2], (1.0, 0.5): SQUARE[2:]}, width=20, height=5)
    out = capsys.readouterr().out
    assert "0" in out and "1" in out


def test_a_two_point_group_is_not_a_pair(capsys: pytest.CaptureFixture[str]) -> None:
    """[[a, b], [c, d]] is two groups, though each group is shaped exactly like a pair."""
    show([SQUARE[:2], SQUARE[2:]], width=20, height=5)
    out = capsys.readouterr().out
    assert MARKS[0] in out and MARKS[1] in out, "read as (centroid, points) pairs instead of groups"
