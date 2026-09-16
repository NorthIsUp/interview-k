"""Regenerate every generated file in this question. `mise run sync kmeans` runs this.

    datasets.json    the data both languages read
    py/solutions.py  expected kmeans() output per dataset
    answers.md       the answer key, as markdown
    ts/parity.json   the fixture holding the TypeScript port to Python's output
    packet.md        library + generator source re-embedded, so the two cannot drift

The packet hands candidates code to paste into a pad, where there is no installed package —
so the embedded copy imports from the pasted module rather than from `interview_k`. That
rewrite happens here, not by hand.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from questions.kmeans.py import answers, datasets, ts_fixture

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
PACKET = HERE / "packet.md"
PASTE_IMPORT = ("from interview_k.dataviz import Centroid, Point", "from dataviz import Centroid, Point")


def _embed(text: str, marker: str, source: str) -> str:
    start = text.index(marker)
    # past the closing fence *and* its newline — the replacement supplies its own, so
    # stopping short of it made every run add a blank line
    end = text.index("\n", text.index("\n```", start) + 4) + 1
    return text[:start] + "```python\n" + source + "\n```\n" + text[end:]


def _sync_packet() -> int:
    show = (ROOT / "src/interview_k/dataviz.py").read_text().rstrip().replace(*PASTE_IMPORT)
    packet = _embed(PACKET.read_text(), '```python\n"""Looking at an answer', show)
    PACKET.write_text(packet)

    blocks = re.findall(r"```python\n(.*?)```", packet, re.DOTALL)
    for i, block in enumerate(blocks, 1):
        try:
            compile(block, f"packet block {i}", "exec")
        except SyntaxError as exc:
            print(f"block {i} does not compile: {exc}", file=sys.stderr)
            return 1
    print(f"packet synced — {len(blocks)} python blocks, all compile")
    return 0


def main() -> int:
    datasets.main()
    # each of these reads what the previous one wrote, so the order is the dependency order
    answers.write_solutions(HERE / "py/solutions.py")
    answers.write_answers(HERE / "answers.md")
    print("wrote py/solutions.py, answers.md")
    ts_fixture.main()
    return _sync_packet()


if __name__ == "__main__":
    raise SystemExit(main())
