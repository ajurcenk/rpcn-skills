---
title: 'The trigger gate measures what users install'
type: 'feature'
ticket: '1'
created: '2026-11-05'
status: 'built'
baseline_revision: 'd5fbb4e9b64aae01aea6f14fb8558c92a779faac'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Today the trigger gate measures a setup no user has.
- **The negatives are too narrow.** They check only that `rpcn-test` stayed silent.
- **The gate misses dropped cases.** `eval_gate.py` silently ignores any case it doesn't recognise, so a dropped case shrinks the suite unnoticed.
- **Only one install path is measured.** Every trigger run loads the whole repo as a plugin, never the `npx` install users get.
- **Nothing checks which skills a session could see.**
- **The runner's own tests aren't required.** Paid evals can start without the `rpcn-test-skills` tests passing.

Epic 2 adds a second skill, so all of this has to hold first (epic R10, AD-13 "What users install").

**Approach:** Tighten the gate in `rpcn-skills`' `tools/` and `evals/`, and in `rpcn-test-skills`' runner. Nothing under `skills/` changes.
- **Graders:** the negatives match any `rpcn-` skill.
- **Case list:** `eval_gate.py` compares the cases it receives with the `evals/` folders.
- **Visible skills:** the runner checks which `rpcn-` skills a session saw.
- **Near-miss scenarios:** a scenario can assert that no `rpcn-` skill fired. Two new `rpcn-test` scenarios give the `npx`-alone pair.
- **Runner tests first:** `run_evals.py` runs the runner's tests before anything it pays for.

## Boundaries & Constraints

**Always:**
- Keep each tool's JSON output and its exit codes 0, 1 and 2. A setup or suite problem is exit 2.
- Use PEP 723 headers and `uv run`, with unittest tests in each repo's existing style.
- Scenario names follow `<skill>__<case>` (AD-10).
- The visible-skills check looks only at `rpcn-*` names. Each session also sees about 19 built-in Claude Code skills (`runs/20261103-153744/results.json`), and those are ignored.

**Never:**
- Edit anything under `skills/`.
- Change what a positive case asserts.
- Apply the visible-skills check to plugin arms (`--plugin-dir`), which load other sets on purpose.
- Edit `.github/workflows/ci.yml` beyond what the new tests need.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Negatives | a miss case where some `rpcn-x` skill fires | the grader fails the case | — |
| Full suite | a result whose case names equal the `evals/*__trigger_*` and `*__miss_*` folders | the gate runs as today | — |
| Missing case | a result without one expected case | gate exit 2, naming the case | `errors` lists it |
| Extra case | a result case that has no folder | gate exit 2, naming the case | `errors` lists it |
| Unexpected skill | a session whose `init.skills` has an `rpcn-*` that is not in `install` | `visible` check fails, and the run fails | named in the check |
| Built-ins only | `init.skills` has `rpcn-test` plus built-ins, with `install = ["rpcn-test"]` | `visible` check passes | — |
| Near-miss | `silent = true`, and no `rpcn-` Skill call | passes; it fails when one fires | — |
| No fixtures | a trigger scenario with no `fixtures/` and no `unchanged`/`report`/`lint` | loads, runs in an empty folder | a missing `fixtures/` is still an error when files are checked |
| Runner tests fail | `tests/test_run_scenarios.py` exits non-zero | `run_evals` exits 2 before any paid step, with no record | the reason says which tests failed |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`, `T` = `rpcn-test-skills`. `T` starts from `3a5290366e78206705c0de0ebf947a60ebc25f74`, a local repo with no remote.

- **`R/evals/rpcn-test__miss_*/graders/not-fired.md` (6 files):** change `input_match` to `'"skill"\s*:\s*"(?:[\w-]+:)?rpcn-[\w-]+"'`, keeping `min: 0, max: 0`. Positive `fired.md` files are unchanged.
- **`R/evals/README.md:12-13`:** describes the negatives. Update it, and document the case-list check.
- **`R/tools/eval_gate.py`:**
  - Prefixes are hardcoded at 43-44 and used by `kind_of()` at 90-95.
  - `gate()` (121-129) drops unknown cases.
  - The CLI is at 168-174, and the incomplete-suite error path is at 154-155.
  - Generalise the prefixes to `^[\w-]+__trigger_` / `^[\w-]+__miss_`, and add `--cases-dir` (default: the repo's `evals/`).
- **`R/tools/tests/test_eval_gate.py`:** builders at 29-62, `GateTest` at 90. Add missing, extra, a generalised prefix, and a skill other than rpcn-test.
- **`R/tools/run_evals.py`:**
  - Calls the gate at 145; pass `--cases-dir` there.
  - `SetupError` is at 69 and is caught in `main()` at 287-289.
  - Run `uv run tests/test_run_scenarios.py` (cwd = project) right after the project check at 257-258, before any paid step.
- **`R/tools/tests/test_eval_record.py` (244-335):** the fake project (318) needs a fake `tests/test_run_scenarios.py`, plus a failing variant test.
- **`T/run_scenarios.py`:**
  - `validate_expect` is at 73-175; its allowed keys are at 82-85. Add `silent` (bool, valid only without `skill`).
  - `load_scenario` (238-240) requires `fixtures/`. Allow it to be absent when no file checks exist.
  - `StreamState` (559-625) collects `skills_used`, and `run_once` (1167-1174) stores `init.skills`.
  - `run_checks` (~1205) gets the new `visible` and `silent` checks. It runs only for skills arms (1194).
  - `run_passed` is at 400-407.
- **`T/tests/test_run_scenarios.py`:** about 116 tests. Add tests for `visible`, `silent`, scenarios without fixtures, and validation.
- **New `T/scenarios/rpcn-test__npx_trigger/`:** a positive case. `prompt.md` reads "Check my Redpanda Connect binary. This run is unattended: don't ask me anything." `expect.toml` has `install = ["rpcn-test"]` and `skill = "rpcn-test"`, with no fixtures.
- **New `T/scenarios/rpcn-test__npx_miss/`:** a near-miss. `prompt.md` asks for a Kafka Connect S3 sink connector config, in the same style as `R/evals/rpcn-test__miss_kafka_connect`, unattended. `expect.toml` has `install = ["rpcn-test"]` and `silent = true`.
- **Don't touch:** `R/skills/`, and `R/tools/eval_record.py`. Its hash covers only `skills/` (32, 72), so grader edits don't need a new record for the hash.

## Tasks & Acceptance

**Execution:**
- [x] `R/evals/rpcn-test__miss_*/graders/not-fired.md`, `R/evals/README.md`: widen the negatives, and document them.
- [x] `R/tools/eval_gate.py` and its tests: generalised prefixes, plus a `--cases-dir` expected-list check (exit 2 on a missing or extra case).
- [x] `R/tools/run_evals.py` and `test_eval_record.py`: pass `--cases-dir`, and run `T`'s tests first (SetupError on failure).
- [x] `T/run_scenarios.py` and its tests: the `visible` check (`rpcn-*` only), the `silent` key and check, and optional fixtures.
- [x] `T/scenarios/rpcn-test__npx_trigger/`, `T/scenarios/rpcn-test__npx_miss/`: the `npx`-alone pair.
- [x] `T/README.md`: document `silent`, `visible`, and trigger scenarios.

**Acceptance Criteria:**
- **Given** this repo, **when** `uv run tools/run_evals.py` runs, **then** `T`'s tests run first, the gate passes with the case list, all scenarios pass 3/3 (including the two new ones), and a passing record is written.
- **Given** any of the four repo test suites (`eval_gate`, `eval_record`, `run_scenarios`, plus CI's existing ones), **when** they run, **then** all pass, and CI stays green.

## Implementation Notes

- **Built as planned in both repos.** Test counts: `eval_gate` 29, `eval_record` 38, `run_scenarios` 137. The other suites are unchanged and green.
- **Eval record:** `evals/results/2026-11-05-93ce7031a1db.json` passed at $6.38, with trigger accuracy 1.0 and the case list checked. All 5 scenarios passed 3/3, including `rpcn-test__npx_trigger` and `rpcn-test__npx_miss`. It was run before the review patches. Those changed only how the tools handle a gate exit 2, the `install` filter, and `silent` validation, not what the run measured. The skills hash is unchanged, so the record stands.
- **`npx_miss`:** Claude tried Bash and Write, which were denied, and that is not an error. `max_turns = 5` leaves room.
- **Change:** a gate exit 2 now stops `run_evals` before the scenarios, with no record. This includes a partial trigger run.

## Review Triage Log

Quick pass: 0 high, 1 medium, 2 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A gate exit 2 (missing or extra case) still paid for the scenarios, wrote a `.failed` record and exited 1 | medium | patch | Confirmed in `run_gate`. A gate exit 2 now raises SetupError: no scenarios, no record, exit 2. The test was replaced. |
| `check_visible` didn't filter `install` to `rpcn-*` | low | patch | `want` now goes through `rpcn_names()`. A test was added. |
| `silent = false` was accepted next to `skill` | low | patch | Any `silent` next to `skill` is now rejected. The README template and tests were updated. |

## Design Notes

- **Why `silent` and not a pattern list:** the only near-miss rule the epic needs is "no `rpcn-` skill". A single bool keeps `expect.toml` small. A pattern list can come later if a sibling ever needs "fires A, not B".
- **The visible rule:** take the visible `rpcn-*` names from `init.skills`, stripping a `plugin:` prefix the way `skill_matches` does. That set must equal `set(install)`.

## Verification

**Commands:**
- `uv run tools/tests/test_eval_gate.py`, `uv run tools/tests/test_eval_record.py`, and in `T`, `uv run tests/test_run_scenarios.py`: all pass.
- `uv run tools/validate_skills.py && uv run tools/sync_shared.py --check && uv run tools/eval_record_check.py`: green, with `skills/` untouched.
- In `T`: `uv run run_scenarios.py --source local:../rpcn-skills --scenario rpcn-test__npx_trigger --scenario rpcn-test__npx_miss --runs 1 --no-judge` gives PASS, as a cheap smoke check.
- `uv run tools/run_evals.py`: passes, and writes a record, at about $6.
