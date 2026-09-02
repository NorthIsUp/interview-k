"""Emit the parity fixture the TypeScript port is tested against.

    uv run python -m tools.ts_fixture   # from py/, writes ../ts/test/parity.json

The TS port only earns the name if it produces the same points and the same picture, so
the check is a digest of every dataset plus the literal stdout of a few show() calls. It
also carries the answer key, which is what holds `ts/main.ts` to the same clusters Python
reaches rather than merely to a converged answer of its own.

Run as `-m` so that `py/` is on the path and `solutions` imports; running the file by path
puts `tools/` there instead. Regenerate whenever data.py, show.py or solutions.py changes;
a TS test failure afterwards means the port drifted, not that the fixture is stale.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable

from interview_k.data import DATASETS, TWENTY
from interview_k.show import Centroid, Point, show
from solutions import ANSWERS, K

FIXTURE = Path(__file__).parent.parent.parent / "ts" / "test" / "parity.json"

SQUARE: list[Point] = [(0, 0), (0, 1), (1, 0), (1, 1)]


# The wire shape, declared once so the TS-side `interface Fixture` has something to match.
class DatasetFixture(TypedDict):
    n: int
    first: list[int]
    last: list[int]
    sha256: str


class AnswerFixture(TypedDict):
    """A digest rather than the partition itself, which would be every point over again.

    It detects exactly what spelling out the clusters would — any point landing in a
    different group changes the hash — for a hundredth of the file. The centroids stay
    literal because they are compared to a tolerance, which a hash cannot do.
    """

    partition: str
    centroids: list[list[float]]


class Fixture(TypedDict):
    datasets: dict[str, DatasetFixture]
    renders: dict[str, str]
    k: int
    answers: dict[str, AnswerFixture]


def digest(points: list[Point]) -> str:
    return hashlib.sha256(";".join(f"{x},{y}" for x, y in points).encode()).hexdigest()


def normalised(clusters: list[tuple[Centroid, list[Point]]]) -> list[tuple[Centroid, list[Point]]]:
    """Sort points inside each cluster, then clusters by their points. Ordering is not graded.

    Points are pairs, so ordering groups by their flattened coordinates is the same order
    Python's tuple comparison gives — and one a JS comparator can reproduce exactly.
    """
    return sorted(((centroid, sorted(points)) for centroid, points in clusters), key=lambda pair: [v for p in pair[1] for v in p])


def rendered(draw: Callable[[], None]) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        draw()
    return buffer.getvalue()


def main() -> int:
    # Same normalisation test_solutions.py applies: ordering is not part of the contract.
    answers: dict[str, AnswerFixture] = {}
    for name, clusters in ANSWERS.items():
        groups = normalised(clusters)
        answers[name.lower()] = {
            "partition": hashlib.sha256("|".join(digest(points) for _, points in groups).encode()).hexdigest(),
            "centroids": [[centroid[0], centroid[1]] for centroid, _ in groups],
        }
    fixture: Fixture = {
        "datasets": {
            name: {"n": len(points), "first": list(points[0]), "last": list(points[-1]), "sha256": digest(points)}
            for name, points in ({"twenty": TWENTY} | DATASETS).items()
        },
        "renders": {
            "twenty": rendered(lambda: show(points=TWENTY, width=40, height=12, title="twenty")),
            "two_groups": rendered(lambda: show([SQUARE[:2], SQUARE[2:]], [(0.0, 0.5), (1.0, 0.5)], width=20, height=5)),
            "nan_centroid": rendered(lambda: show([SQUARE], [(float("nan"), 0.0)], width=20, height=5)),
            "empty": rendered(lambda: show([], width=20, height=5)),
            "identical": rendered(lambda: show(points=[(2, 2)] * 5, width=20, height=5)),
            "blobs": rendered(lambda: show(points=DATASETS["blobs"], width=60, height=16, title="blobs")),
        },
        "k": K,
        "answers": answers,
    }

    FIXTURE.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"wrote {FIXTURE} — {len(fixture['datasets'])} datasets, {len(fixture['renders'])} renders, {len(fixture['answers'])} answers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
