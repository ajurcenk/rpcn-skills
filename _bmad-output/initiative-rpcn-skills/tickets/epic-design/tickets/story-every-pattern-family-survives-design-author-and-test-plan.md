---
title: 'Every pattern family survives Design, Author and Test'
type: 'feature'
ticket: '6'
created: '2026-11-23'
status: 'built'
baseline_revision: 'afd2c776063f9660660a54a2361cfe3d60c0c4f4'
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

**Problem:** story 3.1's tracer proves Design → Author → Test only for a plain DLQ. Story 3.2's pattern scenarios stop at the note. Epic R7 (and Done when) asks for each pattern family: the note names the pattern, Author's pipeline contains it and lints clean, and Test's Design check reports no mismatch.

**Approach:**
- **One three-step headless chain per family**, laid out like `rpcn-design__chain_tracer`:
  - DLQ and retries;
  - batching;
  - idempotency;
  - ordering.
- **Each chain:**
  - Step 1 is the matching 3.2 pattern request, in its own subfolder with a non-default name.
  - Step 2 is "Build the pipeline from its design note".
  - Step 3 is "Test the pipeline".
- **Checks:**
  - The note is ready and names the pattern's Components rows.
  - The pipeline contains the pattern's YAML keys and lints clean on 4.100.0 and 4.117.0.
  - The test report is ready, and its Design check reads `0 deviation-recorded, 0 mismatch`, with at least one `ok`.
- **When a chain fails,** find which step departs and fix that skill's text, not the check.

**Decision (2026-11-23, user):** 3.6 may fix any of the three skills (Design, Author or Test), whichever step departs, with the smallest text change. R7 needs the whole chain, so the epic's "Out: YAML generation (Author, epic 2)" gives way for this story. Each fix is proved by its chain and by that skill's existing scenarios.

**Decision (2026-11-23, user, after the final smoke):** `chain_idempotency` passed 1/2 (`T/runs/20261123-135746`). Test found two gaps in Design's dedupe note, and both are fixed in Design:
1. **A message missing the dedupe key** fails processing (Author's required-field rule, story 2.17). Pattern 5's Note says so, and says where it goes: the failure target, or as the request says.
2. **Dedupe before the write:** a key is recorded before the write. If every output fails, the replayed message is dropped as a repeat and lost. First prove the replay fact with a real-binary `rpcn_check` test on 4.100.0 and 4.117.0, with a SOURCES row (AD-15). Then pattern 5 states the case in Delivery and ordering, as the Basis allows. If the binary doesn't behave this way, report that and state nothing.
- **Smoke only.** The record is 3.9's `--with-compare` run.

## Boundaries & Constraints

**Always:**
- Sessions run on 4.117.0, and the lints run on both pins.
- Every `SKILL.md` stays at or under 4,803 characters, with no validator warnings for the three skills.
- `design@1` is unchanged.
- Smoke only: each chain at `--runs 2`, then every `rpcn-design__*` scenario once. 3.6, 3.8 and 3.9 are pushed together after 3.9's record.

**Never:**
- Weakening a check to get a chain through.
- A pattern in the pipeline that the note doesn't name.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| DLQ and retries | 3.2's `pattern_dlq_retry` request | note: `retry`, `fallback`, `switch` rows; pipeline: `retry` with 3 retries, `fallback` to `orders.dlq`, `switch` on `errored()`; Design check 0 mismatch | — |
| Batching | 3.2's `pattern_batching` request | note: `batching.count: 100`, `archive`; pipeline: `count: 100` and `archive`; lints clean; 0 mismatch | — |
| Idempotency | 3.2's `pattern_idempotency` request | note: `dedupe` and `memory` cache; pipeline: `dedupe` on `event_id` with a `memory` cache; 0 mismatch | — |
| Ordering | 3.2's `pattern_ordering` request | note: `max_in_flight: 1`; pipeline: `max_in_flight: 1` on the API output; 0 mismatch | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `125c0d0008a90675806fc934e176eb85553e015b`; leave the untracked `orders_benthos_test.yaml` alone).

- **T, new chains** `T/scenarios/rpcn-design__chain_<family>/`, each with `step1.md`–`step3.md`, `expect.toml` and an empty `fixtures/<sub>/.keep`:
  - **Families:** `dlq_retry`, `batching`, `idempotency`, `ordering`.
  - **Copy the tracer:** `T/scenarios/rpcn-design__chain_tracer/expect.toml` for `install`, `skill`, `max_turns`, `timeout_s`, `[[step]]` / `[step.status]`, `[[report]]` on the note and the test report (`bare_inputs`), `[[lint]]`, and the note's readiness `[[file]]`.
  - **Step 1:** the request text of `T/scenarios/rpcn-design__pattern_<family>/prompt.md` (`dlq_retry`, `batching`, `idempotency`, `ordering`), under a new subfolder and name. For example `post/order_send`, `bucket/click_store`, `once/event_once` and `seq/customer_seq`. Keep "This run is unattended".
  - **Step 1 note checks:** the 3.2 scenario's `contains` and `lacks`, unchanged. Batching uses an S3 sink, which lints without credentials (`${ARCHIVE_BUCKET}`).
  - **The pipeline's `[[file]] contains`** holds that family's keys:
    - DLQ and retries: `retry:`, `max_retries: 3`, `fallback:`, `switch:`, `errored()`, `orders.dlq`;
    - batching: `count: 100`, `archive`;
    - idempotency: `dedupe`, `event_id`, `memory`;
    - ordering: `max_in_flight: 1`.
  - **The test report's `[[file]] contains`:** `## Design check`, `- file: <name>.design.md` and `0 deviation-recorded, 0 mismatch`.
- **`T/tests/test_run_scenarios.py`:** a `ShippedDesignChainScenarioTests` class beside `ShippedDesignTracerScenarioTests`. It asserts each chain's steps, subfolder, step-1 prompt text and family keys. Add a test that step 1's request matches its 3.2 pattern scenario's request apart from the name.
- **Skill fixes (per the decision):** look at the failing step's transcript first. The likely places are rpcn-author's `references/design-note.md` (building a note's patterns), rpcn-test's Design-check reference, and rpcn-design's `references/patterns.md`.
- **`R/evals/README.md`:** the count (60 pass scenarios) and cost. Each chain costs about $1.6 a run.

## Tasks & Acceptance

**Execution:**
- [x] T: the four chains and their tests; README count.
- [x] Smoke: each chain at `--runs 2` on both pins. Fix any departure per the decision, then re-smoke.
- [x] Smoke: every `rpcn-design__*` scenario once, plus each skill's scenarios that a fix touched. Record the results in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites (`rpcn_check` on both pins) and T's tests run, then all pass.
- Given the smoke run, when it finishes, then each chain passes 2/2: its pattern is in the note and in the pipeline, and the Design check reads `0 deviation-recorded, 0 mismatch`.
- Given the reviewed tree, when it is committed, then it stays local until 3.9's record.

## Implementation Notes

- T: four chains `rpcn-design__chain_{dlq_retry,batching,idempotency,ordering}` (subfolders `post/order_send`, `bucket/click_store`, `once/event_once`, `seq/customer_seq`), generated from the tracer layout and the 3.2 pattern scenarios. Step 1 is the 3.2 request with only the path renamed; the 3.2 note `contains`/`lacks` are copied unchanged. The test report check is `contains "0 deviation-recorded, 0 mismatch"` plus `lacks "Design check: 0 ok"` (at least one `ok`). `ShippedDesignChainScenarioTests` (2 tests) in `T/tests/test_run_scenarios.py`.
- Pipeline key checks read `<sub>/<name>.*yaml` (pipeline and resources file together): in the first smoke, idempotency failed 0/2 only because Author put the `memory` cache in `event_once.resources.yaml`, which pipeline-files.md allows.
- Skill fix (Design, `rpcn-design/references/patterns.md` pattern 5): the note now says how long the cache keeps a key (the request's window, else a `[non-blocking]` pick of the cache's `default_ttl` default from `fields caches memory`) and the cache row says `kept <window>`. Cause: run 2 of the second idempotency smoke had Test report Idempotency `mismatch` because `memory`'s 5m `default_ttl` limits a note that promised dropping repeats with no window. Design was the departing step. With the fix, both notes pick `5m`, Author writes `default_ttl: 5m`, and Test reports `ok`. SKILL.md files unchanged; validator shows no warnings for the three skills.
- Smoke (sessions on 4.117.0, lints on 4.100.0 and 4.117.0, `--no-judge`):
  - `runs/20261123-132440` (before the fix, `--runs 2`): dlq_retry 2/2, batching 2/2, ordering 2/2, idempotency 0/2 (the resources-file check, fixed above).
  - `runs/20261123-133243`: idempotency 1/2 (TTL mismatch and the `switch:` lacks, see Change Log).
  - `runs/20261123-133825` (after the fix): idempotency 2/2; `runs/20261123-134208`: `pattern_idempotency` 1/1.
  - `runs/20261123-134315`: all 25 `rpcn-design__*` scenarios once, 25/25 PASS, including the four chains and `chain_tracer`. Chains cost $1.53 to $1.92 a run.

- After the final smoke (user decision): `T/runs/20261123-135746` chain_idempotency 1/2, where Test found two gaps in run 1.
  - Missing dedupe key: pattern 5 now says, as intent, that a message missing the key goes to the failure target. It adds no component, since pattern 2 applies only by its own When.
  - Dedupe before a failed write: proved first. `RealBinaryCommandsTest.test_pattern_dedupe_before_a_failed_write_loses_it` shows, on 4.100.0 and 4.117.0, that `stdin` (`auto_replay_nacks` true) with `dedupe` before a `switch` that sends `e1` to `reject` prints only `e2` and ends. Without `dedupe`, the run replays `e1` until `--timeout 8`. New SOURCES.md row. Pattern 5's Delivery and ordering note states it as intent and cites the row.
  - `runs/20261123-150516` chain_idempotency 1/3:
    - Run 3: Design added a `| switch |` row for the missing key. Fixed by the wording above.
    - Run 1: the note said "Failed writes are not retried", so Author set `record_retries: 1` with a Deviations row, because `record_retries` defaults to 0 (unlimited, per `fields outputs redpanda` on both pins). Design was the departing step. Pattern 3 now says that with no retries asked for, the note says only that none were asked for, never that a write is not retried.
  - `runs/20261123-151037`: chain_idempotency 3/3, Design check `3 ok, 0 deviation-recorded, 0 mismatch` each time, with no `record_retries` and no `switch` row. `runs/20261123-151453`: pattern_idempotency 1/1 and chain_tracer 1/1.
  - The rpcn_check suite on both pins passed (193), as did the validator (no warnings; SKILL.md files unchanged) and T's tests (380).

- **Final smoke (2026-11-23, the final text):** all 25 `rpcn-design__*` scenarios once each, 25/25 PASS (`T/runs/20261123-151852`, about $16). The run includes the four family chains. Checks: validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` on both pins 193 passed; T 380 passed.
- **Not done here:** the record (3.9's `--with-compare` run) and the push, both together with 3.8 and 3.9.

## Plan Change Log

- 2026-11-23: the pipeline `[[file]]` checks use `<sub>/<name>.*yaml` instead of `<name>.yaml`, so a cache or output resource in the resources file counts (as in `rpcn-author__design_note`). The family keys are unchanged.
- 2026-11-23: added pipeline `lacks` for patterns the note doesn't name (`dedupe:` and `retry:` where the note has no such row). `switch:` was dropped from the non-DLQ chains' lacks: Author routes a message missing a required field through a `switch` to the DLQ (`rpcn-author/references/questions.md`), Test judged that Error handling `ok`, and `switch:` is not one of the plan's family keys.
- 2026-11-23 (review): pattern 5's retention sentence and `kept <window>` row now apply only to a `memory` cache (another cache gets the window as intent), and its Basis cites fields: `default_ttl`. The chains' pipeline `lacks` gained `max_in_flight: 1` (non-ordering chains) and `batching:` (non-batching chains). The batching chain's note must also hold `| archive |`. Every earlier smoke output already meets these checks.

- 2026-11-23 (after the final smoke, user decision): pattern 5 states where a message missing the key goes and the dedupe-before-a-failed-write fact (new real-binary test and SOURCES row). Pattern 3 says no retry claim when none are asked for.

## Review Triage Log

Quick pass (2026-11-23): 0 high, 2 medium, 3 low, 0 false. Four route to patch and one is rejected.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | Pattern 5's new key-retention text has no Basis: it cites only `SOURCES: dedupe` | medium | patch | AD-15: a run-time fact is cited as "fields: …". Add `fields: default_ttl` to pattern 5's Basis. |
| 2 | The retention sentence is unconditional, so for a `redis` request it states a window taken from `memory`'s fields, against the next sentence's "no claim about how that cache behaves" | medium | patch | Limit the window text and the `kept <window>` row to the `memory` cache. |
| 3 | `chain_batching` requires `archive` in the pipeline but never in the note | low | patch | Add a separate note `[[file]] contains` for the `archive` row. 3.2's copied checks stay unchanged. |
| 4 | The pipeline `lacks` cover only `dedupe:` and `retry:`, not another family's `max_in_flight: 1` or `batching:` | low | patch | Add `max_in_flight: 1` to the non-ordering chains and `batching:` to the non-batching chains, where those keys aren't named. |
| 5 | `max_in_flight: 1` is matched anywhere in the pipeline, not on the API output | low | reject | Tying it to the output needs a YAML-path check the runner doesn't have (new surface). Test's Design check judges the output path. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 2 --no-judge --scenario 'rpcn-design__chain_*'` -- all PASS
