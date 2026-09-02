"""Looking at an answer: the scatter plot and the one-line-per-cluster dump.

`show()` lives in show.py and is re-exported here, so a candidate has one place to import
from — `dataviz` is the name the brief gives them, and the pad puts this module beside their
solution rather than pasting it into it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from interview_k.show import MARKS, show

if TYPE_CHECKING:
    from interview_k.show import Centroid, Point

__all__ = ["MARKS", "print_clusters", "show"]


def print_clusters(clusters: list[tuple[Centroid, list[Point]]]) -> None:
    """One line per cluster: `centroid: points`.

    Sorted so two runs are diffable — cluster order and point order are not part of the
    contract, and sorting inside kmeans() would be a misread of it.
    """
    for centroid, pts in sorted(clusters):
        coords = ",".join(f"({x:g},{y:g})" for x, y in sorted(pts))
        cx, cy = centroid
        print(f"({cx:.4g}, {cy:.4g}): {coords}")
