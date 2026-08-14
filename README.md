# interview-k

A live-coding interview problem: implement k-means from scratch.

> [!WARNING]
> This repo contains the **answer key** — `docs/packet.md` (rubric, hint ladder),
> `main.py` (worked solution), `solutions.py` and `docs/answers.md` (expected
> output). Don't send a candidate the repo link; paste them the library and the
> problem statement.

| path | what |
|---|---|
| `src/interview_k/` | `show.py`, `data.py` — the candidate-facing half |
| `docs/packet.md` | interviewer packet: problem, rubric, hints, timeline |
| `docs/answers.md` | reference answers, generated |
| `solutions.py` | expected centroids / sizes / inertia per dataset |
| `main.py` | reference solution |
| `tools/answers.py` | regenerates `docs/answers.md` and `solutions.py` |
| `tools/sync_packet.py` | re-embeds library source into the packet |
| `tests/test_solutions.py` | grades `main.py` against all seven datasets |

## The problem

Implement k-means clustering from scratch. You're given `X`, an array of shape
`(n, d)` — n points in d dimensions — and an integer `k`. Return the cluster
label for each point and the final centroids. numpy is fine; scikit-learn and
scipy's clustering modules are not.

```python
def kmeans(X, k):
    """Returns (labels, centroids) — labels (n,), centroids (k, d)."""
    ...
```

Plenty is left unspecified on purpose. Ask.

## `show()` — ASCII scatter, stdlib only

No numpy, no matplotlib, so it renders the same in CoderPad, Colab, a notebook,
or a bare REPL.

```python
from interview_k import show

show(points)  # one group -> every point is '·'
show(*clusters)  # one mark per group, in argument order
show(*clusters, centroids=C)  # centroids overlaid as their group's digit
```

A group is any iterable of any iterable pair — tuples, lists, ndarray rows,
generators. Dimensions past the first two are ignored. `width`/`height` default
to the terminal size, and the domain is stretched to fill it on each axis
independently: a topology view, not a scale drawing.

Non-finite coordinates are dropped and counted rather than raised on, so a
half-finished solution still draws something:

```text
└────────────────────────────  1 point(s) unusable
```

Run the module to see every input shape it accepts:

```sh
uv run interview-k
```

If `●▲■◆★✚✦❖` render double-width in your terminal the grid will skew — swap
`MARKS` for the ASCII fallback noted on that line.

## Development

```sh
mise install && mise run sync
mise run test
mise run lint

uv run pytest tests/test_solutions.py                 # grade main.py
uv run python tools/answers.py > docs/answers.md      # regenerate answers
uv run python tools/answers.py --write-solutions      # regenerate solutions.py
uv run python tools/sync_packet.py                    # re-embed source in packet
```

To grade a candidate, drop their file in as `main.py` and run the harness.
