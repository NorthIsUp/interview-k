"""Assemble the candidate-facing project for CoderPad, and push it into your question bank.

    uv run python tools/coderpad.py           # write both projects, print where they landed
    uv run python tools/coderpad.py --push    # also create/update both questions

One question per language — "k-means [py]" and "k-means [ts]" — because the pad's language
picks the candidate's. Both are CoderPad multi-file projects, which is what lets the library
go in as the files it already is: `show` and the datasets keep their own modules and their own
imports, and the candidate opens a `main` file with nothing in it but the stub. A single-buffer
pad would mean concatenating all of it into one screenful of someone else's code.

The layout each language expects, and the `.cpad` run targets that drive the Run button, come
from CoderPad's own environment docs. Nothing here rewrites the library: files are copied in
verbatim, so a pad cannot drift from the repo.

--push drives the same GraphQL endpoint the dashboard uses, authenticated as you by your
browser session rather than by an API key — CoderPad gates REST API keys behind Enterprise,
but the question bank is just the web app. Copy your app.coderpad.io cookies into
~/.config/coderpad/cookie (see COOKIE_FILE) and it works; a session lasts weeks, and a stale
one fails loudly rather than writing anything. Re-running edits each QUESTIONS entry in place.
"""

from __future__ import annotations

import json
import os
import re
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


# ── what the candidate opens ─────────────────────────────────────────────────


def _cpad(command: str) -> str:
    """The Run button. One target: there is no test suite in the pad to wire a second one to."""
    return json.dumps({"targets": {"run": {"label": "Main", "command": command}}}, indent=2) + "\n"


def _stub(fence: str, opener: str) -> str:
    """The candidate's stub, read out of the packet so there is one copy of it per language."""
    match = re.search(rf"```{fence}\n({re.escape(opener)}\n.*?)```", PACKET.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit(f"packet.md no longer has a ```{fence} block starting {opener!r} — fix the marker in _stub()")
    return match.group(1).rstrip()


# The imports and the first Run belong to the layout, not to the problem, so they live here
# rather than in the packet. Plotting the raw data means the Run button does something useful
# before kmeans() returns anything.
PY_MAIN = '''"""Your solution. Press Run to execute this file."""

from collections.abc import Sequence

from interview_k import show
from interview_k.data import BLOBS, DATASETS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED

{stub}


if __name__ == "__main__":
    show(points=TWENTY, title="the data")
    # once kmeans works:  clusters = kmeans(TWENTY, 3); print_clusters(clusters); show(clusters)
'''

TS_MAIN = '''/** Your solution. Press Run to execute this file. */

import {{ show, TWENTY }} from "./index.ts";
import type {{ Centroid, Point }} from "./show.ts";

{stub}

show({{ points: TWENTY, title: "the data" }});
// once kmeans works:  const clusters = kmeans(TWENTY, 3); printClusters(clusters); show(clusters);
'''


def python_files() -> dict[str, str]:
    """`python src/main.py` puts src/ on the path, so the package imports itself unchanged."""
    package = {f"src/interview_k/{path.name}": path.read_text() for path in sorted((PY / "src/interview_k").glob("*.py"))}
    stub = _stub("python", "from collections.abc import Sequence")
    # The stub carries its own Sequence import for the packet's benefit; main.py already has one.
    stub = stub.replace("from collections.abc import Sequence\n", "", 1).lstrip()
    return {
        ".cpad": _cpad("python src/main.py"),
        # The template boots with `pip3 install -r requirements.txt`; without the file that fails.
        "requirements.txt": "# The interview is stdlib only.\n",
        **package,
        "src/main.py": PY_MAIN.format(stub=stub),
    }


def typescript_files() -> dict[str, str]:
    """A real npm project, which is what the TypeScript environment expects behind `npm run`."""
    package = {f"src/{path.name}": path.read_text() for path in sorted((TS / "src").glob("*.ts"))}
    manifest = {
        "name": "k-means",
        "private": True,
        "type": "module",
        # Node strips the types itself from 22.18 on, so there is nothing to install or build.
        "scripts": {"main": "node src/main.ts"},
    }
    return {
        ".cpad": _cpad("npm run main"),
        "package.json": json.dumps(manifest, indent=2) + "\n",
        **package,
        "src/main.ts": TS_MAIN.format(stub=_stub("typescript", "type Cluster = [Centroid, Point[]];")),
    }


# ── what the candidate is told ───────────────────────────────────────────────

PAD_NOTE = "The library is already in this project — open the files on the left. Write your solution in the `main` file and press Run.\n"

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
    """One pad's worth of the interview: a title, a language, and where its parts come from.

    `question_id` is the question --push owns, so re-running edits it rather than adding
    another copy. There is no server-side "find my question by title" — questionsSearch is
    the practice library and cannot see your own bank — so the id is pinned here instead. One
    constant in git beats a state file, and it is what stops a second --push writing a second
    question. None means "not pushed yet": the tool creates one and prints the id to paste in.
    """

    title: str
    project_template: int
    question_id: int | None
    solution: Path
    files: Callable[[], dict[str, str]]
    readme: Path

    def instructions(self) -> str:
        """The brief, then this language's library docs. INSTRUCTIONS.md is the problem; the
        README is the reference for the code already sitting in the pad.
        """
        return f"{INSTRUCTIONS.read_text().rstrip()}\n\n{PAD_NOTE}\n{_for_the_candidate(self.readme)}\n"


# A project question takes its environment — and so its language — from a template, which is
# why there is no `language` here: `multifile_python` is a template slug, and passing it as a
# language is rejected. Ids from projectTemplates(category: multifile).
PYTHON_PROJECT = 79
TYPESCRIPT_PROJECT = 93

QUESTIONS = (
    Question(
        title="k-means [py]",
        project_template=PYTHON_PROJECT,
        question_id=385821,
        solution=PY / "main.py",
        files=python_files,
        readme=PY / "README.md",
    ),
    Question(
        title="k-means [ts]",
        project_template=TYPESCRIPT_PROJECT,
        question_id=385822,
        solution=TS / "main.ts",
        files=typescript_files,
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
DELETE = """
mutation($id: Int!) { deleteQuestion(input: { id: $id }) { question { id } message } }
"""

# `fileContents` is on QuestionCreateAttributes and not on QuestionUpdateAttributes: CoderPad
# takes a project's files when the question is made and never again, because after that they
# belong to the pad editor. So changing the library means replacing the question, which costs
# it its id — hence --recreate rather than doing it quietly on every push.
FILES_ARE_CREATE_ONLY = "files differ from the pad's — CoderPad only accepts them at creation. Re-run with --recreate"


def push(question: Question, files: dict[str, str], cookies: str, csrf: str, *, recreate: bool) -> None:
    existing: Any = None
    if question.question_id is not None:
        existing = _graphql(LOOKUP, {"id": question.question_id}, cookies, csrf)["question"]
        if existing is None:
            raise SystemExit(f"question {question.question_id} is gone from the bank — clear its question_id to create it again")

    fields: dict[str, Any] = {
        "title": question.title,
        "description": DESCRIPTION,
        "solution": question.solution.read_text(),
        "candidateInstructions": [{"instructions": question.instructions(), "defaultVisible": True}],
    }

    if existing is not None and not recreate:
        variables = {"input": {"questionAttributes": fields | {"id": question.question_id}}}
        result: Any = _graphql(UPDATE, variables, cookies, csrf)["updateQuestion"]
        verb = "updated"
    else:
        attributes = fields | {"projectTemplateId": question.project_template, "fileContents": files}
        result = _graphql(CREATE, {"input": {"questionAttributes": attributes}}, cookies, csrf)["createQuestion"]
        verb = "created"

    # A mutation can 200 and still refuse the write; `errors` is where it says so.
    if failures := result.get("errors"):
        raise SystemExit(f"CoderPad rejected {question.title}: {json.dumps(failures, indent=2)[:800]}")

    pushed = result["question"]
    # Only now that the replacement exists — deleting first would lose the question outright
    # if the create then failed, which is exactly how 385810 went missing once.
    if existing is not None and recreate:
        _graphql(DELETE, {"id": question.question_id}, cookies, csrf)
        print(f"replaced {question.title} — {question.question_id} deleted")

    draft = " (draft)" if pushed.get("isDraft") else ""
    print(f"{verb} {question.title} — {pushed['id']}{draft} — {APP}/dashboard/questions/edit/{pushed['id']}")
    if existing is None or recreate:
        print(f"  set question_id={pushed['id']} on the {question.title} entry in {Path(__file__).name}")
    elif existing.get("fileContents") != files:
        print(f"  {FILES_ARE_CREATE_ONLY}")


def main(argv: list[str]) -> int:
    built = [(question, question.files()) for question in QUESTIONS]
    for question, files in built:
        # Written out so a project can be eyeballed, and diffed, without a round trip.
        root = BUILD / question.title.replace(" ", "_")
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        print(f"wrote {root} — {len(files)} files: {', '.join(sorted(files))}")

    if "--push" not in argv:
        print(f"--push uploads both to your question bank, using the browser cookies in {COOKIE_FILE}")
        return 0

    # One session for both, so a cookie that expires mid-run fails before the second write.
    cookies = _cookies()
    csrf = _csrf_token(cookies)
    recreate = "--recreate" in argv
    for question, files in built:
        push(question, files, cookies, csrf, recreate=recreate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
