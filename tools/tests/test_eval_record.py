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
FIXTURES = Path(__file__).resolve().parent / "fixtures"

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


FAKE_CLAUDE = """#!/usr/bin/env python3
# Fake claude for run_evals tests: --version, and `plugin eval ... [--case <name>] --json <out>`.
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(" ".join(argv) + "\\n")
if argv[:1] == ["--version"]:
    print("9.9.9 (Claude Code)")
    sys.exit(0)
opt = lambda name: argv[argv.index(name) + 1] if name in argv else None
out, case = opt("--json"), opt("--case")
print("fake eval progress line", flush=True)
if os.environ.get("FAKE_TOUCH_SKILL"):
    with open(os.environ["FAKE_TOUCH_SKILL"], "a") as f:
        f.write("changed\\n")
if os.environ.get("FAKE_NO_RESULT"):
    sys.exit(1)
data = json.load(open(os.environ["FAKE_AGGREGATE"]))
if case is not None:  # one case: a 0.5 run
    data["cases"] = [c for c in data["cases"] if c["name"] == case]
    data["costUsd"] = 0.5
ready = os.environ.get("FAKE_TRIGGER_WAIT_SIGINT")
if ready:  # wait for Ctrl-C, then write a partial result (the first 10 cases complete), like the real eval
    import signal, time
    def on_int(*_):
        for c in data["cases"][10:]:
            c["arms"]["with"] = c["arms"]["with"][:1]
        data["partial"], data["partialReason"] = True, "interrupted"
        time.sleep(0.5)  # longer than subprocess.run's 0.25 s before its SIGKILL
        open(out, "w").write(json.dumps(data))
        sys.exit(130)
    signal.signal(signal.SIGINT, on_int)
    open(ready, "w").write("x")
    time.sleep(60)
    sys.exit(1)
partial = os.environ.get("FAKE_TRIGGER_PARTIAL")
if partial:  # interrupted: cases after the first n have one run of their runs
    for c in data["cases"][int(partial):]:
        c["arms"]["with"] = c["arms"]["with"][:1]
    data["partial"], data["partialReason"] = True, "interrupted"
open(out, "w").write(json.dumps(data))
sys.exit(2 if partial else 0)
"""

FAKE_RUNNER = """# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# Fake run_scenarios.py: writes a synthetic results.json; --resume reuses the
# earlier runs with a verdict, FAKE_SCENARIO_INTERRUPT=<n> stops after n new runs.
import argparse, json, os, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--source")
p.add_argument("--runs", type=int)
p.add_argument("--jobs", type=int)
p.add_argument("--scenario", action="append", default=[])
p.add_argument("--resume")
a = p.parse_args()
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write("run_scenarios " + " ".join(sys.argv[1:]) + "\\n")
    f.write("RPCN_TEST_BINARIES=" + os.environ.get("RPCN_TEST_BINARIES", "") + "\\n")
fail = os.environ.get("FAKE_SCENARIO_FAIL", "")
budget = int(os.environ.get("FAKE_SCENARIO_INTERRUPT") or 10**6)
kept = {}
if a.resume:
    try:
        prev = json.loads((Path(a.resume) / "results.json").read_text())
    except (OSError, ValueError) as exc:
        print(f"error: --resume: unreadable: {exc}", file=sys.stderr)
        sys.exit(2)
    for e in prev["scenarios"]:
        kept[e["name"]] = {r["index"]: r for r in e["runs"] if isinstance(r.get("passed"), bool)}
k = 1
while (Path(__file__).parent / "runs" / f"t{k}").exists():
    k += 1
out = Path(__file__).parent / "runs" / f"t{k}"
out.mkdir(parents=True)
print(f"claude: 9.9.9; results: {out}", flush=True)
results = {"runs_per_scenario": a.runs, "scenarios": []}
if a.resume:
    results["resumed_from"] = a.resume
    results["reused_runs"] = sum(len(v) for v in kept.values())
save = lambda: (out / "results.json").write_text(json.dumps(results))
for name in a.scenario:
    runs = []
    entry = {"name": name, "runs": runs}
    results["scenarios"].append(entry)
    for i in range(1, a.runs + 1):
        if i in kept.get(name, {}):
            runs.append(kept[name][i])
            continue
        if budget == 0:
            results["passed"], results["error"] = False, "interrupted"
            save()
            print("interrupted; finished runs saved", file=sys.stderr)
            sys.exit(130)
        budget -= 1
        runs.append({"index": i, "dir": str(out / name / f"run-{i}"), "passed": name != fail,
                     "cost_usd": 0.25})
    entry["passed"] = all(r["passed"] for r in runs)
    entry["pass_count"] = sum(r["passed"] for r in runs)
    if "compare" in name:
        entry["comparison"] = {"winner": "ours", "judge": {"cost_usd": 0.5},
                               "runs": {"ours": runs, "bare": [{"cost_usd": 0.1}]}}
results["passed"] = all(s["passed"] for s in results["scenarios"])
crashed = 1 if os.environ.get("FAKE_ARMS_CRASHED") else 0
results["arms_crashed"] = crashed
save()
print("scenario progress line", flush=True)
print(f"results: {out / 'results.json'}")
sys.exit(0 if results["passed"] and not crashed else 1)
"""

FAKE_RUNNER_TESTS = '''# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fake tests/test_run_scenarios.py: passes unless FAKE_RUNNER_TESTS_FAIL is set."""
import os, sys
from pathlib import Path
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(f"runner_tests cwd={Path.cwd()}\\n")
if os.environ.get("FAKE_RUNNER_TESTS_FAIL"):
    sys.stderr.write("FAIL: test_visible_check (__main__.VisibleTest.test_visible_check)\\n")
    sys.stderr.write("Ran 120 tests in 1.0s\\n\\nFAILED (failures=1)\\n")
    sys.exit(1)
sys.stderr.write("Ran 120 tests in 1.0s\\n\\nOK\\n")
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


class RunEvalsHarness:
    """A fake repo and test project, a fake `claude` on PATH; mixed into the test classes."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        make_skills(self.repo)
        write(self.repo / ".claude-plugin/plugin.json", json.dumps({"version": "0.1.0"}))
        self.project = self.tmp / "test-project"
        write(self.project / "run_scenarios.py", FAKE_RUNNER)
        write(self.project / "tests/test_run_scenarios.py", FAKE_RUNNER_TESTS)
        for name in POSITIVES + NEGATIVES:  # the case folders the gate checks the result against
            write(self.repo / "evals" / name / "prompt.md", "x\n")
        write(self.project / "scenarios/rpcn-test__lint_broken/expect.toml",
              'skill = "rpcn-test"\n[status]\nstatus = "complete"\n')
        write(self.project / "scenarios/rpcn-test__compare_lint/expect.toml",
              'skill = "rpcn-test"\n[compare]\nenabled = true\n')
        write(self.repo / "tools/rpcn_versions.txt", "# pins\n4.100.0\n4.115.0\n")
        self.binaries = [write(self.repo / f".cache/rpcn/{v}/redpanda-connect", "fake\n")
                         for v in ("4.100.0", "4.115.0")]
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

    def only_record_path(self) -> Path:
        recs = self.records()
        self.assertEqual(len(recs), 1, recs)
        return recs[0]

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


class RunEvalsTests(RunEvalsHarness, unittest.TestCase):
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
                         [{"name": "rpcn-test__lint_broken", "result": "PASS", "runs": 2, "passed": 2}])
        self.assertIsNone(rec["compare"])
        self.assertEqual(rec["plugin_version"], "0.1.0")
        self.assertEqual(rec["claude_version"], "9.9.9 (Claude Code)")
        self.assertAlmostEqual(rec["cost_usd"], 3.5)  # trigger 3.0 + lint_broken 2 runs x 0.25
        for key in ("date", "git_head", "dirty"):
            self.assertIn(key, rec)
        # the documented command lines, and no comparison scenario by default
        calls = self.calls()
        self.assertIn("plugin eval . --ablation none --runs 2 --tag trigger --no-publish "
                      "--trust-plugin --concurrency 4 --json ", calls)
        self.assertIn(f"--source local:{self.repo.resolve()} --runs 2 --jobs 4 "
                      "--scenario rpcn-test__lint_broken", calls)
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

    def test_scenarios_lint_on_every_pinned_binary(self) -> None:
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        want = ":".join(str(b.resolve()) for b in self.binaries)
        self.assertIn(f"RPCN_TEST_BINARIES={want}\n", self.calls())
        self.assertIn(f"] scenarios: lint on {' '.join(str(b.resolve()) for b in self.binaries)}", proc.stdout)

    def test_missing_pinned_binary_is_a_setup_error(self) -> None:
        self.binaries[1].unlink()
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        out = proc.stdout + proc.stderr
        self.assertIn("4.115.0/redpanda-connect", out)
        self.assertIn("uv run tools/fetch_rpcn.py", out)
        self.assertNotIn("run_scenarios", self.calls())
        self.assertEqual(self.records(), [])

    def test_runner_tests_run_first(self) -> None:
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        lines = self.calls().splitlines()
        self.assertEqual(lines[0], f"runner_tests cwd={self.project.resolve()}")
        self.assertIn("] runner tests: ok (Ran 120 tests", proc.stdout)
        # and before the trigger suite, the only paid step that comes first
        self.assertLess(proc.stdout.index("] runner tests: ok"), proc.stdout.index("] trigger:"))

    def test_runner_tests_fail_exits_2_before_any_paid_step(self) -> None:
        proc = self.run_evals(FAKE_RUNNER_TESTS_FAIL="1")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("runner tests failed (exit 1): "
                      "test_visible_check (__main__.VisibleTest.test_visible_check)", proc.stdout)
        calls = self.calls()
        self.assertIn("runner_tests", calls)
        self.assertNotIn("plugin eval", calls)
        self.assertNotIn("run_scenarios", calls)
        self.assertEqual(self.records(), [])

    def test_missing_runner_tests_exits_2(self) -> None:
        (self.project / "tests/test_run_scenarios.py").unlink()
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("tests/test_run_scenarios.py", proc.stdout)
        self.assertEqual(self.calls(), "")
        self.assertEqual(self.records(), [])

    def test_gate_exit_2_stops_before_scenarios_without_record(self) -> None:
        # a case folder with no result in the trigger output: a suite problem, gate exit 2
        write(self.repo / "evals/rpcn-test__miss_dropped/prompt.md", "x\n")
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("error: eval_gate exited 2: missing case rpcn-test__miss_dropped", proc.stdout)
        self.assertNotIn("run_scenarios", self.calls())
        self.assertEqual(self.records(), [])

    def test_runs_option_passes_through(self) -> None:
        self.agg.write_text(json.dumps(aggregate(runs=4)))
        proc = self.run_evals("--runs", "4")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("--runs 4 --tag trigger", self.calls())
        self.assertEqual(self.only_record()["scenarios"][0]["runs"], 4)

    def test_concurrency_and_jobs_pass_through(self) -> None:
        proc = self.run_evals("--concurrency", "2", "--jobs", "8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertIn("--trust-plugin --concurrency 2 --json ", calls)
        self.assertIn("--runs 2 --jobs 8 --scenario", calls)

    def test_concurrency_and_jobs_out_of_range_exit_2(self) -> None:
        for flag, value in (("--concurrency", "0"), ("--concurrency", "9"), ("--jobs", "0"), ("--jobs", "9")):
            with self.subTest(flag=flag, value=value):
                proc = self.run_evals(flag, value)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn(f"{flag} must be from 1 to 8", proc.stderr)
        self.assertEqual(self.calls(), "")
        self.assertEqual(self.records(), [])

    def test_with_compare_adds_comparison_scenarios(self) -> None:
        proc = self.run_evals("--with-compare")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("--scenario rpcn-test__compare_lint", self.calls())
        rec = self.only_record()
        self.assertEqual(rec["compare"], {"rpcn-test__compare_lint": "ours"})
        self.assertEqual(len(rec["scenarios"]), 2)
        # trigger 3.0 + lint_broken 0.5 + compare (0.5 ours + 0.1 bare + 0.5 judge), at 2 runs
        self.assertAlmostEqual(rec["cost_usd"], 4.6)

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
                                               "result": "FAIL", "runs": 2, "passed": 0})

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
        # only the free runner tests ran, no paid step
        self.assertEqual(self.calls(), f"runner_tests cwd={self.project.resolve()}\n")
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


def trigger_sample() -> dict:
    """A trimmed real `claude plugin eval --json` result (story 8.5): 6 cases x 2 runs."""
    return json.loads((FIXTURES / "trigger-sample.json").read_text())


class TriggerMergeTests(unittest.TestCase):
    """The per-case reuse and merge, on the real result shape."""

    def setUp(self) -> None:
        import run_evals
        self.re = run_evals
        self.data = trigger_sample()
        self.names = [c["name"] for c in self.data["cases"]]

    def gate(self, data: dict) -> tuple[int, dict]:
        import eval_gate
        try:
            return eval_gate.gate(data, 0.9, 2, set(self.names))
        except eval_gate.GateError as exc:
            return 2, {"error": str(exc)}

    def test_complete_cases_of_the_real_shape(self) -> None:
        # runsPerCase says 3 (the case default) while --runs 2 ran 2: --runs decides
        self.assertEqual(self.data["cases"][0]["runsPerCase"], 3)
        self.assertEqual(set(self.re.complete_cases(self.data, 2, self.names)), set(self.names))
        self.assertEqual(self.re.complete_cases(self.data, 3, self.names), {})

    def test_short_or_half_written_case_is_incomplete(self) -> None:
        data = trigger_sample()
        data["cases"][0]["arms"]["with"] = data["cases"][0]["arms"]["with"][:1]  # one run missing
        data["cases"][1]["arms"]["with"][1]["graders"] = []  # a run with no grader result
        del data["cases"][2]["arms"]["with"][0]["passed"]  # a run with no verdict
        done = self.re.complete_cases(data, 2, self.names)
        self.assertEqual(set(done), set(self.names[3:]))

    def test_api_error_run_is_incomplete(self) -> None:
        data = trigger_sample()
        data["cases"][0]["arms"]["with"][0]["error"] = "API Error: 529 overloaded"  # graders kept
        self.assertTrue(data["cases"][0]["arms"]["with"][0]["graders"])
        done = self.re.complete_cases(data, 2, self.names)
        self.assertNotIn(self.names[0], done)
        self.assertEqual(len(done), 5)

    def test_failed_case_counts_as_complete(self) -> None:
        data = trigger_sample()
        run = data["cases"][0]["arms"]["with"][0]
        run["passed"] = False
        run["graders"][0]["passed"] = False
        self.assertIn(self.names[0], self.re.complete_cases(data, 2, self.names))

    def test_unreadable_or_foreign_json_has_no_complete_case(self) -> None:
        for bad in (None, [], {"schemaVersion": 2, "cases": self.data["cases"]}, {"schemaVersion": 1}):
            self.assertEqual(self.re.complete_cases(bad, 2, self.names), {})

    def test_merged_json_is_scored_like_one_run(self) -> None:
        whole = trigger_sample()
        part1 = trigger_sample()  # interrupted: the last two cases have one run
        for c in part1["cases"][4:]:
            c["arms"]["with"] = c["arms"]["with"][:1]
        part1["partial"], part1["costUsd"] = True, 0.6
        done = self.re.complete_cases(part1, 2, self.names)
        self.assertEqual(len(done), 4)
        half = self.re.merge_trigger(part1, done, 0.6, self.names, 2)
        self.assertTrue(half["partial"])
        self.assertIn("2 case(s) incomplete", half["partialReason"])
        self.assertEqual(self.gate(half)[0], 2)  # never scored while a case is missing
        cases = {**done, **{c["name"]: c for c in whole["cases"][4:]}}
        merged = self.re.merge_trigger(part1, cases, 0.6 + 0.5 + 0.5, self.names, 2)
        self.assertFalse(merged["partial"])
        self.assertNotIn("partialReason", merged)
        self.assertEqual(merged["costUsd"], 1.6)
        self.assertEqual([c["name"] for c in merged["cases"]], self.names)
        self.assertEqual(self.gate(merged), self.gate(whole))
        self.assertEqual(self.gate(merged)[0], 0)
        self.assertEqual(merged["schemaVersion"], 1)
        self.assertEqual(merged["suite"], whole["suite"])

    def test_atomic_json_write_leaves_no_temp_file(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        target = tmp / "state.json"
        self.re.write_json_atomic(target, {"a": 1})
        self.re.write_json_atomic(target, {"a": 2})
        self.assertEqual(json.loads(target.read_text()), {"a": 2})
        self.assertEqual([p.name for p in tmp.iterdir()], ["state.json"])


class ResumeTests(RunEvalsHarness, unittest.TestCase):
    """--resume, one test per row of the plan's I/O matrix; fake claude and runner only."""

    def setUp(self) -> None:
        super().setUp()
        self.agg.write_text(json.dumps(aggregate(runs=2)))  # as many runs as --runs, like the real eval

    def state_dir(self) -> Path:
        return self.repo / "evals/results/.resume" / eval_record.skills_hash(self.repo)[:12]

    def state(self) -> dict:
        return json.loads((self.state_dir() / "state.json").read_text())

    def calls_after(self, mark: int) -> str:
        return self.calls()[mark:]

    def assert_refused(self, proc: subprocess.CompletedProcess, mark: int, *needles: str) -> None:
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        for n in needles:
            self.assertIn(n, proc.stdout)
        later = self.calls_after(mark)
        self.assertNotIn("plugin eval", later)  # no paid step
        self.assertNotIn("run_scenarios", later)

    def interrupt_in_scenarios(self, **env: str) -> int:
        """A run stopped after 1 of the 2 scenario runs; returns the log mark after it."""
        proc = self.run_evals(FAKE_SCENARIO_INTERRUPT="1", **env)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)  # the runner exited 130
        self.assertEqual(self.records(), [])
        return len(self.calls())

    def test_fresh_run_writes_state_and_no_resumed(self) -> None:
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("resumed", self.only_record())
        st = self.state()
        self.assertEqual(st["skills_hash"], eval_record.skills_hash(self.repo))
        self.assertEqual((st["runs"], st["with_compare"]), (2, False))
        self.assertEqual(st["scenarios"], ["rpcn-test__lint_broken"])
        self.assertEqual(st["trigger_cases"], sorted(NEGATIVES + POSITIVES))
        self.assertEqual(st["runs_dir"], str(self.project / "runs" / "t1"))
        self.assertIn(f"--json {self.state_dir() / 'trigger.json'}", self.calls())
        self.assertTrue((self.state_dir() / "trigger.json").is_file())
        self.assertEqual(sorted(p.name for p in self.state_dir().iterdir()), ["state.json", "trigger.json"])
        # the state folder is never committed: this repo's .gitignore covers it
        shutil.copy(TOOLS.parent / ".gitignore", self.repo / ".gitignore")
        git_init(self.repo)
        tracked = run(["git", "-C", str(self.repo), "ls-files", "evals/results"]).stdout
        self.assertNotIn(".resume", tracked)

    def test_interrupted_in_the_scenarios(self) -> None:
        one_go = self.tmp / "one-go.json"
        self.assertEqual(self.run_evals().returncode, 0)
        shutil.copy(self.only_record_path(), one_go)
        for rec in self.records():
            rec.unlink()
        shutil.rmtree(self.project / "runs")
        mark = self.interrupt_in_scenarios()
        self.assertEqual(self.state()["runs_dir"], str(self.project / "runs" / "t1"))
        proc = self.run_evals("--resume")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        later = self.calls_after(mark)
        self.assertNotIn("plugin eval", later)  # the trigger stage is reused
        self.assertIn(f"--resume {self.project / 'runs' / 't1'}", later)
        rec = self.only_record()
        self.assertEqual(rec["resumed"], {
            "state_dir": f"evals/results/.resume/{eval_record.skills_hash(self.repo)[:12]}",
            "runs_dir": "runs/t1", "trigger_cases": 14, "scenario_runs": 1})
        # the acceptance criterion: the check takes it exactly like the run done in one go
        self.assertEqual(self.check_code(), 0)
        whole = json.loads(one_go.read_text())
        for key in ("schema", "skills_hash", "trigger", "scenarios", "compare", "passed", "cost_usd"):
            self.assertEqual(rec[key], whole[key], key)

    def test_interrupted_in_the_trigger_stage(self) -> None:
        proc = self.run_evals(FAKE_TRIGGER_PARTIAL="10")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)  # gate: partial run
        mark = len(self.calls())
        proc = self.run_evals("--resume")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        later = self.calls_after(mark)
        names = POSITIVES + NEGATIVES
        for name in names[10:]:
            self.assertIn(f"--case {name} --json", later)
        for name in names[:10]:
            self.assertNotIn(f"--case {name} ", later)
        self.assertEqual(later.count("plugin eval"), 4)
        merged = json.loads((self.state_dir() / "trigger.json").read_text())
        self.assertFalse(merged["partial"])
        self.assertEqual(sorted(c["name"] for c in merged["cases"]), sorted(names))
        rec = self.only_record()
        self.assertTrue(rec["passed"])
        self.assertEqual(rec["trigger"]["runs_total"], 28)
        self.assertEqual(rec["resumed"]["trigger_cases"], 10)
        self.assertEqual(rec["resumed"]["scenario_runs"], 0)
        self.assertIsNone(rec["resumed"]["runs_dir"])
        self.assertAlmostEqual(rec["cost_usd"], 3.0 + 4 * 0.5 + 0.5)  # partial + 4 cases + scenarios
        self.assertEqual(self.check_code(), 0)

    def test_no_readable_trigger_json_reruns_the_whole_stage(self) -> None:
        self.assertEqual(self.run_evals(FAKE_NO_RESULT="1").returncode, 2)
        mark = len(self.calls())
        proc = self.run_evals("--resume")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        later = self.calls_after(mark)
        self.assertEqual(later.count("plugin eval"), 1)
        self.assertNotIn("--case", later)
        self.assertEqual(self.only_record()["resumed"]["trigger_cases"], 0)

    def test_failed_run_is_reused_as_failed(self) -> None:
        mark = self.interrupt_in_scenarios(FAKE_SCENARIO_FAIL="rpcn-test__lint_broken")
        proc = self.run_evals("--resume")  # nothing fails now, but run 1 did
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("plugin eval", self.calls_after(mark))
        rec = self.only_record()
        self.assertFalse(rec["passed"])
        self.assertEqual(rec["scenarios"], [{"name": "rpcn-test__lint_broken", "result": "FAIL",
                                             "runs": 2, "passed": 1}])
        self.assertEqual(self.check_code(), 1)

    def test_runs_dir_with_no_results_runs_every_scenario_again(self) -> None:
        self.interrupt_in_scenarios()
        (self.project / "runs" / "t1" / "results.json").unlink()  # killed before its first save
        mark = len(self.calls())
        proc = self.run_evals("--resume")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("--resume", self.calls_after(mark))
        self.assertEqual(self.only_record()["resumed"]["scenario_runs"], 0)

    def test_mismatches_are_refused_by_name(self) -> None:
        self.interrupt_in_scenarios()
        cases = [
            (("--runs", "3"), "--runs differs (saved 2, now 3)"),
            (("--with-compare",), "--with-compare differs (saved False, now True)"),
        ]
        for extra, needle in cases:
            with self.subTest(extra=extra):
                mark = len(self.calls())
                self.assert_refused(self.run_evals("--resume", *extra), mark, needle,
                                    "run without --resume to start over")

    def test_trigger_case_file_edit_mismatch(self) -> None:
        self.interrupt_in_scenarios()
        write(self.repo / "evals" / POSITIVES[2] / "prompt.md", "edited\n")
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark,
                            f"trigger case files differ (changed {POSITIVES[2]})")

    def test_ctrl_c_in_the_trigger_stage_keeps_the_partial_json(self) -> None:
        import signal
        ready = self.tmp / "eval-started"
        proc = subprocess.Popen(
            ["uv", "run", str(RUN_EVALS), "--repo", str(self.repo), "--test-project", str(self.project)],
            env={**self.env, "FAKE_TRIGGER_WAIT_SIGINT": str(ready)}, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True)
        for _ in range(300):
            if ready.exists():
                break
            time.sleep(0.05)
        self.assertTrue(ready.exists())
        os.killpg(proc.pid, signal.SIGINT)  # Ctrl-C reaches the whole foreground group
        out, _ = proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, 130, out)
        saved = json.loads((self.state_dir() / "trigger.json").read_text())
        self.assertTrue(saved["partial"])
        mark = len(self.calls())
        proc2 = self.run_evals("--resume")
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)
        self.assertEqual(self.calls_after(mark).count("plugin eval"), 4)
        self.assertEqual(self.only_record()["resumed"]["trigger_cases"], 10)

    def test_scenario_list_mismatch(self) -> None:
        self.interrupt_in_scenarios()
        write(self.project / "scenarios/rpcn-test__new/expect.toml", 'skill = "rpcn-test"\n')
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark,
                            "scenario list differs (added rpcn-test__new)")

    def test_trigger_case_list_mismatch(self) -> None:
        self.interrupt_in_scenarios()
        shutil.rmtree(self.repo / "evals" / NEGATIVES[0])
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark,
                            f"trigger case list differs (dropped {NEGATIVES[0]})")

    def test_test_project_head_and_status_mismatch(self) -> None:
        git_init(self.project)
        self.interrupt_in_scenarios()
        write(self.project / "scenarios/rpcn-test__lint_broken/notes.txt", "x\n")  # untracked
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark, "test project `git status --porcelain` differs")
        subprocess.run(["git", "-C", str(self.project), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.project), "commit", "-q", "-m", "x"], check=True,
                       capture_output=True)
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark, "test project HEAD differs")

    def test_full_skills_hash_mismatch(self) -> None:
        self.interrupt_in_scenarios()
        path = self.state_dir() / "state.json"
        st = json.loads(path.read_text())
        st["skills_hash"] = st["skills_hash"][:12] + "0" * 52  # same prefix, other hash
        path.write_text(json.dumps(st))
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark, "skills hash differs")

    def test_other_skills_hash_has_nothing_to_resume(self) -> None:
        self.interrupt_in_scenarios()
        write(self.repo / "skills/rpcn-test/SKILL.md", "---\nname: rpcn-test\n---\nbody 2\n")
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark, "nothing to resume for skills hash")

    def test_no_state_is_nothing_to_resume(self) -> None:
        proc = self.run_evals("--resume")
        self.assert_refused(proc, 0, "nothing to resume")
        self.assertEqual(self.records(), [])

    def test_truncated_results_json_is_refused(self) -> None:
        self.interrupt_in_scenarios()
        results = self.project / "runs" / "t1" / "results.json"
        results.write_text(results.read_text()[:20])  # killed mid-save, before saves were atomic
        mark = len(self.calls())
        self.assert_refused(self.run_evals("--resume"), mark, "is unreadable")

    def test_fresh_run_after_an_interruption_starts_over(self) -> None:
        self.interrupt_in_scenarios()
        mark = len(self.calls())
        proc = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        later = self.calls_after(mark)
        self.assertIn("plugin eval", later)
        self.assertNotIn("--resume", later)
        self.assertNotIn("resumed", self.only_record())
        self.assertEqual(self.state()["runs_dir"], str(self.project / "runs" / "t2"))

    def test_help_shows_resume(self) -> None:
        proc = run(["uv", "run", str(RUN_EVALS), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--resume", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
