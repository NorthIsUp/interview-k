"""What the CoderPad project for this question looks like, per language.

tools/coderpad.py owns the pad mechanics — templates, file copying, the import rewrites a
pad needs. This file owns the part that is about k-means: what the candidate's `main` opens
with, and the `*_OPENER` line that finds their stub in packet.md.
"""

from __future__ import annotations

# What the bank calls this question. The directory is a python package, so it cannot be
# "k-means" — and the ids in coderpad.toml are keyed by title, so this may not drift.
TITLE = "k-means"

DESCRIPTION = "Implement k-means from scratch. Rubric, hint ladder and expected output: questions/kmeans/packet.md in the interview-k repo."

# The line each language's stub starts with, used to find it in packet.md.
PY_OPENER = "from collections.abc import Sequence"
TS_OPENER = "type Cluster = [Centroid, Point[]];"

# The imports and the first Run belong to the project layout, not to the problem, so they live
# here rather than in the packet. Plotting the raw data gives the Run button something to do
# before kmeans() returns anything.
PY_MAIN = '''"""Your solution. Press Run to execute this file."""

import json
from collections.abc import Sequence
from pathlib import Path

from dataviz import print_clusters, show

DATASETS = {{
    name: [(x, y) for x, y in points]
    for name, points in json.loads(Path(__file__).with_name("datasets.json").read_text()).items()
}}
TWENTY = DATASETS["TWENTY"]

{stub}


if __name__ == "__main__":
    show(points=TWENTY, title="the data")
    # once kmeans works:  clusters = kmeans(TWENTY, 3); print_clusters(clusters); show(clusters)
'''

TS_MAIN = """/** Your solution. Press Run to execute this file. */

import {{ printClusters, show }} from "./index";
import {{ TWENTY }} from "./datasets";
import type {{ Centroid, Point }} from "./dataviz";

{stub}

show({{ points: TWENTY, title: "the data" }});
// once kmeans works:  const clusters = kmeans(TWENTY, 3); printClusters(clusters); show(clusters);
"""
