"""The bundle is assembled by string surgery on show.py, data.py and packet.md.

That only holds while their headers keep the shape `coderpad.py` expects, and the failure
is silent — a bundle that still writes but no longer runs in the pad. So: build it, parse
it, execute it, and use it.
"""

from __future__ import annotations

from tools.coderpad import bundle


def test_bundle_executes_and_exposes_the_candidate_surface() -> None:
    namespace: dict[str, object] = {}
    exec(compile(bundle(), "bundle", "exec"), namespace)  # our own generated source

    assert callable(namespace["show"])
    assert callable(namespace["kmeans"]), "the stub must survive extraction from packet.md"
    assert callable(namespace["print_clusters"])
    assert len(namespace["TWENTY"]) == 20  # type: ignore[arg-type]
    assert len(namespace["BLOBS"]) == 1000  # type: ignore[arg-type]


def test_bundle_has_exactly_one_future_import() -> None:
    # two would be a SyntaxError; zero would change how the annotations evaluate
    assert bundle().count("from __future__ import annotations") == 1
