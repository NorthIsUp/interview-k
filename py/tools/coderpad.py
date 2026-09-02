"""Assemble the candidate-facing bundle for CoderPad, and push it if the API is open to you.

    uv run python tools/coderpad.py           # write the bundle, print where it landed
    uv run python tools/coderpad.py --push    # also create/update the question via the API

A CoderPad pad is one buffer, so the bundle is show.py + data.py + the stub concatenated
into a single importable module — assembled from the same sources the packet embeds, so it
cannot drift from what the interviewer is reading. Without --push the tool is offline: paste
the file into a pad and "Save code as draft question", which is the UI path to the question
bank.

--push wants CODERPAD_API_KEY, and CoderPad gates API keys behind an Enterprise plan. It is
idempotent on QUESTION_TITLE: PUT when a question of that title already exists, POST when
not, so re-running edits the same question rather than piling up duplicates.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, TypedDict, cast

PY = Path(__file__).parent.parent
PACKET = PY.parent / "docs" / "packet.md"
BUNDLE = PY / "build" / "coderpad_question.py"
API = "https://app.coderpad.io/api"

QUESTION_TITLE = "k-means from scratch"
LANGUAGE = "python"

# Only reached with --push; the interviewer-facing half of the packet stays out of the pad.
DESCRIPTION = "Implement k-means from scratch. Rubric, hint ladder and expected output: docs/packet.md in the interview-k repo."
CANDIDATE_INSTRUCTIONS = (
    "Implement kmeans(points, k) from scratch: cluster the points into k groups and return one "
    "(centroid, its points) pair per cluster. Standard library only — no scikit-learn, no scipy "
    "clustering. show() and the datasets are already in the pad; use them to look at your answer."
)

# data.py imports its types from show.py, which is inlined above it — so the import goes.
DATA_TYPE_IMPORT = "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from interview_k.show import Centroid, Point\n"
FUTURE = "from __future__ import annotations"


def _without_future(source: str) -> str:
    """One `from __future__` line survives, at the top of the bundle — the rest are syntax errors."""
    return "\n".join(line for line in source.splitlines() if not line.startswith(FUTURE))


def _stub() -> str:
    """The candidate's stub, read out of the packet so there is one copy of it."""
    match = re.search(r"```python\n(from collections\.abc import Sequence\n.*?)```", PACKET.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit("packet.md no longer contains the kmeans stub block — fix the marker in _stub()")
    return match.group(1).rstrip()


def bundle() -> str:
    """show.py + data.py + the stub, as one module a candidate can paste into a pad."""
    show = _without_future((PY / "src/interview_k/show.py").read_text())
    data = (PY / "src/interview_k/data.py").read_text()
    if DATA_TYPE_IMPORT not in data:
        raise SystemExit("data.py's type import moved — update DATA_TYPE_IMPORT")
    data = _without_future(data.replace(DATA_TYPE_IMPORT, ""))

    text = f"{FUTURE}\n{show}\n\n{data}\n\n{_stub()}\n"
    compile(text, "coderpad bundle", "exec")  # a bundle that does not parse is worse than none
    return text


# Any: a serialization boundary. The response shape is CoderPad's to change, so it is
# checked at runtime below rather than declared here as if we controlled it.
def _request(method: str, path: str, key: str, fields: dict[str, str] | None = None) -> Any:  # ruff: ignore[any-type]
    body = urllib.parse.urlencode(fields).encode() if fields else None
    request = urllib.request.Request(f"{API}{path}", data=body, method=method)
    request.add_header("Authorization", f'Token token="{key}"')
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise SystemExit(f"CoderPad {method} {path} -> {exc.code}: {detail}") from exc


class _Question(TypedDict, total=False):
    """Only the two fields this tool reads; the API returns plenty more."""

    id: int
    title: str


def _existing_id(key: str) -> int | None:
    payload: Any = _request("GET", "/organization/questions", key)
    # a bare list or {"questions": [...]}; the docs do not pin which, so accept both
    raw: Any = payload.get("questions", payload) if hasattr(payload, "get") else payload
    if not isinstance(raw, list):
        raise SystemExit(f"unexpected /organization/questions shape: {str(payload)[:200]}")
    for question in cast("list[_Question]", raw):
        if question.get("title") == QUESTION_TITLE:
            return question.get("id")
    return None


def push(text: str) -> int:
    key = os.environ.get("CODERPAD_API_KEY")
    if not key:
        raise SystemExit(
            "CODERPAD_API_KEY is unset. CoderPad issues API keys on Enterprise plans only — "
            "without one, paste the bundle and use 'Save code as draft question'."
        )

    # The docs' worked example posts these flat; their parameter table spells the first two
    # question[title] / question[language]. Flat is what their curl actually runs.
    fields = {
        "title": QUESTION_TITLE,
        "language": LANGUAGE,
        "description": DESCRIPTION,
        "contents": text,
        "solution": (PY / "main.py").read_text(),
        "candidate_instructions": json.dumps([{"instructions": CANDIDATE_INSTRUCTIONS}]),
    }
    question_id = _existing_id(key)
    if question_id is None:
        created: Any = _request("POST", "/questions", key, fields)
        print(f"created question {created.get('id')} — {QUESTION_TITLE}")
    else:
        _request("PUT", f"/questions/{question_id}", key, fields)
        print(f"updated question {question_id} — {QUESTION_TITLE}")
    return 0


def main(argv: list[str]) -> int:
    text = bundle()
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(text)
    print(f"wrote {BUNDLE} — {len(text.splitlines())} lines, parses clean")
    if "--push" in argv:
        return push(text)
    print("paste it into a pad, then 'Save code as draft question'; --push needs an Enterprise API key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
