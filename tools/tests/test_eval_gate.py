# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Unit tests for tools/eval_gate.py, run against synthetic aggregate-result.json files.

The synthetic files follow the shape `claude plugin eval` 2.1.312 writes
(schemaVersion 1, cases[].arms.with[] runs with graders[]).

Run: uv run tools/tests/test_eval_gate.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "eval_gate.py"

MAX_TURNS = "exit 1: Reached maximum number of turns (2)"
POSITIVES = [f"rpcn-test__trigger_p{i}" for i in range(8)]
NEGATIVES = [f"rpcn-test__miss_n{i}" for i in range(6)]


def make_run(kind: str, passed: bool = True, error: str | None = MAX_TURNS,
             graders: bool = True) -> dict:
    name = "fired" if kind == "positive" else "not-fired"
    count = (1 if passed else 0) if kind == "positive" else (0 if passed else 1)
    expected = "1..∞" if kind == "positive" else "0..0"
    return {
        "score": 1 if passed else 0,
        "passed": passed,
        "turns": 3,
        "costUsd": 0.06,
        "judgeCostUsd": 0,
        "durationSeconds": 7,
        "startedAt": "2026-10-29T10:00:00.000Z",
        "error": error,
        "tracePath": "/tmp/trace.jsonl",
        "skippedPaidGraders": False,
        "graders": [{
            "name": name,
            "passed": passed,
            "weight": 1,
            "explanation": f"Skill called {count}x (expected {expected})",
            "withOnly": False,
            "scored": True,
        }] if graders else [],
    }


def make_case(name: str, runs: list[dict]) -> dict:
    score = sum(r["score"] for r in runs) / len(runs) if runs else 0
    return {"name": name, "aggregates": {"score": score, "passRate": score},
            "arms": {"with": runs}}


def make_suite(failures: dict[str, set[int]] | None = None, runs: int = 3,
               extra_cases: list[dict] | None = None, **top: object) -> dict:
    """14 cases x `runs`; `failures` maps a case name to the 1-based runs that fail."""
    failures = failures or {}
    cases = []
    for names, kind in ((POSITIVES, "positive"), (NEGATIVES, "negative")):
        for name in names:
            cases.append(make_case(name, [
                make_run(kind, passed=i not in failures.get(name, set()))
                for i in range(1, runs + 1)
            ]))
    cases.extend(extra_cases or [])
    data = {
        "schemaVersion": 1,
        "claudeVersion": "2.1.312",
        "startedAt": "2026-10-29T10:00:00.000Z",
        "durationSeconds": 300,
        "costUsd": 2.9,
        "partial": False,
        "suite": {},
        "cases": cases,
        "aggregates": {"casesTotal": len(cases), "casesPassed": len(cases),
                       "overallScore": 1, "overallPassRate": 1},
    }
    data.update(top)
    return data


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_gate(self, data: object | None = None, raw: str | None = None,
                 path: Path | None = None, *args: str) -> tuple[int, dict]:
        if path is None:
            path = self.dir / "aggregate-result.json"
            path.write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SCRIPT), str(path), *args],
                              capture_output=True, text=True, timeout=60)
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"stdout is not JSON: {proc.stdout!r} {proc.stderr!r}") from exc
        for key in ("ok", "accuracy", "runs_total", "runs_correct", "positives",
                    "negatives", "failed_runs", "partial"):
            self.assertIn(key, out)
        return proc.returncode, out

    def test_all_correct(self) -> None:
        code, out = self.run_gate(make_suite())
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["accuracy"], 1.0)
        self.assertEqual((out["runs_total"], out["runs_correct"]), (42, 42))
        self.assertEqual(out["positives"], {"runs": 24, "correct": 24})
        self.assertEqual(out["negatives"], {"runs": 18, "correct": 18})
        self.assertEqual(out["failed_runs"], [])
        self.assertFalse(out["partial"])

    def test_max_turns_error_counts_as_correct(self) -> None:
        # every synthetic run already carries the max-turns error; make it explicit
        data = make_suite()
        self.assertEqual(data["cases"][0]["arms"]["with"][0]["error"], MAX_TURNS)
        code, out = self.run_gate(data)
        self.assertEqual(code, 0)
        self.assertEqual(out["runs_correct"], 42)

    def test_below_threshold(self) -> None:
        failures = {POSITIVES[0]: {1, 2, 3}, POSITIVES[1]: {2}, POSITIVES[2]: {3}}
        code, out = self.run_gate(make_suite(failures))
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertEqual(out["accuracy"], 0.881)
        self.assertEqual(out["runs_correct"], 37)
        self.assertEqual(len(out["failed_runs"]), 5)
        self.assertIn({"case": POSITIVES[1], "run": 2,
                       "explanation": "Skill called 0x (expected 1..∞)"},
                      out["failed_runs"])

    def test_min_accuracy_flag(self) -> None:
        failures = {POSITIVES[0]: {1, 2, 3}, POSITIVES[1]: {2}, POSITIVES[2]: {3}}
        code, out = self.run_gate(make_suite(failures), None, None, "--min-accuracy", "0.85")
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])

    def test_one_negative_firing_fails_despite_accuracy(self) -> None:
        code, out = self.run_gate(make_suite({NEGATIVES[3]: {2}}))
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertGreaterEqual(out["accuracy"], 0.9)
        self.assertEqual(out["negatives"], {"runs": 18, "correct": 17})
        self.assertEqual(out["failed_runs"][0]["case"], NEGATIVES[3])
        self.assertEqual(out["failed_runs"][0]["run"], 2)

    def test_partial_run(self) -> None:
        code, out = self.run_gate(make_suite(partial=True, partialReason="cost ceiling hit"))
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])
        self.assertTrue(out["partial"])
        self.assertEqual(out["partialReason"], "cost ceiling hit")

    def test_api_error_counts_as_incorrect(self) -> None:
        data = make_suite()
        data["cases"][0]["arms"]["with"][0] = make_run(
            "positive", passed=True, error="API Error: 529 overloaded", graders=False)
        data["cases"][1]["arms"]["with"][0] = make_run(
            "positive", passed=True, error="API Error: 500 internal")
        code, out = self.run_gate(data)
        self.assertEqual(out["runs_correct"], 40)
        self.assertEqual(len(out["failed_runs"]), 2)
        self.assertTrue(all(f["explanation"].startswith("API error") for f in out["failed_runs"]))
        self.assertEqual(code, 0)  # 40/42 = 0.952, still above the gate

    def test_missing_grader_counts_as_incorrect(self) -> None:
        data = make_suite()
        data["cases"][-1]["arms"]["with"][0]["graders"] = []
        code, out = self.run_gate(data)
        self.assertEqual(code, 1)  # a negative with no verdict is not clean
        self.assertIn("no 'not-fired' grader", out["failed_runs"][0]["explanation"])

    def test_other_cases_are_ignored(self) -> None:
        other = make_case("rpcn-author__something", [make_run("positive", passed=False)])
        code, out = self.run_gate(make_suite(extra_cases=[other]))
        self.assertEqual(code, 0)
        self.assertEqual(out["runs_total"], 42)

    def test_no_trigger_cases(self) -> None:
        data = make_suite()
        data["cases"] = [make_case("rpcn-test__lint_broken", [make_run("positive")])]
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertIn("no trigger cases", out["error"])

    def test_no_negative_cases(self) -> None:
        data = make_suite()
        data["cases"] = [c for c in data["cases"] if c["name"] in POSITIVES]
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])
        self.assertIn("no negative trigger cases", out["error"])

    def test_no_positive_cases(self) -> None:
        data = make_suite()
        data["cases"] = [c for c in data["cases"] if c["name"] in NEGATIVES]
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertIn("no positive trigger cases", out["error"])

    def test_case_with_too_few_runs(self) -> None:
        data = make_suite()
        data["cases"][2]["arms"]["with"] = data["cases"][2]["arms"]["with"][:1]
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertIn(f"{POSITIVES[2]} has 1 runs (need 3)", out["error"])

    def test_single_run_suite_with_min_runs_1(self) -> None:
        code, out = self.run_gate(make_suite(runs=1), None, None, "--min-runs", "1")
        self.assertEqual(code, 0)
        self.assertEqual(out["runs_total"], 14)

    def test_empty_with_runs(self) -> None:
        data = make_suite()
        data["cases"][-1]["arms"]["with"] = []
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertIn(f"{NEGATIVES[-1]} has 0 runs", out["error"])

    def test_partial_without_finished_trigger_runs(self) -> None:
        data = make_suite(partial=True, partialReason="cost ceiling hit")
        for case in data["cases"]:
            case["arms"]["with"] = []
        code, out = self.run_gate(data)
        self.assertEqual(code, 2)
        self.assertTrue(out["partial"])
        self.assertEqual(out["partialReason"], "cost ceiling hit")
        self.assertIn("partial run: cost ceiling hit", out["error"])

    def test_schema_version_must_be_int_1(self) -> None:
        for bad in (True, 1.0, "1"):
            with self.subTest(schemaVersion=bad):
                code, out = self.run_gate(make_suite(schemaVersion=bad))
                self.assertEqual(code, 2)
                self.assertIn("schemaVersion", out["error"])

    def test_missing_file(self) -> None:
        code, out = self.run_gate(None, None, self.dir / "nope.json")
        self.assertEqual(code, 2)
        self.assertIn("cannot read", out["error"])

    def test_not_json(self) -> None:
        code, out = self.run_gate(None, "{not json")
        self.assertEqual(code, 2)
        self.assertIn("not JSON", out["error"])

    def test_unknown_schema_version(self) -> None:
        code, out = self.run_gate(make_suite(schemaVersion=2))
        self.assertEqual(code, 2)
        self.assertIn("schemaVersion", out["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
