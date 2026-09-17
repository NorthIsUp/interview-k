"""Re-embed each question's library source into its `_packet.md`, so the two cannot drift.

    mise run sync          # every question
    uv run python -m tools.packet

The packet hands the interviewer code to read beside the candidate's pad. The copy in the
packet is the copy in the language directory, pasted in by this, never by hand — and every
python block in the packet is compiled afterwards, because a packet that does not run is
worse than one that is merely out of date.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUESTION_ROOT = ROOT / "questions"

# The packet's copy is meant to be pasted into a pad, where `dataviz` is a sibling file
# rather than an installed package.
MARKER = '```python\n"""Looking at an answer'


def _embed(text: str, marker: str, source: str) -> str:
    start = text.index(marker)
    # past the closing fence *and* its newline — the replacement supplies its own, so
    # stopping short of it made every run add a blank line
    end = text.index("\n", text.index("\n```", start) + 4) + 1
    return text[:start] + "```python\n" + source + "\n```\n" + text[end:]


def sync(packet: Path, library: Path) -> int:
    text = _embed(packet.read_text(), MARKER, library.read_text().rstrip())
    packet.write_text(text)

    blocks = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
    for i, block in enumerate(blocks, 1):
        try:
            compile(block, f"{packet.name} block {i}", "exec")
        except SyntaxError as exc:
            print(f"{packet}: block {i} does not compile: {exc}", file=sys.stderr)
            return 1
    print(f"{packet.name} synced — {len(blocks)} python blocks, all compile")
    return 0


def main() -> int:
    failed = 0
    for question in sorted(QUESTION_ROOT.iterdir()):
        packet, library = question / "_packet.md", question / "py" / "dataviz.py"
        if packet.is_file() and library.is_file():
            failed |= sync(packet, library)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
