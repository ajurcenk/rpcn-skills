---
title: 'A newcomer reaches a tested pipeline in under 10 minutes'
type: 'feature'
ticket: '8'
created: '2026-11-23'
status: 'done'
baseline_revision: '78c42113057223e4e08aabf457d6ca3da47de645'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** epic R8 (initiative R15) promises a newcomer goes from a plain request to a linted, tested pipeline in under 10 minutes. Nothing measures it. The chains check outcomes, and the runner logs each run's summed session time (`claude_duration_s`), but no check fails a run that is too slow.

**Approach:**
- **A runner check:** a new top-level `expect.toml` key `max_wall_s` (a positive number). The run fails the check `wall` when its `claude_duration_s` exceeds it. That value is the session time summed across a chain's steps, and the run's own lint and check time is not counted (as R8 says: "wall time summed across the chain's steps").
- **One end-to-end scenario,** `rpcn-design__newcomer_e2e`: three headless steps (Design, Author, Test) on a plain newcomer request with a light transform, a named dead-letter topic and a sample-friendly field.
  - **Checks:** a ready note, a pipeline that lints clean on both pins, a ready test report whose checks pass with `0 mismatch`, and `max_wall_s = 600`.
- **The record:** a scenario PASS in the record means every run stayed under 10 minutes. The record keeps per-scenario results, not durations, so no schema change.
- **Decision (2026-11-23, user, after the smoke):** `newcomer_e2e` met the time goal (179–250 s) but passed 1/3. Two real rpcn-author defects with non-JSON payloads caused it: the DLQ case's `root = this` fails and drops the error metadata, and a non-JSON payload is sometimes deleted instead of failed. Fix rpcn-author's references (its `SKILL.md` is at the size limit). The DLQ path sets error metadata with `mutation`, never `root = this`. A payload that can't be parsed is thrown, never deleted. Each behaviour is proved by a real-binary test and a SOURCES row on 4.100.0 and 4.117.0 (AD-15). rpcn-test's dry-run "routed by design" rule and its test-report-format note (both from this build) stay.
- **Smoke only.** 3.9's record covers it. The ticket's verify asks for 3/3, so the smoke runs it 3 times. Records run 2 (decision 2026-11-21).

## Boundaries & Constraints

**Always:**
- Sessions run on 4.117.0, and the lints run on both pins.
- `max_wall_s` is optional. A scenario without it gets no `wall` check, so every existing scenario is unchanged.
- Nothing under `skills/` changes, unless a smoke shows a skill makes the chain slow or fail. Then fix that skill's text, with the smallest change, as 3.6 did.

**Never:**
- Raising `max_wall_s` above 600, or counting only part of the chain, to make it pass.
- A newcomer request that names component or field names. It stays plain language.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| A run under the limit | `max_wall_s = 600`, a run of 300 s | check `wall` passes, its why giving both figures | — |
| A run over the limit | a run of 700 s | `wall` fails: "700.0 s over 600 s" | — |
| No `max_wall_s` | any existing scenario | no `wall` check | — |
| A bad value | `max_wall_s = 0` or `"ten"` | `SetupError` naming the key | as other keys |
| A chain stopped early | step 2 fails | `wall` still reports the summed time of the steps that ran; the scenario fails on step 2 anyway | — |

</frozen-after-approval>

## Code Map

`T` = `rpcn-test-skills` (local, baseline `afcc3b1b2c99a95068d86db03cdea4fbe6e8d233`; leave the untracked `orders_benthos_test.yaml` alone). `R` = `rpcn-skills`.

- **`T/run_scenarios.py`:**
  - **Expect keys:** `validate_expect`'s `top` set (line ~155) gets `max_wall_s`. Validate it like `timeout_s` (line ~174): a positive number, else `bad(...)`. `normalise_expect` (line ~339) defaults it to `None`.
  - **The check:** add a `check_wall(limit, seconds) -> Check` near `check_reply_contains` (line ~779). Call it where `run_checks` (line ~3023) assembles checks, using `run["claude_duration_s"]`. That value is set for single runs (line ~2988) and chains (line ~2911). If the value isn't available inside `run_checks`, append the check where the run is finalized instead, before `passed` is computed. Find the right spot, and make sure a failing `wall` fails the run.
- **`T/tests/test_run_scenarios.py`:** unit tests for the matrix rows: parse (valid, `0`, a string), `check_wall` under, over and equal, and no key meaning no check. Add one chain test with stubbed step durations that sum over the limit. Use the `StepExpectTests` (line ~4906) and `ExpectTests` (line ~126) patterns.
- **New `T/scenarios/rpcn-design__newcomer_e2e/`:** copy `T/scenarios/rpcn-design__chain_tracer/` (steps, `[step.status]`, `[[report]]` on the note and the report with `bare_inputs`, `[[lint]]`), with `max_wall_s = 600`.
  - **Step 1:** a plain request in a subfolder with a non-default name, for example `start/signup_stream`. For example: read JSON signups from the Redpanda topic `signups`, drop the ones with an empty email, lowercase the email, write the rest to the topic `signups_clean`, and send anything that fails to `signups.dlq`. Just the design; unattended.
  - **Steps 2 and 3:** as in the tracer, "build it from its design note" and "test it".
  - **Report checks:** `contains` `## Design check` and `0 mismatch`, and `lacks` `| fail |` (see the report format for the failing-check wording).
- **`T/tests/test_run_scenarios.py`:** a shipped-scenario test for `newcomer_e2e`: its steps, `max_wall_s == 600`, and the subfolder.
- **`T/README.md`:** document `max_wall_s` next to `timeout_s`.
- **`R/evals/README.md`:** the count (61 pass scenarios) and cost.

## Tasks & Acceptance

**Execution:**
- [ ] T runner: the `max_wall_s` key and the `wall` check, with its tests and README.
- [ ] T: the `newcomer_e2e` scenario and its shipped test. R README count.
- [ ] Smoke: `newcomer_e2e` at `--runs 3` on both pins, and every `rpcn-design__chain_*` once, so the new check is shown to leave scenarios without the key alone. Record each run's `claude_duration_s` in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when T's tests and all `tools/` suites run, then all pass.
- Given the smoke, when it finishes, then `newcomer_e2e` passes 3/3, every run under 600 s, with its `wall` check passing.
- Given the reviewed tree, when it is committed, then it stays local until 3.9's record.

## Implementation Notes

- T runner: `max_wall_s` validated in `validate_expect` like `timeout_s` (default `None`). `check_wall(limit, seconds)` gives `"<s> s over <limit> s"` (fail) or `"<s> s within <limit> s"`, and is appended in `run_once` after `run_checks`, using `run["claude_duration_s"]` (a chain stopped early sums the steps that ran). Tests: `ExpectTests.test_max_wall_s`, `WallCheckTests`, `StepProcessTests.test_wall_*` (a fake clock of 350 s/200 s per step), `ShippedNewcomerScenarioTests`.
- Scenario `rpcn-design__newcomer_e2e` (`start/signup_stream`). The report check also needs `**Verdict:** pass` (R8: "a passing test report") and lacks the backticked `` | `fail` | `` cell the format uses for sample rows.
- Smoke 1 (before any skill change): `newcomer_e2e` 2/3. Claude time 249.9 / 195.5 / 169.9 s. Run 1 had verdict `fail` only from the dry run: the mapping's errored message, which the pipeline routes to `signups.dlq` with a `switch` on `errored()`, counted as a dry-run failure. Every `rpcn-design__chain_*` passed 1/1, with no `wall` check.
- Skill fix (coordinator-directed, per Boundaries): `rpcn-test/references/dry-run.md` "Routed by design": when a `switch` output case's check is `errored()`, those runtime errors are listed under **Routed to the failure path:** instead of failing, and the Summary reads `Dry run: passed, <r> routed`. The shared `test-report-format.md` (synced to rpcn-test and rpcn-author) says the same, and SOURCES row "`switch` on `errored()`" lists dry-run.md. `report-writing.md`: with no note, `Not run: no design note.` without reading design-check.md (one `rpcn-test__dry_run_error` run had read it).
- Smoke 2 (after the fix): `rpcn-test__dry_run_{error,needs_service,pass}` all PASS 1/1. `newcomer_e2e` 1/3. Claude time 213.8 / 179.2 / 233.1 s, all under 600 s, `wall` passes in every run. Run 1's dry run read `passed, 1 routed`, so the fix works. The two failures are real pipeline defects rpcn-test found in Author's output, both on non-JSON payloads, which the note says go to `signups.dlq`: run 1's DLQ case runs `root = this` (it fails on non-JSON and loses the error metadata, a Design check `mismatch`), and run 3's mapping deletes a non-JSON payload silently (a unit test failed). Open: an rpcn-author fix, or a request/check change. Not done here.
- rpcn-author fix (user decision, after the smoke):
  - **Proved first,** with real-binary tests on 4.100.0 and 4.117.0 in `RealBinaryCommandsTest`:
    - `test_pattern_dlq_metadata_with_mutation_not_mapping`: on `not json`, a `mapping` with `root = this` plus `meta` gives no metadata and `errored()` true. A `mutation` keeps the payload and sets the metadata.
    - `test_pattern_non_json_deleted_by_match_failed_by_parse_json`: a `match` on `this.email` with a `deleted()` arm deletes `not json` silently. `content().parse_json()` leaves it errored.
  - **Two SOURCES.md rows** record these facts.
  - **The fix:** `skills/rpcn-author/references/questions.md` (Required fields) gets two bullets, citing both tests:
    - read a payload that may not parse with `content().parse_json()`, so it fails and is never deleted;
    - on the failure path, set the error metadata with a `mutation`, never a `mapping` with `root = this`.
  - **Checks:** the rpcn_check suite on both pins (195 passed), the validator (no errors or warnings), `sync_shared --check` (clean) and `tools/tests` plus `skills` (146 passed).
- Smoke 3 (after the rpcn-author fix):
  - `newcomer_e2e` PASS 3/3, with `wall` passing in every run. Claude time 163.2 / 204.3 / 178.4 s, about $1.25 a run.
  - `rpcn-author__implied_required`, `rpcn-author__design_note`, `rpcn-design__chain_dlq_retry` and `rpcn-design__chain_tracer` each PASS 1/1.

- **Final state (2026-11-23):** `newcomer_e2e` 3/3 (`T/runs/20261123-183631`: 188, 177, 173 s, about $1.46 a run). After the review patches, every chain and every `rpcn-test__dry_run_*` scenario passed once (`T/runs/20261123-180603`). Validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` on both pins 195 passed; T 388 passed. 3.8's smoke runs cost about $55 in total.
- **Not done here:** the record (3.9's `--with-compare` run, which covers 3.6 to 3.9) and the push.

- **Pushed:** `72cf82a..560f483`, with 3.6–3.9 together. CI run 45450913995 was green. The record is `evals/results/2026-11-23-d38b0a5cc8a4.json`. T commits stay local.

## Plan Change Log

- 2026-11-23: smoke showed skill text making the chain fail, so `skills/` changed under the Boundaries rule:
  - **rpcn-test** (`dry-run.md`, `report-writing.md`, and the shared `test-report-format.md` synced to rpcn-test and rpcn-author): an errored message that a `switch` case on `errored()` routes is reported as routed, not as a dry-run failure. Its format stays `test-report@2`, with no section change. Design-check.md is not read with no note.
  - **rpcn-author** (`questions.md`): non-JSON payloads fail and are never deleted, and failure-path metadata is set with `mutation`. Two new SOURCES rows, proved on both pins.
  - **The scenario's report check** also requires `**Verdict:** pass` (R8: "a passing test report"). It needs a new eval record, which 3.9's covers.

## Review Triage Log

- 2026-11-23, review round 1, all fixed:
  - **dry-run "Routed by design":** narrowed to a top-level `switch` whose first case is `errored()`, with at least one message in `data.outputs`.
  - **The format:** gets the same rule and the `, <r> routed` Summary suffix (synced). The SOURCES switch row lists the format and its copies.
  - **The metadata test:** re-proved on the advised form (a message errored by `root = this`, then `mutation: meta error = error()`), on both pins. Its SOURCES row is updated.
  - **questions.md:** "Both facts" now reads "These facts".
  - **`check_wall`:** prints the limit as given (`700.0 s over 600 s`).
  - **Tests:** the stopped-early wall test is now a three-step chain failing at step 2. The shipped test pins both `fail` lacks.
  - **evals README:** $1.25 a run, ~$53.10.
  - Smoke results above predate these edits.
- 2026-11-23, after the final smoke (`runs/20261123-182619`: chains and dry-run 9/9, newcomer 2/3):
  - **The failure:** run 3's Author followed the parse_json bullet with `$doc.merge(...)`, which turned `email` into an array.
  - **The fix:** the bullet now gives the full form: `root = content().parse_json()`, then each changed field set by assignment (`root.email = this.email.lowercase()`). The non-JSON test now proves exactly that form on both pins, and its SOURCES row is updated.
  - **Re-smoke** (`runs/20261123-183631`): newcomer_e2e PASS 3/3, Claude time 188.1 / 176.9 / 173.1 s, `wall` passing every run, about $1.46 a run. `rpcn-author__implied_required` PASS 3/3.

Quick pass (2026-11-23): 0 high, 4 medium, 7 low, 0 false. All eleven route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The dry-run "routed by design" rule passes a pipeline whose mapping fails on good input, even when every message goes to the DLQ | medium | patch | Narrow it: routed errors pass only when at least one message reaches the sink output. If every message errors, the dry run fails. |
| 2 | The rule assumes routing that is never run or proved: any `switch` with an `errored()` case, at any position, nested or not | medium | patch | Limit it to what the SOURCES fact proves: the top-level output is a `switch` whose first case's `check` is `errored()`. Anything else still fails. |
| 3 | The SOURCES `switch` on `errored()` row doesn't list `test-report-format.md` and its synced copies | low | patch | Add them. |
| 4 | The shared format doesn't define the Summary suffix `, <r> routed` | low | patch | Add it to the format's Summary spec, and sync. |
| 5 | rpcn-author `questions.md` says "Both facts" before four | low | patch | Say "These facts". |
| 6 | The `mutation` metadata test sets metadata on a message that isn't errored, not from `error()` on an errored one | medium | patch | Prove the failure-path case: a message errored by a `mapping`, then a `mutation` with `meta error = error()`, keeps its payload and sets the metadata. Update the row. |
| 7 | The `wall` message gives "600.0 s", not the matrix's "600 s" | low | patch | Print the limit as given (`600`), and update the test. |
| 8 | The "chain stopped early" test fails step 1, not step 2 | low | patch | Use a three-step fake chain where step 2 fails, and assert the summed time of steps 1–2. |
| 9 | Four chains weren't re-run after the rpcn-test and rpcn-author changes | medium | patch | After these patches, smoke every `rpcn-design__chain_*` and `rpcn-test__dry_run_*` scenario once, and `newcomer_e2e` 3 times. |
| 10 | The README says $1.30 a run; $1.25 was measured | low | patch | Use the measured figure and adjust the totals. |
| 11 | `ShippedNewcomerScenarioTests` doesn't check the backticked `fail` lacks | low | patch | Assert both forms. |

## Verification

**Commands:**
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `uv run tools/validate_skills.py`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `cd T && RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run run_scenarios.py --source local:<R> --runs 3 --no-judge --scenario rpcn-design__newcomer_e2e` -- PASS 3/3, `wall` pass
