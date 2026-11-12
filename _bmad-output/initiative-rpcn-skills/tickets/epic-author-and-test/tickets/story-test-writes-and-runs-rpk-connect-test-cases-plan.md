---
title: 'Test writes and runs rpk connect test cases'
type: 'feature'
ticket: '9'
created: '2026-11-11'
status: 'done'
baseline_revision: '07b9d0e0fde29097b0ef707dfd9b9533d68e201f'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** the Unit tests section of the test report is always `Not run: not in this version of rpcn-test.` Nothing tests the whole pipeline's output against what it should produce, and the developer gets no `rpk connect test` cases to keep.

**Approach:**
- rpcn-test writes `<dir>/<name>_benthos_test.yaml` beside the pipeline. The cases come from intent: the request, a ready design note, and the samples' inputs and outputs.
- It runs them with `rpcn_check test <dir>/<pipeline>`, which is the plain `rpk connect test` call with no extra flags.
- It fills the Unit tests section: counts, plus one row per failing case.

## Boundaries & Constraints

**Always:**
- **AD-6:** rpcn-test is the only writer of `<name>_benthos_test.yaml`. It never edits the pipeline or a `.blobl`.
- **Expected outputs come from intent,** as with samples. They never come from running the pipeline or reading its code.
- **The `rpcn_check test` call has no extra flags beyond the pipeline target, except `--resources <res>` when `<res>` exists** (decision 2026-11-11, review), so the developer's own `rpk connect test [--resources <res>] <dir>/<pipeline>` (or `./...` with no `<res>`) runs the same cases.
- **AD-15:** each binary fact the skill relies on gets a `SOURCES.md` row and a real-binary `rpcn_check` test on 4.100.0 and 4.115.0. The facts, already probed on both:
  - `test <dir>/<name>.yaml` finds the sibling `<name>_benthos_test.yaml`;
  - `json_equals` and `json_contains` work;
  - `mocks` replace a processor by label;
  - an unset `${VAR}` doesn't stop a test;
  - `from "<path>"` resolves from the working directory.
- **Size:** `SKILL.md` stays at 4,803 characters or less, so the detail goes in a new `references/unit-tests.md`. Shared files change only under `tools/shared/`, then `sync_shared.py` runs.
- **The report stays `test-report@2`.** The Unit tests section already exists in @2. This story only fixes its content.

**Never:**
- Edit the pipeline to make it testable, or pass flags to the test run beyond the pipeline target and `--resources <res>`.
- Diagnose failures beyond a proposed diff (story 2.11), or check the design note (story 2.10).
- Let a test case call an outside service.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Correct pipeline, no test file | lints clean, intent is clear | Writes `<name>_benthos_test.yaml` with 2–4 cases; all pass; `Unit tests: N passed, 0 failed`; the verdict is unaffected | — |
| Broken pipeline | the output contradicts the request | The cases fail; one row per failing case (case name, line, message); verdict `fail`; a proposed diff | — |
| Lint fails | lint errors | `Not run: lint failed.`, and no file written | — |
| Non-deterministic output | a field from `now()` or `uuid_v4()` | That case uses `json_contains` on the deterministic fields | — |
| Intent unclear | no request detail, samples or note for the output | `Not run: intent unclear.`, a question in `open_questions`, no file written | — |
| Target fails to start | `Failed to execute test target` | One `fail` row with the error; verdict `fail` | A check failure, not `blocked` |

**Decisions (2026-11-11, user):**
- **Outside services:** mock them. Each processor that calls an outside service (the `dry-run.md` §1 list) gets a `mocks:` entry in every case, keyed by its label, or by its path when it has none. The mock is a `mapping` giving what the intent says the service returns.
- **Existing test file:** run it as is and never edit it. Its failures are reported, and fixes to it come in story 2.11.
- **Case counts:** counted in the skill. Test counts the cases in the file, and passed = cases − failed cases. `rpcn_check` doesn't change.
- **Plan size:** kept whole, over the size guideline.
- **Resources (2026-11-11, review):** a cache or rate-limit resource defined in `<res>` stops `rpk connect test` from starting without `--resources`, on both binaries (`cache resource 'seen' was not found`). When `<res>` exists, Test runs `test --resources <res> <dir>/<pipeline>`, as lint does, and the Unit tests line names that command. With no `<res>`, it still passes no flags.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `eb552e4ff6476ab8a378cd19de0008054e77fb89`.

- **`R/tools/shared/rpcn_check/rpcn_check.py` `cmd_test` (around 1490) and `SCHEMA.md` §`test`:**
  - These already parse targets and failures into `failures[{target, case, line, message}]`. Reuse them, with no contract change.
  - Add real-binary tests to `tests/test_rpcn_check.py` (see `RPCN_TEST_BINARIES` near 2255) for the AD-15 facts: sibling discovery, a `json_contains` failure, a label mock, an unset `${VAR}`, and `from` resolving from the working directory. Base them on the probe files below.
- **`R/tools/shared/formats/test-report-format.md` §5 Unit tests:**
  - **Content:** the line `` `<name>_benthos_test.yaml`: <p> passed, <f> failed. ``, then on failure a table `case`, `line`, `message`, plus the `Not run:` lines from the matrix.
  - **Summary line:** `Unit tests: <p> passed, <f> failed` or `not run`.
  - The example (around 246) is already in this form.
- **`R/skills/rpcn-test/`:**
  - `SKILL.md` (4,798 characters, full) gets a fenced `uv run …/rpcn_check.py test <dir>/<pipeline>` after the dry run. Pay for it by trimming wording, as story 2.8 did.
  - The description gains "writes and runs rpk connect test cases" and a trigger phrase. It is 928 characters, with a 1,024 limit.
  - New `references/unit-tests.md`: when the file is written, the case shape (`target_processors: /pipeline/processors`, `input_batch`, `output_batches` with `json_equals` or `json_contains`), the intent rule, the mocks, the existing file, the counts, the section, and the proposed fix with a fix check in the temp folder.
  - `report-writing.md`: drop "Unit tests: Not run: not in this version", and the verdict line adds "no failed case".
  - `status-block.md`: `checks.tests` folds in the unit tests, and `artifacts` lists the test file when it was written.
- **`R/skills/rpcn-author/references/apply-report.md`:** no change. It already treats `<name>_benthos_test.yaml` as Test's file.
- **`R/SOURCES.md`:** rows for the facts above, from benthos `internal/cli/test` at both pins, MIT.
- **`R/evals/`:** one trigger positive, `rpcn-test__trigger_unit_tests` ("write rpk connect unit tests for my pipeline"), plus the README counts.
- **`T/run_scenarios.py`:** a new `[[unit]]` check, `{file, ok, report?}`, modelled on `[[lint]]` (`lint_args` and `evaluate_lint_all`, around 560–606; wired near 1625; key schema near 221).
  - It runs the installed `rpcn_check.py test <file>` from the run folder on each binary in `RPCN_TEST_BINARIES`.
  - It expects `ok`. When `report` is given, every `failures[].case` must appear in that report.
  - Add it to `has_file_checks` (around 297) and to the README.
- **New `T/scenarios/`,** all with `no_cd`, a pipeline in `pipes/` and a non-default name:
  - `rpcn-test__unit_pass`: `payments.yaml` with a `.blobl`, its samples file, and a labelled `http` processor (`${ENRICH_URL:http://localhost:1}`). Cases are written and pass; `[[unit]] ok=true`; verdict `pass`.
  - `rpcn-test__unit_bug`: an inline mapping that computes `total * 10` for "total in cents"; no samples. `[[unit]] ok=false`, with the failing cases in the report; verdict `fail`; `+++ b/<name>.yaml`.
  - `rpcn-test__unit_existing`: a user test file with one wrong case, which stays `unchanged`; that case is named; verdict `fail`.
- **`T/tests/test_run_scenarios.py`:** `[[unit]]` parsing and evaluation (fake envelopes), and the new scenarios in `NAMES`.
- **Probe files** (scratchpad, not committed): `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/p29b/`.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/` (real-binary tests, format §5), then `sync_shared.py`.
- [x] `R/skills/rpcn-test/` (`SKILL.md`, `unit-tests.md`, `report-writing.md`, `status-block.md`), within the size limit.
- [x] `R/SOURCES.md` and `R/evals/` (case and README).
- [x] `T/run_scenarios.py` `[[unit]]`, `T/README.md`, `T/tests/test_run_scenarios.py`, and the new `T/scenarios/rpcn-test__unit_*`.

**Acceptance Criteria:**
- **Given** the repo, **when** the validator, `sync_shared --check`, all `tools/` suites and the `rpcn_check` tests on both binaries run, **then** all pass, with no new warning.
- **Given** both binaries, **when** every non-compare scenario runs (`--jobs 4 --runs 1 --no-judge`), **then** all pass, including the new `unit_*` scenarios whose `[[unit]]` check runs `rpcn_check test` with no extra flags.
- **Given** the reviewed, committed tree, **when** `run_evals.py` runs, **then** it passes and a `dirty: false` record is committed. Report the wall time, the first measured since the speed-up.

## Implementation Notes

- Real-binary facts: `RealBinaryCommandsTest.test_test_unit_case_facts` (sibling discovery from the project root, `from` from the working directory, a label mock and a JSON-pointer path mock in place of two `http` processors, one with an unset `${VAR}` URL, `json_contains` and `json_equals`, a failing `json_contains` case with its line, and the same case failing without mocks) and `test_test_dropped_messages` (a dropped message has no output entry; `output_batches: []`; `wrong batch count`). One `SOURCES.md` row covers them.
- `SKILL.md` is 4,803 characters after the review fixes (was 4,798) (limit 4,803): paid for by trimming wording in Steps 1-5 and Next. Description 999 characters, with the trigger phrase "write rpk connect unit tests". `Exit 2 ... (but blobl, run, test)`: `unit-tests.md` handles the `test` exit 2.
- `unit-tests.md` mocks a `resource` processor only when its resource calls an outside service (`dry-run.md` §1); the run passes `--resources <res>` when `<res>` exists (Resources decision). An existing file's failures get a pipeline diff only when the request or design note agrees with the case, else a question.
- Smoke run (2026-11-11, both binaries, `--jobs 4 --runs 1 --no-judge`, all 26 non-compare scenarios): all PASS, about $8.50 (`runs/20261111-155019`). Not yet done: review, commit, and the `run_evals.py` record.
- `[[unit]]` fails a run whose `rpcn_check test` printed `No tests were found`, so a never-written file can't pass as `ok = false`.
- **Matrix audit follow-up (2026-11-11, user):** `rpcn-test__lint_broken` also checks `Unit tests: not run`. `rpcn-test__unit_pass` has a `stamp` processor that adds `checked_at: now()`, so its cases must use `json_contains`. Both passed 1/1 on both binaries. "Intent unclear" and "target fails to start" are deferred in `deferred-work.md`.
- **After the review fixes:** the validator shows no new warning (`rpcn-test` is 4,803 characters, exactly the limit). `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries (185 tests) and T's tests pass. Smoke run with `--jobs 4 --runs 1 --no-judge`, 26 non-compare scenarios: 26/26 on both binaries (`T/runs/20261111-164303`).
- **Eval record:** `evals/results/2026-11-11-f4965b3b0001.json` passed with `dirty: false`, at $32.97, on the first full run. Trigger accuracy was 1.0, and all 26 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. Wall time was 27 minutes (16:48–17:15), the first full run since the speed-up. The trigger gate took 226 s, against 954 s for story 2.8. `run_evals`' monotonic timer reads 1,144 s, so the 8-minute gap is probably a system suspend.
- **Pushed:** `134af75..6cc14e6`. CI run 43250217148 was green.

## Plan Change Log

- **2026-11-11, review (intent renegotiated by the user):**
  - **Trigger:** the review found, and both binaries confirmed, that a local cache defined in `<res>` makes the target fail to start without `--resources`. The skill would report every case as failed and propose a fix that can't work.
  - **Amended:** the "no extra flags" Always and Never lines, plus a Resources decision.
  - **Not reverted:** the user chose to patch in place, as in story 2.8. The change is contained in `unit-tests.md`, `SKILL.md`'s `test` line, the format's §5 and a real-binary test.
  - **KEEP:** the intent rule, mocks, the existing-file rule, counts in the skill, the `[[unit]]` check and the three scenarios.

## Review Triage Log

Quick pass: 0 high, 3 medium, 4 low, 0 false, 0 maybe-false. One finding changed frozen intent, so it went to the user as an intent gap. The user decided it and chose to patch in place (Plan Change Log).

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A cache or rate-limit resource in `<res>` stops the target from starting without `--resources` | medium | intent_gap, then patch | Probed on both binaries: `cache resource 'seen' was not found` without the flag, and a pass with it. The user chose to pass `--resources <res>`. A real-binary test covers it. |
| `ok = false` in `[[unit]]` passes with no failing case (an init error or a malformed file) | medium | patch | `evaluate_unit` now needs `data.failures` on every binary. The unit test covers an init-only failure and a parse failure. |
| Some exit-1 shapes have no rule (`test target failed`, `test exited N`, an unparsable test file) | medium | patch | Probed: a bad test file gives `Failed to obtain test targets…`, exit 1. `unit-tests.md` §4 treats any exit 1 with no failures as a target that failed to start. |
| "No tests were found" gives `-1 passed` | low | patch | `<p>` is never below 0: `0 passed, 1 failed`. |
| The no-mocks step asserts only exit 1 | low | patch | It now asserts the failure is the case `contains cents`. |
| `content_equals` and a nested `branch` mock path have no AD-15 proof | low | patch | A real-binary test on both binaries, and the `SOURCES.md` row extended. |
| The `Not run:` forms differ between the format and `unit-tests.md` | low | patch | The format adds `Not run: <message>` for exit 2, and the Summary line is `Unit tests: not run`. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, every `tools/tests` suite, and the `rpcn_check` tests with `RPCN_TEST_BINARIES` pointing at `.cache/rpcn/{4.100.0,4.115.0}/redpanda-connect`: all pass.
- In `T`: `uv run tests/test_run_scenarios.py`, then the smoke run from the AC (about $7).
