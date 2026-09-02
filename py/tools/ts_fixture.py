"""Emit the parity fixture the TypeScript port is tested against.

    uv run python tools/ts_fixture.py   # from py/, writes ../ts/test/parity.json

The TS port only earns the name if it produces the same points and the same picture, so
the check is a digest of every dataset plus the literal stdout of a few show() calls.
Regenerate this whenever data.py or show.py changes; a TS test failure afterwards means
the port drifted, not that the fixture is stale.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from interview_k.data import DATASETS, TWENTY
from interview_k.show import Point, show

FIXTURE = Path(__file__).parent.parent.parent / "ts" / "test" / "parity.json"

SQUARE: list[Point] = [(0, 0), (0, 1), (1, 0), (1, 1)]


def digest(points: list[Point]) -> str:
    return hashlib.sha256(";".join(f"{x},{y}" for x, y in points).encode()).hexdigest()


def rendered(draw: Callable[[], None]) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        draw()
    return buffer.getvalue()


def main() -> int:
    fixture = {
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
    }
    FIXTURE.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"wrote {FIXTURE} — {len(fixture['datasets'])} datasets, {len(fixture['renders'])} renders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
