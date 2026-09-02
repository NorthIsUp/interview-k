"""Run each CoderPad project the way its own pad would, before a candidate does it for us.

    uv run python -m tools.coderpad_check   # from py/, offline

`coderpad:sync` writes trees that upload cleanly and then fail on the Run button, because a
pad's toolchain is not this repo's. TypeScript is where that bites: a pad is ts-node under
Node 20 compiling CommonJS, while ts/ is ESM run by node's own type stripping, so
`mise run ts:typecheck` passes on code a pad rejects. Two such bugs — TS5097 for a `.ts`
import specifier, TS1343 + TS2339 for `import.meta` — were each found by a live interview
pad and nothing else. So the compile below is spelled out the way ts-node spells it rather
than deferred to ts/tsconfig.json, which would agree with the code and still be wrong.

Each project is checked three ways: every file compiles, the `.cpad` run target exits 0 with
something on stdout (the Run button is the first thing a candidate presses), and a project
shipping a tests/ directory runs it through the `.cpad` test target. Neither project ships
tests today — that arm says so rather than passing silently, and starts working the day one
appears. Nothing here talks to CoderPad.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

from tools.coderpad import QUESTIONS, TS, python_project, typescript_project

if TYPE_CHECKING:
    from collections.abc import Callable

    from tools.coderpad import Question

# node's type stripping demands the exact path ts-node forbids, so the copy we execute gets
# back the extension strip_ts_extension() took off. The pad-shaped tree keeps it off.
RESTORE_TS = re.compile(r'(from\s+"\./[^"]+)(")')

TSC = TS / "node_modules/.bin/tsc"

# ts-node's compile, written out. Naming files on the command line is also what makes tsc
# ignore ts/tsconfig.json — which is nodenext ESM, and would pass what a pad refuses.
PAD_TSC = ("--noEmit", "--module", "commonjs", "--target", "es2022", "--strict", "--types", "node")

NPM_RUN = "npm run "
PYTHONS = frozenset({"python", "python3"})
# ts-node is the pad's; it does not install on a current node. node runs the same file.
TS_RUNNERS = frozenset({"ts-node", "tsx", "node"})

TESTS = "tests/"


def _lay_out(project: dict[str, str], root: Path) -> Path:
    """A runnable copy of the pad's tree — identical but for the specifiers node insists on."""
    for name, text in project.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RESTORE_TS.sub(r"\1.ts\2", text) if name.endswith(".ts") else text)
    return root


def _run(argv: list[str], cwd: Path, what: str) -> str:
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"{what}\n    {' '.join(argv)}\n{done.stdout[-2000:]}{done.stderr[-2000:]}")
    return done.stdout


def _command(project: dict[str, str], target: str) -> str | None:
    """A `.cpad` button's command. The file is CoderPad's shape, so it is read here, not modeled."""
    targets = cast("dict[str, dict[str, str]]", json.loads(project[".cpad"])["targets"])
    entry = targets.get(target)
    return None if entry is None else entry["command"]


def python_argv(project: dict[str, str], target: str) -> list[str] | None:
    """The pad's own command, on the interpreter running this — `python` there is not `python` here."""
    command = _command(project, target)
    if command is None:
        return None
    interpreter, *rest = command.split()
    if interpreter not in PYTHONS:
        raise SystemExit(f"the python project's {target} target is {command!r}, which this check cannot reproduce")
    return [sys.executable, *rest]


def typescript_argv(project: dict[str, str], target: str) -> list[str] | None:
    """`npm run main` followed through package.json, so renaming either end fails here."""
    command = _command(project, target)
    if command is None:
        return None
    if not command.startswith(NPM_RUN):
        raise SystemExit(f"the typescript project's {target} target is {command!r}, which this check cannot reproduce")
    scripts = cast("dict[str, str]", json.loads(project["package.json"])["scripts"])
    name = command.removeprefix(NPM_RUN).strip()
    if name not in scripts:
        raise SystemExit(f"the .cpad runs {command!r} but package.json has no {name!r} script — the pad's button is dead")
    runner, *rest = scripts[name].split()
    if runner not in TS_RUNNERS:
        raise SystemExit(f"package.json runs {scripts[name]!r}; only {sorted(TS_RUNNERS)} are reproducible here")
    return ["node", *rest]


def _check_targets(project: dict[str, str], root: Path, argv: Callable[[dict[str, str], str], list[str] | None]) -> None:
    run = argv(project, "run")
    if run is None:
        raise SystemExit("the .cpad has no run target — the pad's Run button does nothing")
    stdout = _run(run, root, "the Run button fails:")
    if not stdout.strip():
        raise SystemExit(f"`{' '.join(run)}` printed nothing — the candidate's first Run is meant to plot the data")
    print(f"  run ..... {' '.join(run)} -> {len(stdout.splitlines())} lines")

    shipped = sorted(name for name in project if name.startswith(TESTS))
    test = argv(project, "test")
    if test is None:
        # A tests/ directory the pad has no button for is worse than none: the candidate cannot
        # run it, and neither can this check.
        if shipped:
            raise SystemExit(f"ships {shipped} with no `test` target in .cpad — nothing in the pad can run them")
        print("  tests ... none shipped")
        return
    _run(test, root, "the test target fails:")
    print(f"  tests ... {' '.join(test)} over {len(shipped)} file(s)")


def check_python(question: Question) -> None:
    """Compile every module, then press Run.

    In a copy rather than in build/, because compiling leaves __pycache__ behind and build/ is
    the tree that gets uploaded — anything sitting there is a file someone could hand a candidate.
    """
    project = question.project()
    with tempfile.TemporaryDirectory() as tmp:
        root = _lay_out(project, Path(tmp))
        _run([sys.executable, "-m", "compileall", "-q", "."], root, "the python project does not compile:")
        _check_targets(project, root, python_argv)


def check_typescript(question: Question) -> None:
    """Compile the bytes that go up, then run a copy node can execute."""
    if not TSC.exists():
        raise SystemExit(f"no tsc at {TSC} — run `mise run ts:sync`")
    sources = sorted(str(path) for path in (question.build_root / "src").glob("*.ts"))
    _run([str(TSC), *PAD_TSC, *sources], TS, "the typescript project does not compile the way a pad compiles it:")
    project = question.project()
    with tempfile.TemporaryDirectory() as tmp:
        _check_targets(project, _lay_out(project, Path(tmp)), typescript_argv)


# Keyed on the builder rather than the title, so a question renamed keeps its check and a
# question added without one stops the run instead of going unchecked.
CHECKS: dict[Callable[[], dict[str, str]], Callable[[Question], None]] = {
    python_project: check_python,
    typescript_project: check_typescript,
}


def main() -> int:
    for question in QUESTIONS:
        check = CHECKS.get(question.project)
        if check is None:
            raise SystemExit(f"no pad check knows how to run {question.title} — add one to CHECKS")
        print(f"{question.title} — {question.write()}")
        check(question)
    print(f"{len(QUESTIONS)} projects compile and run the way their pads do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
