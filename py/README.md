# interview-k — Python

The candidate-facing half is `src/interview_k/`: `show.py` and `data.py`, stdlib only.

## `show()` — ASCII scatter, stdlib only

No numpy, no matplotlib, so it renders the same in CoderPad, Colab, a notebook,
or a bare REPL.

```python
from interview_k import show

show(points=pts)  # one group -> every point is '·'
show(clusters)  # one mark per group, in list order
show(clusters, C)  # centroids overlaid as their group's digit
```

`clusters` is a list of groups, so one group is `show(points=pts)`. Passing a
bare list of points raises rather than plotting nonsense.

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

`data.py` generates seven of them once at import and exports each as a
constant — `TWENTY`, `BLOBS`, `TIGHT`, `LOPSIDED`, `ELONGATED`, `UNSCALED`,
`UNIFORM` — plus `DATASETS`, keyed by name. Integer coordinates throughout, and
deterministic: the same seed gives the same points every run.

```python
from interview_k.data import BLOBS, DATASETS, TWENTY
```

## Development

```sh
uv run interview-k                                    # the show() demo, every input shape
uv run pytest                                         # the whole suite
uv run pytest tests/test_solutions.py                 # grade main.py
uv run pyright

uv run python tools/answers.py > ../docs/answers.md   # regenerate answers
uv run python tools/answers.py --write-solutions      # regenerate solutions.py
uv run python tools/sync_packet.py                    # re-embed source in packet
uv run python -m tools.ts_fixture                     # refresh the TS parity fixture
uv run python tools/coderpad.py --push                # sync both CoderPad projects
```

To grade a candidate, drop their file in as `main.py` and run the harness.
