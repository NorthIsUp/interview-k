"""Each pad is a project assembled from the repo's own files plus a stub cut out of the packet.

The failure mode is silent — a project that still uploads but no longer runs — so the tests
that matter here write each project to disk and execute it with the exact command its `.cpad`
gives the Run button. The TypeScript one needs node, which mise installs; it skips rather than
fails where there is none.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.coderpad import QUESTIONS, python_files, read_cookie_header, typescript_files


def _write(files: dict[str, str], root: Path) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def test_python_project_has_the_layout_the_template_boots() -> None:
    files = python_files()
    # requirements.txt is not decoration: the template's initCommand pip-installs from it.
    assert "requirements.txt" in files
    assert files.keys() >= {".cpad", "src/main.py", "src/interview_k/show.py", "src/interview_k/data.py"}
    assert json.loads(files[".cpad"])["targets"]["run"]["command"] == "python src/main.py"


def test_typescript_project_has_the_layout_the_template_boots() -> None:
    files = typescript_files()
    assert files.keys() >= {".cpad", "package.json", "src/main.ts", "src/show.ts", "src/data.ts", "src/random.ts"}
    manifest = json.loads(files["package.json"])
    assert manifest["type"] == "module", "the sources use ESM imports"
    assert json.loads(files[".cpad"])["targets"]["run"]["command"] == "npm run main"


def test_library_files_go_in_verbatim() -> None:
    """The point of a project over one buffer: nothing is rewritten, so nothing can drift."""
    source = Path(__file__).parent.parent / "src/interview_k/show.py"
    assert python_files()["src/interview_k/show.py"] == source.read_text()


def test_python_project_runs_its_run_target(tmp_path: Path) -> None:
    root = _write(python_files(), tmp_path)
    done = subprocess.run([sys.executable, "src/main.py"], cwd=root, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is what runs the TypeScript project")
def test_typescript_project_runs_its_run_target(tmp_path: Path) -> None:
    root = _write(typescript_files(), tmp_path)
    done = subprocess.run(["node", "src/main.ts"], cwd=root, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


def test_instructions_come_from_the_readme_without_the_interviewer_half() -> None:
    """The README's warning block, file table and Development section are not the candidate's.

    They say where the worked solution and the expected output live, and how the candidate is
    graded. The prose sections quoted here mention an answer key exists, which is both obvious
    and useless without the repo; naming its path is the thing to keep out.
    """
    for question in QUESTIONS:
        text = question.instructions()
        assert "## The problem" in text
        assert "Don't send a candidate the repo link" not in text
        assert "To grade a candidate" not in text
        assert "| `py/main.py` | reference solution |" not in text
        assert "docs/answers.md" not in text


def test_questions_are_the_two_the_interview_ships() -> None:
    assert [q.title for q in QUESTIONS] == ["k-means [py]", "k-means [ts]"]
    for question in QUESTIONS:
        assert question.solution.exists(), f"{question.title} has no reference solution at {question.solution}"
        assert question.question_id is not None, f"{question.title} is unpinned — a push would make a second copy"


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
