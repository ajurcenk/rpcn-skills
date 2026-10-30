# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Unit tests for tools/eval_record.py, tools/eval_record_check.py and
tools/run_evals.py. No Claude calls: run_evals is driven by a fake `claude`
on PATH and a fake test project whose run_scenarios.py writes a synthetic
results.json.

Run: uv run tools/tests/test_eval_record.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import eval_record  # noqa: E402

CHECK = TOOLS / "eval_record_check.py"
RUN_EVALS = TOOLS / "run_evals.py"

POSITIVES = [f"rpcn-test__trigger_p{i}" for i in range(8)]
NEGATIVES = [f"rpcn-test__miss_n{i}" for i in range(6)]


def write(path: Path, text: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def make_skills(root: Path) -> None:
    write(root / "skills/rpcn-test/SKILL.md", "---\nname: rpcn-test\n---\nbody\n")
    write(root / "skills/rpcn-test/references/a.md", "ref a\n")
    write(root / "skills/rpcn-test/scripts/rpcn_check.py", "print('x')\n")


def git_init(root: Path) -> None:
    for cmd in (["init", "-q"], ["config", "user.email", "t@example.com"],
                ["config", "user.name", "t"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


class HashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_matches_the_documented_formula(self) -> None:
        make_skills(self.tmp)
        expected = hashlib.sha256()
        for rel in sorted(["skills/rpcn-test/SKILL.md", "skills/rpcn-test/references/a.md",
                           "skills/rpcn-test/scripts/rpcn_check.py"]):
            d = hashlib.sha256((self.tmp / rel).read_bytes()).hexdigest()
            expected.update(rel.encode() + b"\0" + d.encode() + b"\n")
        self.assertEqual(eval_record.skills_hash(self.tmp), expected.hexdigest())

    def test_stable_across_calls_and_mtime(self) -> None:
        make_skills(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        self.assertEqual(eval_record.skills_hash(self.tmp), first)
        f = self.tmp / "skills/rpcn-test/SKILL.md"
        os.utime(f, (time.time() - 86400 * 30, time.time() - 86400 * 30))
        self.assertEqual(eval_record.skills_hash(self.tmp), first)

    def test_independent_of_creation_order_and_location(self) -> None:
        make_skills(self.tmp)
        other = self.tmp / "elsewhere" / "repo"
        # same content, created in reverse order, at another path
        write(other / "skills/rpcn-test/scripts/rpcn_check.py", "print('x')\n")
        write(other / "skills/rpcn-test/references/a.md", "ref a\n")
        write(other / "skills/rpcn-test/SKILL.md", "---\nname: rpcn-test\n---\nbody\n")
        self.assertEqual(eval_record.skills_hash(self.tmp), eval_record.skills_hash(other))

    def test_changes_when_content_changes(self) -> None:
        make_skills(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        write(self.tmp / "skills/rpcn-test/references/a.md", "ref a!\n")
        self.assertNotEqual(eval_record.skills_hash(self.tmp), first)

    def test_changes_when_a_file_is_renamed_or_added(self) -> None:
        make_skills(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        (self.tmp / "skills/rpcn-test/references/a.md").rename(self.tmp / "skills/rpcn-test/references/b.md")
        second = eval_record.skills_hash(self.tmp)
        self.assertNotEqual(second, first)
        write(self.tmp / "skills/rpcn-test/references/c.md", "")
        self.assertNotEqual(eval_record.skills_hash(self.tmp), second)

    def test_ignores_pycache_without_git(self) -> None:
        make_skills(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        write(self.tmp / "skills/rpcn-test/scripts/__pycache__/rpcn_check.cpython-312.pyc", b"\0\1")
        self.assertEqual(eval_record.skills_hash(self.tmp), first)

    def test_ignores_pycache_and_gitignored_in_git(self) -> None:
        make_skills(self.tmp)
        write(self.tmp / ".gitignore", "*.log\n")
        git_init(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        write(self.tmp / "skills/rpcn-test/scripts/__pycache__/x.pyc", b"\0")
        write(self.tmp / "skills/rpcn-test/debug.log", "noise")
        self.assertEqual(eval_record.skills_hash(self.tmp), first)
        # an untracked but trackable file counts
        write(self.tmp / "skills/rpcn-test/references/new.md", "new\n")
        self.assertNotEqual(eval_record.skills_hash(self.tmp), first)

    def test_git_failure_in_a_checkout_raises_instead_of_walking(self) -> None:
        make_skills(self.tmp)
        write(self.tmp / ".git", "gitdir: /nonexistent/gitdir\n")
        with self.assertRaises(eval_record.HashError):
            eval_record.skills_hash(self.tmp)
        proc = run(["uv", "run", str(CHECK), "--root", str(self.tmp)])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        out = json.loads(proc.stdout)
        self.assertFalse(out["ok"])
        self.assertIn("git", out["reason"])

    def test_git_and_walk_agree_on_a_clean_checkout(self) -> None:
        make_skills(self.tmp)
        walked = eval_record.skills_hash(self.tmp)
        git_init(self.tmp)
        self.assertEqual(eval_record.skills_hash(self.tmp), walked)

    def test_only_skills_counts(self) -> None:
        make_skills(self.tmp)
        first = eval_record.skills_hash(self.tmp)
        write(self.tmp / "evals/README.md", "x")
        write(self.tmp / "tools/x.py", "x")
        write(self.tmp / "README.md", "x")
        self.assertEqual(eval_record.skills_hash(self.tmp), first)


def record(full_hash: str, passed: bool = True, schema: object = 1) -> dict:
    return {"schema": schema, "skills_hash": full_hash, "date": "2026-10-30",
            "git_head": None, "dirty": None, "plugin_version": "0.1.0", "claude_version": "x",
            "trigger": {"ok": passed}, "scenarios": [], "compare": None,
            "passed": passed, "cost_usd": 0}


class CheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        make_skills(self.tmp)
        self.full = eval_record.skills_hash(self.tmp)
        self.results = self.tmp / "evals/results"

    def put(self, data: dict | str, date: str = "2026-10-30", prefix: str | None = None) -> Path:
        name = f"{date}-{(prefix or self.full)[:12]}.json"
        text = data if isinstance(data, str) else json.dumps(data)
        return write(self.results / name, text)

    def check(self) -> tuple[int, dict]:
        proc = run(["uv", "run", str(CHECK), "--root", str(self.tmp)])
        return proc.returncode, json.loads(proc.stdout)

    def test_fresh_record_passes(self) -> None:
        path = self.put(record(self.full))
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertTrue(out["ok"])
        self.assertEqual(out["skills_hash"], self.full)
        self.assertEqual(out["record"], path.relative_to(self.tmp).as_posix())

    def test_no_record_fails_and_names_the_command(self) -> None:
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertIsNone(out["record"])
        self.assertIn("uv run tools/run_evals.py", out["reason"])

    def test_skill_edited_after_record_fails(self) -> None:
        self.put(record(self.full))
        write(self.tmp / "skills/rpcn-test/SKILL.md", "---\nname: rpcn-test\n---\nbody.\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("run_evals.py", out["reason"])

    def test_failed_record_only_fails(self) -> None:
        self.put(record(self.full, passed=False))
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("run_evals.py", out["reason"])

    def test_failed_and_passing_records_pass(self) -> None:
        self.put(record(self.full, passed=False), date="2026-10-29")
        self.put(record(self.full, passed=True), date="2026-10-30")
        self.assertEqual(self.check()[0], 0)

    def test_prefix_collision_fails(self) -> None:
        other = self.full[:12] + ("0" if self.full[12] != "0" else "1") + self.full[13:]
        self.put(record(other), prefix=self.full)
        code, out = self.check()
        self.assertEqual(code, 1, out)

    def test_record_for_other_hash_ignored(self) -> None:
        self.put(record("ab" * 32), prefix="ab" * 32)
        self.assertEqual(self.check()[0], 1)

    def test_not_json_exits_2_naming_the_file(self) -> None:
        path = self.put("{not json")
        code, out = self.check()
        self.assertEqual(code, 2)
        self.assertIn(path.name, out["reason"])

    def test_wrong_schema_exits_2(self) -> None:
        path = self.put(record(self.full, schema=2))
        code, out = self.check()
        self.assertEqual(code, 2)
        self.assertIn(path.name, out["reason"])

    def test_bool_schema_exits_2(self) -> None:
        self.put(record(self.full, schema=True))
        self.assertEqual(self.check()[0], 2)

    def test_timestamped_eval_folders_are_ignored(self) -> None:
        (self.results / "2026-10-30T10-00-00").mkdir(parents=True)
        self.put(record(self.full))
        self.assertEqual(self.check()[0], 0)


FAKE_CLAUDE = """#!/bin/sh
# Fake claude for run_evals tests: --version, and `plugin eval ... --json <out>`.
echo "$*" >> "$FAKE_LOG"
if [ "$1" = "--version" ]; then echo "9.9.9 (Claude Code)"; exit 0; fi
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "--json" ]; then out="$a"; fi
  prev="$a"
done
echo "fake eval progress line"
if [ -n "$FAKE_TOUCH_SKILL" ]; then echo "changed" >> "$FAKE_TOUCH_SKILL"; fi
if [ -n "$FAKE_NO_RESULT" ]; then exit 1; fi
cp "$FAKE_AGGREGATE" "$out"
"""

FAKE_RUNNER = '''# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fake run_scenarios.py: writes a synthetic results.json."""
import argparse, json, os, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--source")
p.add_argument("--runs", type=int)
p.add_argument("--scenario", action="append", default=[])
a = p.parse_args()
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write("run_scenarios " + " ".join(sys.argv[1:]) + "\\n")
fail = os.environ.get("FAKE_SCENARIO_FAIL", "")
out = Path(__file__).parent / "runs" / "t1"
out.mkdir(parents=True, exist_ok=True)
scenarios = []
for name in a.scenario:
    runs = [{"index": i, "passed": name != fail, "cost_usd": 0.25} for i in range(1, a.runs + 1)]
    entry = {"name": name, "passed": name != fail,
             "pass_count": sum(r["passed"] for r in runs), "runs": runs}
    if "compare" in name:
        entry["comparison"] = {"winner": "ours", "judge": {"cost_usd": 0.5},
                               "runs": {"ours": runs, "bare": [{"cost_usd": 0.1}]}}
    scenarios.append(entry)
passed = all(s["passed"] for s in scenarios)
crashed = 1 if os.environ.get("FAKE_ARMS_CRASHED") else 0
(out / "results.json").write_text(json.dumps(
    {"scenarios": scenarios, "passed": passed, "arms_crashed": crashed}))
print("scenario progress line", flush=True)
print(f"results: {out / 'results.json'}")
sys.exit(0 if passed and not crashed else 1)
'''


def aggregate(fail_cases: int = 0, runs: int = 3) -> dict:
    """14 cases x runs; the first `fail_cases` positives fail every run."""
    cases = []
    for i, name in enumerate(POSITIVES + NEGATIVES):
        kind = "positive" if name in POSITIVES else "negative"
        ok = not (kind == "positive" and i < fail_cases)
        grader = "fired" if kind == "positive" else "not-fired"
        cases.append({"name": name, "arms": {"with": [
            {"passed": ok, "error": None, "graders": [{"name": grader, "passed": ok, "explanation": ""}]}
            for _ in range(runs)]}})
    return {"schemaVersion": 1, "costUsd": 3.0, "partial": False, "cases": cases}


class RunEvalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        make_skills(self.repo)
        write(self.repo / ".claude-plugin/plugin.json", json.dumps({"version": "0.1.0"}))
        self.project = self.tmp / "test-project"
        write(self.project / "run_scenarios.py", FAKE_RUNNER)
        write(self.project / "scenarios/rpcn-test__lint_broken/expect.toml",
              'skill = "rpcn-test"\n[status]\nstatus = "complete"\n')
        write(self.project / "scenarios/rpcn-test__compare_lint/expect.toml",
              'skill = "rpcn-test"\n[compare]\nenabled = true\n')
        bindir = self.tmp / "bin"
        claude = write(bindir / "claude", FAKE_CLAUDE)
        claude.chmod(claude.stat().st_mode | stat.S_IXUSR)
        self.log = self.tmp / "calls.log"
        self.agg = self.tmp / "aggregate.json"
        self.agg.write_text(json.dumps(aggregate()))
        self.env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_LOG": str(self.log), "FAKE_AGGREGATE": str(self.agg)}

    def run_evals(self, *extra: str, **env: str) -> subprocess.CompletedProcess:
        return run(["uv", "run", str(RUN_EVALS), "--repo", str(self.repo),
                    "--test-project", str(self.project), *extra],
                   env={**self.env, **env})

    def records(self) -> list[Path]:
        return sorted((self.repo / "evals/results").glob("*.json"))

    def only_record(self) -> dict:
        recs = self.records()
        self.assertEqual(len(recs), 1, recs)
        full = eval_record.skills_hash(self.repo)
        rec = json.loads(recs[0].read_text())
        if rec["passed"]:
            self.assertRegex(recs[0].name, rf"^\d{{4}}-\d\d-\d\d-{full[:12]}\.json$")
        else:  # a name the check's *-<hash12>.json glob never matches
            self.assertRegex(recs[0].name, rf"^\d{{4}}-\d\d-\d\d-{full[:12]}\.failed-\d{{6}}\.json$")
        return rec

    def check_code(self) -> int:
        return run(["uv", "run", str(CHECK), "--root", str(self.repo)]).returncode

    def calls(self) -> str:
        return self.log.read_text() if self.log.exists() else ""

    def test_pass_writes_a_passing_record(self) -> None:
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rec = self.only_record()
        self.assertEqual(rec["schema"], 1)
        self.assertEqual(rec["skills_hash"], eval_record.skills_hash(self.repo))
        self.assertTrue(rec["passed"])
        self.assertTrue(rec["trigger"]["ok"])
        self.assertEqual(rec["trigger"]["accuracy"], 1.0)
        self.assertEqual(rec["scenarios"],
                         [{"name": "rpcn-test__lint_broken", "result": "PASS", "runs": 3, "passed": 3}])
        self.assertIsNone(rec["compare"])
        self.assertEqual(rec["plugin_version"], "0.1.0")
        self.assertEqual(rec["claude_version"], "9.9.9 (Claude Code)")
        self.assertAlmostEqual(rec["cost_usd"], 3.75)
        for key in ("date", "git_head", "dirty"):
            self.assertIn(key, rec)
        # the documented command lines, and no comparison scenario by default
        calls = self.calls()
        self.assertIn("plugin eval . --ablation none --runs 3 --tag trigger --no-publish "
                      "--trust-plugin --json ", calls)
        self.assertIn(f"--source local:{self.repo.resolve()} --runs 3 --scenario rpcn-test__lint_broken", calls)
        self.assertNotIn("compare_lint", calls)
        # progress lines, and the children's own output passed through
        for step in ("trigger:", "gate: accuracy=1.0", "scenarios:", "record: evals/results/"):
            self.assertIn(f"] {step}", proc.stdout)
        self.assertIn("[run_evals +", proc.stdout)
        self.assertIn("fake eval progress line", proc.stdout)
        self.assertIn("scenario progress line", proc.stdout)
        # and the check accepts it
        check = run(["uv", "run", str(CHECK), "--root", str(self.repo)])
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_runs_option_passes_through(self) -> None:
        self.agg.write_text(json.dumps(aggregate(runs=4)))
        proc = self.run_evals("--runs", "4")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("--runs 4 --tag trigger", self.calls())
        self.assertEqual(self.only_record()["scenarios"][0]["runs"], 4)

    def test_with_compare_adds_comparison_scenarios(self) -> None:
        proc = self.run_evals("--with-compare")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("--scenario rpcn-test__compare_lint", self.calls())
        rec = self.only_record()
        self.assertEqual(rec["compare"], {"rpcn-test__compare_lint": "ours"})
        self.assertEqual(len(rec["scenarios"]), 2)
        # trigger 3.0 + lint_broken 0.75 + compare (0.75 ours + 0.1 bare + 0.5 judge)
        self.assertAlmostEqual(rec["cost_usd"], 5.1)

    def test_gate_fail_writes_failed_record(self) -> None:
        self.agg.write_text(json.dumps(aggregate(fail_cases=3)))
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        rec = self.only_record()
        self.assertFalse(rec["passed"])
        self.assertFalse(rec["trigger"]["ok"])
        self.assertLess(rec["trigger"]["accuracy"], 0.9)
        self.assertEqual(rec["scenarios"][0]["result"], "PASS")  # scenarios still ran
        check = run(["uv", "run", str(CHECK), "--root", str(self.repo)])
        self.assertEqual(check.returncode, 1)

    def test_scenario_fail_writes_failed_record(self) -> None:
        proc = self.run_evals(FAKE_SCENARIO_FAIL="rpcn-test__lint_broken")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        rec = self.only_record()
        self.assertFalse(rec["passed"])
        self.assertTrue(rec["trigger"]["ok"])
        self.assertEqual(rec["scenarios"][0], {"name": "rpcn-test__lint_broken",
                                               "result": "FAIL", "runs": 3, "passed": 0})

    def test_passing_record_kept_when_a_later_run_fails(self) -> None:
        self.assertEqual(self.run_evals().returncode, 0)
        passing = self.records()
        self.assertEqual(len(passing), 1)
        before = passing[0].read_text()
        self.agg.write_text(json.dumps(aggregate(fail_cases=3)))
        self.assertEqual(self.run_evals().returncode, 1)
        self.assertEqual(passing[0].read_text(), before)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(self.check_code(), 0)

    def test_later_passing_run_replaces_failing_one(self) -> None:
        self.agg.write_text(json.dumps(aggregate(fail_cases=3)))
        self.assertEqual(self.run_evals().returncode, 1)
        self.assertEqual(self.check_code(), 1)
        self.agg.write_text(json.dumps(aggregate()))
        self.assertEqual(self.run_evals().returncode, 0)
        self.assertEqual(self.check_code(), 0)

    def test_crashed_comparison_arm_fails_the_record(self) -> None:
        proc = self.run_evals("--with-compare", FAKE_ARMS_CRASHED="1")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        rec = self.only_record()
        self.assertFalse(rec["passed"])
        self.assertTrue(all(r["result"] == "PASS" for r in rec["scenarios"]))
        self.assertTrue(rec["trigger"]["ok"])

    def test_git_failure_exits_2_without_record(self) -> None:
        write(self.repo / ".git", "gitdir: /nonexistent/gitdir\n")
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("git", proc.stdout)
        self.assertEqual(self.calls(), "")
        self.assertEqual(self.records(), [])

    def test_skills_change_mid_run_exits_2_without_record(self) -> None:
        skill = self.repo / "skills/rpcn-test/SKILL.md"
        proc = self.run_evals(FAKE_TOUCH_SKILL=str(skill))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("skills changed", proc.stdout)
        self.assertEqual(self.records(), [])

    def test_missing_test_project_exits_2_before_any_run(self) -> None:
        proc = run(["uv", "run", str(RUN_EVALS), "--repo", str(self.repo),
                    "--test-project", str(self.tmp / "nope")], env=self.env)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.calls(), "")
        self.assertEqual(self.records(), [])

    def test_missing_claude_exits_2(self) -> None:
        env = {**self.env, "PATH": str(Path(shutil.which("uv")).parent)}
        if shutil.which("claude", path=env["PATH"]):
            self.skipTest("a real claude shares uv's folder")
        proc = run(["uv", "run", str(RUN_EVALS), "--repo", str(self.repo),
                    "--test-project", str(self.project)], env=env)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("claude", proc.stdout)
        self.assertEqual(self.records(), [])

    def test_no_trigger_result_exits_2_without_record(self) -> None:
        proc = self.run_evals(FAKE_NO_RESULT="1")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("run_scenarios", self.calls())
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
