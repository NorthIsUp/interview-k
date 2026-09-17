# interview-k — Python

The candidate-facing half is this question's `py/dataviz.py` plus its `common/data.json`, stdlib only.

## `show()` — ASCII scatter, stdlib only

No numpy, no matplotlib, so it renders the same in CoderPad, Colab, a notebook,
or a bare REPL.

```python
from dataviz import show

show(pts)  # one group -> every point is '·'
show(points=pts)  # the same, spelled as a keyword
show(groups)  # one mark per group, in list order
show(groups, C)  # centroids overlaid as their group's digit
show(cluster(pts, k))  # [(centroid, its points), ...] — both at once
show({centroid: pts, ...})  # the same, as a mapping
```

Whatever shape you have, pass it. Each is told apart by its first element and
they cannot collide: a point is a pair of numbers, a `(centroid, points)` pair
is a pair whose first element is one, and a group of points is neither — so
`cluster()`'s own return value goes straight in.

A group is any iterable of any iterable pair — tuples, lists, ndarray rows,
generators. Dimensions past the first two are ignored. `width`/`height` default
to the terminal size, and the domain is stretched to fill it on each axis
independently: a topology view, not a scale drawing.

Non-finite coordinates are dropped and counted rather than raised on, so a
half-finished solution still draws something:

```text
└────────────────────────────  1 point(s) unusable
```

If `●▲■◆★✚✦❖` render double-width in your terminal the grid will skew — swap
`MARKS` for the ASCII fallback noted on that line.

## `print_clusters()` — one line per cluster

```python
from dataviz import print_clusters

print_clusters(clusters)  # (0, 8.5): (0,8)
```

Sorted by centroid, and points sorted within each cluster, so two runs are diffable. Cluster
order and point order are not part of the contract — sorting inside `kmeans` is a misread.

## The datasets

Seven of them, in `questions/kmeans/common/data.json`: `TWENTY`, `BLOBS`, `TIGHT`,
`LOPSIDED`, `ELONGATED`, `UNSCALED`, `UNIFORM`. Integer coordinates throughout.
No import and no package — the TypeScript side reads the same file:

```python
DATASETS = {name: [(x, y) for x, y in pts] for name, pts in json.loads(Path("data.json").read_text()).items()}
```

`questions/kmeans/common/data.py` holds the generators and the note on how each
set breaks k-means; `mise run sync kmeans` regenerates the file.

## Development

```sh
uv run interview-k                 # the show() demo, every input shape
uv run pytest                      # the whole suite
uv run pytest questions/kmeans     # grade that question's main.py
uv run pyright

mise run sync kmeans               # regenerate that question: data, answers, fixture, packet
mise run coderpad:sync --push      # sync every CoderPad project
```

To grade a candidate, drop their file in as `questions/<name>/py/main.py` and run the harness.
