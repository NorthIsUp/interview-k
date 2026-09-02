# k-means — Interviewer Packet

|                    |                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------- |
| Candidate          | ⬜                                                                                 |
| Interviewer        | ⬜                                                                                 |
| Date               | ⬜                                                                                 |
| Role / level       | ⬜ Data Scientist / Applied AI — ⬜                                                |
| Language &amp; env | HackerRank **CodePair** · Python 3 · numpy **2.4.1** ✅ · `sklearn.cluster` banned |
| Duration           | 45 min (5 setup · 25 core · 10 stretch · 5 wrap)                                   |

---

## 1. The Problem

**Prompt read aloud:**

> Implement k-means clustering from scratch. You're given `X`, a numpy array of shape
> `(n, d)` — n points in d dimensions — and an integer `k`. Return the cluster label for
> each point and the final centroids. numpy is fine; scikit-learn and scipy's clustering
> modules are not. Assume the data fits in memory.

**Given to the candidate:** the stub below, the datasets, and `show()`.

```python
from collections.abc import Sequence

Point = tuple[int, int]  # a data point: pixels, counts, ages
Centroid = tuple[float, float]  # a cluster center: a mean, so rarely integral


def kmeans(points: Sequence[Point], k: int, max_iter: int = 100) -> list[tuple[Centroid, list[Point]]]:
    """Cluster points into k groups.

    k: number of clusters, 1 <= k <= len(points)

    Returns one (centroid, its points) pair per cluster.
    """
    ...

```

`print_clusters` / `printClusters` is given to them, in the `dataviz` module beside their file.

```
(0, 8.5): (0,8)
(1.9, 2.6): (1,2),(2,3),(3,3)
(8.048, 8.5): (8,8),(8,9)
```

The TypeScript half of the repo hands them the same thing. `Point` and `Centroid` are
already defined by `show()`, so the stub does not redeclare them:

```typescript
type Cluster = [Centroid, Point[]];

/**
 * Cluster points into k groups.
 *
 * k: number of clusters, 1 <= k <= points.length
 *
 * Returns one [centroid, its points] pair per cluster.
 */
function kmeans(points: readonly Point[], k: number, maxIter = 100): Cluster[] {
  throw new Error("not implemented");
}
```

**Order is not graded** — not cluster order, not point order. `print_clusters` sorts so runs
are diffable. Sorting inside `kmeans` is a misread: say so, watch what they do (**Values
Feedback**).

Two things to watch for if they don't raise them:

- **`Sequence`, not `Iterable`** — k-means is multi-pass. A generator yields nothing on the
  second pass: centroids go `nan` and it "converges" to garbage with no exception.
- **Pairs, not `dict[Centroid, ...]`** — centroids move, collide, and can be `nan`. Two
  clusters converging to the same point merge into one entry and the first bucket's points are
  silently gone.

Row identity is the caller's job, not this function's.

### The dtype trap

Integer points are normal (pixels, counts, ages). Integer _centroids_ are not — a centroid is
a mean. The bug is letting `X`'s dtype reach them: `np.empty_like(centroids)` is `int64`, so
the assignment narrows.

```
X.mean(axis=0)            -> [0.333, 0.333]  float64   # fine
new[j] = X.mean(axis=0)   -> [0, 0]                    # narrowed, silently
```

Fix is `.astype(float)` on the initial centroids. It's scale-dependent, measured on integer
data, 100 seeds per cell:

| blob separation | int centroids wrong | float centroids wrong |
| --------------- | ------------------- | --------------------- |
| 3               | **78/100**          | 1/100                 |
| 8               | 20/100              | 23/100                |

Survives testing, breaks in production. Hand them `TIGHT` once their solution works. Naming
_where_ it breaks is a 4; naming that it depends on scale is a 4 you should hire.

**Plotting helper** (source at `src/interview_k/show.py`). Stdlib only, takes `Iterable[Point]`,
and drops non-finite coordinates with a count instead of raising — so a `nan` centroid still
plots and reports `1 point(s) unusable`.

```python
show(points=pts)  # one group -> every point is '·'
show(clusters)  # one mark per group, in list order
show(clusters, C)  # centroids overlaid as their group's digit
```

```python
"""ASCII scatter plot for the k-means interview. Stdlib only.

    show(points=pts)              -> every point is '·'
    show(clusters)                -> one mark per group, in list order
    show(clusters, C)             -> centroids overlaid as their group's digit

`clusters` is a list of groups, so a single group is `show(points=pts)` — passing one bare
list of points is the easy mistake and raises rather than plotting nonsense.

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
from itertools import cycle
from math import isfinite
from shutil import get_terminal_size
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

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


def _groups(clusters: Sequence[Iterable[Point]], points: Iterable[Point] | None) -> Sequence[Iterable[Point]]:
    """Resolve the two call shapes, and catch the one that would silently plot nonsense."""
    if points is not None:
        return [points]
    first = clusters[0] if clusters else None
    # a non-empty tuple of numbers is a Point, so it is a bare point list, not a cluster list
    if isinstance(first, tuple) and first and all(isinstance(v, (int, float)) for v in first):
        raise TypeError("show() takes a list of clusters — use show(points=pts) for one group, show([a, b]) for several")
    return clusters


def show(  # ruff: ignore[too-many-arguments] — width/height/title are plotting knobs, keyword-only and defaulted
    clusters: Sequence[Iterable[Point]] = (),
    centroids: Iterable[Centroid] | None = None,
    *,
    points: Iterable[Point] | None = None,
    height: int = 0,
    width: int = 0,
    title: str = "",
) -> None:
    """Print an ASCII scatter, one mark per group. See the module docstring."""
    groups = [_finite(group) for group in _groups(clusters, points)]
    centers, dropped = _finite(centroids if centroids is not None else ())
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
    print(f"┌{rule}")
    print("\n".join("│" + "".join(row) for row in grid))
    print(f"└{rule}  " + "  ·  ".join(notes))


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
```












`uv run interview-k` prints the self-tests. If `●▲■◆★✚✦❖` render double-width in your
terminal the grid skews — swap `MARKS` for the ASCII fallback on that line.

Open with `show(points=TWENTY)` and "how many clusters do you see?" — their answer tells you whether
they treat k as a parameter or a question.

### Datasets

`TWENTY` is the warm-up — small enough to read, to check by hand, and to print in full.

```python
TWENTY = [
    (10, 15),
    (14, 20),
    (9, 22),
    (15, 14),
    (11, 19),
    (16, 21),
    (8, 17),
    (80, 28),
    (85, 33),
    (78, 31),
    (84, 26),
    (88, 30),
    (81, 35),
    (45, 75),
    (50, 80),
    (47, 82),
    (52, 76),
    (44, 79),
    (51, 83),
    (48, 77),
]
```




Then the generated sets, each breaking k-means a different way. They double as the §5
failure-mode probes, so you can *show* a failure instead of describing it.

| dataset | what it does |
|---|---|
| `blobs` | three well-separated round clusters — the baseline, should just work |
| `tight` | same shape on a small integer range — integer centroids quantize and it breaks |
| `lopsided` | sizes 700/250/50, unequal spread — k-means pulls boundaries toward the big one |
| `elongated` | anisotropic clusters — k-means fits spheres, so it cuts them the wrong way |
| `unscaled` | y spans ~1000x x — Euclidean distance sees only y until you standardize |
| `uniform` | 100 points, **no clusters at all** — k-means still returns k of them |

Source — paste after the plotting helper:

```python
"""Datasets for the k-means interview. Stdlib only, deterministic, integer coordinates throughout.

TWENTY is a literal you can read at a glance and check by hand: 20 integer points in
[0, 100], three obvious clusters of 7/6/7. The generated sets each break k-means a
different way, so they double as the failure-mode probes — 1000 points each except
uniform, which is 100:

Each is generated once at import and exported as a constant: BLOBS, TIGHT, and so on.
The functions remain if you want a different seed.

    blobs       three well-separated clusters — the baseline that should just work
    tight       same shape on a small integer range — int centroids truncate here
    lopsided    cluster sizes 700/250/50 and unequal spread — k-means likes them even
    elongated   anisotropic clusters — k-means carves spheres, so it splits them wrong
    unscaled    y spans 1000x x — Euclidean distance sees only one feature
    uniform     100 points, no clusters at all — k-means still returns k of them
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kmeans_show import Centroid, Point

TWENTY: list[Point] = [
    (10, 15),
    (14, 20),
    (9, 22),
    (15, 14),
    (11, 19),
    (16, 21),
    (8, 17),
    (80, 28),
    (85, 33),
    (78, 31),
    (84, 26),
    (88, 30),
    (81, 35),
    (45, 75),
    (50, 80),
    (47, 82),
    (52, 76),
    (44, 79),
    (51, 83),
    (48, 77),
]


def _blob(rng: random.Random, center: Centroid, n: int, spread: tuple[float, float]) -> list[Point]:
    cx, cy = center
    sx, sy = spread
    return [(round(cx + rng.gauss(0, sx)), round(cy + rng.gauss(0, sy))) for _ in range(n)]


def blobs(seed: int = 1) -> list[Point]:
    """Three well-separated round clusters. The baseline."""
    r = random.Random(seed)
    pts = _blob(r, (20, 20), 334, (4, 4)) + _blob(r, (80, 30), 333, (4, 4)) + _blob(r, (50, 80), 333, (4, 4))
    r.shuffle(pts)
    return pts


def tight(seed: int = 2) -> list[Point]:
    """Same shape, small integer range. Integer centroids quantize and it breaks."""
    r = random.Random(seed)
    pts = _blob(r, (0, 0), 334, (0.6, 0.6)) + _blob(r, (3, 3), 333, (0.6, 0.6)) + _blob(r, (0, 3), 333, (0.6, 0.6))
    r.shuffle(pts)
    return pts


def lopsided(seed: int = 3) -> list[Point]:
    """700/250/50 with unequal spread. k-means pulls boundaries toward the big one."""
    r = random.Random(seed)
    pts = _blob(r, (20, 20), 700, (6, 6)) + _blob(r, (60, 60), 250, (3, 3)) + _blob(r, (20, 70), 50, (1.5, 1.5))
    r.shuffle(pts)
    return pts


def elongated(seed: int = 4) -> list[Point]:
    """Anisotropic clusters. k-means fits spheres, so it cuts these the wrong way."""
    r = random.Random(seed)
    pts = _blob(r, (30, 20), 334, (25, 2)) + _blob(r, (30, 40), 333, (25, 2)) + _blob(r, (30, 60), 333, (25, 2))
    r.shuffle(pts)
    return pts


def unscaled(seed: int = 5) -> list[Point]:
    """y spans ~1000x x. Euclidean distance sees only y until you standardize."""
    r = random.Random(seed)
    pts = _blob(r, (2, 5000), 334, (0.5, 900)) + _blob(r, (5, 5000), 333, (0.5, 900)) + _blob(r, (8, 5000), 333, (0.5, 900))
    r.shuffle(pts)
    return pts


def uniform(seed: int = 6) -> list[Point]:
    """100 points spread evenly over [0, 100]^2. There is no cluster structure here.

    k-means has no way to say so: it returns k clusters, every point assigned, inertia
    dutifully minimized. Nothing in the output distinguishes this from real structure —
    which is the whole argument for looking at the data before trusting the answer.
    """
    r = random.Random(seed)
    return [(r.randint(0, 100), r.randint(0, 100)) for _ in range(100)]


BLOBS = blobs()
TIGHT = tight()
LOPSIDED = lopsided()
ELONGATED = elongated()
UNSCALED = unscaled()
UNIFORM = uniform()

# Derived, for tours and tests. The constants above are the normal way in.
DATASETS: dict[str, list[Point]] = {
    "blobs": BLOBS,
    "tight": TIGHT,
    "lopsided": LOPSIDED,
    "elongated": ELONGATED,
    "unscaled": UNSCALED,
    "uniform": UNIFORM,
}
```









```python
show(points=ELONGATED)  # look at one
show(clusters, C)  # after they cluster it
```

`show()` stretches each axis to fill the box, so **`unscaled` plots fine while the algorithm
fails on it** — a plot normalizing away the exact problem the metric has. Worth saying aloud.

#### Grading harness

`tests/test_solutions.py` grades a solution against all seven datasets:

```sh
uv run pytest tests/test_solutions.py                    # grades reference/main.py
KMEANS_SOLUTION=~/their/main.py uv run pytest tests/test_solutions.py
```

It asserts the k-means **fixed-point conditions** rather than an expected answer, because
there is no single right answer — different initialisations reach different local minima and
all are legitimate:

| check | catches |
|---|---|
| every point assigned exactly once | dropped, duplicated, or invented points |
| no cluster is empty | the `nan` centroid |
| **centroid == mean of its points** | **integer truncation** — a mean stored as an int is not the mean |
| every point is nearest its own centroid | not actually converged |
| inertia within 1.25x of the reference | a badly unlucky run |

The third one earns its keep: it catches the dtype trap on all seven datasets with a message
like `x: got 82, mean is 82.66666666666667`, no special-casing needed. Verified against four
deliberately broken solutions — truncating, non-converged, point-dropping, and restart-free.

**One thing it cannot detect: a missing restart loop.** With k-means++ a single run lands near
the optimum ~97% of the time, so the restart-free variant passed all 42 checks. Raise restarts
in conversation; the harness will not do it for you.

#### Answer key

`docs/answers.md` holds the reference output — regenerate with
`uv run python tools/answers.py > docs/answers.md`. It takes the best of 40 k-means++ restarts,
so it is the global optimum rather than one run's local minimum, and it is reproducible.

**Answer key — never paste it into the shared pad.**

It carries the full expected `print_clusters` output for `TWENTY` (diffable line by line),
and for the 1000-point sets the centroids, inertia and sizes — plus a one-line reading of
what each result tells you. Three worth knowing before the interview:

- **TIGHT** — the correct centroids are *not* integers. A candidate returning whole numbers
  inherited their centroid dtype from the integer data.
- **ELONGATED** — the optimal answer is structurally wrong: three vertical wedges over data
  that is three horizontal bars. Restarts do not help; k-means fits spheres.
- **UNSCALED** — all three centroids share x (4.88, 5.00, 5.23). The planted structure was
  three bands *in x*, and the metric never saw it.

#### `uniform` is the sharp one

k-means cannot report "there is no structure here." It returns k clusters, every point
assigned, inertia minimized, and the output looks exactly like a real result:

| k | cluster sizes | inertia |
|---|---|---|
| 3 | 37 / 29 / 34 | 61,594 |
| 5 | 14 / 18 / 24 / 21 / 23 | **33,423** |

Balanced sizes, and k=5 scores *better* — on pure noise. Inertia falls monotonically as k
rises, because more centroids always means shorter distances, so the one number the algorithm
produces can never choose k for you. That's why the elbow method exists, and why on this data
there is no elbow to find.

Use it for **S2**: let them pick k on `BLOBS`, then hand them `UNIFORM` without saying what
changed. A 4 checks whether the clusters are real before reporting them.

**Constraints stated up front:**

- numpy yes; `sklearn.cluster`, `scipy.cluster` no.
- It has to run. We execute it on the toy data before the stretch section.
- Don't worry about data that doesn't fit in memory — unless you want to talk about it.

**Deliberately left ambiguous** (candidate should ask; each one they raise unprompted is
evidence for _Thrives in Ambiguity_):

- How are initial centroids chosen? (random data points / uniform in the bounding box /
  k-means++ — and does it matter?)
- What's the stopping condition? A 4 wants _both_ a tolerance and a `max_iter`, and can
  say why relying on either alone is a bug.
- What happens when a cluster ends up empty? (`X[mask].mean()` on an empty mask → `nan`,
  and everything downstream is poisoned.)
- Ties — a point exactly equidistant from two centroids.
- Is the data pre-scaled? Euclidean distance means unequal feature scales silently
  dominate the clustering.
- Determinism — should two runs with the same input agree?

---

## 2. Reference Solution

The bar for a **3**. Converges in \~7 iterations on the toy blobs.

```python
import numpy as np


def kmeans(X: Points, k: int, *, max_iter: int = 100, tol: float = 1e-6, seed: int = 0) -> tuple[Labels, Points]:
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    centroids = X[rng.choice(n, k, replace=False)].copy()

    for _ in range(max_iter):
        # (n, k) squared distances; sqrt is monotone, so argmin doesn't need it
        d2 = ((X[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = d2.argmin(axis=1)

        new = np.empty_like(centroids)
        for j in range(k):
            mask = labels == j
            new[j] = X[mask].mean(axis=0) if mask.any() else X[rng.integers(n)]

        shift = np.abs(new - centroids).max()
        centroids = new
        if shift <= tol:
            break

    return labels, centroids
```

**Complexity:** O(n·k·d) time per iteration, O(n·k·d) peak space — see the trap below.

### Local minima

On the toy data — three Gaussian blobs, σ=0.6, centers 8 apart, i.e. _obviously_ separable
by eye — the solution above lands in a **bad local minimum in 32% of runs** (64/200 seeds):
two centroids split one blob while the other two blobs merge. Swapping the init for
k-means++ drops that to **2.5%** (5/200).

Run both in front of a candidate who finishes early and ask why.

```text
┌──────────────────────────────────────────────────────────
│        ■■■■   ■                             ▲  ▲ ▲     ▲
│    ■■■■■■■■■■  ■                         ▲▲▲ ▲▲▲▲▲▲▲▲▲
│■ ■■■■■■2■■■■■                            ▲ ▲▲▲ ▲1▲▲ ▲▲▲ ▲
│   ■■  ■■■■   ■                            ▲    ▲ ▲  ▲▲
│
│
│
│
│               ●
│     ●● ●●●●
│  ● ●●●●●0●●●●●●
│   ●●● ●●●●● ●
└──────────────────────────────────────────────────────────  seed 4  inertia=204
```

```text
┌──────────────────────────────────────────────────────────
│        ■■■■   ■                             ▲  ● ●     ●
│    ■■■■■■■■■■  ■                         ▲▲▲ ▲▲▲●●●●●●
│■ ■■■■■■■■■■■■                            ▲ ▲▲1 ▲●●0 ●●● ●
│   ■■  ■■■■   ■                            ▲    ▲ ●  ●●
│
│
│         2
│
│               ■
│     ■■ ■■■■
│  ■ ■■■■■■■■■■■■
│   ■■■ ■■■■■ ■
└──────────────────────────────────────────────────────────  seed 0  inertia=3389
```

Same data, same code, different seed. On the bottom one the top-right blob is torn in half
between `▲` and `●`, the two left blobs are fused into one `■`, and centroid `2` is stranded
in empty space between them — a centroid sitting where there is no data is the tell.

"It works 68% of the time — is that fine?" The failure is _self-detecting_:

|               | inertia                                       |
| ------------- | --------------------------------------------- |
| 136 good runs | 203.9 – 203.9 — identical, the global optimum |
| 64 bad runs   | 3388.9 – 6622.2                               |

No overlap, 16× gap, on the objective it already computes each iteration. So restarts plus
keep-lowest-inertia is a complete fix:

| `n_init` | wrong    |
| -------- | -------- |
| 1        | 29.5%    |
| 3        | 2.5%     |
| 5        | **0.0%** |

A **4** gets to "run it a few times and keep the best inertia" on their own, and knows that's
why `sklearn` defaults to `n_init=10`. A **3** needs the nudge "what would tell you, from
inside the algorithm, that this run went badly?" A **2** treats 68% as good enough, or
reaches for a fix that requires labels they wouldn't have in production.

### Things a 4 mentions unprompted

- **The broadcasting memory trap.** `X[:, None, :] - centroids[None, :, :]` materializes an
  `(n, k, d)` intermediate — not `(n, k)`. At n=1e6, k=100, d=10 that's 8 GB. The fix is the
  expanded square: `d2 = (X**2).sum(1)[:,None] - 2 * X @ C.T + (C**2).sum(1)`, which only
  ever allocates `(n, k)`. Chunking rows is the other answer. Separates people who have
  written numpy at scale from people who have read about it.
- Skipping the `sqrt` because `argmin` is invariant under a monotone transform.
- The `for j in range(k)` update loop is the other slow half; `np.add.at` or
  `np.bincount(labels, weights=...)` vectorizes it.
- Inertia is non-increasing every step, so it always converges — **to a local minimum**, not
  the global one. Hence `n_init` restarts, keep the lowest inertia.
- Empty clusters produce `nan` via `mean` of an empty slice, and `nan` propagates silently.
- Euclidean distance means feature scaling is not optional.
- k-means assumes spherical, similarly-sized clusters — it will confidently carve a
  crescent or a density-varying dataset into nonsense.

---

## 3. Timeline &amp; Checkpoints

| At    | Expect                                                 | If not                                                                                         |
| ----- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| 0:05  | Clarifying questions asked, signature agreed           | Prompt once: "anything you'd want to pin down before coding?" — then hint 1                    |
| 0:15  | Assign step working (nearest centroid for every point) | Hint 2                                                                                         |
| 0:25  | Update step + a loop that terminates                   | Hint 3; if still nothing by 0:30, this caps _Problem Solving_ at 2                             |
| 0:30  | Runs end-to-end on the toy data                        | Have them run it regardless — a wrong answer they can see beats a clean-looking one they can't |
| 0:30+ | Move to stretch (§5)                                   | Still debugging? Stay. A finished core beats a rushed extension                                |

---

## 4. Hint Ladder

Give in order. Record which were used — hints cap **Thrives in Ambiguity**.

| #   | Trigger                            | Hint                                                                                          | Used? |
| --- | ---------------------------------- | --------------------------------------------------------------------------------------------- | ----- |
| 1   | 5 min in, no structure on the page | "What are the two steps that repeat until it settles?" → assign, then update                  | ☐     |
| 2   | Stuck on the distance computation  | "For a single point, how would you find its nearest centroid? Now do all n at once."          | ☐     |
| 3   | Loop with no exit, or `while True` | "How do you know when to stop?" — accept convergence, then push: "and if it never converges?" | ☐     |
| 4   | `nan` in the centroids             | "What happened to cluster 2 on that iteration?" → empty cluster → mean of an empty slice      | ☐     |
| 5   | Nested Python loops over n         | "What's the cost of this as n grows? Can numpy do the inner loop?"                            | ☐     |

**Hint 1 or 2 needed → cap _Thrives in Ambiguity_ at 2.** Hints 3–5 are cheaper; they're
about a specific edge case rather than about not knowing the shape of the algorithm.

---

## 5. Stretch Goals

Only if the core lands fast (≤ 25 min). **This is the 3-vs-4 line.** Not reaching them is no
deduction — they gate the top of the range, not the floor.

| #   | Extension      | Ask                                                                                                                                                               | Reached? | Notes |
| --- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----- |
| S1  | k-means++ init | "Your result changed between runs. Why, and what would you do about it?" — then show them the 32% → 2.5% number                                                   | ☐        | ⬜    |
| S2  | Choosing k     | "The client doesn't know k. Now what?" — elbow, silhouette, and the honest answer that it's often a domain question, not a math one                               | ☐        | ⬜    |
| S3  | Failure modes  | "When does this give a confidently wrong answer?" — unscaled features, outliers dragging centroids, non-spherical/crescent clusters, wildly unequal cluster sizes | ☐        | ⬜    |
| S4  | Scale to n=10M | "This has to run on 10 million points. What breaks first?" — the `(n, k, d)` intermediate; wants the expanded-square form or row chunking, then minibatch         | ☐        | ⬜    |

---

## 6. Running Notes

- `00:00` ⬜

---

## 7. Scorecard

| #   | Category                         | Score       | Evidence |
| --- | -------------------------------- | ----------- | -------- |
| 1   | Coding &amp; Syntax              | ⬜          | ⬜       |
| 2   | Data Structures &amp; Algorithms | ⬜          | ⬜       |
| 3   | Problem Solving                  | ⬜          | ⬜       |
| 4   | Communication                    | ⬜          | ⬜       |
| 5   | Thrives in Ambiguity             | ⬜          | ⬜       |
| 6   | Values Feedback                  | ⬜          | ⬜       |
|     | **Total**                        | **⬜ / 24** |          |

**Recommendation:** ⬜ Strong Hire · Leaning Hire · Leaning Don't Hire · Strong Don't Hire

**One-line summary for the packet:** ⬜

---

## Rubric Anchors

### 1. Coding &amp; Syntax

- **4** — No syntax errors. Turned each refinement into code effortlessly. Fluent with
  numpy idiom (broadcasting, axis args, boolean masks) and can name the equivalent in
  another language/framework. Compared several ways to write the same step.
- **3** — Few-to-no syntax errors. Translated the plan to code with little difficulty.
  Comfortable with common array constructs; may reach for a loop where broadcasting fits.
- **2** — Minor syntax errors. Coded the naive loop version but stumbled. Shaky on
  shapes, axes, or copy-vs-view.
- **1** — Several logical or syntactic errors that broke correctness. Confused about
  array shapes throughout.

### 2. Data Structures and Algorithms

- **4** — Explained the naive per-point loop and its cost, then the vectorized form,
  and picked deliberately. Gave O(n·k·d·iters) time and O(n·k) vs O(n+k) space, and tied
  the choice to a product constraint (n too large to materialize the distance matrix,
  latency budget, memory ceiling).
- **3** — Produced a working algorithm with sensible array layout. Fully explained or
  coded a more optimized version. Correct O-notation for time and space.
- **2** — Sub-optimal representation (e.g. list-of-lists, recomputing distances every
  pass) showing minor misunderstanding of how the cost scales. Naive algorithm, maybe
  suggested improvements.
- **1** — Poorly suited representation. Unclear on why the loop is slow or what the
  memory grows with. Could not move past the naive version.

### 3. Problem Solving

- **4** — Rapidly produced a correct, well-written solution with ample time left for
  stretch goals or alternatives.
- **3** — Solved the core problem with limited time to briefly discuss extensions.
- **2** — Barely finished in the time. Moved slowly, or made several wrong attempts
  before landing.
- **1** — Did not finish. Frequently lost, could not progress unassisted.

### 4. Communication

- **4** — Clearly narrated the solution and volunteered tangential depth — what
  `np.linalg.norm` / broadcasting actually does, why the objective decreases each step.
  Weighed pros and cons of sub-problems (init strategy, tie-breaking, stopping rule).
- **3** — Explained their thinking very clearly, but didn't fully justify the design and
  algorithmic choices behind it.
- **2** — Explained their process, but meandered when stuck. Went silent while thinking.
- **1** — Little or no narration. Interviewer had to prompt continuously.

### 5. Thrives in Ambiguity

- **4** — Worked independently. Raised the underspecified parts early and correctly —
  init strategy, convergence criterion, empty clusters, ties, feature scaling — and
  challenged assumptions (does k-means even fit this data?) with more than one answer.
- **3** — Needed minor hints. Asked a few good questions. Handled edge cases once they
  surfaced.
- **2** — Needed several major hints. Unclear whether they'd have progressed alone. No
  real discussion of the problem's open ends.
- **1** — Struggled to work independently. Avoided the unfamiliar parts. Leaned on the
  interviewer for direction.

### 6. Values Feedback

- **4** — Took feedback immediately, dug into why it was right, and pushed back where
  the pushback was warranted.
- **3** — Took feedback immediately, without probing or challenging it.
- **2** — Applied feedback slowly and without showing they understood it.
- **1** — Ignored hints or made little use of them.

---

## 8. HackerRank Setup

Environment is **CodePair**, numpy **2.4.1**. Runs as written in §1–§5.

On 2.4.1 a candidate reaching for `np.random.seed()` instead of a `Generator` is showing the
age of their habits, not an environment limit.

Re-check if HackerRank changes the image — their docs call CodePair's libraries sparse and
don't commit to numpy:

```python
import numpy as np

print(np.__version__)
```

### Paste-in setup cell

Drop this in the pad before they arrive:

```python
# setup — paste kmeans_show.py and data.py above this line, then:
show(points=TWENTY)  # "how many clusters do you see?"
```

### Authoring fields

HackerRank's custom-question form takes seven fields. Filled in for this problem:

**Challenge Name**

```
k-means from scratch
```

**Description** (one line, shown on the shared link)

```
Implement Lloyd's algorithm and reason about where it goes wrong.
```

**Problem Statement**

```
Implement k-means clustering from scratch.

You are given a sequence of Points and an integer k. Return one
(centroid, its points) pair per cluster. scikit-learn and scipy's
clustering modules are not available.

Several details are deliberately unspecified. Ask about anything you need.
```

**Input Format**

```
Not applicable — this is a CodePair pairing question, not a stdin/stdout
auto-graded one. X is created by the setup cell already in the pad.
```

**Constraints**

```
1 <= k <= n <= 10_000
d = 2 for the toy data; the solution should not assume d == 2
Data fits in memory
```

**Output Format**

```
One line per cluster, `centroid: points`, via the supplied print_clusters:

    (0, 8.5): (0,8)
    (1.9, 2.6): (1,2),(2,3),(3,3)
    (8.048, 8.5): (8,8),(8,9)

Cluster order and point order are not part of the contract. print_clusters
sorts both so that correct runs are diffable.
```

**Tags**

```
clustering, k-means, numpy, unsupervised-learning, pair-programming
```

**Input Format** and **Output Format** are artifacts of HackerRank's auto-graded questions and
carry no weight in CodePair. Fill them so the question saves; don't let them drag you toward a
print-the-answer framing.

### If numpy ever disappears

`show()` and the datasets are stdlib, so nothing in the setup changes — only the reference
solution does. The candidate writes plain Python, Category 2's evidence shifts from
broadcasting-vs-looping to hoisting invariants out of the inner loop, and the `(n, k, d)`
trap becomes a discussion question rather than a coded one.
