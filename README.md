# interview-k

A live-coding interview problem: implement k-means from scratch.

> [!WARNING]
> This repo contains the **answer key** — `docs/packet.md` (rubric, hint ladder),
> `py/main.py` / `ts/main.ts` (worked solutions), `py/solutions.py` and `docs/answers.md`
> (expected output). Don't send a candidate the repo link; paste them the library
> and the problem statement.

Python in `py/`, TypeScript in `ts/`, interview material in `docs/`. Each
language documents its own half:

- [`py/README.md`](py/README.md) — `show()`, the datasets, the Python harness
- [`ts/README.md`](ts/README.md) — the same two modules, ported

| path | what |
|---|---|
| `INSTRUCTIONS.md` | the candidate-facing brief; what `coderpad:sync` puts in the pad |
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
| `py/tools/coderpad.py` | builds both CoderPad projects; `--push` syncs them to the question bank |
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

`INSTRUCTIONS.md` is the version a candidate sees — keep the two in step.

## Development

```sh
mise install && mise run sync
mise run test          # pytest + node --test
mise run typecheck     # pyright + tsc
mise run lint
mise run coderpad:sync --push   # sync "k-means [py]" and "k-means [ts]" to the question bank
                                # add --recreate to change a project's files: CoderPad only
                                # takes them at creation, so the questions get new ids
```

Per-language commands live in each half's README.

To grade a candidate, drop their file in as `py/main.py` and run the harness.
