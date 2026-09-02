# interview-k

A live-coding interview problem: implement k-means from scratch.

> [!WARNING]
> This repo contains the **answer key** — `docs/packet.md` (rubric, hint ladder),
> `py/main.py` / `ts/main.ts` (worked solutions), `py/solutions.py` and `docs/answers.md`
> (expected output). Don't send a candidate the repo link; paste them the library
> and the problem statement.

Python in `py/`, TypeScript in `ts/`, interview material in `docs/`.

| path | what |
|---|---|
| `py/src/interview_k/` | `show.py`, `data.py` — the candidate-facing half |
| `ts/src/` | `show.ts`, `data.ts` — the same two modules, ported |
| `docs/packet.md` | interviewer packet: problem, rubric, hints, timeline |
| `docs/answers.md` | reference answers, generated |
| `py/solutions.py` | expected centroids / sizes / inertia per dataset |
| `py/main.py` | reference solution |
| `ts/main.ts` | the same solution, ported — same seeds, same clusters |
| `py/tools/answers.py` | regenerates `docs/answers.md` and `solutions.py` |
| `py/tools/sync_packet.py` | re-embeds library source into the packet |
| `py/tools/ts_fixture.py` | regenerates `ts/test/parity.json` (datasets, renders, answer key) |
| `py/tools/coderpad.py` | builds both pad bundles; `--push` syncs them to CoderPad |
| `py/tests/test_solutions.py` | grades `main.py` against all seven datasets |
| `ts/test/solutions.test.ts` | holds `main.ts` to the same answers |

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

Run the module to see every input shape it accepts:

```sh
uv run interview-k
```

If `●▲■◆★✚✦❖` render double-width in your terminal the grid will skew — swap
`MARKS` for the ASCII fallback noted on that line.

## TypeScript

`ts/` is a port of those same two modules — no dependencies, no build step
(Node ≥ 22.18 strips the types itself).

```ts
import { show, TWENTY, DATASETS } from "./ts/src/index.ts";

show({ points: TWENTY });                         // one group -> every point is '·'
show([left, right]);                              // one mark per group
show([left, right], C, { title: "k=2" });         // centroids as their group's digit
```

Same two call shapes as Python. The object form is what Python spells
`show(points=pts)` — TypeScript has no keyword arguments, so the single-group
call takes an object instead. What doesn't survive the port is the
`Point`/`Centroid` int/float split: both are `[number, number]`, and the
distinction is a comment.

The datasets are identical point for point, not merely similar — `ts/src/random.ts`
reproduces CPython's Mersenne Twister, seeding and all, so `blobs(1)` is the same
1000 points in both languages and the same answer key grades both.
`ts/test/parity.test.ts` enforces that against a fixture Python generates, down to
the byte-for-byte stdout of `show()`.

```sh
node ts/src/show.ts   # the same demo
```

## Development

```sh
mise install && mise run sync
mise run test          # pytest + node --test
mise run typecheck     # pyright + tsc
mise run lint
mise run coderpad:sync --push   # push "k-means [py]" and "k-means [ts]" to the question bank

cd py
uv run pytest tests/test_solutions.py                 # grade main.py
uv run python tools/answers.py > ../docs/answers.md   # regenerate answers
uv run python tools/answers.py --write-solutions      # regenerate solutions.py
uv run python tools/sync_packet.py                    # re-embed source in packet
uv run python tools/ts_fixture.py                     # refresh the TS parity fixture
```

To grade a candidate, drop their file in as `py/main.py` and run the harness.
