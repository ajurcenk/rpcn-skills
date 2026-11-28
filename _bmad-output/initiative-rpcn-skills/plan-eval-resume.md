---
title: 'Resume an interrupted eval record'
type: 'feature'
ticket: ''
created: '2026-11-28'
status: 'built'
baseline_revision: 'df8ef846c1cbc01f0e0f409cd5c6a2f5205ce655'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
test_project_baseline: '41786dd8d6e00922e5ce76a9d7dcaf9581253e33'
context:
  - '{project-root}/evals/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** An eval record (`tools/run_evals.py`) takes 45 to 100 minutes and costs about $76. When it is interrupted, or the session dies, everything starts again from the first case, so the finished, paid-for work is lost.

**Approach:** Add `uv run tools/run_evals.py --resume`. It continues the last run for the current skills hash and reuses only work that is provably the same:
- each finished trigger case;
- each finished scenario run.

Everything else runs again. The record says it was resumed and where each reused result came from (user request, 2026-11-28: "Build resume first").

## Boundaries & Constraints

**Always:**
- Reuse a result only when all of these match the earlier run:
  - the full skills hash;
  - the rpcn-test-skills HEAD and its `git status --porcelain` output;
  - `--runs`;
  - `--with-compare`;
  - the scenario list;
  - the trigger case list.

  Any mismatch: refuse to resume (exit 2, naming the mismatch). Never silently start over.
- A finished result is reused whether it passed or failed: a resume never retries a failure away. "Finished" means:
  - a trigger case with `runsPerCase` complete runs on its arm;
  - a scenario run with a full record (not a `crashed_run` and not interrupted).

  Half-written runs, crashed runs, missing runs and missing cases run again.
- The record gains a `resumed` object: the state and runs folders reused, and the counts of trigger cases and scenario runs reused. `schema` stays 1, and `eval_record_check.py` still accepts the record.
- `results.json` saves (runner) and the resume state file (run_evals) are atomic: write a temp file, then `os.replace`.
- Without `--resume`, the run behaves as today, except that it also writes the resume state.
- `claude plugin eval` keeps `--no-publish`.
- Tests use fixtures and the existing fake-`claude` setup only.

**Never:**
- Change `skills/`, `eval_gate.py`'s pass rules, or the 2-run minimum.
- Reuse across different skills hashes.
- Commit the state folder.
- The implementation agent never commits, and never runs a paid Claude session (no record, no trigger suite, no `run_scenarios.py` against Claude). Leave `T/orders_benthos_test.yaml` alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Fresh run | No state | Runs everything, writes the state as it goes; record as today, no `resumed` | — |
| Interrupted in the scenarios | State with the trigger stage done and K scenario runs finished | Trigger stage reused (no `claude plugin eval` call); only the unfinished runs run; record `resumed` with the counts | — |
| Interrupted in the trigger stage | Some cases complete in the saved trigger JSON | Only the missing cases run (`--case`); the case lists merge; the gate scores the merged JSON | No readable partial JSON: rerun the whole trigger stage |
| Failed run reused | A finished run failed | Kept as failed; the record fails | — |
| Crashed or half-written run | `crashed_run`, or a run folder with no record | Runs again | — |
| Mismatch | Skills hash, T HEAD or status, runs, compare or a list differs | No paid step | Exit 2 naming the mismatch |
| No state | `--resume` with no state for this hash | No paid step | Exit 2: "nothing to resume" |
| Truncated `results.json` | Killed mid-save (old runs) | The atomic save prevents it from now on | Unreadable: exit 2 |

</frozen-after-approval>

## Code Map

- `tools/run_evals.py` (407 lines):
  - `main` (340): the order of steps, and the record dict.
  - `run_trigger` (144): today it writes to a temp dir. Move its output into the state folder `evals/results/.resume/<hash12>/`, which `.gitignore` already covers through `evals/results/*/`.
  - `run_scenarios` (217): pass `--resume <runs dir>` to the runner, and record the runs dir it reports (`results: …` line) in the state as soon as it prints.
  - `summarize` (286): unchanged.
  - Exit codes and the module docstring: document `--resume`.
- The trigger JSON (`claude plugin eval --json`):
  - top level: `schemaVersion`, `costUsd`, `partial`, `suite`, `cases[]` and `aggregates`;
  - each case: `name`, `runsPerCase`, `arms` and `aggregates`.
  - `claude plugin eval` has `--case <glob>` (one per case, or repeated; check its help).
  - A real sample with 52 cases is at `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/trigger-8.5.json`. Copy a trimmed version into the test fixtures.
  - Check what `tools/eval_gate.py` reads before merging: the merged JSON must be scored exactly like a single run's, with `costUsd` summed and `partial` false only when every case is complete.
- `T/run_scenarios.py` (3,836 lines):
  - `parse_args` (3535): add `--resume <runs dir>`.
  - `main` (3726), `run_pool` (3679) and `run_once` (3227): skip run indices that the earlier `results.json` holds finished, and copy their records in unchanged (each keeps its `dir`).
  - `save()` (3763): make it atomic.
  - Results schema (3751–3797): add `resumed_from`.
  - `run_passed` (1599) and `scenario_passed` (1611): unchanged, since they decide pass/fail for reused runs too.
  - Crashed runs (3668) and interrupts (3799) are not finished.
  - Comparison scenarios: reuse at scenario level only when the whole comparison finished; otherwise rerun it.
- Tests:
  - `tools/tests/test_eval_record.py` (the fake `claude`, line 6 onward);
  - `T/tests/test_run_scenarios.py`.
- `evals/README.md`: a "Resume" paragraph next to "Run it".

## Tasks & Acceptance

**Execution:**
- [x] `T/run_scenarios.py`: `--resume`, the atomic `save()` and `resumed_from`, plus unit tests for each matrix row that belongs to the runner.
- [x] `tools/run_evals.py`: the state folder, `--resume`, the mismatch checks, the trigger per-case reuse and merge, and the record's `resumed` object.
- [x] `tools/tests/test_eval_record.py`: tests for every matrix row, using the fake `claude` and fixture JSON.
- [x] `evals/README.md`: the Resume paragraph.

**Acceptance Criteria:**
- Given a record resumed after an interruption, then `eval_record_check.py` accepts it exactly as it would the same run done in one go.

## Implementation Notes

- `runsPerCase` in the real trigger JSON is the case default (3), not the `--runs` override (the 8.5 sample has `runsPerCase: 3` with 2 runs), so a trigger case is complete when its `with` arm has exactly `--runs` runs, each with a bool `passed` and a non-empty `graders` list whose entries all have a bool `passed`. A run with no grader results (for example an API error) is not provably finished, so its case runs again.
- `claude plugin eval --case <glob>` is not variadic (commander `<glob>`, not `<glob...>`), so repeating it would keep only the last value. The resume runs one `--case <name>` call per incomplete case and merges each into `<state>/trigger.json` (atomic) as it finishes. When no case is complete, the whole stage runs instead.
- The runner prints `claude: <v>; results: <runs dir>` before any run; run_evals records that folder in the state as soon as it appears. The runner now saves `results.json` once before the first run, so a resumed runs folder always holds the reused records.
- Runner `results.json` gains `resumed_from` and also `reused_runs` (the count run_evals copies into `resumed.scenario_runs`). A finished run is a record with an int `index` in 1..runs and a bool `passed` that is not a `crashed:` run. A comparison entry is reused whole only when it carries `comparison` with `winner`/`decided_by` and every arm has all its runs; it is set on the entry only after the comparison finishes.
- The runner itself also refuses a `--resume` folder whose `runs_per_scenario` differs from `--runs` (exit 2).
- jobs=1 now puts every scenario entry into `results.json` up front (as `--jobs` > 1 already did), so the reused runs are saved before any new run starts.
- T `README.md` gained a short `--resume` paragraph, beside `--jobs`.
- Fixture: `tools/tests/fixtures/trigger-sample.json`, 6 cases trimmed from the 8.5 sample, with the paths scrubbed.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens), 2026-11-28: 7 findings, 0 high, 4 medium, 3 low, 0 false, 0 maybe-false

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `comparison_reusable` reuses a comparison that holds crashed arm runs | medium | patch | Confirmed at run_scenarios.py:3703-3714: no `crashed_runs` or `run_finished` check, which breaks the matrix's "crashed → runs again". Fix: not reusable when any arm run is unfinished. |
| 2 | `run_complete` keeps API-error runs that carry grader entries | medium | patch | Confirmed at run_evals.py:226 against eval_gate.py:123. Fix: an `error` starting with `API` means not complete. |
| 3 | Ctrl-C during the trigger stage SIGKILLs `claude plugin eval` before it can write a partial JSON | medium | patch | Confirmed: `run_trigger` still uses `subprocess.run`. Fix: Popen plus `stop_child`, as in the scenario stage. |
| 4 | Trigger cases are matched by name only, so an edited case reuses stale results | medium | patch | Confirmed: `trigger_case_names` only; the skills hash doesn't cover `evals/`. Fix: a per-case content hash in the state. |
| 5 | `resumed.runs_dir` is an absolute `/home/...` path in a committed record | low | patch | Confirmed. Fix: record it relative to the test project. |
| 6 | The atomic `save()` leaves `results.json` at mode 0600 | low | patch | Confirmed: mkstemp at run_scenarios.py:3033 and 3856. Fix: chmod to the umask default before the replace. |
| 7 | `reused_runs` counts only `ours` for a reused comparison | low | patch | Confirmed at run_scenarios.py:3845. Fix: count every arm's runs. |

## Verification

**Commands:**
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest tools/shared/rpcn_check/tests tools/tests -q`: expected all pass.
- From T: `uv run tests/test_run_scenarios.py`: expected all pass.
- `uv run tools/run_evals.py --help`: shows `--resume`.
- The first real use is the shared 8.4–8.6 record, run by the orchestrator after review.
