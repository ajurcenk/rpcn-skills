---
title: 'Local eval runner and the eval-record check'
type: 'feature'
ticket: '11'
created: '2026-10-30'
status: 'built'
baseline_revision: '5160bf02b51f43af1864119b636338c68c092c79'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md', '{project-root}/evals/README.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** R12 says every change that affects a skill runs the evals. Evals run locally (decision 2026-10-23), so today that's only a convention. A skill can change and merge with no eval evidence, and nothing on GitHub notices.

**Approach:**
- **Run everything:** `tools/run_evals.py` runs the trigger suite and the gate (story 7) and the `rpcn-test-skills` pass scenarios (story 6) in one command. It writes a committed record, `evals/results/<YYYY-MM-DD>-<skills-hash12>.json`.
- **Check the record:** `tools/eval_record_check.py`, run in CI, fails unless a passing record exists for the current skill content.
- **Enforce it:** branch protection on `main` makes the CI job required.

## Boundaries & Constraints

**Always:**
- **The skills hash:** `tools/eval_record.py` (shared by both scripts) computes it as the sha256 over every file under `skills/`. Each file contributes its repo-relative POSIX path, a NUL byte, its own sha256 and a newline, in sorted path order. It covers only content tracked or trackable by git: no `__pycache__/` and nothing gitignored. The filename uses the first 12 hex characters, and the record stores the full hash. The same content always gives the same hash, whatever the mtime or checkout path.
- **`tools/run_evals.py`:** a PEP 723 script, standard library only, run with `uv run`.
  - **Options:** `--test-project <path>` (default `../rpcn-test-skills`), `--runs <n>` (default 3) and `--with-compare` (adds the benchmark scenarios, about +$4; off by default).
  - **What it runs, in order:**
    1. the skills hash
    2. `claude plugin eval . --ablation none --runs <n> --tag trigger --no-publish --trust-plugin --json <tmp>`
    3. `uv run tools/eval_gate.py <tmp>`
    4. in the test project, `uv run run_scenarios.py --source local:<this repo> --runs <n>` for every scenario that isn't a comparison, plus the comparison scenarios with `--with-compare`
  - **Progress:** one line per step: `[run_evals +<s>s] trigger: …`, `gate: accuracy=…`, `scenarios: …`, `record: <path>`. Each child's own progress passes through live.
  - **The record:** `{"schema":1, "skills_hash", "date", "git_head", "dirty", "plugin_version", "claude_version", "trigger": <gate JSON>, "scenarios": [{"name","result","runs","passed"}], "compare": <winner per scenario, or null>, "passed": bool, "cost_usd"}`. `passed` is true only when the gate is ok and every scenario passed. The record is written even when it fails, so failures are visible.
  - **Exit codes:** 0 when passed, 1 when not, 2 for a setup error (no `claude` or `uv`, a missing test project, the skills hash changing while the run is in progress).
- **`tools/eval_record_check.py`:** a PEP 723 script, standard library only, run with `uv run`.
  - **What it does:** computes the current skills hash and looks for any `evals/results/*-<hash12>.json` whose `skills_hash` equals the full hash and whose `passed` is true.
  - **Output:** one JSON object `{"ok", "skills_hash", "record": <path|null>, "reason"}`.
  - **Exit codes:**
    - 0 when a passing record is found
    - 1 when none is found. The reason names the command to run: `uv run tools/run_evals.py`, then commit the record.
    - 2 when a record is malformed
- **`.gitignore`:** the existing `evals/results/*/` rule still hides `claude plugin eval`'s timestamped folders. The `evals/results/*.json` records are committed.
- **CI:** a step, `Eval record matches the skills (R12)`, runs `uv run tools/eval_record_check.py` after the drift check. A test step runs `uv run tools/tests/test_eval_record.py`.
- **Unit tests:** `tools/tests/test_eval_record.py`, with no Claude calls. It covers:
  - the hash: stable, independent of order and mtime, changes when content changes, ignores `__pycache__`
  - the check: a match passes; no record fails; a failed record fails; a 12-character prefix match with a different full hash fails; a malformed record exits 2
  - `run_evals.py` orchestration: a fake `claude` and a fake `run_scenarios.py` give pass, gate fail and scenario fail, and a record is written each time
- **The first real record:** made by the orchestrator, not the implementer, for the current skill content, then committed, so CI goes green.

- **Decision (user, 2026-10-30), option (a):** branch protection on `main` requires the `check` status check for pull requests. Admin direct pushes stay allowed (`enforce_admins: false`, no required reviews). The orchestrator sets it up with `gh api` during verification, once this plan is approved.

**Never:**
- running evals in CI
- writing records anywhere except `evals/results/`
- including `evals/`, `tools/` or docs in the hash. Only `skills/` defines what a user installs.
- editing skills in this story

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh record | the record's hash equals the current one, `passed: true` | check exit 0 | — |
| Skill edited | any byte under `skills/` changed after the record | check exit 1, reason names `run_evals.py` | — |
| Failed record only | the hash matches but `passed: false` | check exit 1 | — |
| Prefix collision | the filename prefix matches but the full hash differs | check exit 1 | — |
| Malformed record | not JSON, or `schema` isn't 1 | check exit 2, naming the file | — |
| Gate fails | accuracy below 0.9 | `run_evals` writes the record with `passed: false`, exit 1 | — |
| Scenario fails | a pass scenario FAILs | the record has `passed: false`, exit 1 | — |
| Skills change mid-run | the hash differs before and after | exit 2, no record written | — |
| Missing test project | the `--test-project` path doesn't exist | exit 2 before any run | — |

</frozen-after-approval>

## Code Map

- **Reuse:**
  - `tools/eval_gate.py` (story 7): `uv run tools/eval_gate.py <json>` gives JSON with `ok`, `accuracy` and the rest. The trigger command is in `evals/README.md`.
  - The test project's `rpcn-test-skills/run_scenarios.py`: `--source local:<path>` and `--scenario`, with exit code 0 when everything passes. Its `results.json` holds `scenarios[]` with `passed` and the run counts. Comparison scenarios are the ones that set `[compare] enabled = true` in `scenarios/*/expect.toml`; today that's `rpcn-test__compare_lint`.
- **Style to follow:** `tools/sync_shared.py` and `tools/fetch_rpcn.py` (PEP 723, docstring, JSON output). Tests go in `tools/tests/`.
- **CI:** `.github/workflows/ci.yml` runs one `check` job, with the drift check first, then cache, fetch, the `rpcn_check` tests, the `sync_shared` tests and the `eval_gate` tests. Add the record check straight after the drift check, and the new tests at the end.
- **Cost of a default run:** the trigger suite is about $3.30 (14 × 3, measured twice). `rpcn-test__lint_broken` × 3 is about $0.90. That's about $4.20 in total.
- **Branch protection:** none on `main` today (the API returns 404). The CI job's check is named `check`.

## Tasks & Acceptance

**Execution:**
- [x] `tools/eval_record.py` -- the skills hash and record find and validate helpers -- shared logic
- [x] `tools/run_evals.py` -- orchestration per the Boundaries -- R10
- [x] `tools/eval_record_check.py` -- the CI check -- R10, R11
- [x] `tools/tests/test_eval_record.py` -- every matrix row, plus the hash properties -- correctness
- [x] `.github/workflows/ci.yml` -- the record check after the drift check, and the test step -- enforcement
- [x] `evals/README.md` -- a "Recording a run" section: the command, what gets committed, cost -- contributor guidance
- [x] (orchestrator) a first `uv run tools/run_evals.py`, with the record committed -- CI green
- [x] (orchestrator, approved with the plan) branch protection on `main`: required check `check`, admins exempt -- merge gate
- [x] (orchestrator, with the user's consent) a throwaway PR that touches `skills/rpcn-test/SKILL.md` with no record: show the check failing, then close it -- proves the acceptance criteria

**Acceptance Criteria:**
- Given a PR that changes `skills/rpcn-test/` with no matching record, when CI runs, then the record check fails and the PR can't merge.
- Given the same PR with a fresh passing record committed, when CI runs, then it passes and can merge.
- Given `uv run tools/tests/test_eval_record.py`, then every test passes.

## Implementation Notes

- **Hash file list:** `git ls-files -z --cached --others --exclude-standard -- skills` when the root is a git toplevel (tracked files deleted from the working tree are dropped); otherwise a walk of `skills/` that skips `__pycache__/`. `__pycache__/` and `*.pyc` are excluded in both paths.
- **`scenarios[]` row:** `runs` is the number of runs and `passed` the number that passed (the `result` word carries the verdict). A requested scenario missing from `results.json` is recorded as `FAIL 0/0`.
- **Failure vs setup error:** a gate exit 2 (incomplete suite, partial run) is recorded as a failed trigger (`trigger.ok: false`), exit 1. These are setup errors (exit 2, no record): no `claude`/`uv`, no `run_scenarios.py` in the test project, no scenarios to run, `claude plugin eval` leaving no readable JSON (scenarios are then skipped, to save cost), `run_scenarios.py` exit 2 or no `results:` line, and a skills-hash change mid-run.
- **Scenario results:** read from the `results: <path>` line `run_scenarios.py` prints at the end; its stdout is echoed live while being scanned.
- **`cost_usd`:** the trigger aggregate's `costUsd`, plus every scenario run's `cost_usd`; for comparison scenarios every arm's runs plus the judge's `cost_usd`.
- **`--test-project`:** a relative path is resolved against the current folder; the default is `rpcn-test-skills` beside this repo. A hidden `--repo <root>` option exists for the tests only (records still go to `<root>/evals/results/`).
- **Comparison detection:** `tomllib` on Python >= 3.11, a small `[compare]` / `enabled = true` line parser on 3.10 (the 3.10 path is not exercised locally: no 3.10 interpreter installed).
- **Review fixes:** a failing run writes `<date>-<hash12>.failed-<HHMMSS>.json`, outside the check's `*-<hash12>.json` glob, so it never overwrites a passing record (a later passing run takes the standard name). `passed` also requires `run_scenarios.py` exit 0, its top-level `passed: true` and `arms_crashed` 0. `--runs` below 3 can never pass (the gate needs 3 runs per case); the help and README say so. When the root has `.git` and a git command fails, the hash raises `HashError` (both scripts exit 2) instead of falling back to the walk. `dirty` is `git status --porcelain -- skills`.
- **Check:** every record whose name ends in `-<hash12>.json` is validated (`schema` the integer 1, `skills_hash` a string, `passed` a bool); any malformed one gives exit 2 even if another record passes.

## Plan Change Log
- **Orchestrator verification (2026-10-30):**
  - **First real run:** `uv run tools/run_evals.py` took 657 s and cost $4.28. Trigger accuracy 1.0, the gate ok, `rpcn-test__lint_broken` PASS 3/3, exit 0. Record `evals/results/2026-10-30-f7572be95821.json`, committed in `9a7c82f`. CI is green, including the new record check.
  - **Branch protection on `main`:** required status check `check`, `strict: false`, `enforce_admins: false`, no required reviews.
  - **Acceptance criterion 1:** throwaway PR #1 added a trailing newline to `skills/rpcn-test/SKILL.md` (skills hash `dc9c52218c17`, no record). CI failed on "Eval record matches the skills (R12)", and the merge state was `BLOCKED`. The PR was closed and its branch deleted.
  - **Acceptance criterion 2** ("with a fresh record it can"): shown on `main` at `9a7c82f`. That commit carries the passing record for its skills content, and its `check` is green. A second $4 run on the throwaway edit wasn't made.

## Review Triage Log

**Pass 1 (quick):** 5 → patch, 2 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | Acceptance criteria 1 and 2 can't be shown from the diff alone (no record, no protection) | low | reject (false) | Those are the orchestrator's tasks by design. The first record, branch protection and the throwaway PR come next. |
| 2 | A failing re-run overwrites a passing record with the same date and hash | medium | patch | `write_text` overwrites unconditionally, so content that passed would go red. |
| 3 | `run_scenarios.py`'s exit 1 and `arms_crashed` are ignored | medium | patch | Crashed comparison arms can give `passed: true`. |
| 4 | `--runs` below 3 always writes a failing record, and that isn't documented | low | patch | `eval_gate` requires 3 runs by default. A doc correction. |
| 5 | The missing-`claude` test is skipped locally, and the missing-`uv` path is untested | low | reject | It's a test-environment limit. The code path is simple (`shutil.which`), and testing it would need PATH-shim scaffolding. |
| 6 | When git fails inside a checkout, the hash silently switches to a file walk | medium | patch | A false record mismatch with no warning, for example from `safe.directory`. |
| 7 | `dirty` is computed over the whole repo | low | patch | It should reflect `skills/` only. A direct correction. |

## Verification

**Who runs what:** the implementer writes the code and runs only the unit tests and a `--help` check. The orchestrator runs the real `run_evals.py` (about $4.20) with live progress, commits the record, sets up or relays the branch protection, and runs the throwaway-PR check.

**Commands** (from `rpcn-skills`):
- `uv run tools/tests/test_eval_record.py` -- expected: all pass
- `uv run tools/run_evals.py` -- expected: gate ok, scenarios PASS, record written, exit 0
- `uv run tools/eval_record_check.py` -- expected: exit 0 once the record exists, and exit 1 after any `skills/` edit
