"""Assemble the candidate-facing pad for CoderPad, and push it into your question bank.

    uv run python tools/coderpad.py           # write both pads locally, print where they landed
    uv run python tools/coderpad.py --push    # also create/update both questions

One question per language — "k-means [py]" and "k-means [ts]" — because the pad's language
picks the candidate's.

The pad the candidate opens holds the stub and nothing else. `show()` and the datasets ride
along as CoderPad **custom files**, which the pad copies to DATA_DIR on the container, so the
buffer is three imports and the problem rather than five hundred lines of someone else's code.

Why not a multi-file project: a project's files live under `fileContents`, which the API will
accept and then cannot read back — preview and pad creation both 500 on a question written
that way, and even a project question made in the UI stores `{}` there. Custom files are the
supported route, and `customFileIds` is an *update* attribute, so the library can be re-synced
forever without the question ever changing id.

--push drives the same GraphQL endpoint the dashboard uses, authenticated as you by your
browser session rather than by an API key — CoderPad gates REST API keys behind Enterprise,
but the question bank is just the web app. Copy your app.coderpad.io cookies into
~/.config/coderpad/cookie (see COOKIE_FILE) and it works; a session lasts weeks, and a stale
one fails loudly rather than writing anything.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
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

# Where an attached custom file lands in the pad's container. CoderPad's own docs: "the file
# is copied to the language environment's filesystem so participants can write code to access
# the file", and the editor builds paths as /home/coderpad/data/<filename>.
DATA_DIR = "/home/coderpad/data"

# Ours, so a re-sync knows which attached files are safe to replace.
FILE_MARK = "interview-k"

DESCRIPTION = "Implement k-means from scratch. Rubric, hint ladder and expected output: docs/packet.md in the interview-k repo."


# ── the library that rides along ─────────────────────────────────────────────

# data.py reaches for the package it no longer lives in once the modules are flat.
PACKAGE_IMPORT = "from interview_k.show import"


def python_library() -> dict[str, str]:
    """show.py and data.py, flattened out of the package — custom files have no directories."""
    files = {path.name: path.read_text() for path in (PY / "src/interview_k").glob("*.py") if path.name != "__init__.py"}
    if PACKAGE_IMPORT not in files["data.py"]:
        raise SystemExit(f"data.py no longer contains {PACKAGE_IMPORT!r} — update PACKAGE_IMPORT")
    files["data.py"] = files["data.py"].replace(PACKAGE_IMPORT, "from show import")
    return files


def typescript_library() -> dict[str, str]:
    """Verbatim: the modules import each other relatively, and land in one directory together."""
    return {path.name: path.read_text() for path in (TS / "src").glob("*.ts")}


# ── the buffer the candidate opens ───────────────────────────────────────────


def _stub(fence: str, opener: str) -> str:
    """The candidate's stub, read out of the packet so there is one copy of it per language."""
    match = re.search(rf"```{fence}\n({re.escape(opener)}\n.*?)```", PACKET.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit(f"packet.md no longer has a ```{fence} block starting {opener!r} — fix the marker in _stub()")
    return match.group(1).rstrip()


# The bootstrap belongs to the pad, not to the problem, so it lives here rather than in the
# packet. Plotting the raw data means the Run button does something before kmeans() returns.
PY_BUFFER = '''"""Your solution. Press Run to execute this file."""

import sys

sys.path.insert(0, "{data_dir}")  # where CoderPad copies the attached files; must precede them

from collections.abc import Sequence

from data import BLOBS, DATASETS, ELONGATED, LOPSIDED, TIGHT, TWENTY, UNIFORM, UNSCALED
from show import show

{stub}


if __name__ == "__main__":
    show(points=TWENTY, title="the data")
    # once kmeans works:  clusters = kmeans(TWENTY, 3); print_clusters(clusters); show(clusters)
'''

TS_BUFFER = '''/** Your solution. Press Run to execute this file. */

import {{ show, TWENTY }} from "{data_dir}/index.ts";
import type {{ Centroid, Point }} from "{data_dir}/show.ts";

{stub}

show({{ points: TWENTY, title: "the data" }});
// once kmeans works:  const clusters = kmeans(TWENTY, 3); printClusters(clusters); show(clusters);
'''


def python_buffer() -> str:
    stub = _stub("python", "from collections.abc import Sequence")
    # The packet's stub carries its own Sequence import; the buffer already has one.
    stub = stub.replace("from collections.abc import Sequence\n", "", 1).lstrip()
    text = PY_BUFFER.format(data_dir=DATA_DIR, stub=stub)
    compile(text, "coderpad buffer", "exec")  # a buffer that does not parse is worse than none
    return text


def typescript_buffer() -> str:
    return TS_BUFFER.format(data_dir=DATA_DIR, stub=_stub("typescript", "type Cluster = [Centroid, Point[]];"))


# ── what the candidate is told ───────────────────────────────────────────────

PAD_NOTE = (
    f"`show()` and the datasets are attached to this pad at `{DATA_DIR}` and already imported. "
    "Write your solution below and press Run.\n"
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
    """One pad's worth of the interview: a title, a language, and where its parts come from.

    `question_id` is the question --push owns, so re-running edits it rather than adding
    another copy. There is no server-side "find my question by title" — questionsSearch is the
    practice library and cannot see your own bank — so the id is pinned here instead. One
    constant in git beats a state file. None means "not pushed yet": the tool creates one and
    prints the id to paste in.
    """

    title: str
    language: str
    question_id: int | None
    solution: Path
    buffer: Callable[[], str]
    library: Callable[[], dict[str, str]]
    readme: Path

    def instructions(self) -> str:
        """The brief, then this language's library docs. INSTRUCTIONS.md is the problem; the
        README is the reference for the code attached to the pad.
        """
        return f"{INSTRUCTIONS.read_text().rstrip()}\n\n{PAD_NOTE}\n{_for_the_candidate(self.readme)}\n"


QUESTIONS = (
    Question(
        title="k-means [py]",
        language="python",
        question_id=385853,
        solution=PY / "main.py",
        buffer=python_buffer,
        library=python_library,
        readme=PY / "README.md",
    ),
    Question(
        title="k-means [ts]",
        language="typescript",
        question_id=385854,
        solution=TS / "main.ts",
        buffer=typescript_buffer,
        library=typescript_library,
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


def _upload(path: Path, title: str, cookies: str, csrf: str) -> str:
    """Custom files arrive as a GraphQL multipart request; `file` is an Upload scalar.

    Three parts: the operation with the file slot nulled, a map saying which part fills it,
    and the bytes. There is no JSON form of this — hence the hand-rolled body.
    """
    operations = json.dumps(
        {"query": CREATE_FILE, "variables": {"input": {"customFileAttributes": {"title": title, "description": "", "file": None}}}}
    )
    file_map = json.dumps({"0": ["variables.input.customFileAttributes.file"]})
    boundary = f"----coderpad{uuid.uuid4().hex}"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="operations"\r\n\r\n{operations}\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="map"\r\n\r\n{file_map}\r\n'.encode(),
        f'--{boundary}\r\nContent-Disposition: form-data; name="0"; filename="{path.name}"\r\n'
        f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}\r\n\r\n".encode(),
        path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    request = urllib.request.Request(
        GRAPHQL,
        data=b"".join(parts),
        headers={
            "Cookie": cookies,
            "X-CSRF-Token": csrf,
            "User-Agent": USER_AGENT,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "apollo-require-preflight": "true",
        },
        method="POST",
    )
    payload: Any = json.loads(_open(request))
    if errors := payload.get("errors"):
        raise SystemExit(f"uploading {path.name} failed: {json.dumps(errors, indent=2)[:600]}")
    return cast("str", payload["data"]["createCustomFile"]["customFile"]["id"])


# The dashboard's own operations, recovered from its JS bundle (introspection is off in prod).
LOOKUP = """
query($id: Int!) { question(id: $id) { id title customFiles { id title } } }
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
CREATE_FILE = """
mutation($input: CreateCustomFileInput!) {
  createCustomFile(input: $input) { customFile { id title filename filesize } }
}
"""
DELETE_FILE = """
mutation($id: String!) { deleteCustomFile(input: { id: $id }) { customFile { id } } }
"""


def push(question: Question, root: Path, cookies: str, csrf: str) -> None:
    existing: Any = None
    if question.question_id is not None:
        existing = _graphql(LOOKUP, {"id": question.question_id}, cookies, csrf)["question"]
        if existing is None:
            raise SystemExit(f"question {question.question_id} is gone from the bank — clear its question_id to create it again")

    # Upload the replacements before detaching the old ones, so a failure here leaves the
    # question with a working library rather than none.
    uploaded = [_upload(root / name, f"{FILE_MARK} {name}", cookies, csrf) for name in sorted(question.library())]

    fields: dict[str, Any] = {
        "title": question.title,
        "language": question.language,
        "description": DESCRIPTION,
        "contents": question.buffer(),
        "solution": question.solution.read_text(),
        "candidateInstructions": [{"instructions": question.instructions(), "defaultVisible": True}],
        "customFileIds": uploaded,
    }

    if existing is None:
        result: Any = _graphql(CREATE, {"input": {"questionAttributes": fields}}, cookies, csrf)["createQuestion"]
        verb = "created"
    else:
        result = _graphql(UPDATE, {"input": {"questionAttributes": fields | {"id": question.question_id}}}, cookies, csrf)
        result = result["updateQuestion"]
        verb = "updated"

    # A mutation can 200 and still refuse the write; `errors` is where it says so.
    if failures := result.get("errors"):
        raise SystemExit(f"CoderPad rejected {question.title}: {json.dumps(failures, indent=2)[:800]}")

    # Now that the new files are attached, drop the ones this question used to carry. Only
    # ours: a file we did not upload may be attached to somebody else's question too.
    attached: list[Any] = [] if existing is None else existing.get("customFiles") or []
    stale: list[str] = [str(f["id"]) for f in attached if str(f["title"]).startswith(FILE_MARK)]
    for file_id in stale:
        _graphql(DELETE_FILE, {"id": file_id}, cookies, csrf)

    pushed = result["question"]
    replaced = f", replaced {len(stale)} old file(s)" if stale else ""
    print(f"{verb} {question.title} — {pushed['id']} — {len(uploaded)} files attached{replaced}")
    print(f"  {APP}/dashboard/questions/edit/{pushed['id']}")
    if question.question_id is None:
        print(f"  set question_id={pushed['id']} on the {question.title} entry in {Path(__file__).name}")


def main(argv: list[str]) -> int:
    roots: list[tuple[Question, Path]] = []
    for question in QUESTIONS:
        root = BUILD / question.title.replace(" ", "_")
        root.mkdir(parents=True, exist_ok=True)
        for name, text in question.library().items():
            (root / name).write_text(text)
        (root / "pad_buffer.txt").write_text(question.buffer())
        roots.append((question, root))
        print(f"wrote {root} — buffer + {len(question.library())} attached files")

    if "--push" not in argv:
        print(f"--push uploads both to your question bank, using the browser cookies in {COOKIE_FILE}")
        return 0

    # One session for both, so a cookie that expires mid-run fails before the second write.
    cookies = _cookies()
    csrf = _csrf_token(cookies)
    for question, root in roots:
        push(question, root, cookies, csrf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
