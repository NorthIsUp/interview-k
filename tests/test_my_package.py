from __future__ import annotations

from my_package import add


def test_add() -> None:
    assert add(2, 3) == 5
