# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Run every eval for the current skill content and write the eval record (R12, AD-14).

Steps, in order, one progress line each (`[run_evals +<s>s] ...`); each child's
own output passes through live:

  0. in the test project: uv run tests/test_run_scenarios.py (the runner's
         own unit tests, free); a failure stops the run before any paid step
  1. the skills hash (tools/eval_record.py)
  2. claude plugin eval . --ablation none --runs <n> --tag trigger
         --no-publish --trust-plugin --concurrency <c> --json <state>/trigger.json
  3. uv run tools/eval_gate.py <state>/trigger.json --cases-dir <this repo>/evals
  4. in the test project: uv run run_scenarios.py --source local:<this repo>
         --runs <n> --jobs <j> --scenario <s>... for every scenario that is not a
         comparison ([compare] enabled = true in expect.toml), plus the
         comparison scenarios with --with-compare (about +$12)

Then it re-checks the skills hash and writes
`evals/results/<YYYY-MM-DD>-<skills-hash12>.json` when the run passed, or
`evals/results/<YYYY-MM-DD>-<skills-hash12>.failed-<HHMMSS>.json` when it did
not (the check ignores that name, so a failed re-run never replaces a passing
record):

  {"schema": 1, "skills_hash", "date", "git_head", "dirty", "plugin_version",
   "claude_version", "trigger": <gate JSON>,
   "scenarios": [{"name", "result": "PASS"|"FAIL", "runs", "passed"}],
   "compare": {<scenario>: <winner>} | null, "passed": bool, "cost_usd"}

plus, on a resumed run only, "resumed": {"state_dir", "runs_dir",
"trigger_cases", "scenario_runs"} (the state folder, the earlier runs folder
whose finished runs were reused or null, and how many trigger cases and
scenario runs were reused).

Resume. Every run keeps its state in `evals/results/.resume/<skills-hash12>/`
(gitignored): `state.json` (written atomically) and the trigger JSON. With
--resume the run continues the last run for the current skills hash, reusing
only work that is provably the same, passed or failed alike:

  - each trigger case with --runs complete runs (every run has its grader
    results) in the saved trigger JSON; only the other cases run, one
    `claude plugin eval --case <name>` each, merged into that JSON (costUsd
    summed; partial only while a case is incomplete). With no readable saved
    JSON, or no complete case in it, the whole trigger stage runs again.
  - each finished scenario run: run_scenarios.py --resume <the earlier runs
    folder> copies them in unchanged and runs only the rest.

It refuses (exit 2, naming each mismatch, before any paid step) when the full
skills hash, the test project's HEAD or `git status --porcelain`, --runs,
--with-compare, the scenario list, the trigger case list or any trigger
case's files (a hash per case folder) differ from the
saved state, when no state exists for this hash, or when the earlier
results.json is unreadable. It never silently starts over. Without --resume a
run starts fresh and overwrites the state.

`scenarios[].runs` is the number of runs and `scenarios[].passed` the number
that passed. The top-level `passed` is true only when the gate is ok, every
scenario passed, and run_scenarios.py exited 0 with top-level `passed` true and
no crashed comparison arm. The record is written even when it fails. A record
can pass only with --runs >= 2 (eval_gate requires 2 runs per case); fewer is
a smoke run.

Exit codes:
  0  passed
  1  not passed (the record is still written)
  2  setup error, no record: no `claude` or `uv`, a missing test project,
     the test project's own tests failed, the trigger eval wrote no result,
     eval_gate exited 2 (a suite problem, such as a missing or extra case), run_scenarios.py reported a setup
     error, the skills hash changed while the run was in progress, or
     --resume could not resume (no state, a mismatch, an unreadable results.json)
  130 interrupted (Ctrl-C), no record; a running run_scenarios.py is
     sent SIGINT and terminated if it does not exit within 15 s

A default run costs about $6.40 (trigger suite ~$3.50, scenarios ~$2.90).
Sessions run in parallel: --concurrency (default 4) trigger sessions at once,
then --jobs (default 4) scenario runs at once; the stages stay in order and
comparison scenarios still run one at a time. All sessions share one account
rate limit. --concurrency 1 --jobs 1 is the old sequential run (about 58 min).

Run: uv run tools/run_evals.py [--test-project ../rpcn-test-skills] [--runs 2] [--with-compare]
                               [--concurrency 4] [--jobs 4] [--resume]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import eval_gate
import eval_record
import fetch_rpcn

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_PARALLEL = 4  # default --concurrency and --jobs
MAX_PARALLEL = 8  # the 1..8 range of both flags
GATE = TOOLS_DIR / "eval_gate.py"
RESUME_DIR = Path("evals") / "results" / ".resume"  # gitignored through evals/results/*/
STATE_SCHEMA = 1
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


def write_json_atomic(path: Path, data: object) -> None:
    """Write JSON to a temp file beside `path`, then os.replace it into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_json(path: Path) -> object | None:
    """The parsed JSON at `path`, or None when it is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def trigger_cmd(runs: int, out_json: Path, concurrency: int, case: str | None = None) -> list[str]:
    cmd = ["claude", "plugin", "eval", ".", "--ablation", "none", "--runs", str(runs),
           "--tag", "trigger", "--no-publish", "--trust-plugin", "--concurrency", str(concurrency)]
    if case is not None:
        cmd += ["--case", case]
    return cmd + ["--json", str(out_json)]


def run_trigger(root: Path, runs: int, out_json: Path, concurrency: int = DEFAULT_PARALLEL,
                case: str | None = None) -> float | None:
    """Run the trigger suite (or one case of it); return its cost. SetupError
    when no result file appears."""
    out_json.unlink(missing_ok=True)  # never read an earlier run's file as this one's
    cmd = trigger_cmd(runs, out_json, concurrency, case)
    say(f"trigger: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=root)
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        # SIGINT with a grace period, so the eval can write its partial --json
        # into the state folder for --resume; then stop as before.
        stop_child(proc)
        raise
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"claude plugin eval exited {code} and wrote no readable result: {exc}")
    cost = data.get("costUsd") if isinstance(data, dict) else None
    say(f"trigger: done (exit {code}, cost ${cost if isinstance(cost, (int, float)) else '?'})")
    return cost if isinstance(cost, (int, float)) else None


def trigger_case_names(root: Path) -> list[str]:
    """The trigger case list: the <skill>__trigger_* and <skill>__miss_* folders
    in evals/, the same list eval_gate checks the result against."""
    folder = root / "evals"
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_dir() and eval_gate.kind_of(p.name))


def trigger_case_hashes(root: Path, names: list[str]) -> dict[str, str]:
    """A sha256 per trigger case over its files under evals/<case>/ (path, NUL,
    file sha256, newline, in path order; no __pycache__), like the skills hash,
    so an edited prompt or grader is seen."""
    out = {}
    for name in names:
        folder = root / "evals" / name
        h = hashlib.sha256()
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            rel = path.relative_to(folder).as_posix()
            if eval_record._excluded(rel):
                continue
            h.update(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
        out[name] = h.hexdigest()
    return out


def run_complete(run: object) -> bool:
    """A trigger run that finished: a verdict and its grader results, and no
    API error (eval_gate: then the graders never really ran)."""
    if not isinstance(run, dict) or not isinstance(run.get("passed"), bool):
        return False
    error = run.get("error")
    if isinstance(error, str) and error.startswith("API"):
        return False
    graders = run.get("graders")
    return (isinstance(graders, list) and bool(graders)
            and all(isinstance(g, dict) and isinstance(g.get("passed"), bool) for g in graders))


def case_complete(case: object, runs: int) -> bool:
    """A trigger case with all `runs` runs complete on its `with` arm. (The
    case's own `runsPerCase` is its default, not the --runs override, so the
    count to have is --runs.)"""
    if not isinstance(case, dict):
        return False
    arms = case.get("arms") if isinstance(case.get("arms"), dict) else {}
    with_runs = arms.get("with")
    return isinstance(with_runs, list) and len(with_runs) == runs and all(run_complete(r) for r in with_runs)


def complete_cases(data: object, runs: int, expected: list[str]) -> dict[str, dict]:
    """The complete trigger cases of a saved trigger JSON, by name (expected names only)."""
    if not isinstance(data, dict) or data.get("schemaVersion") != eval_gate.SCHEMA_VERSION \
            or not isinstance(data.get("cases"), list):
        return {}
    out: dict[str, dict] = {}
    for case in data["cases"]:
        name = case.get("name") if isinstance(case, dict) else None
        if name in expected and name not in out and case_complete(case, runs):
            out[name] = case
    return out


def merge_trigger(base: dict, cases: dict[str, dict], cost: float, expected: list[str], runs: int) -> dict:
    """One trigger JSON the gate scores like a single run's: the expected cases
    in case-list order, costUsd the sum of every part, and partial false only
    when every case is complete."""
    merged = {k: v for k, v in base.items() if k not in ("cases", "costUsd", "partial", "partialReason")}
    merged["schemaVersion"] = eval_gate.SCHEMA_VERSION
    merged["costUsd"] = round(cost, 6)
    merged["cases"] = [cases[n] for n in expected if n in cases]
    missing = [n for n in expected if n not in cases or not case_complete(cases[n], runs)]
    merged["partial"] = bool(missing)
    if missing:
        merged["partialReason"] = f"resume: {len(missing)} case(s) incomplete: {', '.join(missing)}"
    passed = sum(1 for n in expected if n in cases and case_complete(cases[n], runs)
                 and all(r["passed"] is True for r in cases[n]["arms"]["with"]))
    merged["aggregates"] = {"casesTotal": len(merged["cases"]), "casesPassed": passed}
    return merged


def run_trigger_stage(root: Path, runs: int, out_json: Path, concurrency: int,
                      expected: list[str], resume: bool) -> tuple[float | None, int]:
    """The trigger stage; returns (its cost, the trigger cases reused).

    Fresh, or resumed with no readable saved JSON or no complete case in it:
    the whole suite, into out_json. Resumed otherwise: only the incomplete
    cases, one --case call each, each merged into out_json as it finishes."""
    saved = read_json(out_json) if resume else None
    done = complete_cases(saved, runs, expected)
    if not done:
        if resume:
            say("trigger: resume: no complete case saved, the whole trigger stage runs again")
        return run_trigger(root, runs, out_json, concurrency), 0
    assert isinstance(saved, dict)
    reused = len(done)
    todo = [n for n in expected if n not in done]
    cost = _num(saved.get("costUsd"))
    say(f"trigger: resume: {reused} complete case(s) reused, {len(todo)} to run")
    cases = dict(done)
    part = out_json.with_name("trigger-part.json")
    for name in todo:
        run_trigger(root, runs, part, concurrency, case=name)
        data = read_json(part)
        if isinstance(data, dict):
            cost += _num(data.get("costUsd"))
            for case in data.get("cases") or []:
                if isinstance(case, dict) and case.get("name") == name:
                    cases[name] = case
        write_json_atomic(out_json, merge_trigger(saved, cases, cost, expected, runs))
        part.unlink(missing_ok=True)
    write_json_atomic(out_json, merge_trigger(saved, cases, cost, expected, runs))
    return cost, reused


RUNNER_TESTS = Path("tests") / "test_run_scenarios.py"


def run_runner_tests(project: Path) -> None:
    """Run the test project's own unit tests; SetupError when they fail."""
    if not (project / RUNNER_TESTS).is_file():
        raise SetupError(f"test project has no {RUNNER_TESTS.as_posix()}: {project}")
    cmd = ["uv", "run", RUNNER_TESTS.as_posix()]
    say(f"runner tests: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, check=False)
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        failed = re.findall(r"^(?:FAIL|ERROR): (\S+ \([^)]*\))", proc.stdout, re.MULTILINE)
        summary = ", ".join(failed[:10]) + (f" and {len(failed) - 10} more" if len(failed) > 10 else "")
        tail = proc.stdout.strip().splitlines()[-1:] or ["no output"]
        raise SetupError(f"runner tests failed (exit {proc.returncode}): "
                         + (summary or tail[0]))
    last = [ln for ln in proc.stdout.splitlines() if ln.startswith("Ran ")]
    say(f"runner tests: ok ({last[-1] if last else 'passed'})")


def run_gate(out_json: Path, cases_dir: Path) -> dict:
    proc = subprocess.run(["uv", "run", str(GATE), str(out_json), "--cases-dir", str(cases_dir)],
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
    if proc.returncode == 2:  # a setup or suite problem: no scenarios, no record
        errors = result.get("errors") if isinstance(result.get("errors"), list) else []
        why = "; ".join(str(e) for e in errors) or result.get("error") or "no reason given"
        raise SetupError(f"eval_gate exited 2: {why}")
    return result


def scenario_binaries(root: Path) -> list[Path]:
    """The cached binary of every version in tools/rpcn_versions.txt, so each
    scenario's [[lint]] runs on the floor and the newest pin (AD-5)."""
    versions_file = root / "tools" / "rpcn_versions.txt"
    try:
        versions = fetch_rpcn.read_versions(versions_file)
    except (OSError, fetch_rpcn.FetchError) as exc:
        raise SetupError(f"cannot read the pinned versions in {versions_file}: {exc}")
    paths = [root / ".cache" / "rpcn" / v / fetch_rpcn.BINARY_NAME for v in versions]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise SetupError(f"pinned binary missing: {', '.join(missing)}; run `uv run tools/fetch_rpcn.py`")
    return [p.resolve() for p in paths]


def run_scenarios(root: Path, project: Path, names: list[str], runs: int,
                  jobs: int = DEFAULT_PARALLEL, resume_from: Path | None = None,
                  on_runs_dir=None) -> tuple[dict, bool]:
    """Run the scenarios; return (the parsed results.json, whether the whole run passed).

    With resume_from, run_scenarios.py gets --resume <that runs folder>.
    on_runs_dir(path) is called as soon as the runner names its runs folder.
    The run passed only when run_scenarios.py exited 0, its top-level `passed`
    is true and no comparison arm crashed."""
    cmd = ["uv", "run", "run_scenarios.py", "--source", f"local:{root}", "--runs", str(runs),
           "--jobs", str(jobs)]
    if resume_from is not None:
        cmd += ["--resume", str(resume_from)]
    for name in names:
        cmd += ["--scenario", name]
    binaries = scenario_binaries(root)
    env = {**os.environ, "RPCN_TEST_BINARIES": ":".join(str(b) for b in binaries)}
    say(f"scenarios: lint on {' '.join(str(b) for b in binaries)}")
    say(f"scenarios: {' '.join(cmd)}")
    results_path = None
    proc = subprocess.Popen(cmd, cwd=project, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            m = re.match(r"results: (.+results\.json)\s*$", line)
            if m:
                results_path = Path(m.group(1))
            m = re.match(r"claude: .*; results: (.+?)\s*$", line)
            if m and on_runs_dir is not None:
                runs_dir = Path(m.group(1))
                on_runs_dir(runs_dir if runs_dir.is_absolute() else project / runs_dir)
        code = proc.wait()
    except KeyboardInterrupt:
        stop_child(proc)
        raise
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


def stop_child(proc: subprocess.Popen, grace_s: float = 15) -> None:
    """On Ctrl-C: SIGINT the child, so it kills its sessions and saves its
    finished runs; terminate it if it has not exited within grace_s."""
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except (OSError, KeyboardInterrupt):  # a second Ctrl-C: stop waiting
        proc.kill()


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
    p.add_argument("--runs", type=int, default=2, help="runs per trigger case and scenario (default 2); a record can pass "
                        "only with 2 or more, fewer is a smoke run that never passes")
    p.add_argument("--with-compare", action="store_true",
                   help="also run the comparison (benchmark) scenarios, about +$12")
    p.add_argument("--concurrency", type=int, default=DEFAULT_PARALLEL,
                   help=f"trigger sessions at once, 1-{MAX_PARALLEL} (default %(default)s)")
    p.add_argument("--jobs", type=int, default=DEFAULT_PARALLEL,
                   help=f"scenario runs at once, 1-{MAX_PARALLEL} (default %(default)s); "
                        "comparison scenarios always run one at a time")
    p.add_argument("--resume", action="store_true",
                   help="continue the last run for the current skills hash: reuse its complete "
                        "trigger cases and finished scenario runs (passed or failed), run the rest; "
                        "exit 2 when anything that decides the result differs")
    p.add_argument("--repo", type=Path, default=eval_record.REPO_ROOT, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.runs < 1:
        p.error("--runs must be at least 1")
    for flag in ("concurrency", "jobs"):
        if not 1 <= getattr(args, flag) <= MAX_PARALLEL:
            p.error(f"--{flag} must be from 1 to {MAX_PARALLEL}")
    return args


def state_dir(root: Path, full_hash: str) -> Path:
    return root / RESUME_DIR / full_hash[:eval_record.PREFIX_LEN]


# The state fields a resume must match, with the name a mismatch is reported by.
MATCH_FIELDS = (
    ("skills_hash", "skills hash"),
    ("test_project_head", "test project HEAD"),
    ("test_project_status", "test project `git status --porcelain`"),
    ("runs", "--runs"),
    ("with_compare", "--with-compare"),
    ("scenarios", "scenario list"),
    ("trigger_cases", "trigger case list"),
    ("trigger_case_hashes", "trigger case files"),
)


def _show(v: object) -> str:
    if isinstance(v, list):
        return f"{len(v)} item(s)"
    if isinstance(v, str) and len(v) > 40:
        return repr(v[:12] + "...") if "\n" not in v else f"{len(v.splitlines())} line(s)"
    return repr(v)


def load_state(folder: Path, now: dict) -> dict:
    """The saved state to resume, checked against `now`; SetupError when there
    is none, it is unreadable, or anything that decides the result differs."""
    path = folder / "state.json"
    if not path.is_file():
        raise SetupError(f"nothing to resume for skills hash {now['skills_hash'][:eval_record.PREFIX_LEN]} "
                         f"(no {path}); run without --resume")
    state = read_json(path)
    if not isinstance(state, dict) or state.get("schema") != STATE_SCHEMA:
        raise SetupError(f"cannot resume: {path} is unreadable or not schema {STATE_SCHEMA}")
    diffs = []
    for key, label in MATCH_FIELDS:
        if state.get(key) != now[key]:
            if isinstance(now[key], dict) and isinstance(state.get(key), dict):
                changed = sorted(n for n in now[key] if n in state[key] and state[key][n] != now[key][n])
                diffs.append(f"{label} differ ({'changed ' + ', '.join(changed) if changed else 'cases differ'})")
            elif isinstance(now[key], list) and isinstance(state.get(key), list):
                added = sorted(set(now[key]) - set(state[key]))
                dropped = sorted(set(state[key]) - set(now[key]))
                detail = "; ".join(x for x in (f"added {', '.join(added)}" if added else "",
                                                f"dropped {', '.join(dropped)}" if dropped else "") if x)
                diffs.append(f"{label} differs ({detail or 'order differs'})")
            else:
                diffs.append(f"{label} differs (saved {_show(state.get(key))}, now {_show(now[key])})")
    if diffs:
        raise SetupError("cannot resume: " + "; ".join(diffs) + "; run without --resume to start over")
    return state


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
        run_runner_tests(project)
        scenario_binaries(root)  # fail before any paid step when a pinned binary is missing
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

        folder = state_dir(root, before)
        now = {
            "skills_hash": before,
            "test_project_head": git(project, "rev-parse", "HEAD"),
            "test_project_status": git(project, "status", "--porcelain"),
            "runs": args.runs, "with_compare": args.with_compare,
            "scenarios": names, "trigger_cases": trigger_case_names(root),
        }
        now["trigger_case_hashes"] = trigger_case_hashes(root, now["trigger_cases"])
        out_json = folder / "trigger.json"
        resume_from = None
        if args.resume:
            state = load_state(folder, now)
            prev_runs = state.get("runs_dir")
            if isinstance(prev_runs, str) and (Path(prev_runs) / "results.json").exists():
                prev_results = Path(prev_runs) / "results.json"
                data = read_json(prev_results)
                if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
                    raise SetupError(f"cannot resume: {prev_results} is unreadable (killed mid-save?); "
                                     "run without --resume to start over")
                resume_from = Path(prev_runs)
            say(f"resume: {folder.relative_to(root).as_posix()}"
                + (f", scenario runs from {resume_from}" if resume_from else ", no scenario runs saved"))
        else:
            state = {"schema": STATE_SCHEMA, **now, "runs_dir": None,
                     "started": datetime.now().astimezone().isoformat(timespec="seconds")}
            for old in (out_json, folder / "trigger-part.json"):
                old.unlink(missing_ok=True)
        write_json_atomic(folder / "state.json", state)

        def on_runs_dir(path: Path) -> None:
            state["runs_dir"] = str(path)
            write_json_atomic(folder / "state.json", state)

        trigger_cost, trigger_reused = run_trigger_stage(
            root, args.runs, out_json, args.concurrency, now["trigger_cases"], args.resume)
        gate = run_gate(out_json, root / "evals")
        results, scenarios_ok = run_scenarios(root, project, names, args.runs, args.jobs,
                                              resume_from, on_runs_dir)
        rows, winners, scenario_cost = summarize(results, names)

        after = eval_record.skills_hash(root)
        if after != before:
            raise SetupError(f"skills changed during the run ({before[:12]} -> {after[:12]}); "
                             "no record written, run again")
    except (SetupError, eval_record.HashError) as exc:
        say(f"error: {exc}")
        return 2
    except KeyboardInterrupt:
        say("interrupted: no record written")
        return 130

    record["trigger"] = gate
    record["scenarios"] = rows
    record["compare"] = winners if args.with_compare else None
    record["passed"] = (gate.get("ok") is True and scenarios_ok and bool(rows)
                        and all(r["result"] == "PASS" for r in rows))
    record["cost_usd"] = round(_num(trigger_cost) + scenario_cost, 4)
    if args.resume:
        reused_runs = results.get("reused_runs")
        record["resumed"] = {
            "state_dir": folder.relative_to(root).as_posix(),
            # relative to the test project, like state_dir: no local path in a committed record
            "runs_dir": (os.path.relpath(resume_from, project).replace(os.sep, "/")
                         if resume_from else None),
            "trigger_cases": trigger_reused,
            "scenario_runs": reused_runs if isinstance(reused_runs, int) and resume_from else 0,
        }
        say(f"resume: reused {trigger_reused} trigger case(s) and "
            f"{record['resumed']['scenario_runs']} scenario run(s)")

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
