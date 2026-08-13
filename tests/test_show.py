from __future__ import annotations

from typing import TYPE_CHECKING

from interview_k import show

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
    assert len(lines) == 9                      # 7 rows + 2 rules
    assert all(len(line) >= 31 for line in lines)


def test_degenerate_all_points_identical(capsys: pytest.CaptureFixture[str]) -> None:
    show([(2.0, 2.0)] * 5, width=20, height=5)  # zero span must not divide by zero
    assert "·" in capsys.readouterr().out
