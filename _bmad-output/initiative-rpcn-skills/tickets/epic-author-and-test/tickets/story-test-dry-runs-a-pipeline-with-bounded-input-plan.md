---
title: 'Test dry-runs a pipeline with bounded input'
type: 'feature'
ticket: '8'
created: '2026-11-11'
status: done
baseline_revision: '1d1bec03f0c022366a3bc5846f88947a20420850'
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

**Problem:** a pipeline can lint clean and pass its samples, yet fail on real messages at runtime. For example, a mapping can meet a field of the wrong type. Nothing in rpcn-test runs the whole pipeline.

**Approach:**
- rpcn-test dry-runs the pipeline through `rpcn_check run` with a bounded input: a fixed set of messages fed through stdin in place of the real input. The output goes to stdout in place of the real sink.
- The pipeline YAML is never edited (AD-6).
- The result goes in a new **Dry run** section of the test report: passed, or each runtime error.

## Boundaries & Constraints

**Always:**
- **AD-6 and AD-4:** the pipeline YAML and `.blobl` files are never edited. Bounding happens through the binary's own flags, inside `rpcn_check`.
- **AD-15:** both behaviour facts are proved by `rpcn_check` tests on both binaries, with `SOURCES.md` rows:
  - `--set` with an object replaces the input or output;
  - a mapping error logs `level=error … path=…` and exits 0.
- **Size:** `SKILL.md` files stay at 4,803 characters or less, so new behaviour goes in references. Shared files change only under `tools/shared/`, then `sync_shared.py` runs.
- **Readers keep working:** every reader of a test report reads both the old and the new format (`hash --check`, rpcn-author's apply-report, the T fixtures).

**Never:**
- A dry run against real inputs, outputs or brokers.
- Unit test cases (story 2.9).
- A new hand-off file beside the pipeline.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Working pipeline | lints clean, a valid bounded input | Dry run `passed`, the outputs are listed, the verdict is unaffected | — |
| Runtime failure | lints clean, a mapping error on one message (such as `total: "x"`) | Dry run `failed`, with the error, its processor path and the message. Verdict `fail`, with a proposed fix | The binary exits 0, so `rpcn_check` detects a message still errored at the output (decision 2026-11-11, review) |
| Lint fails | lint errors | Dry run `Not run: lint failed.` | — |
| Hangs | the pipeline doesn't finish within the timeout | `failed`, with "timed out", and the outputs so far | `run` exit 2 on timeout is a check failure, not `blocked` |
| Needs an outside service | an `http_client`, `cache` or `sql` processor, or a resource | `Not run: needs <component>`, verdict unaffected | — |
| Old report | a `test-report@1` file | `hash --check` and Author still read it | — |

**Decisions (2026-11-11, user):**
- **Bounding:** `rpcn_check run --bounded` adds `--set 'input={"stdin":{}}'` and `--set 'output={"stdout":{}}'` to the binary call, and `--input` feeds the messages through stdin. This is an additive change to AD-4's `run`, recorded in `SCHEMA.md`.
- **Input messages:** Test writes them from intent (the request, the design note's Inputs, the samples' inputs) into a temporary file, never by running the pipeline, and records the messages used in the Dry run section. There is no new hand-off file.
- **Outside services:** when a processor or resource calls an outside service (such as `http_client`, a `cache` or `sql`), the Dry run section is `Not run: needs <component>`, and the verdict is unaffected.
- **Format:** bump to `test-report@2`. rpcn-test writes @2. `rpcn_check` (`KNOWN_FORMATS`) and rpcn-author accept both @1 and @2, and the format doc keeps a short note on @1.
- **Plan size:** the plan is kept whole, over the size guideline.
- **Failure rule (2026-11-11, review):** a dry-run message fails only when it reaches the output still errored (`errored()`), which an output processor added by `--bounded` detects. Errors that a later `catch` handles (DLQ routing) pass. Log lines give only the processor path. `--bounded` also pins `logger.format=logfmt` and `logger.level=info`. On both binaries, a caught error still logs `level=error`.
- **Dropped processors (2026-11-11, review):** `--bounded` replaces the whole input and output, so the dry run covers `pipeline.processors` only. When the pipeline has input or output processors, the Dry run section says which were not run.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `71c8403fccb5313aa3c81d40f941b3c673c6c65b`.

- **`R/tools/shared/rpcn_check/rpcn_check.py` `run`:**
  - The contract is in `SCHEMA.md` §`run`. Today a non-zero exit is the only failure.
  - Add runtime-error detection: stderr lines with `level=error` and a `path=` (a processor) go into `data.runtime_errors[]` as `{path, message}`, and any of them gives exit 1.
  - Add `--bounded`, which adds the two `--set` flags. It needs `--input`.
  - Tests go in `tests/test_rpcn_check.py`: fake binaries, plus real-binary tests for both facts.
- **`R/tools/shared/formats/test-report-format.md`:**
  - the Dry run section (status, input messages, outputs, errors) and its place in the section order;
  - the verdict rule: a failed dry run means `fail`;
  - `test-report@2`, with `KNOWN_FORMATS` in `rpcn_check.py` updated and the example hashes kept valid.
- **`R/skills/rpcn-test/`:** `SKILL.md` (4,800 characters) gets a fenced `run` command, paid for by trimming wording. A new `references/dry-run.md` covers the input from intent, the outside-service rule, the section and the proposed fix. `report-writing.md` and `status-block.md` (`checks.tests` folds in the dry run) are updated, and the shared copies are synced.
- **`R/skills/rpcn-author/references/apply-report.md`:** reads @1 and @2. Proposed changes are unchanged.
- **`R/SOURCES.md`:** two rows, the `--set` replacement and the runtime-error log, from benthos at both pins, MIT, with the new tests as proof.
- **`R/evals/`:** one trigger positive ("dry-run my pipeline"), plus README counts.
- **New `T/scenarios/`**, with `no_cd` and `pipes/`:
  - `rpcn-test__dry_run_pass`: verdict `pass`, the report contains `passed`
  - `rpcn-test__dry_run_error`: lints clean, but a mapping error on one fixture-intent message; verdict `fail`; the report contains the error and its processor path
- **T fixtures:** the existing `test-report@1` fixtures (`apply_report`, `stale_report`, `draft_report`) must still be accepted. Leave them at @1 as the old-report row's proof.
- **`T/tests/test_run_scenarios.py`:** `NAMES` and the fixture tests.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/rpcn_check/` (code, `SCHEMA.md`, tests) and `R/tools/shared/formats/test-report-format.md`, then `sync_shared.py`.
- [x] `R/skills/rpcn-test/` and `R/skills/rpcn-author/references/apply-report.md`, within the size limit.
- [x] `R/SOURCES.md` and `R/evals/` (case and README).
- [x] `T/scenarios/rpcn-test__dry_run_{pass,error}/` and `T/tests/test_run_scenarios.py`.

**Acceptance Criteria:**
- **Given** the repo, **when** the validator, `sync_shared --check`, all `tools/` suites and the `rpcn_check` tests on both binaries run, **then** all pass, with no new warning.
- **Given** both binaries, **when** all author and test scenarios except the comparison smoke-run (`--runs 1 --no-judge`), **then** all pass, including the @1-report author scenarios.
- **Given** the reviewed, committed tree, **when** `run_evals.py` runs (about $24), **then** it passes and a `dirty: false` record is committed.

## Implementation Notes

- **`run` runtime errors apply without `--bounded` too.** As the Code Map says, any `level=error` log line with a `path=` gives exit 1, whatever the flags. The old real-binary `test_run` fed `samples.jsonl` (line 2 is not JSON) and expected exit 0; it now expects exit 1 with one `runtime_errors` entry at `root.pipeline.processors.0`. `data.runtime_errors` is always present (additive, no schema bump).
- **`KNOWN_FORMATS` holds tuples of majors** (`{"design": (1,), "test-report": (1, 2)}`), so `format_known` means "the major is one of its entries". The `hash` unit test's default report is now `@2`; `test_old_major_still_read` proves `@1`, and `test_unknown_major` uses `@3`. `handoff-header.md`'s example header was bumped to `@2` with the report example (a test requires them to match).
- **Section order:** Dry run is section 4, between Bloblang samples and Unit tests. The report example now has a passed Dry run whose outputs were produced by both binaries from the example `orders.yaml` (the sha256 values are unchanged).
- **Env vars (not in the plan):** `run` has no `--skip-env-var-check`, so a pipeline with `${VAR}` and no default fails at once with `required environment variables were not set`, even when the var is only in the replaced input or output (seen on both binaries with the format example). `dry-run.md` handles it: Test writes `<name>.dry-run.env` in its temp folder (the user's env file lines, then `VAR=dry-run` for each missing one) and runs once more with it. This is the one `--env-file` the user did not name. The new scenarios use no env vars, so no scenario exercises it yet.
- **`checks.tests`** folds the samples and the dry run: `fail` if either failed, `pass` if at least one ran and none failed, `skipped` if neither ran. `samples.md` section 5 now points to `status-block.md`.
- **SKILL.md is 4,798 characters** (limit 4,803). The `run` command and the description's "dry-runs it" / "dry-run my pipeline" were paid for by trimming wording (the JSON field list, the "0 errors" Next line, "the run can't test", and similar).
- **Outside-service list** in `dry-run.md` §1 goes beyond the plan's three examples (`http_client`, `cache`, `sql`): other network processors, `command`/`subprocess`/`wasm`, a `resource` processor, and cache or rate-limit resources that are not local (`memory`, `lru`).
- **Smoke run (2026-11-11, `--runs 1 --no-judge`, both binaries, every scenario but `rpcn-test__compare_lint`):** 21 of 22 passed, including both new dry-run scenarios and the `@1` author scenarios. `rpcn-author__apply_report` failed once: in the rpcn-test half of the loop, the agent applied the old report's item 6 (a rename in `orders_benthos_test.yaml`) because Test owns that file, which breaks the scenario's `unchanged` check. A re-run passed 2/2. This is not something this story's code changes; it may come back in the 3-run eval.
- **Matrix audit follow-up (2026-11-11, user):** `rpcn-test__lint_broken` now checks that its report contains `Not run: lint failed.`. The new `rpcn-test__dry_run_needs_service` has a pipeline with an `http` processor (`${ENRICH_URL:http://localhost:1}`) and expects `Not run: needs http` with verdict `pass`. `dry-run.md`'s outside-service list only named `http_client`, so it now also names the `http` processor (this changes `skills/`). Both scenarios passed 1/1 on both binaries (`--runs 1 --no-judge`), and T's unit tests pass.
- **Review fixes (2026-11-11, after the Failure rule and Dropped processors decisions):**
  - **`run --bounded` flags:** it adds `--set logger.format=logfmt`, `--set logger.level=info` and `--set output.processors=[{"mapping":"<marker>"}]`, each value comma-free. A message still `errored()` at the output becomes a `__rpcn_check_unhandled_error__` line (`error()` plus `content().string()`).
  - **Marker lines:** `rpcn_check` moves them from `outputs` into `runtime_errors` as `{path, message, input}`. `path` comes from the first unmatched logged error with the same message, else `null`. Only marker lines fail.
  - **Without `--bounded`:** detection stays log-based, with `input` `null`.
  - **Real-binary proof:** on both binaries, a caught error is logged but its bounded run exits 0, and a `logger: {level: none, format: json}` pipeline is still detected.
  - **Docs:** `SCHEMA.md` and `SOURCES.md` are updated. `dry-run.md` and the format's Dry run section are rewritten: they cover `pipeline.processors` only, with a `Skipped:` line, and the outside-service rule now only counts components that call out. Timeout wording now matches `rpcn_check`, errors from a non-zero exit are listed, the failing message comes from the marker, non-JSON input goes in a `text` block, the `.blobl` fix check uses its samples or is `(unverified)`, and the temp folder rule is named directly.
  - **`SKILL.md`:** notes the `dry-run.md` env-file exception.
  - **T:** `dry_run_error` also checks `"total":"12.50"`. Item 6 in the `apply_report`, `stale_report` and `draft_report` fixture reports no longer tells rpcn-test to apply the rename now; the three reports keep their byte relationships.
  - **Smoke run:** `rpcn-test__dry_run_*` and `rpcn-author__apply_report` passed 1/1 on both binaries.
- **After the review fixes:** the validator passes with no new warning (`rpcn-author` 4,792 characters, `rpcn-test` 4,798), and so do `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries, and T's tests. Smoke run of 23 scenarios (everything except `compare_lint`): 23/23 pass on both binaries (`T/runs/20261111-094818`).
- **Eval record:** `evals/results/2026-11-11-3c6d8e1c18bd.json` passed with `dirty: false`, at $26.96, on the first full run. Trigger accuracy was 1.0, and all 23 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. That includes the @1-report author scenarios and the reworded `apply_report` loop.
- **Pushed:** `1d1bec0..0e32a44`. CI run 43062637944 was green.

## Plan Change Log

- **2026-11-11, review (intent renegotiated by the user):**
  - **Trigger:** a handled error (`catch`, DLQ) still logs `level=error` on both binaries, so log-based detection failed correct pipelines. `--bounded` also silently dropped input and output processors.
  - **Amended:** the frozen matrix row and two decisions above.
  - **Not reverted:** the code was patched in place rather than reverted. The change is contained in `run --bounded` and `dry-run.md`, and everything else in the diff stands.
  - **KEEP:** `--bounded`'s input and output replacement, `test-report@2` with @1 accepted, the outside-service rule, and the scenarios.

## Review Triage Log

Quick pass: 0 high, 4 medium, 11 low, 1 false, 0 maybe-false. Two findings changed frozen intent, so they went to the user as an intent gap. The user decided them, and the code was patched in place (Plan Change Log).

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A handled error (`catch`, DLQ) still counts as a runtime failure | medium | intent_gap, then patch | Probed on both binaries: a caught error still logs `level=error`. The user chose "unhandled at the output": a `--bounded` marker processor checks `errored()`. Real-binary tests cover caught and uncaught errors. |
| A JSON or silent logger hides every runtime error | medium | patch | `--bounded` pins `logger.format=logfmt` and `logger.level=info`, with a real-binary test using a JSON logger at level `none`. |
| `--bounded` silently drops input and output processors and routing | medium | intent_gap, then patch | The user chose to state the limit: the Dry run section gets a `Skipped: <what>.` line. |
| Network `input_resources` and `output_resources` missing from the outside-service list | medium | patch | Added. |
| The outside-service rule contradicts itself on `cache` and `resource` processors | low | patch | Local caches and resources no longer count. |
| Timeout wording and data don't match `rpcn_check` | low | patch | Aligned, and runtime errors logged before the timeout are kept as rows. |
| Exit 1 drops errors from a non-zero binary exit | low | patch | They are listed as rows too. |
| The failing message may be missing, and the scenario doesn't assert it | low | patch | Each row takes the message from the marker's `input`. `dry_run_error` checks `"total":"12.50"`. |
| Non-JSON input conflicts with the format's `json` block | low | patch | Non-JSON goes verbatim in a fenced `text` block. |
| The `.blobl` fix check feeds the pipeline's input to a later mapping | low | patch | A fix is checked with samples, else marked `(unverified)`. |
| A step reference points to the wrong step | low | patch | The temp folder rule is named directly. |
| `SKILL.md`'s `--env-file` rule contradicts `dry-run.md` | low | patch | Added the exception (4,798 characters). |
| `SCHEMA.md` synopsis lists `--input` twice | low | patch | Fixed. |
| `kafka*` in a hand-written reference would trip AD-11's deprecated scan | low | patch | Now "`redpanda` or any Kafka-protocol component". |
| (own) `apply_report` loop is flaky, because item 6 invited rpcn-test to apply it | low | patch | Item 6 reworded in all three fixture reports, which keep their byte relationships. |
| A stray `orders_benthos_test.yaml` in T | false | reject | It is the user's manual-test leftover from story 2.5, not smoke-run output, and is never committed. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, every `tools/tests` suite, and the `rpcn_check` tests with `RPCN_TEST_BINARIES`: all pass.
- In `T`: `uv run tests/test_run_scenarios.py`, then the smoke run in the AC.
