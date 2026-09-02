"""Each question is a CoderPad project: a stub in `main` with the library beside it.

The failure mode is silent — a tree that still uploads but no longer imports — so the tests
that matter write the project to disk and run its `.cpad` command. The TypeScript one is run
with node rather than ts-node, and node wants the `.ts` specifiers the pad forbids, so the
local run puts them back; what it proves is that the modules still resolve each other and the
stub. It needs node, which mise installs, and skips rather than fails where there is none.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.coderpad import QUESTIONS, python_project, read_cookie_header, strip_ts_extension, typescript_project

RESTORE_TS = re.compile(r'(from\s+"\./[^"]+)(")')


def _lay_out(project: dict[str, str], root: Path) -> Path:
    for name, text in project.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RESTORE_TS.sub(r"\1.ts\2", text) if name.endswith(".ts") else text)
    return root


def _run_command(project: dict[str, str]) -> list[str]:
    """Whatever the Run button would run, straight out of the project's own .cpad."""
    return str(json.loads(project[".cpad"])["targets"]["run"]["command"]).split()


def test_python_project_has_what_the_template_boots() -> None:
    project = python_project()
    # requirements.txt is not decoration: the template's initCommand pip-installs from it.
    assert {".cpad", "requirements.txt", "src/main.py", "src/show.py", "src/data.py"} == set(project)
    assert _run_command(project) == ["python", "src/main.py"]
    # Flattened out of the package: src/ is the import root, so data.py imports its sibling.
    assert "from interview_k.show import" not in project["src/data.py"]
    assert "from show import" in project["src/data.py"]


def test_typescript_project_has_what_the_template_boots() -> None:
    project = typescript_project()
    assert {".cpad", "package.json", "src/main.ts", "src/show.ts", "src/data.ts", "src/random.ts"} <= set(project)
    assert _run_command(project) == ["npm", "run", "main"]
    assert json.loads(project["package.json"])["scripts"]["main"] == "ts-node src/main.ts"


def test_ts_specifiers_lose_their_extension() -> None:
    """ts-node rejects a `.ts` specifier (TS5097); node's type stripping requires one."""
    assert strip_ts_extension('from "./random.ts";') == 'from "./random";'
    assert 'from "./random"' in typescript_project()["src/show.ts"]


def test_python_project_runs_its_run_target(tmp_path: Path) -> None:
    project = python_project()
    _lay_out(project, tmp_path)
    _, entry = _run_command(project)
    done = subprocess.run([sys.executable, entry], cwd=tmp_path, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is what runs a TypeScript project")
def test_typescript_project_runs_its_entry(tmp_path: Path) -> None:
    _lay_out(typescript_project(), tmp_path)
    done = subprocess.run(["node", "src/main.ts"], cwd=tmp_path, capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr[-2000:]
    assert "│" in done.stdout, "the first Run should plot the data"


def test_instructions_are_the_brief_plus_the_language_readme() -> None:
    """INSTRUCTIONS.md is the problem; each language README documents the code in the project."""
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
    # Project templates, not languages: `multifile_python` is rejected as a language.
    assert [q.project_template for q in QUESTIONS] == [79, 93]
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
