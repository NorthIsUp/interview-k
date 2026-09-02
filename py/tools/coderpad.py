"""Assemble the candidate-facing bundles for CoderPad, and push them into your question bank.

    uv run python tools/coderpad.py           # write both bundles, print where they landed
    uv run python tools/coderpad.py --push    # also create/update both questions

One question per language — "k-means [py]" and "k-means [ts]" — because the pad's language
picks the candidate's, and a pad is one buffer. So each bundle is that language's show,
datasets and stub concatenated into a single file, assembled from the same sources the packet
embeds so it cannot drift from what the interviewer is reading. Without --push the tool is
offline: paste a bundle into a pad and "Save code as draft question", which is the UI path to
the question bank.

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

# Only reached with --push; the interviewer-facing half of the packet stays out of the pad.
DESCRIPTION = "Implement k-means from scratch. Rubric, hint ladder and expected output: docs/packet.md in the interview-k repo."
INSTRUCTIONS = (
    "Implement {call} from scratch: cluster the points into k groups and return one "
    "(centroid, its points) pair per cluster. {ban} {helper} and the datasets are already in "
    "the pad; use them to look at your answer."
)

# data.py imports its types from show.py, which is inlined above it — so the import goes.
DATA_TYPE_IMPORT = "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from interview_k.show import Centroid, Point\n"
FUTURE = "from __future__ import annotations"
MAIN_GUARD = 'if __name__ == "__main__":'
# The TS equivalent of the __main__ guard, and just as unwelcome in a pad.
TS_MAIN_GUARD = "if (import.meta.main)"

# Dependency order, since one buffer has no imports to resolve it for us.
TS_MODULES = ("src/random.ts", "src/show.ts", "src/data.ts")


def _without_future(source: str) -> str:
    """One `from __future__` line survives, at the top of the bundle — the rest are syntax errors."""
    return "\n".join(line for line in source.splitlines() if not line.startswith(FUTURE))


def _without_main_guard(source: str) -> str:
    """Drop `if __name__ == "__main__":` and its body.

    A pad runs its buffer as __main__, so the demo would print five plots before the candidate
    has typed anything. demo() stays defined for anyone who wants to call it.
    """
    out: list[str] = []
    skipping = False
    for line in source.splitlines():
        if line.startswith(MAIN_GUARD):
            skipping = True
            continue
        if skipping:
            if not line.strip() or line.startswith((" ", "\t")):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


def _stub(fence: str, opener: str) -> str:
    """The candidate's stub, read out of the packet so there is one copy of it per language."""
    match = re.search(rf"```{fence}\n({re.escape(opener)}\n.*?)```", PACKET.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit(f"packet.md no longer has a ```{fence} block starting {opener!r} — fix the marker in _stub()")
    return match.group(1).rstrip()


def python_bundle() -> str:
    """show.py + data.py + the stub, as one module a candidate can paste into a pad."""
    show = _without_main_guard(_without_future((PY / "src/interview_k/show.py").read_text()))
    data = (PY / "src/interview_k/data.py").read_text()
    if DATA_TYPE_IMPORT not in data:
        raise SystemExit("data.py's type import moved — update DATA_TYPE_IMPORT")
    data = _without_main_guard(_without_future(data.replace(DATA_TYPE_IMPORT, "")))

    text = f"{FUTURE}\n{show}\n\n{data}\n\n{_stub('python', 'from collections.abc import Sequence')}\n"
    compile(text, "coderpad bundle", "exec")  # a bundle that does not parse is worse than none
    return text


def _flatten_ts(source: str) -> str:
    """Concatenation is the only module system a pad has: drop the imports, unexport the rest.

    Leaving the `export`s in would make the buffer a module, and a module's imports would then
    have to resolve — which is the thing there is no way to do here.
    """
    kept = [line for line in source.splitlines() if not line.startswith(("import ", TS_MAIN_GUARD))]
    return "\n".join(re.sub(r"^export ", "", line) for line in kept)


def typescript_bundle() -> str:
    """random.ts + show.ts + data.ts + the stub, as one buffer node can run with types stripped."""
    text = "\n\n".join(_flatten_ts((TS / module).read_text()) for module in TS_MODULES)
    text += f"\n\n{_stub('typescript', 'type Cluster = [Centroid, Point[]];')}\n"
    # The flattener is line-based, so a multi-line import would survive it in pieces.
    if 'from "./' in text:
        raise SystemExit("a ts/src import survived flattening — is one of them written across lines?")
    return text


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
query($id: Int!) { question(id: $id) { id title } }
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
    language: str
    question_id: int | None
    filename: str
    solution: Path
    build: Callable[[], str]
    instructions: str


QUESTIONS = (
    Question(
        title="k-means [py]",
        language="python",
        question_id=385810,
        filename="coderpad_question.py",
        solution=PY / "main.py",
        build=python_bundle,
        instructions=INSTRUCTIONS.format(
            call="kmeans(points, k)",
            ban="Standard library only — no scikit-learn, no scipy clustering.",
            helper="show()",
        ),
    ),
    Question(
        title="k-means [ts]",
        language="typescript",
        question_id=385815,
        filename="coderpad_question.ts",
        solution=TS / "main.ts",
        build=typescript_bundle,
        instructions=INSTRUCTIONS.format(
            call="kmeans(points, k)",
            ban="No npm packages — everything you need is in the pad.",
            helper="show()",
        ),
    ),
)


def push(question: Question, text: str, cookies: str, csrf: str) -> None:
    fields: dict[str, Any] = {
        "title": question.title,
        "language": question.language,
        "description": DESCRIPTION,
        "contents": text,
        "solution": question.solution.read_text(),
        "candidateInstructions": [{"instructions": question.instructions, "defaultVisible": True}],
    }

    if question.question_id is not None and _graphql(LOOKUP, {"id": question.question_id}, cookies, csrf)["question"] is None:
        raise SystemExit(f"question {question.question_id} is gone from the bank — clear its question_id to create it again")

    if question.question_id is None:
        result: Any = _graphql(CREATE, {"input": {"questionAttributes": fields}}, cookies, csrf)["createQuestion"]
        verb = "created"
    else:
        variables = {"input": {"questionAttributes": fields | {"id": question.question_id}}}
        result = _graphql(UPDATE, variables, cookies, csrf)["updateQuestion"]
        verb = "updated"

    # A mutation can 200 and still refuse the write; `errors` is where it says so.
    if failures := result.get("errors"):
        raise SystemExit(f"CoderPad rejected {question.title}: {json.dumps(failures, indent=2)[:800]}")

    pushed = result["question"]
    draft = " (draft)" if pushed.get("isDraft") else ""
    print(f"{verb} {question.title} — {pushed['id']}{draft} — {APP}/dashboard/questions/edit/{pushed['id']}")
    if question.question_id is None:
        print(f"  set question_id={pushed['id']} on the {question.title} entry in {Path(__file__).name} so the next --push edits it")


def main(argv: list[str]) -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    built = [(question, question.build()) for question in QUESTIONS]
    for question, text in built:
        path = BUILD / question.filename
        path.write_text(text)
        print(f"wrote {path} — {len(text.splitlines())} lines")

    if "--push" not in argv:
        print(f"--push uploads both to your question bank, using the browser cookies in {COOKIE_FILE}")
        return 0

    # One session for both, so a cookie that expires mid-run fails before the second write.
    cookies = _cookies()
    csrf = _csrf_token(cookies)
    for question, text in built:
        push(question, text, cookies, csrf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
