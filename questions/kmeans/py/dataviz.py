"""Looking at an answer: the ASCII scatter plot and the one-line-per-cluster dump.

`dataviz` is the name the brief gives the candidate, and the pad puts this module beside
their solution rather than pasting it into it.


    show(pts)                     -> every point is '·'
    show(points=pts)              -> the same, spelled as a keyword
    show(groups)                  -> one mark per group, in list order
    show(groups, C)               -> centroids overlaid as their group's digit
    show(kmeans(pts, k))          -> [(centroid, its points), ...] — both at once
    show({centroid: pts, ...})    -> the same, as a mapping

Each shape is told apart by its first element and they cannot collide: a Point is a 2-tuple
of numbers, a (centroid, points) pair is a 2-tuple whose first element is one, and a group
of points is neither.

A group is any iterable of Point — a list, a generator, whatever. `Iterable` rather than
`Sequence` is deliberate and the opposite of kmeans(): show() makes exactly one pass and
materializes, so a generator is safe here in a way it is not for a multi-pass algorithm.

Non-finite coordinates are dropped and counted rather than raised on, so a half-broken
solution still draws something.

width/height of 0 mean auto: both come from the terminal, leaving room for the borders and
the prompt. The data is then stretched to fill that box on each axis independently, so the
result is a topology view rather than a scale drawing. Pass them explicitly for a fixed size.
"""

from __future__ import annotations  # so `| None` works on Python 3.9

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from itertools import cycle
from math import isfinite
from shutil import get_terminal_size
from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from collections.abc import Callable

MARKS = "●▲■◆★✚✦❖"  # if your terminal misaligns these, use "oxv+*#@%"
UNLABELED = "·"
BLANK = " "


# Plain tuples — no constructor to import, nothing to convert. The int/float split is
# the domain: data points are integral (pixels, counts, ages), a centroid is a mean and
# rarely is. By the numeric tower a Point is accepted wherever a Centroid is expected,
# but not the reverse — so a mean can never be mistaken for a data point.
Point = tuple[int, int]
Centroid = tuple[float, float]

Cell = tuple[int, int]  # (row, col) into the character grid
Pair = tuple[Centroid, Sequence[Point]]  # what kmeans() returns, one per cluster

# Every shape the first positional argument may take. A group is Iterable rather than
# Sequence on purpose — show() makes exactly one pass, so a generator is safe here.
Clusters = dict[Centroid, Sequence[Point]] | Sequence[Point] | Sequence[Iterable[Point]] | Iterable[Pair]


def _finite(points: Iterable[Centroid]) -> tuple[list[Centroid], int]:
    """Split points into the plottable ones and a count of the rest."""
    usable: list[Centroid] = []
    dropped = 0
    for x, y in points:
        if isfinite(x) and isfinite(y):
            usable.append((x, y))
        else:
            dropped += 1
    return usable, dropped


def _terminal_box(width: int, height: int) -> tuple[int, int]:
    """Grid size, defaulting to the terminal with room for borders and the prompt."""
    cols, rows = get_terminal_size((80, 24))
    return (
        width or max(20, min(120, cols - 2)),  # 2 columns for the │ borders
        height or max(5, min(60, rows - 4)),  # 2 rules, a title, a prompt
    )


def _projection(points: list[Centroid], width: int, height: int) -> Callable[[Centroid], Cell]:
    """Map data coordinates onto grid cells, stretching each axis to fill the box."""
    x0, x1 = min(x for x, _ in points), max(x for x, _ in points)
    y0, y1 = min(y for _, y in points), max(y for _, y in points)
    span_x, span_y = (x1 - x0) or 1.0, (y1 - y0) or 1.0

    def cell(point: Centroid) -> Cell:
        x, y = point
        col = round((x - x0) / span_x * (width - 1))
        row = round((y1 - y) / span_y * (height - 1))  # flip y: row 0 is the top
        return max(0, min(height - 1, row)), max(0, min(width - 1, col))

    return cell


def _is_point(value: object) -> bool:
    match value:
        case (int() | float(), int() | float()):
            return True
        case _:
            return False


def _resolve(
    clusters: Clusters,
    points: Iterable[Point] | None,
    centroids: Iterable[Centroid] | None,
) -> tuple[list[Iterable[Point]], list[Centroid]]:
    """Work out which of the call shapes this is. See the module docstring for all of them.

    Each is told apart by its first element and they cannot collide: a Point is a 2-sequence of
    numbers, a (centroid, points) pair is a 2-sequence whose first element is one, and a group
    of points is neither.
    """
    given = list(centroids) if centroids is not None else []
    if points is not None:
        return [points], given
    if isinstance(clusters, dict):
        # The mapping form: keys are the centroids, values their points. Checked before the
        # match below because a dict iterates as its keys, which is not what it means here.
        # The cast is because a dict is also an Iterable of its keys, so `Iterable[Pair]`
        # matches it too and widens them.
        mapping = cast("dict[Centroid, Sequence[Point]]", clusters)
        return list(mapping.values()), list(mapping.keys())

    items = list(clusters)
    match items:
        case []:
            return [], given
        case [(int() | float(), int() | float()), *_]:
            return [cast("list[Point]", items)], given  # one bare group: what a candidate reaches for first
        # `not _is_point(group)` is what keeps a two-point group from reading as a pair
        case [(centroid, group), *_] if _is_point(centroid) and not _is_point(group):
            pairs = cast("list[Pair]", items)
            return [pts for _, pts in pairs], [centroid for centroid, _ in pairs]
        case _:
            return cast("list[Iterable[Point]]", items), given


@overload
def show(clusters: dict[Centroid, Sequence[Point]], /, *, title: str = "", height: int = 0, width: int = 0) -> None: ...
@overload
def show(clusters: Iterable[Pair], /, *, title: str = "", height: int = 0, width: int = 0) -> None: ...
@overload
def show(points: Sequence[Point], /, *, title: str = "", height: int = 0, width: int = 0) -> None: ...
@overload
def show(clusters: Sequence[Iterable[Point]], /, *, title: str = "", height: int = 0, width: int = 0) -> None: ...
@overload
def show(
    clusters: Sequence[Iterable[Point]], centroids: Iterable[Centroid], /, *, title: str = "", height: int = 0, width: int = 0
) -> None: ...
@overload
def show(*, points: Iterable[Point] | None = None, title: str = "", height: int = 0, width: int = 0) -> None: ...


def _legend(centers: list[Centroid], marks: str, groups: int) -> str:
    """Which digit on the plot is which centroid, and the mark of the group it belongs to.

    A centroid past the last group gets no mark: the pairing is positional, so there is
    nothing for it to name.
    """
    return "  ".join(
        f"({cx:.4g}, {cy:.4g}): {index % 10}{marks[index % len(marks)] if index < groups else ''}"
        for index, (cx, cy) in enumerate(centers)
    )


def show(  # ruff: ignore[too-many-arguments] — width/height/title are plotting knobs, keyword-only and defaulted
    clusters: Clusters = (),
    centroids: Iterable[Centroid] | None = None,
    *,
    points: Iterable[Point] | None = None,
    title: str = "",
    height: int = 0,
    width: int = 0,
) -> None:
    """Print an ASCII scatter, one mark per group. See the module docstring."""
    resolved, centers = _resolve(clusters, points, centroids)
    groups = [_finite(group) for group in resolved]
    centers, dropped = _finite(centers)
    dropped += sum(n for _, n in groups)
    plotted = [point for group, _ in groups for point in group]

    if not plotted and not centers:
        print(f"(nothing to plot — {dropped} unusable)" if dropped else "(no points)")
        return

    width, height = _terminal_box(width, height)
    cell_of = _projection(plotted + centers, width, height)

    # Groups overlap, so tally every mark landing in a cell and let the majority hold it.
    marks = UNLABELED if len(groups) == 1 else MARKS
    tally: defaultdict[Cell, Counter[str]] = defaultdict(Counter)
    for mark, (group, _) in zip(cycle(marks), groups):
        for point in group:
            tally[cell_of(point)][mark] += 1

    grid = [[BLANK] * width for _ in range(height)]
    for (row, col), here in tally.items():
        grid[row][col] = here.most_common(1)[0][0]
    for index, center in enumerate(centers):  # drawn last, so a centroid wins its cell
        row, col = cell_of(center)
        grid[row][col] = str(index % 10)

    rule = "─" * width
    notes = [note for note in (title, f"{dropped} point(s) unusable" if dropped else "") if note]
    if centers:
        notes.append(_legend(centers, marks, len(groups)))
    print(f"┌{rule}")
    print("\n".join("│" + "".join(row) for row in grid))
    print(f"└{rule}  " + "  ·  ".join(notes))


def print_clusters(clusters: list[tuple[Centroid, list[Point]]]) -> None:
    """One line per cluster: `centroid: points`.

    Sorted so two runs are diffable — cluster order and point order are not part of the
    contract, and sorting inside kmeans() would be a misread of it.
    """
    for centroid, pts in sorted(clusters):
        coords = ",".join(f"({x:g},{y:g})" for x, y in sorted(pts))
        cx, cy = centroid
        print(f"({cx:.4g}, {cy:.4g}): {coords}")


def _demo() -> None:
    """Self-test: the input shapes show() accepts. Entry point for `interview-k`."""
    quad: list[Point] = [(x, x * x // 8 - 40) for x in range(-20, 21)]
    left = [p for p in quad if p[0] < 0]
    right = [p for p in quad if p[0] >= 0]

    show(points=quad, width=44, height=8, title="one group -> unlabeled")
    show([left, right], [(-10.0, -20.0), (10.0, -20.0)], width=44, height=8, title="two groups + centroids")
    show([(p for p in left), (p for p in right)], width=44, height=8, title="generators — safe, show() is single-pass")
    show([quad], [(0.0, float("nan"))], width=44, height=8, title="nan centroid does not crash")
    show(width=44)

    try:
        import numpy as np
    except ImportError:
        print("(numpy absent — stdlib path fine)")
    else:
        rng = np.random.default_rng(1)
        arr = rng.normal(0, 20, (80, 2))
        pts: list[Point] = [(round(x), round(y)) for x, y in arr]  # ndarray rows -> Point
        mid = [[p for p in pts if p[0] < 0], [p for p in pts if p[0] >= 0]]
        show(mid, [(-20.0, 0.0), (20.0, 0.0)], width=44, title="from an ndarray")


if __name__ == "__main__":
    _demo()
