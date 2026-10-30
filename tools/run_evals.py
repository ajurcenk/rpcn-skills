# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Run every eval for the current skill content and write the eval record (R12, AD-14).

Steps, in order, one progress line each (`[run_evals +<s>s] ...`); each child's
own output passes through live:

  1. the skills hash (tools/eval_record.py)
  2. claude plugin eval . --ablation none --runs <n> --tag trigger
         --no-publish --trust-plugin --json <tmp>
  3. uv run tools/eval_gate.py <tmp>
  4. in the test project: uv run run_scenarios.py --source local:<this repo>
         --runs <n> --scenario <s>... for every scenario that is not a
         comparison ([compare] enabled = true in expect.toml), plus the
         comparison scenarios with --with-compare (about +$4)

Then it re-checks the skills hash and writes
`evals/results/<YYYY-MM-DD>-<skills-hash12>.json` when the run passed, or
`evals/results/<YYYY-MM-DD>-<skills-hash12>.failed-<HHMMSS>.json` when it did
not (the check ignores that name, so a failed re-run never replaces a passing
record):

  {"schema": 1, "skills_hash", "date", "git_head", "dirty", "plugin_version",
   "claude_version", "trigger": <gate JSON>,
   "scenarios": [{"name", "result": "PASS"|"FAIL", "runs", "passed"}],
   "compare": {<scenario>: <winner>} | null, "passed": bool, "cost_usd"}

`scenarios[].runs` is the number of runs and `scenarios[].passed` the number
that passed. The top-level `passed` is true only when the gate is ok, every
scenario passed, and run_scenarios.py exited 0 with top-level `passed` true and
no crashed comparison arm. The record is written even when it fails. A record
can pass only with --runs >= 3 (eval_gate requires 3 runs per case); fewer is
a smoke run.

Exit codes:
  0  passed
  1  not passed (the record is still written)
  2  setup error, no record: no `claude` or `uv`, a missing test project,
     the trigger eval wrote no result, run_scenarios.py reported a setup
     error, or the skills hash changed while the run was in progress

A default run costs about $4.20 (trigger suite ~$3.30, scenarios ~$0.90).

Run: uv run tools/run_evals.py [--test-project ../rpcn-test-skills] [--runs 3] [--with-compare]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

import eval_record

TOOLS_DIR = Path(__file__).resolve().parent
GATE = TOOLS_DIR / "eval_gate.py"
START = time.monotonic()


class SetupError(Exception):
    """Exit 2, no record."""


def say(msg: str) -> None:
    print(f"[run_evals +{time.monotonic() - START:.0f}s] {msg}", flush=True)


def is_compare(expect: Path) -> bool:
    """True when expect.toml sets [compare] enabled = true."""
    text = expect.read_text(encoding="utf-8")
    try:
        import tomllib  # Python >= 3.11
    except ModuleNotFoundError:
        section = None
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line.startswith("["):
                section = line.strip("[]").strip()
            elif section == "compare" and re.fullmatch(r"enabled\s*=\s*true", line):
                return True
        return False
    data = tomllib.loads(text)
    compare = data.get("compare")
    return isinstance(compare, dict) and compare.get("enabled") is True


def list_scenarios(project: Path, with_compare: bool) -> list[str]:
    names = []
    for expect in sorted((project / "scenarios").glob("*/expect.toml")):
        if with_compare or not is_compare(expect):
            names.append(expect.parent.name)
    return names


def git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, check=False)
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def plugin_version(root: Path) -> str | None:
    try:
        data = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("version") if isinstance(data, dict) else None


def claude_version() -> str | None:
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return None
    return out.stdout.strip() or None


def run_trigger(root: Path, runs: int, out_json: Path) -> float | None:
    """Run the trigger suite; return its cost. SetupError when no result file appears."""
    cmd = ["claude", "plugin", "eval", ".", "--ablation", "none", "--runs", str(runs),
           "--tag", "trigger", "--no-publish", "--trust-plugin", "--json", str(out_json)]
    say(f"trigger: {' '.join(cmd)}")
    code = subprocess.run(cmd, cwd=root, check=False).returncode
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"claude plugin eval exited {code} and wrote no readable result: {exc}")
    cost = data.get("costUsd") if isinstance(data, dict) else None
    say(f"trigger: done (exit {code}, cost ${cost if isinstance(cost, (int, float)) else '?'})")
    return cost if isinstance(cost, (int, float)) else None


def run_gate(out_json: Path) -> dict:
    proc = subprocess.run(["uv", "run", str(GATE), str(out_json)],
                          stdout=subprocess.PIPE, text=True, check=False)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = None
    if not isinstance(result, dict):
        result = {"ok": False, "error": f"eval_gate exited {proc.returncode} with no JSON"}
    if proc.returncode != 0:
        result["ok"] = False
    say(f"gate: accuracy={result.get('accuracy')} ok={str(result.get('ok')).lower()}"
        f" exit={proc.returncode}" + (f" error={result['error']}" if result.get("error") else ""))
    return result


def run_scenarios(root: Path, project: Path, names: list[str], runs: int) -> tuple[dict, bool]:
    """Run the scenarios; return (the parsed results.json, whether the whole run passed).

    The run passed only when run_scenarios.py exited 0, its top-level `passed`
    is true and no comparison arm crashed."""
    cmd = ["uv", "run", "run_scenarios.py", "--source", f"local:{root}", "--runs", str(runs)]
    for name in names:
        cmd += ["--scenario", name]
    say(f"scenarios: {' '.join(cmd)}")
    results_path = None
    proc = subprocess.Popen(cmd, cwd=project, stdout=subprocess.PIPE, text=True, bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        m = re.match(r"results: (.+results\.json)\s*$", line)
        if m:
            results_path = Path(m.group(1))
    code = proc.wait()
    if code == 2:
        raise SetupError("run_scenarios.py reported a setup error (exit 2)")
    if results_path is None:
        raise SetupError(f"run_scenarios.py exited {code} without naming its results.json")
    if not results_path.is_absolute():
        results_path = project / results_path
    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"cannot read {results_path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
        raise SetupError(f"{results_path} has no scenarios[] list")
    crashed = data.get("arms_crashed")
    ok = code == 0 and data.get("passed") is True and not crashed
    if not ok:
        say(f"scenarios: run not passed (exit {code}, passed={data.get('passed')}, "
            f"arms_crashed={crashed})")
    return data, ok


def _num(v: object) -> float:
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def summarize(results: dict, names: list[str]) -> tuple[list[dict], dict, float]:
    """(scenario rows, winners by comparison scenario, scenario cost)."""
    rows, winners, cost = [], {}, 0.0
    seen = set()
    for sc in results["scenarios"]:
        if not isinstance(sc, dict):
            continue
        runs = sc.get("runs") if isinstance(sc.get("runs"), list) else []
        passed = sc.get("passed") is True
        rows.append({"name": sc.get("name"), "result": "PASS" if passed else "FAIL",
                     "runs": len(runs),
                     "passed": sum(1 for r in runs if isinstance(r, dict) and r.get("passed") is True)})
        seen.add(sc.get("name"))
        comp = sc.get("comparison")
        if isinstance(comp, dict):
            winners[sc.get("name")] = comp.get("winner")
            for arm_runs in (comp.get("runs") or {}).values():
                cost += sum(_num(r.get("cost_usd")) for r in arm_runs if isinstance(r, dict))
            judge = comp.get("judge")
            if isinstance(judge, dict):
                cost += _num(judge.get("cost_usd"))
        else:
            cost += sum(_num(r.get("cost_usd")) for r in runs if isinstance(r, dict))
    for name in names:  # a requested scenario with no result counts as a failure
        if name not in seen:
            rows.append({"name": name, "result": "FAIL", "runs": 0, "passed": 0})
    for row in rows:
        say(f"scenarios: {row['name']} {row['result']} {row['passed']}/{row['runs']}")
    return rows, winners, cost


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--test-project", type=Path, default=None,
                   help="the rpcn-test-skills folder (default: ../rpcn-test-skills beside this repo)")
    p.add_argument("--runs", type=int, default=3, help="runs per trigger case and scenario (default 3); a record can pass "
                        "only with 3 or more, fewer is a smoke run that never passes")
    p.add_argument("--with-compare", action="store_true",
                   help="also run the comparison (benchmark) scenarios, about +$4")
    p.add_argument("--repo", type=Path, default=eval_record.REPO_ROOT, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.runs < 1:
        p.error("--runs must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo.resolve()
    project = (args.test_project or root.parent / "rpcn-test-skills").resolve()
    try:
        for tool in ("claude", "uv"):
            if shutil.which(tool) is None:
                raise SetupError(f"`{tool}` is not on PATH")
        if not (project / "run_scenarios.py").is_file():
            raise SetupError(f"test project not found: {project} has no run_scenarios.py")
        names = list_scenarios(project, args.with_compare)
        if not names:
            raise SetupError(f"no scenarios to run in {project / 'scenarios'}")

        before = eval_record.skills_hash(root)
        say(f"skills: hash {before[:eval_record.PREFIX_LEN]} "
            f"({len(eval_record.skill_files(root))} files)")
        record = {
            "schema": eval_record.SCHEMA, "skills_hash": before,
            "date": date.today().isoformat(),
            "git_head": git(root, "rev-parse", "HEAD"),
            "dirty": None, "plugin_version": plugin_version(root),
            "claude_version": claude_version(),
        }
        status = git(root, "status", "--porcelain", "--", eval_record.SKILLS_DIR)
        record["dirty"] = None if status is None else bool(status)

        with tempfile.TemporaryDirectory(prefix="run_evals-") as tmp:
            out_json = Path(tmp) / "trigger.json"
            trigger_cost = run_trigger(root, args.runs, out_json)
            gate = run_gate(out_json)
        results, scenarios_ok = run_scenarios(root, project, names, args.runs)
        rows, winners, scenario_cost = summarize(results, names)

        after = eval_record.skills_hash(root)
        if after != before:
            raise SetupError(f"skills changed during the run ({before[:12]} -> {after[:12]}); "
                             "no record written, run again")
    except (SetupError, eval_record.HashError) as exc:
        say(f"error: {exc}")
        return 2

    record["trigger"] = gate
    record["scenarios"] = rows
    record["compare"] = winners if args.with_compare else None
    record["passed"] = (gate.get("ok") is True and scenarios_ok and bool(rows)
                        and all(r["result"] == "PASS" for r in rows))
    record["cost_usd"] = round(_num(trigger_cost) + scenario_cost, 4)

    path = eval_record.record_path(root, record["date"], before)
    if not record["passed"]:
        # Never overwrite a passing record: a failed run gets a name the check ignores.
        stamp = datetime.now().strftime("%H%M%S")
        path = path.with_name(f"{path.stem}.failed-{stamp}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    say(f"record: {path.relative_to(root).as_posix()} passed={str(record['passed']).lower()} "
        f"cost=${record['cost_usd']:.2f}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
