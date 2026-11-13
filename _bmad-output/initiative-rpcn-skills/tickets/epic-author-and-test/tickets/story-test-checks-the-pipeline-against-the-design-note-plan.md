---
title: 'Test checks the pipeline against the design note'
type: 'feature'
ticket: '10'
created: '2026-11-12'
status: 'done'
baseline_revision: 'd957cec52f4d608dd088e2040d0fc71dee50000a'
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

**Problem:** the Design check section of the test report is always `Not run: not in this version of rpcn-test.` A pipeline can quietly drop the DLQ, break the ordering or lose the dedupe key the design note asks for, and nothing reports it. A departure Author recorded as a Deviations row looks the same as one nobody recorded (AD-7).

**Approach:**
- When a ready `<dir>/<name>.design.md` exists, rpcn-test reads the pipeline (and `<res>`) against the note's Error handling, Delivery and ordering, and Idempotency sections.
- It writes one Design check row per section: `ok`, `mismatch`, or `deviation-recorded` when an unresolved Deviations row with that `section` covers the departure.
- The note becomes a hashed report input, so a new Deviations row makes the report stale.
- A `mismatch` fails the verdict and `checks.tests`.

## Boundaries & Constraints

**Always:**
- **The note is read only** (design-format "Who writes what"). Test never edits it, and never edits the pipeline (AD-6).
- **The note counts only when ready:** `hash --check` reports it ready, and the format's Readiness list passes. Only then is it a report input, recorded as `<name>.design.md` (bare, relative to the report's folder).
- **One row per section, in the format's order.**
  - When a section has several findings, the worst result wins: `mismatch`, then `deviation-recorded`, then `ok`. The `finding` cell names them all.
  - A row with `resolved: yes` does not cover a departure.
  - A section that asks for nothing the pipeline can be checked against (`None.`, or the outside service's job, such as API-side dedupe) is `ok`, and its finding says why.
- **Summary line:** `Design check: <o> ok, <d> deviation-recorded, <m> mismatch`, or `Design check: not run`.
- **Size:** `SKILL.md` stays at 4,803 characters or less (today exactly 4,803), and the description at 1,024 or less (today 999). Pay by trimming or by sharing a fence. The detail goes in a new `references/design-check.md`. Shared files change only under `tools/shared/`, then `sync_shared.py` runs. rpcn-test needs `design-format.md` named in `SKILL.md` or a reference, which clears the validator's existing warning.
- **The report stays `test-report@2`.** The section and its columns already exist.

**Never:**
- Write or edit a Deviations row, or suggest that Test does. Recording a departure is rpcn-author's job.
- Check any note section other than these three.
- Run the pipeline against outside services for this check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Matching pipeline | ready note; the pipeline has the note's retries, fallback DLQ, ordering and dedupe key | 3 rows `ok`; `Design check: 3 ok, 0 deviation-recorded, 0 mismatch`; the verdict is unaffected; the note is in `inputs` | — |
| Missing DLQ, not recorded | ready note with a DLQ; the pipeline drops failed messages; no Deviations row | `Error handling` is `mismatch`; verdict `fail`; `checks.tests` `fail`; a Proposed changes item | — |
| Missing DLQ, recorded | the same pipeline; the note has an `Error handling` row with `resolved: no` | `Error handling` is `deviation-recorded`, with the row's `what` in `finding`; the verdict is unaffected by it | — |
| Recorded but resolved | the row says `resolved: yes` | `mismatch` | — |
| No note | no `<name>.design.md` | `Not run: no design note.`; the note is not in `inputs` | — |
| Not-ready note | draft, stale, malformed, or a `[blocking]` open decision | `Not run: design note not ready (<reason>).`; a line in `open_questions`; not an input | not `blocked` |

**Decisions (2026-11-12, user):**
- **Lint fails:** the Design check runs anyway, because it reads the YAML and doesn't need the binary. When the YAML doesn't parse at all, the section is `Not run: the pipeline does not parse.`
- **Mismatch fix:** each `mismatch` gets a Proposed changes item with a pipeline diff that makes the pipeline do what the section says. It is checked with lint as `fix-check.md` does, and marked `(unverified)` when lint can't confirm it. The item also says that keeping the departure means having rpcn-author record a Deviations row. Story 2.11 adds the full diagnosis.
- **Plan size:** kept whole, over the size guideline.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `362acb88ee76c266e4a35a6725495eb3cc00f64c`. The untracked `T/orders_benthos_test.yaml` is the user's file: leave it alone.

- **`R/skills/rpcn-test/SKILL.md`** (4,803 characters, full):
  - **Step 2:** first run `hash --check <dir>/<name>.design.md`.
    - Exit 2 for a missing file means no note.
    - Ready means `<note>` joins the `hash` inputs, after the `.blobl` files.
    - Anything else means not ready.
    - Share one generic `hash --check <dir>/<file>` fence with Step 5, as rpcn-author's Steps 2 and 7 do (`skills/rpcn-author/SKILL.md`).
  - **Step 3:** add "Then `references/design-check.md`".
  - **Exit-2 rule:** extend the "Exit 2 in Steps 1–3 (but …)" exception to the note's `hash --check`.
  - **Description:** add "checks it against its design note" and the trigger "check my pipeline against its design note". Trim elsewhere to stay within 1,024.
- **New `R/skills/rpcn-test/references/design-check.md`:**
  - the readiness rule: `hash --check`, plus design-format's Readiness list;
  - what to look for per section:
    - **Error handling:** retries and their count, `fallback`/`catch`/`switch` routing, the DLQ destination, drops;
    - **Delivery and ordering:** `max_in_flight`, batching or parallel outputs against an ordering requirement, auto-ack against at-least-once;
    - **Idempotency:** the dedupe key kept on every output path;
  - matching a departure to an unresolved Deviations row by `section`;
  - the worst-wins rule, the section and Summary lines, the proposed change, and the lint-fail rule.
- **`R/tools/shared/formats/test-report-format.md` §6** (then `sync_shared.py`):
  - the Summary line;
  - the `Not run:` lines from the matrix;
  - the worst-wins rule;
  - `resolved: yes` doesn't cover a departure.

  Keep the example's sha256 values valid: the rpcn_check tests check them.
- **`R/skills/rpcn-test/shared.txt`:** check that `formats/design-format.md` is listed (the file is already in `references/`), and name it from `design-check.md`.
- **`R/skills/rpcn-test/references/`:**
  - `report-writing.md`: Design check as `design-check.md` says; the verdict adds "no `mismatch`"; design fixes go against the pipeline.
  - `status-block.md`: `checks.tests` folds in a `mismatch` (AD-8 allows only the `lint` and `tests` keys).
  - `lint-errors.md:43` already points design questions to the Design check. Check that it still reads right.
- **`R/evals/`:** a trigger positive, `rpcn-test__trigger_design_check` ("check my pipeline against its design note"), and the README counts.
- **New `T/scenarios/`:**
  - **Setup:** each scenario copies the 2.6 note `scenarios/rpcn-author__design_note/fixtures/pipes/order_fulfilment.design.md`. It has `install = ["rpcn-test"]`, `no_cd`, and a hand-written `pipes/order_fulfilment.yaml` that lints clean on both binaries: a redpanda input, a mapping, and `http_client` with `retries: 3`.
  - **Checks:** `[[report]]` with `bare_inputs`, `[[lint]] ok`, and `unchanged` for the pipeline and the note. `[[file]]` on the report contains `- file: order_fulfilment.design.md`, plus the per-scenario strings below.
  - `rpcn-test__design_ok`: a `fallback` to the `orders.dlq` redpanda output. `Design check: 3 ok, 0 deviation-recorded, 0 mismatch`; verdict `pass`.
  - `rpcn-test__design_mismatch`: no fallback; failures are logged and dropped. `Design check: 2 ok, 0 deviation-recorded, 1 mismatch`; verdict `fail`; `checks.tests` `fail`.
  - `rpcn-test__design_deviation_recorded`: the mismatch pipeline, plus the note with one `Error handling` row (`resolved: no`), as rpcn-author's `design_deviation` writes it. `Design check: 2 ok, 1 deviation-recorded, 0 mismatch`; verdict `pass`.
  - **Expected side effects:** each test run also writes unit tests and runs the dry run (`Not run: needs redpanda`). Keep each pipeline's mapping correct for the note's intent (`total_cents` = total × 100), so only the Design check differs.
- **Existing T scenarios:**
  - `rpcn-test__dry_run_pass` gains `[[file]]` contains `Not run: no design note.`
  - `rpcn-author__apply_report`'s re-test will now see the fixture's note, if it has one: check, and adjust only its expected strings.
- **`T/tests/test_run_scenarios.py`:** `NAMES` for the new scenarios, and the `dry_run_pass` expectation if a test pins it.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/formats/test-report-format.md` §6, then `sync_shared.py`.
- [x] `R/skills/rpcn-test/` (`SKILL.md`, `design-check.md`, `report-writing.md`, `status-block.md`), within both size limits.
- [x] `R/evals/` (case and README).
- [x] `T/scenarios/rpcn-test__design_{ok,mismatch,deviation_recorded}/`, `dry_run_pass`, and `T/tests/test_run_scenarios.py`.

**Acceptance Criteria:**
- **Given** the repo, **when** the validator, `sync_shared --check`, all `tools/` suites and the `rpcn_check` tests on both binaries run, **then** all pass, and the validator shows no warning for rpcn-test.
- **Given** both binaries, **when** every non-compare scenario runs (`--jobs 4 --runs 1 --no-judge`), **then** all pass, including the three new `design_*` scenarios.
- **Given** the reviewed, committed tree, **when** `run_evals.py` runs (about $36), **then** it passes and a `dirty: false` record is committed.

## Implementation Notes

- **SKILL.md size:** 4,793 characters (limit 4,803); description 994 (limit 1,024). Paid for by one shared `hash --check` fence (Step 2 line 1, reused by Step 5), moving Step 5's not-ready recovery into `report-writing.md` and the unexpanded-session-id rule into `fix-check.md`, and small wording trims. Step 2 names `references/design-format.md`, which clears the validator's file-refs warning; `tools/tests/test_validate_skills.py` pinned that warning and now asserts no warnings.
- **Mismatch fixture:** "no fallback" read as "no DLQ fallback": the pipeline's `fallback` goes from `http_client` (retries 3) to a `drop` output with an ERROR `log`, the shape rpcn-author's `design_deviation` scenario writes. A literal no-`fallback` pipeline cannot both log and drop a failed output write.
- **Dry run:** the new fixtures have only a `mapping` processor, so the dry run runs and passes (not `Not run: needs redpanda`: the bounded run replaces the redpanda input and output). No scenario checks the dry-run line.
- `rpcn-author__apply_report`'s fixture has no design note, so its expectations are unchanged.
- `rpcn-test__design_deviation_resolved` was added at the matrix audit (user choice, 2026-11-12) to cover the `resolved: yes` row (the recorded fixture with the row marked `resolved: yes`: `mismatch`, verdict `fail`), so four design_* scenarios ship.
- Delivery and ordering in `design-check.md` keeps only what the YAML shows directly (`max_in_flight`, `broker` or parallel outputs, batching, parallel processors); the `memory` buffer and `auto_replay_nacks: false` examples were dropped, since no SOURCES.md row or real-binary test proves them (AD-15).
- **After the review fixes:** the validator shows no warnings (`rpcn-test` 4,793 characters, description 995). `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries (185 tests) and T's tests pass. Smoke run with `--jobs 4 --runs 1 --no-judge`, 30 non-compare scenarios: 30/30 on both binaries (`T/runs/20261112-130317`).
- **Eval record:** `evals/results/2026-11-12-c28124e01f52.json` passed with `dirty: false`, at $41.65, on the first full run. Trigger accuracy was 1.0, and all 30 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. Wall time was 22.5 minutes.
- **Pushed:** `6cc14e6..160884b`. CI run 43442422908 was green.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 1 medium, 6 low, 0 false, 0 maybe-false, plus one finding of our own. The fix for one low finding would edit the plan, so it was rejected and the plan's Implementation Notes record it instead.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A clean-lint run with a failing sample loses the unexpanded `${CLAUDE_SESSION_ID}` rule (it moved to `fix-check.md`, which `samples.md` never reads) | medium | patch | `samples.md` §4 now states the temp folder and the rule directly. |
| `evals/README.md` counts 29 pass scenarios, but 30 run | low | patch | Now 30, about $37. |
| The plan doesn't record the fourth scenario (`design_deviation_resolved`) | low | reject | The fix edits this build's plan. The Implementation Notes record it as the user's matrix-audit choice. |
| A fix to `<res>` is never linted | low | patch | The fixed `<res>` copy is linted with `--resources` set to it, else the fix is marked `(unverified)`. |
| The note is listed as an input when the check said `Not run: the pipeline does not parse.` | low | patch | The note is an input only when the Design check wrote rows, in `design-check.md`, `report-writing.md` and the format. |
| `deviation_recorded` doesn't check that the row's `what` is in `finding` | low | patch | It checks `logs it at ERROR level`, and `design-check.md` §3 copies `what` word for word. |
| The mismatch scenarios don't check the "record a Deviations row" sentence | low | patch | Both check `Deviations row`, which `design-check.md` §4 requires. |
| (own) `design-check.md` relied on `memory`-buffer and `auto_replay_nacks` facts with no AD-15 row | low | patch | Both examples were dropped (option b). Delivery and ordering now checks only what the YAML shows. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, every `tools/tests` suite, and the `rpcn_check` tests with `RPCN_TEST_BINARIES` set to `.cache/rpcn/{4.100.0,4.115.0}/redpanda-connect`: all pass.
- In `T`: `uv run tests/test_run_scenarios.py`, then the smoke run from the AC (about $10).
