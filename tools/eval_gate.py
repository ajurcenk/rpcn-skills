# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Gate the rpcn-test trigger evals on suite accuracy (R12, AD-13).

Reads the `aggregate-result.json` written by `claude plugin eval` and counts
every run of every trigger case in `cases[].arms.with[]`:

  rpcn-test__trigger_<slug>  positive: its `fired` grader must pass
  rpcn-test__miss_<slug>     near-miss negative: its `not-fired` grader must pass

The eval output carries no tags, so cases are told apart by name prefix. A run
is correct when its trigger grader passed and its `error` does not start with
`API` (an API failure means the graders never really ran). A run that stopped
at the turn limit still counts: the Skill call is already in the transcript.

Prints one JSON object:
  {"ok", "accuracy", "runs_total", "runs_correct",
   "positives": {"runs", "correct"}, "negatives": {"runs", "correct"},
   "failed_runs": [{"case", "run", "explanation"}], "partial": bool}
plus "partialReason" when the run was partial, and "error" on exit 2.

Exit codes:
  0  accuracy >= --min-accuracy and every negative run is correct
  1  otherwise
  2  missing or unreadable file, unknown schemaVersion, no trigger cases,
     an incomplete suite (no positive or no negative trigger case, or a
     trigger case with fewer than --min-runs runs), or a partial run.
     `partial` and `partialReason` are kept in the output on every exit 2.

Run: uv run tools/eval_gate.py <aggregate-result.json> [--min-accuracy 0.9] [--min-runs 3]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
POSITIVE_PREFIX = "rpcn-test__trigger_"
NEGATIVE_PREFIX = "rpcn-test__miss_"
GRADER_FOR = {"positive": "fired", "negative": "not-fired"}


class GateError(Exception):
    """A problem that makes the result impossible to judge (exit 2)."""

    def __init__(self, message: str, result: dict | None = None) -> None:
        super().__init__(message)
        self.result = result


def empty_result() -> dict:
    return {
        "ok": False,
        "accuracy": None,
        "runs_total": 0,
        "runs_correct": 0,
        "positives": {"runs": 0, "correct": 0},
        "negatives": {"runs": 0, "correct": 0},
        "failed_runs": [],
        "partial": False,
    }


def load(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(f"{path} is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError(f"{path} is not a JSON object")
    version = data.get("schemaVersion")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise GateError(
            f"unknown schemaVersion {data.get('schemaVersion')!r} (expected {SCHEMA_VERSION})"
        )
    if not isinstance(data.get("cases"), list):
        raise GateError("no cases[] list in the result")
    return data


def kind_of(name: str) -> str | None:
    if name.startswith(POSITIVE_PREFIX):
        return "positive"
    if name.startswith(NEGATIVE_PREFIX):
        return "negative"
    return None


def judge_run(run: object, kind: str) -> tuple[bool, str]:
    """Return (correct, explanation) for one run."""
    if not isinstance(run, dict):
        return False, "run is not an object"
    error = run.get("error")
    if isinstance(error, str) and error.startswith("API"):
        return False, f"API error: {error}"
    wanted = GRADER_FOR[kind]
    graders = run.get("graders") if isinstance(run.get("graders"), list) else []
    grader = next((g for g in graders if isinstance(g, dict) and g.get("name") == wanted), None)
    if grader is None:
        suffix = f" (error: {error})" if error else ""
        return False, f"no '{wanted}' grader result{suffix}"
    explanation = str(grader.get("explanation", ""))
    return grader.get("passed") is True, explanation


def gate(data: dict, min_accuracy: float, min_runs: int = 3) -> tuple[int, dict]:
    result = empty_result()
    result["partial"] = bool(data.get("partial"))
    if result["partial"]:
        result["partialReason"] = data.get("partialReason")

    trigger_cases = [
        c for c in data["cases"]
        if isinstance(c, dict) and isinstance(c.get("name"), str) and kind_of(c["name"])
    ]
    if not trigger_cases:
        raise GateError(
            f"no trigger cases (names starting {POSITIVE_PREFIX!r} or {NEGATIVE_PREFIX!r})",
            result,
        )
    kinds = {kind_of(c["name"]) for c in trigger_cases}
    missing = [f"no {k} trigger cases" for k in ("positive", "negative") if k not in kinds]
    short = []

    for case in trigger_cases:
        name = case["name"]
        kind = kind_of(name)
        bucket = result["positives" if kind == "positive" else "negatives"]
        arms = case.get("arms") if isinstance(case.get("arms"), dict) else {}
        runs = arms.get("with") if isinstance(arms.get("with"), list) else []
        if len(runs) < min_runs:
            short.append(f"{name} has {len(runs)} runs (need {min_runs})")
        for index, run in enumerate(runs, start=1):
            correct, explanation = judge_run(run, kind)
            bucket["runs"] += 1
            result["runs_total"] += 1
            if correct:
                bucket["correct"] += 1
                result["runs_correct"] += 1
            else:
                result["failed_runs"].append(
                    {"case": name, "run": index, "explanation": explanation}
                )

    if missing or short:
        raise GateError("incomplete suite: " + "; ".join(missing + short), result)

    result["accuracy"] = round(result["runs_correct"] / result["runs_total"], 3)
    negatives_clean = result["negatives"]["correct"] == result["negatives"]["runs"]
    exact = result["runs_correct"] / result["runs_total"]
    result["ok"] = exact >= min_accuracy and negatives_clean and not result["partial"]

    if result["partial"]:
        result["error"] = f"partial run: {result.get('partialReason') or 'no reason given'}"
        return 2, result
    return (0 if result["ok"] else 1), result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result", type=Path, help="aggregate-result.json from claude plugin eval")
    parser.add_argument("--min-accuracy", type=float, default=0.9)
    parser.add_argument("--min-runs", type=int, default=3,
                        help="runs every trigger case must have (default 3, AD-13)")
    args = parser.parse_args(argv)

    try:
        code, result = gate(load(args.result), args.min_accuracy, args.min_runs)
    except GateError as exc:
        result = exc.result if exc.result is not None else empty_result()
        result["ok"] = False
        result["error"] = str(exc)
        if result.get("partial"):
            result["error"] += f"; partial run: {result.get('partialReason') or 'no reason given'}"
        code = 2
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
