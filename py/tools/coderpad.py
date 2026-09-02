"""Build the CoderPad project for each language, and sync it to your question bank.

    uv run python tools/coderpad.py           # write both project trees under build/
    uv run python tools/coderpad.py --push    # also create/update both questions

One question per language — "k-means [py]" and "k-means [ts]" — each a CoderPad *project*, so
the candidate opens a file tree with the stub in `main` and the library beside it, rather than
one buffer holding five hundred lines of someone else's code. The questions are templates: an
interview is a Live Pad or an "Edit a Copy" made from one.

The files go up with the question. `fileContents` takes a *list* of records whose path is
base64 — `[{"path": b64("src/main.py"), "contents": "..."}]` — and not the `{path: contents}`
map it reads back as in some views; sending the map is accepted and then produces a question
whose preview and pads both 500, which is a long way to find a typo. It is also create-only:
QuestionUpdateAttributes has no `fileContents`, so changing the tree means replacing the
question, and --recreate says so out loud because that costs the question its id.

--push drives the same GraphQL endpoint the dashboard uses, authenticated as you by your
browser session rather than by an API key — CoderPad gates REST API keys behind Enterprise,
but the question bank is just the web app. Copy your app.coderpad.io cookies into
~/.config/coderpad/cookie (see COOKIE_FILE) and it works; a session lasts weeks, and a stale
one fails loudly rather than writing anything.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

PY = Path(__file__).parent.parent
TS = PY.parent / "ts"
PACKET = PY.parent / "docs" / "packet.md"
INSTRUCTIONS = PY.parent / "INSTRUCTIONS.md"
BUILD = PY / "build"

APP = "https://app.coderpad.io"
GRAPHQL = f"{APP}/graphql"
# Any page carrying the <meta> will do — the logged-out page has one too, so reaching this
# successfully says nothing about the session. GraphQL is what rejects a stale cookie.
CSRF_PAGE = f"{APP}/dashboard/questions"

# Kept out of the repo entirely rather than gitignored — a session cookie is a bearer token.
COOKIE_FILE = Path(os.environ.get("CODERPAD_COOKIE_FILE") or Path.home() / ".config/coderpad/cookie")

# Cloudflare answers urllib's default User-Agent with a 403 (error 1010) before CoderPad sees
# the request. We are driving the web app as the browser, so say so.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

DESCRIPTION = "Implement k-means from scratch. Rubric, hint ladder and expected output: docs/packet.md in the interview-k repo."

# A project question takes its environment — and so its language — from a template. Note that
# `multifile_python` is a template slug and is rejected as a `language`; the two are separate
# namespaces. Ids from projectTemplates(category: multifile).
PYTHON_PROJECT = 79
TYPESCRIPT_PROJECT = 93


# ── the project each pad opens ───────────────────────────────────────────────


def _cpad(command: str) -> str:
    """The Run button. One target: there is no test suite in the pad to wire a second one to."""
    return json.dumps({"targets": {"run": {"label": "Main", "command": command}}}, indent=2) + "\n"


def _stub(fence: str, opener: str) -> str:
    """The candidate's stub, read out of the packet so there is one copy of it per language."""
    match = re.search(rf"```{fence}\n({re.escape(opener)}\n.*?)```", PACKET.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit(f"packet.md no longer has a ```{fence} block starting {opener!r} — fix the marker in _stub()")
    return match.group(1).rstrip()


# The imports and the first Run belong to the project layout, not to the problem, so they live
# here rather than in the packet. Plotting the raw data gives the Run button something to do
# before kmeans() returns anything.
PY_MAIN = '''"""Your solution. Press Run to execute this file."""

from collections.abc import Sequence

from data import BLOBS, DATASETS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED
from dataviz import print_clusters, show

{stub}


if __name__ == "__main__":
    show(points=TWENTY, title="the data")
    # once kmeans works:  clusters = kmeans(TWENTY, 3); print_clusters(clusters); show(clusters)
'''

TS_MAIN = '''/** Your solution. Press Run to execute this file. */

import {{ printClusters, show, TWENTY }} from "./index";
import type {{ Centroid, Point }} from "./show";

{stub}

show({{ points: TWENTY, title: "the data" }});
// once kmeans works:  const clusters = kmeans(TWENTY, 3); printClusters(clusters); show(clusters);
'''

# data.py reaches for the package it no longer lives in once the modules sit beside main.py.
PACKAGE_IMPORT = "from interview_k.show import"

# A leading underscore means the file is ours. A pad project is handed to the candidate whole,
# so anything the interviewer keeps beside it — `_tests/`, scratch, the marking scheme — is
# named that way and never ships. It also covers `__init__.py`, which a flat pad has no use for.
PRIVATE = "_"


def shipped(project: dict[str, str]) -> dict[str, str]:
    return {path: text for path, text in project.items() if not any(part.startswith(PRIVATE) for part in path.split("/"))}


def python_project() -> dict[str, str]:
    """The template runs `python src/main.py`, so src/ is the package root and imports stay flat."""
    sources = {f"src/{path.name}": path.read_text() for path in (PY / "src/interview_k").glob("*.py")}
    # Every module that reaches for the package has to reach sideways instead; nothing is a
    # package in the pad, they are just files next to each other under src/.
    if not any(PACKAGE_IMPORT in text for text in sources.values()):
        raise SystemExit(f"no module imports {PACKAGE_IMPORT!r} any more — update PACKAGE_IMPORT")
    files = {name: text.replace(PACKAGE_IMPORT, "from show import") for name, text in sources.items()}

    stub = _stub("python", "from collections.abc import Sequence")
    # The packet's stub carries its own Sequence import; main.py already has one.
    stub = stub.replace("from collections.abc import Sequence\n", "", 1).lstrip()
    main = PY_MAIN.format(stub=stub)
    compile(main, "main.py", "exec")  # a stub that does not parse is worse than none

    return shipped(
        {
            ".cpad": _cpad("python src/main.py"),
            # The template boots with `pip3 install -r requirements.txt`; without it that fails.
            "requirements.txt": "# The interview is stdlib only.\n",
            **files,
            "src/main.py": main,
        }
    )


def strip_ts_extension(source: str) -> str:
    """The repo writes `./random.ts` because node's own type stripping demands the exact path.

    A pad compiles with ts-node, which rejects it — `TS5097: An import path can only end with a
    '.ts' extension when 'allowImportingTsExtensions' is enabled` — and the pad owns tsconfig.
    """
    return re.sub(r'(from\s+")([^"]+)\.ts(")', r"\1\2\3", source)


# show.ts ends with one, to run its demo when node executes the file directly.
TS_ENTRY_GUARD = "if (import.meta.main)"


def strip_entry_guard(source: str) -> str:
    """A pad compiles with ts-node under CommonJS, where `import.meta` is a compile error.

    TS1343 ("only allowed when '--module' is es2020...") plus TS2339 (`main` is not on
    ImportMeta), and it takes the whole project down with it — the candidate's Run button
    fails on a line that only exists so `node src/show.ts` can show its own demo.
    """
    return "\n".join(line for line in source.splitlines() if not line.startswith(TS_ENTRY_GUARD)).rstrip() + "\n"


def typescript_project() -> dict[str, str]:
    files = {f"src/{path.name}": strip_entry_guard(strip_ts_extension(path.read_text())) for path in (TS / "src").glob("*.ts")}
    manifest = {"name": "k-means", "private": True, "scripts": {"main": "ts-node src/main.ts"}}
    return shipped(
        {
            ".cpad": _cpad("npm run main"),
            "package.json": json.dumps(manifest, indent=2) + "\n",
            **files,
            "src/main.ts": TS_MAIN.format(stub=_stub("typescript", "type Cluster = [Centroid, Point[]];")),
        }
    )


# ── what the candidate is told ───────────────────────────────────────────────

PAD_NOTE = (
    "`show()` and the datasets are in this project already — open the files on the left. "
    "Write your solution in `main` and press Run.\n"
)

# Repo commands: regenerating the answer key, running the harness, grading a candidate's
# file. None of it means anything inside a pad, and the last of it is nobody's business.
INTERVIEWER_SECTIONS = frozenset({"Development"})


def _for_the_candidate(readme: Path) -> str:
    """A language README's sections, minus the ones written for whoever is running the interview.

    Excluding by name rather than picking by name so that a section added to a README turns up
    in the pad by default — the READMEs are the library's documentation, and that is the half
    the candidate is owed.
    """
    sections = re.split(r"^## ", readme.read_text(), flags=re.MULTILINE)[1:]
    kept = [section for section in sections if section.split("\n", 1)[0].strip() not in INTERVIEWER_SECTIONS]
    if not kept:
        raise SystemExit(f"{readme} has no candidate-facing sections left — did its headings change?")
    return "\n\n".join(f"## {section.rstrip()}" for section in kept)


# ── the questions ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Question:
    """One question's worth of the interview, and where each part of it comes from.

    `question_id` is the question --push owns, so re-running edits it rather than adding
    another copy. There is no server-side "find my question by title" — questionsSearch is the
    practice library and cannot see your own bank — so the id is pinned here instead. One
    constant in git beats a state file. None means "not pushed yet": the tool creates one and
    prints the id to paste in.
    """

    title: str
    project_template: int
    question_id: int | None
    solution: Path
    project: Callable[[], dict[str, str]]
    readme: Path

    @property
    def build_root(self) -> Path:
        return BUILD / self.title.replace(" ", "_")

    def instructions(self) -> str:
        """The brief, then this language's library docs. INSTRUCTIONS.md is the problem; the
        README is the reference for the code sitting in the project.
        """
        return f"{INSTRUCTIONS.read_text().rstrip()}\n\n{PAD_NOTE}\n{_for_the_candidate(self.readme)}\n"

    def write(self) -> Path:
        """Lay the project out on disk, from scratch.

        From scratch because running the project here leaves __pycache__ behind, and anything
        still sitting in the directory is a file somebody could upload into a pad by hand.
        """
        shutil.rmtree(self.build_root, ignore_errors=True)
        for name, text in self.project().items():
            path = self.build_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return self.build_root


QUESTIONS = (
    Question(
        title="k-means [py]",
        project_template=PYTHON_PROJECT,
        question_id=385885,
        solution=PY / "main.py",
        project=python_project,
        readme=PY / "README.md",
    ),
    Question(
        title="k-means [ts]",
        project_template=TYPESCRIPT_PROJECT,
        question_id=385886,
        solution=TS / "main.ts",
        project=typescript_project,
        readme=TS / "README.md",
    ),
)


# ── the browser session ──────────────────────────────────────────────────────


def read_cookie_header(text: str) -> str:
    """Both ways a browser hands you cookies: a `Cookie:` header, or DevTools' cookie table.

    The table is what you get from Application -> Cookies -> select all -> copy, and is
    tab-separated with the name and value first. Accepting it saves reconstructing a header
    by hand, which is where this goes wrong.
    """
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        if "\t" in line:
            name, _, rest = line.partition("\t")
            if name.strip():
                pairs.append((name.strip(), rest.split("\t")[0]))
        else:
            pairs += [(k.strip(), v.strip()) for k, _, v in (part.partition("=") for part in line.split(";")) if k.strip() and v]
    if not any(name.startswith("_coderpad_rails_session") for name, _ in pairs):
        raise SystemExit(f"no _coderpad_rails_session cookie in {COOKIE_FILE} — copy the app.coderpad.io cookies again")
    return "; ".join(f"{name}={value}" for name, value in pairs)


def _cookies() -> str:
    if not COOKIE_FILE.exists():
        raise SystemExit(
            f"no cookie file at {COOKIE_FILE}. Open {APP} logged in, DevTools -> Application -> "
            f"Cookies -> app.coderpad.io, copy the rows (or the Cookie: request header), and:\n"
            f"    mkdir -p {COOKIE_FILE.parent} && pbpaste > {COOKIE_FILE}"
        )
    return read_cookie_header(COOKIE_FILE.read_text())


def _open(request: urllib.request.Request) -> bytes:
    try:
        with urllib.request.urlopen(request) as response:
            return cast("bytes", response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise SystemExit(f"CoderPad {request.get_method()} {request.full_url} -> {exc.code}: {detail}") from exc


def _csrf_token(cookies: str) -> str:
    """Rails wants the per-session token from a page's <meta>; GraphQL 422s without it."""
    request = urllib.request.Request(CSRF_PAGE, headers={"Cookie": cookies, "User-Agent": USER_AGENT})
    match = re.search(r'name="csrf-token" content="([^"]+)"', _open(request).decode(errors="replace"))
    if match is None:
        raise SystemExit(f"no csrf-token <meta> on {CSRF_PAGE} — the page shape changed, or something is in front of it")
    return match.group(1)


# Any: a serialization boundary. The schema is CoderPad's to change and introspection is off,
# so responses are checked at the point of use rather than declared here as if we owned them.
def _graphql(query: str, variables: dict[str, Any], cookies: str, csrf: str) -> Any:  # ruff: ignore[any-type]
    request = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Cookie": cookies, "X-CSRF-Token": csrf, "Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    payload: Any = json.loads(_open(request))
    if errors := payload.get("errors"):
        # The one that will actually happen: the cookies aged out. Say what to do about it.
        if any("logged in" in error.get("message", "") for error in errors):
            raise SystemExit(f"CoderPad says you are logged out — the session in {COOKIE_FILE} has expired, copy it again")
        raise SystemExit(f"GraphQL error: {json.dumps(errors, indent=2)[:800]}")
    return payload["data"]


# The dashboard's own operations, recovered from its JS bundle (introspection is off in prod).
LOOKUP = """
query($id: Int!) { question(id: $id) { id title fileContents } }
"""
DELETE = """
mutation($id: Int!) { deleteQuestion(input: { id: $id }) { question { id } message } }
"""

FILES_ARE_CREATE_ONLY = "the project files differ from the question's. CoderPad only takes them at creation — re-run with --recreate"


def _file_records(project: dict[str, str]) -> list[dict[str, str]]:
    """The shape CoderPad stores a project in: a list, with each path base64-encoded."""
    return [{"path": base64.b64encode(path.encode()).decode(), "contents": text} for path, text in project.items()]


def _stored_project(question_payload: Any) -> dict[str, str]:  # ruff: ignore[any-type]
    """The inverse, so a push can tell whether the tree it holds is already up there."""
    records: Any = question_payload.get("fileContents") or []
    if not isinstance(records, list):
        return {}
    return {base64.b64decode(r["path"]).decode(): r["contents"] for r in cast("list[dict[str, str]]", records)}


CREATE = """
mutation($input: CreateQuestionInput!) {
  createQuestion(input: $input) { question { id title isDraft } errors { message path } }
}
"""
UPDATE = """
mutation($input: UpdateQuestionInput!) {
  updateQuestion(input: $input) { question { id title isDraft } errors { message path } }
}
"""


def push(question: Question, cookies: str, csrf: str, *, recreate: bool) -> None:
    existing: Any = None
    if question.question_id is not None:
        existing = _graphql(LOOKUP, {"id": question.question_id}, cookies, csrf)["question"]
        if existing is None:
            raise SystemExit(f"question {question.question_id} is gone from the bank — clear its question_id to create it again")

    project = question.project()
    fields: dict[str, Any] = {
        "title": question.title,
        "description": DESCRIPTION,
        "solution": question.solution.read_text(),
        "candidateInstructions": [{"instructions": question.instructions(), "defaultVisible": True}],
    }

    if existing is not None and not recreate:
        result: Any = _graphql(UPDATE, {"input": {"questionAttributes": fields | {"id": question.question_id}}}, cookies, csrf)
        result = result["updateQuestion"]
        verb = "updated"
    else:
        # projectTemplateId and fileContents are both create-only, and between them they are
        # what makes the question a project with our code in it.
        attributes = fields | {"projectTemplateId": question.project_template, "fileContents": _file_records(project)}
        result = _graphql(CREATE, {"input": {"questionAttributes": attributes}}, cookies, csrf)["createQuestion"]
        verb = "created"

    # A mutation can 200 and still refuse the write; `errors` is where it says so.
    if failures := result.get("errors"):
        raise SystemExit(f"CoderPad rejected {question.title}: {json.dumps(failures, indent=2)[:800]}")

    pushed = result["question"]
    # Only once the replacement exists: deleting first loses the question outright if the
    # create then fails, which is exactly how one went missing.
    if existing is not None and recreate:
        _graphql(DELETE, {"id": question.question_id}, cookies, csrf)
        print(f"replaced {question.title} — {question.question_id} deleted")

    print(f"{verb} {question.title} — {pushed['id']} — {APP}/dashboard/questions/edit/{pushed['id']}")
    if existing is None or recreate:
        print(f"  set question_id={pushed['id']} on the {question.title} entry in {Path(__file__).name}")
    elif _stored_project(existing) != project:
        print(f"  {FILES_ARE_CREATE_ONLY}")


def main(argv: list[str]) -> int:
    for question in QUESTIONS:
        root = question.write()
        print(f"wrote {root} — {len(question.project())} files")

    if "--push" not in argv:
        print(f"--push syncs both questions, using the browser cookies in {COOKIE_FILE}")
        return 0

    # One session for both, so a cookie that expires mid-run fails before the second write.
    cookies = _cookies()
    csrf = _csrf_token(cookies)
    recreate = "--recreate" in argv
    for question in QUESTIONS:
        push(question, cookies, csrf, recreate=recreate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
