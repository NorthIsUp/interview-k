"""Re-embed the library source into docs/packet.md so the two cannot drift.

    uv run python tools/sync_packet.py

The packet hands candidates code to paste into a CodePair pad, where there is no
installed package — so the embedded copy of data.py imports from the pasted module
rather than from `interview_k`. That rewrite happens here, not by hand.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PACKET = ROOT / "docs" / "packet.md"
PASTE_IMPORT = ("from interview_k.show import Centroid, Point", "from kmeans_show import Centroid, Point")


def embed(text: str, marker: str, source: str) -> str:
    start = text.index(marker)
    end = text.index("\n```", start) + 4
    return text[:start] + "```python\n" + source + "\n```\n" + text[end:]


def main() -> int:
    show = (ROOT / "src/interview_k/show.py").read_text().rstrip()
    data = (ROOT / "src/interview_k/data.py").read_text().rstrip().replace(*PASTE_IMPORT)

    packet = PACKET.read_text()
    packet = embed(packet, '```python\n"""ASCII scatter', show)
    packet = embed(packet, '```python\n"""Datasets for', data)
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


if __name__ == "__main__":
    raise SystemExit(main())
