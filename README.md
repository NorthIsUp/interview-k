# interview-k

Live-coding interview questions, one directory each, in Python and TypeScript —
plus `show()`, a dependency-free ASCII scatter that renders anywhere a candidate
might be typing.

> [!WARNING]
> This repo contains the **answer keys** — packets, worked solutions and expected
> output. Don't send a candidate the repo link; paste them the library and the
> problem statement.

| path | what |
|---|---|
| `questions/<name>/` | one question: brief, packet, data, and a directory per language |
| `src/interview_k/` | `dataviz.py` — `show()`, shared by every question |
| `ts/src/` | `dataviz.ts`, `index.ts` — the same helper, ported |
| `tools/coderpad.py` | builds a CoderPad project per question per language; `--push` syncs them |
| `coderpad.toml` | which question in the bank is which of ours; maintained by `coderpad:sync` |
| `tests/` | library and tooling tests; each question grades itself in its own directory |

## A question directory

`questions/kmeans/` is the pattern. The only required file is `sync.py` —
`mise run sync <name>` runs it, `mise run sync` runs every one, and a directory
becomes a question the moment it has one.

| path | what |
|---|---|
| `INSTRUCTIONS.md` | the candidate-facing brief; what `coderpad:sync` puts in the pad |
| `packet.md` | interviewer packet: problem, rubric, hint ladder, timeline |
| `pad.py` | this question's pad title, description and `main` templates |
| `sync.py` | regenerates everything generated here; the whole contract |
| `py/` `ts/` | one directory per language — reference solution, generators, tests |
| `datasets.json` `answers.md` | generated; both languages read the data |

A language directory holds that language's `main` (the reference solution — swap
in a candidate's to grade theirs) and its tests. Python adds the generators
(`datasets.py`, `answers.py`, `ts_fixture.py`) and the generated `solutions.py`;
TypeScript adds `datasets.ts` and the generated `parity.json` that holds the port
to Python's output.

Adding a language to a question is adding a directory named for it. Adding a
question is adding a directory with a `sync.py`. Neither edits a registry —
`tools/coderpad.py` discovers both.

## The kmeans problem

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

`questions/kmeans/INSTRUCTIONS.md` is the version a candidate sees — keep the two
in step.

## Development

```sh
mise run install       # uv sync + npm ci
mise run sync          # regenerate every question
mise run sync kmeans   # just one
mise run test          # pytest + node --test, both languages
mise run typecheck     # pyright + tsc
mise run lint

mise run coderpad:sync --push   # sync every question to the CoderPad question bank
                                # each is a project you copy per interview; add
                                # --recreate to change its files, which changes the id
```

The library halves document themselves:
[`src/interview_k/README.md`](src/interview_k/README.md) and
[`ts/README.md`](ts/README.md).

To grade a candidate, drop their file in as `questions/<name>/<lang>/main.*` and
run `mise run test`.
