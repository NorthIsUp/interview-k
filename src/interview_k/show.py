"""ASCII scatter plot for the k-means interview. Stdlib only.

    show(points)                      -> every point is '·'
    show(*clusters)                   -> one mark per group, in argument order
    show(*clusters, centroids=C)      -> centroids overlaid as their group's digit

A group is any iterable of any indexable/iterable pair: tuples, lists, ndarray rows,
generators. Extra dimensions past the first two are ignored. Non-finite coordinates
are dropped and counted rather than raised on, so a half-broken solution still draws.

width/height of 0 mean auto: both are taken from the terminal, leaving room for the
borders and the prompt. The data domain is then stretched to fill that box on each
axis independently — the picture fills the screen, so it is a topology view, not a
scale drawing. Pass width/height explicitly when you need a fixed size for notes.
"""

from __future__ import annotations  # so `| None` works on Python 3.9

from collections import Counter
from collections.abc import Iterable, Sequence
from math import isfinite
from shutil import get_terminal_size

Group = Iterable[Sequence[float]]

MARKS = "●▲■◆★✚✦❖"       # if your terminal misaligns these, use "oxv+*#@%"
UNLABELED = "·"


def _xy(rows: Group) -> tuple[list[tuple[float, float]], int]:
    """-> (finite (x, y) pairs, count dropped as non-finite or malformed)."""
    pts: list[tuple[float, float]] = []
    dropped = 0
    for row in rows:
        try:
            it = iter(row)
            x, y = float(next(it)), float(next(it))
        except (StopIteration, TypeError, ValueError):
            dropped += 1
            continue
        if isfinite(x) and isfinite(y):
            pts.append((x, y))
        else:
            dropped += 1
    return pts, dropped


# ponytail: 23 locals is honest for a plotting routine — splitting it into helpers
# would trade one readable pass over the data for indirection. Ceiling: if this grows
# a third axis or styling, extract a Grid class.
def show(  # ruff: ignore[too-many-locals]
    *groups: Group,
    centroids: Group | None = None,
    height: int = 0,
    width: int = 0,
    title: str = "",
) -> None:
    """Print an ASCII scatter, one mark per group. See module docstring."""
    parsed = [_xy(g) for g in groups]
    cloud = [p for pts, _ in parsed for p in pts]
    cpts, cdropped = _xy(centroids) if centroids is not None else ([], 0)
    dropped = sum(d for _, d in parsed) + cdropped
    if not cloud and not cpts:
        print(f"(nothing to plot — {dropped} unusable)" if dropped else "(no points)")
        return

    xs = [p[0] for p in cloud + cpts]
    ys = [p[1] for p in cloud + cpts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    dx, dy = (x1 - x0) or 1.0, (y1 - y0) or 1.0

    cols, rows = get_terminal_size((80, 24))
    w = width or max(20, min(120, cols - 2))     # 2 for the │ borders
    h = height or max(5, min(60, rows - 4))      # 2 rules + title + prompt

    cell: dict[tuple[int, int], list[str]] = {}

    def place(pts: list[tuple[float, float]], ch: str) -> None:
        for x, y in pts:
            c = min(w - 1, max(0, round((x - x0) / dx * (w - 1))))
            r = min(h - 1, max(0, round((y1 - y) / dy * (h - 1))))   # flip y
            cell.setdefault((r, c), []).append(ch)

    solo = len(parsed) == 1
    for i, (pts, _) in enumerate(parsed):
        place(pts, UNLABELED if solo else MARKS[i % len(MARKS)])
    for i, c in enumerate(cpts):
        place([c], str(i % 10))

    grid = [[" "] * w for _ in range(h)]
    for (r, c), chs in cell.items():
        digits = [x for x in chs if x.isdigit()]      # centroid always wins its cell
        grid[r][c] = digits[0] if digits else Counter(chs).most_common(1)[0][0]

    bar = "─" * w
    print(f"┌{bar}")
    print("\n".join("│" + "".join(row) for row in grid))
    notes = [n for n in (title, f"{dropped} point(s) unusable" if dropped else "") if n]
    print(f"└{bar}  " + "  ·  ".join(notes))


def _demo() -> None:
    """Self-test: six input shapes. Entry point for `interview-k`."""
    quad = [(x / 4, (x / 4) ** 2 / 4 - 2) for x in range(-20, 21)]
    left = [p for p in quad if p[0] < 0]
    right = [p for p in quad if p[0] >= 0]

    show(quad, width=44, height=8, title="one group -> unlabeled")
    show(left, right, centroids=[(-2.5, 0.0), (2.5, 0.0)],
         width=44, height=8, title="two groups + centroids")
    show((p for p in left), (p for p in right), width=44, height=8, title="generators")
    show(quad, centroids=[(0.0, float("nan"))], width=44, height=8,
         title="nan centroid does not crash")
    show(width=44)
    try:
        import numpy as np
    except ImportError:
        print("(numpy absent — stdlib path fine)")
    else:
        rng = np.random.default_rng(1)
        pts = rng.normal(0, 1, (80, 2))
        lab = (pts[:, 0] > 0).astype(int)
        show(pts[lab == 0], pts[lab == 1], centroids=np.array([[-1.0, 0.0], [1.0, 0.0]]),
             width=44, title="ndarray groups, auto height")


if __name__ == "__main__":
    _demo()
