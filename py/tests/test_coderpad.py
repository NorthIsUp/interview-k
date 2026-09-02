"""Each bundle is assembled by string surgery on that language's sources and packet.md.

That only holds while their headers keep the shape `coderpad.py` expects, and the failure is
silent — a bundle that still writes but no longer runs in the pad. So: build it, run it, and
use it. The TypeScript half needs node, which mise installs; it skips rather than fails if the
suite is run somewhere without it.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tools.coderpad import QUESTIONS, python_bundle, read_cookie_header, typescript_bundle

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_python_bundle_executes_and_exposes_the_candidate_surface() -> None:
    namespace: dict[str, object] = {}
    exec(compile(python_bundle(), "bundle", "exec"), namespace)  # our own generated source

    assert callable(namespace["show"])
    assert callable(namespace["kmeans"]), "the stub must survive extraction from packet.md"
    assert callable(namespace["print_clusters"])
    assert len(namespace["TWENTY"]) == 20  # type: ignore[arg-type]
    assert len(namespace["BLOBS"]) == 1000  # type: ignore[arg-type]


def test_python_bundle_has_exactly_one_future_import() -> None:
    # two would be a SyntaxError; zero would change how the annotations evaluate
    assert python_bundle().count("from __future__ import annotations") == 1


@pytest.mark.parametrize("build", [python_bundle, typescript_bundle], ids=["py", "ts"])
def test_bundle_does_not_run_a_demo_on_import(build: Callable[[], str]) -> None:
    """A pad runs its buffer directly, so a surviving entry point greets the candidate with plots."""
    text = build()
    assert 'if __name__ == "__main__":' not in text
    assert "if (import.meta.main)" not in text


def test_typescript_bundle_is_one_flat_buffer() -> None:
    """No imports to resolve and no exports, which is what makes it a script rather than a module."""
    text = typescript_bundle()
    assert "\nimport " not in f"\n{text}"
    assert "\nexport " not in f"\n{text}"
    assert "function kmeans" in text, "the stub must survive extraction from packet.md"
    assert "function printClusters" in text


@pytest.mark.skipif(shutil.which("node") is None, reason="node is what runs a TypeScript pad")
def test_typescript_bundle_runs_clean_and_silent(tmp_path: Path) -> None:
    """The TS counterpart of exec()ing the Python bundle: type-strip it, run it, expect nothing."""
    path = tmp_path / "bundle.ts"
    path.write_text(typescript_bundle())
    done = subprocess.run(["node", str(path)], capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert done.stdout == "", f"the bundle printed on load: {done.stdout[:200]}"


def test_questions_are_the_two_the_interview_ships() -> None:
    assert [q.title for q in QUESTIONS] == ["k-means [py]", "k-means [ts]"]
    assert [q.language for q in QUESTIONS] == ["python", "typescript"]
    for question in QUESTIONS:
        assert question.solution.exists(), f"{question.title} has no reference solution at {question.solution}"


def test_cookie_header_from_devtools_table() -> None:
    # Application -> Cookies -> select all -> copy: name, value, domain, path, expires, size...
    table = "_coderpad_rails_session_3\tabc123\t.coderpad.io\t/\tSession\t57B\n" "currency\tUSD\tapp.coderpad.io\t/\tSession\t11B\n"
    assert read_cookie_header(table) == "_coderpad_rails_session_3=abc123; currency=USD"


def test_cookie_header_from_a_request_header() -> None:
    assert read_cookie_header("_coderpad_rails_session_3=abc123; currency=USD") == "_coderpad_rails_session_3=abc123; currency=USD"


def test_cookie_header_rejects_a_paste_without_the_session() -> None:
    # the failure this catches is a 200 that quietly serves the logged-out page
    with pytest.raises(SystemExit, match="_coderpad_rails_session"):
        read_cookie_header("currency\tUSD\tapp.coderpad.io\t/")
