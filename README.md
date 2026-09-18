# interview-k

Live-coding interview questions, one directory each, in Python and TypeScript —
plus `show()`, a dependency-free ASCII scatter that renders anywhere a candidate
might be typing.

> [!WARNING]
> `RUBRIC.md` is the interviewer's scoring rubric. Don't send a candidate the repo link.

| path | what |
|---|---|
| `questions/<name>/` | one question: the brief, the data, and a directory per language |
| `RUBRIC.md` | how a candidate is scored — shared by every question |
| `tools/coderpad.py` | builds a CoderPad project per question per language; `--push` syncs them |
| `coderpad.toml` | which question in the bank is which of ours; maintained by `coderpad:sync` |
| `mise-tasks/` | one executable per task; `py/test` is `mise run py:test` |

## A question directory

`questions/kmeans/` is the pattern. A directory becomes a question the moment it
has a `common/question.toml`.

| path | what |
|---|---|
| `common/INSTRUCTIONS.md` | the candidate-facing brief; what `coderpad:sync` puts in the pad |
| `common/question.toml` | the title the CoderPad bank knows it by, and the pad description |
| `common/data.py` | prints the dataset to stdout; `mise run sync` redirects it into `data.json` |
| `common/data.json` | generated but committed — every language reads it |
| `py/` `ts/` | one directory per language |

A language directory is exactly what the candidate opens, hand-made for that
language: `main` (the stub they type into) and `dataviz` (the `show()` helper
they're given). Nothing else ships — no reference solution, no grading suite.
Files prefixed `_` are the interviewer's and never reach a pad, which is where
each language's `_README.md` and its `show()` tests live.

Adding a language to a question is adding a directory named for it. Adding a
question is adding a directory with a `common/question.toml`. Neither edits a
registry — `tools/coderpad.py` discovers both.

Everything derived lands in `build/`, which is gitignored: one assembled pad
project per question per language.

## The kmeans problem

Implement clustering from scratch. You're given a list of _x y_ points and an
integer _k_; return each centroid and the points assigned to it. numpy is fine;
`sklearn.cluster` and `scipy.cluster` are not.

```python
def cluster(points: Iterable[Point], k: int, max_iter: int = 100) -> Iterable[tuple[Centroid, list[Point]]]: ...
```

Plenty is left unspecified on purpose. Ask.

`questions/kmeans/common/INSTRUCTIONS.md` is the version a candidate sees.

## Development

```sh
mise run install       # uv sync + npm ci
mise run sync          # every question: data.json, then its pad projects under build/
mise run sync kmeans   # just one
mise run test          # pytest + node --test, both languages
mise run typecheck     # pyright + tsc
mise run lint

mise run coderpad:sync --push   # sync every question to the CoderPad question bank
                                # each is a project you copy per interview; add
                                # --recreate to change its files, which changes the id
mise run coderpad:test          # compile and run each pad the way its own pad does
```

The stubs are excluded from `lint` and `typecheck` — unfinished is the point, and
`coderpad:test` compiles them in the pad's own toolchain, which is the check that
has actually caught bugs.
