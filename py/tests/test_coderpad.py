"""The pad is a stub in the buffer plus the library attached beside it as custom files.

The failure mode is silent — a pad that still uploads but no longer imports — so the tests
that matter write the library out and run the buffer against it. The pad resolves the library
at DATA_DIR, which does not exist here, so the local runs rewrite that prefix to the directory
the files were written to; what they prove is that the flattened modules still import each
other and the stub, which is the part that can rot. The TypeScript half needs node, which mise
installs; it skips rather than fails where there is none.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.coderpad import (
    DATA_DIR,
    QUESTIONS,
    python_buffer,
    python_library,
    read_cookie_header,
    typescript_buffer,
    typescript_library,
)


def _lay_out(library: dict[str, str], buffer: str, root: Path, entry: str) -> Path:
    for name, text in library.items():
        (root / name).write_text(text)
    path = root / entry
    path.write_text(buffer.replace(f"{DATA_DIR}/", "./"))
    return path


def test_python_library_is_flat_and_self_importing() -> None:
    """Custom files have no directories, so the package import has to become a flat one."""
    library = python_library()
    assert set(library) == {"show.py", "data.py"}
    assert "from interview_k.show import" not in library["data.py"]
    assert "from show import" in library["data.py"]


def test_typescript_library_goes_in_verbatim() -> None:
    """Its modules import each other relatively and land in one directory, so nothing is rewritten."""
    library = typescript_library()
    assert {"show.ts", "data.ts", "random.ts", "index.ts"} <= set(library)
    assert library["show.ts"] == (Path(__file__).parent.parent.parent / "ts/src/show.ts").read_text()


@pytest.mark.parametrize("buffer", [python_buffer, typescript_buffer], ids=["py", "ts"])
def test_buffer_carries_the_stub_and_finds_the_library(buffer: object) -> None:
    text = buffer()  # type: ignore[operator]
    assert DATA_DIR in text, "the buffer must point at where CoderPad copies the attached files"
    assert "kmeans" in text, "the stub must survive extraction from packet.md"


def test_python_buffer_runs_against_its_library(tmp_path: Path) -> None:
    path = _lay_out(python_library(), python_buffer(), tmp_path, "main.py")
    done = subprocess.run([sys.executable, path.name], cwd=tmp_path, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is what runs a TypeScript pad")
def test_typescript_buffer_runs_against_its_library(tmp_path: Path) -> None:
    path = _lay_out(typescript_library(), typescript_buffer(), tmp_path, "main.ts")
    done = subprocess.run(["node", path.name], cwd=tmp_path, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


def test_instructions_are_the_brief_plus_the_language_readme() -> None:
    """INSTRUCTIONS.md is the problem; each language README documents the code in the pad."""
    brief = (Path(__file__).parent.parent.parent / "INSTRUCTIONS.md").read_text().rstrip()
    python, typescript = (question.instructions() for question in QUESTIONS)

    for text in (python, typescript):
        assert brief in text, "the candidate brief goes in whole"
    assert "from interview_k import show" in python
    assert './src/index.ts"' in typescript
    assert "from interview_k import show" not in typescript


def test_instructions_leave_the_interviewer_half_behind() -> None:
    """A README's Development section is repo commands — including how the candidate is graded."""
    for question in QUESTIONS:
        text = question.instructions()
        assert "## Development" not in text
        assert "To grade a candidate" not in text
        assert "--write-solutions" not in text
        assert "answers.md" not in text


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
