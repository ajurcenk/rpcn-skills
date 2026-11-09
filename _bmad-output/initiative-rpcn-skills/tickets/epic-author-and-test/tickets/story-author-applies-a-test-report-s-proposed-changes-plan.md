---
title: "Author applies a test report's proposed changes"
type: 'feature'
ticket: '5'
created: '2026-11-09'
status: done
baseline_revision: 'e09b532ea27458694987352ded8f84de91818102'
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

**Problem:** `rpcn-test` writes a `<name>.test-report.md` whose Proposed changes are diffs that only `rpcn-author` may apply (AD-6, one writer per file). `rpcn-author` can't do that yet: it only writes new files and never touches an existing one. So the Author and Test loop is open (epic R3).

**Approach:**
- **The skill:** `rpcn-author` gets a report flow:
  - check the report with `rpcn_check hash --check`, and refuse a draft or stale report with the reason
  - apply each Proposed change aimed at a file Author owns, of any kind (not only lint)
  - lint
  - name re-running `rpcn-test` as Next
- **The sibling:** `rpcn-test`'s description and Next point report fixes to `rpcn-author`.
- **Proof:** a two-skill loop scenario (apply, then re-test to verdict `pass`), a stale-report scenario, and trigger cases for the new phrasing.

## Boundaries & Constraints

**Always:**
- AD-6:
  - Author edits only its own files: `<name>.yaml`/`.yml`, `<name>.resources.yaml`/`.yml`, `<name>.<label>.blobl` and `.env.example`.
  - It never edits the report, or any file Test owns.
- AD-8: a report that isn't ready gives `blocked` (it's a required input). A change that can't be applied doesn't. The run still ends `complete`, with that item in `open_questions`.
- AD-9:
  - both `SKILL.md` files stay at 4,803 characters or less, and the validator reports no warnings for `rpcn-author`
  - each fenced `rpcn_check` command stays in `SKILL.md` (placeholders expand only there)
  - new detail goes in a reference read at its step
- Shared files come only through `shared.txt` and `sync_shared.py`.
- Every new scenario uses a pipeline in a subfolder with a non-default name, and sets `no_cd = true`.
- Commit before the paid eval run, which runs only after review. Run all `tools/` suites before any push.

**Never:**
- Overwrite an existing pipeline on a plain write request. Story 2.4's existing-file block stays.
- Apply a change from a report that `hash --check` says isn't ready, or guess at a hunk that doesn't match the file.
- Change `rpcn_check.py` or the shared formats.
- Add design-note, Bloblang-sample or unit-test behaviour (stories 2.6–2.9).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Loop | `pipes/orders.yaml` (3 lint errors) and its ready `fail` report with 3 lint diffs plus 1 non-lint diff. Headless: "apply the report, then re-test with rpcn-test" | the pipeline lints clean on both binaries; the non-lint change is in the file; the new report is ready, verdict `pass`, `pipeline_ready: true` | — |
| Stale report | the same report, but `orders.yaml` was edited after hashing | nothing is written; headless: `blocked`, and `reason` says the input changed; Next: re-run rpcn-test | — |
| Draft report | `status: draft` | the same as stale, and the reason is "draft" | — |
| Verdict pass, `None.` | ready report, no proposed changes | nothing to apply, files unchanged; `complete` | — |
| Hunk doesn't match | a diff's context isn't in the file | that item isn't applied, and is named in the reply and `open_questions`; the others are applied; `complete` | never guess at it |
| Diff on a Test-owned file | a diff against `orders_benthos_test.yaml` | skipped and named: rpcn-test applies its own files | — |
| Lint fails after applying | the applied diffs still don't lint | Step 6 revisions (at most 3), then as Step 6 says | — |
| Write request, file exists | as in story 2.4 | still `blocked`; the report flow runs only when a report is named | — |
| Trigger | "apply the fixes in orders.test-report.md" | `rpcn-author` fires and `rpcn-test` stays silent | — |

**Decision (2026-11-09, user):** the plan stays whole, at about 2,950 tokens, and isn't split. Its parts can't ship apart.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local only). `T`'s baseline is `d2d32d8e1af827389cdf41601366f6d2d51a4429`.

- **`R/skills/rpcn-author/SKILL.md`** (4,700 characters now; the ceiling is 4,803, counting frontmatter):
  - Description: says it also applies a test report's proposed changes, with 2–3 trigger phrases ("apply the test report", "fix my pipeline from its test report").
  - The preamble's "Read and Write tools" gains Edit.
  - Step 2 gets one line: when the user names or asks to apply a `<name>.test-report.md`, go to the new **Step 7: Apply a test report** instead of Steps 2–5.
  - Step 7:
    - the fenced `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <dir>/<name>.test-report.md`
    - only on exit 0 with `data.ready: true`
    - otherwise write nothing, give each `errors[].message`, and treat an input `state: changed` as stale
    - then "read `references/apply-report.md` and follow it, with `references/test-report-format.md`"
    - lint as in Step 6
  - Next gets two bullets: report applied → re-run rpcn-test; report stale or draft → re-run rpcn-test for a fresh one.
  - **To pay for it:** move the three status-block bullets to a new skill-local `references/status-block.md` (the way `rpcn-test` did in 2.4), and tighten wording elsewhere.
- **New `R/skills/rpcn-author/references/apply-report.md`** (skill-local):
  - the readiness-list checks
  - find the pipeline: `inputs[0]` relative to the report's folder; `<res>` is any resources input
  - apply only diffs against Author's files, using Edit, hunk by hunk, matching their context exactly
  - skip and name diffs on other files
  - an unmatched hunk becomes an open question
  - `(unverified)` items are still applied, and lint decides
  - `None.` means nothing to do
  - never edit the report
  - the reply lists each item as applied or skipped
- **`R/skills/rpcn-author/shared.txt`:** add `formats/test-report-format.md references/test-report-format.md`, then run `uv run tools/sync_shared.py`. `handoff-header.md` isn't needed, because `hash --check` enforces it.
- **New `R/skills/rpcn-author/references/status-block.md`:** the moved bullets, plus a `blocked` case: "a report that is not ready (`reason` says why)". It also says that `artifacts` lists edited files too.
- **`R/skills/rpcn-test/SKILL.md`** (4,652 characters):
  - The description becomes "Not for writing pipelines or applying a report's changes: use rpcn-author."
  - The Next bullet "Errors found: apply the proposed changes …" becomes "apply them with rpcn-author, then re-run rpcn-test."
  - Keep every trigger phrase.
- **`R/evals/`:**
  - `rpcn-author__trigger_apply_report` and `rpcn-author__trigger_fix_from_report`: positives, copied from `rpcn-author__trigger_write_pipeline`.
  - `rpcn-test__miss_apply_report`: a sibling negative with a grader for `rpcn-test` only (`min: 0`, `max: 0`, `arm: both`), copied from `rpcn-test__miss_write_new_pipeline`.
  - Update `README.md`: the case counts, the scenario count, and the cost.
- **`T/scenarios/rpcn-author__apply_report/`:**
  - `install = ["rpcn-author", "rpcn-test"]`, `skill = "rpcn-author"`, and `no_cd = true`
  - about 60 turns, `timeout_s` about 600
  - fixtures:
    - `pipes/orders.yaml`: the `rpcn-test__lint_broken/fixtures/multi_error.yaml` content
    - `pipes/orders.test-report.md`: hand-written to `test-report-format.md`
      - `status: ready`, verdict `fail`
      - its real `sha256` from `rpcn_check hash`
      - the 3 lint errors
      - 4 Proposed changes: the 3 lint diffs, plus a non-lint one: change the `log` message to `heartbeat`, with the reason "a clear log line"
  - checks:
    - `[[lint]] pipes/orders.yaml ok = true`
    - `[[file]] pipes/orders.yaml contains ["heartbeat"]`
    - `[[report]] pipes/orders.test-report.md` with `ready = true`, `verdict = "pass"`, `pipeline_ready = true` and `bare_inputs = true`
  - There's no `[status]`, because both skills run and `parse_status_block` needs exactly one block.
- **`T/scenarios/rpcn-author__stale_report/`:**
  - `install = ["rpcn-author"]` and `no_cd = true`
  - the same report, and an `orders.yaml` with one edited line after hashing
  - `unchanged` = both files
  - `[status] status = "blocked"`, `skill = "rpcn-author"`
- **`T/tests/test_run_scenarios.py`:**
  - `ShippedAuthorScenarioTests.NAMES` gains `stale_report`.
  - Add a test that `apply_report` installs exactly `rpcn-author` and `rpcn-test`, sets `no_cd`, and checks `pipeline_ready`.
- **No changes needed in:** the runner, `eval_gate.py`, `run_evals.py`, and CI. They already pick up new cases and scenarios, and pass both binaries to the scenarios.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-author/` (`SKILL.md`, `references/apply-report.md`, `references/status-block.md`, `shared.txt`), then `uv run tools/sync_shared.py`: the Step 7 report flow, within the size limit.
- [x] `R/skills/rpcn-test/SKILL.md`: the "Not for" line and the Next bullet name `rpcn-author`.
- [x] `R/evals/rpcn-author__trigger_{apply_report,fix_from_report}/`, `R/evals/rpcn-test__miss_apply_report/` and `R/evals/README.md`.
- [x] `T/scenarios/rpcn-author__{apply_report,stale_report}/`, with the fixture report hashed by the real script.
- [x] `T/tests/test_run_scenarios.py`: the shipped-scenario tests above.

**Acceptance Criteria:**
- **Given** the repo, **when** `uv run tools/validate_skills.py` runs, **then** `rpcn-author` has no warnings, `rpcn-test` has no `size` warning, and each `SKILL.md` is at 4,803 characters or less.
- **Given** both cached binaries in `RPCN_TEST_BINARIES`, **when** `run_scenarios.py --source local:../rpcn-skills --scenario 'rpcn-author__*' --runs 1 --no-judge` runs, **then** all 6 author scenarios pass. That includes `existing_file`, which proves the write-request block still holds.
- **Given** the reviewed and committed tree, **when** `uv run tools/run_evals.py` runs (about $15), **then** the gate passes with negatives silent, every scenario passes 3/3, and a `dirty: false` record is committed.
- **Given** all `tools/` suites and T's tests, **when** they run before the push, **then** all pass, and CI is green.

## Implementation Notes

- `rpcn-author/SKILL.md` is 4,785 characters (ceiling 4,803); `rpcn-test/SKILL.md` is 4,701. The validator reports no `rpcn-author` warnings; `rpcn-test` keeps only its pre-existing `design-format.md` file-refs warning.
- To fit the budget, beyond moving the status-block bullets: the description's file list was shortened, the Step 1 `${CLAUDE_SKILL_DIR}` note and several Step 3–6 sentences were tightened, and the Next bullets "Lint clean" and "Report applied" share one line. Step 7's not-ready branch says "stop as on exit 2" rather than repeating it.
- The rpcn-test description uses `report''s` (doubled quote): the description is a single-quoted YAML scalar.
- **Implementer's smoke run:** all 6 `rpcn-author__*` scenarios passed 1/1 on both binaries, for $1.11 in total.
- **Matrix audit (2026-11-09):** 5 rows had no test. The user chose "Draft + fold-ins":
  - **New `rpcn-author__draft_report`:** the same pipeline, and the report with `status: draft`, so `hash --check` exits 1 with a matching hash. It expects `blocked`, both files unchanged, and `no_cd`.
  - **`apply_report`:** gains a Test-owned fixture, `pipes/orders_benthos_test.yaml`, and a 6th item that diffs it, with `unchanged` on that file. This covers the "Diff on a Test-owned file" row.
  - **Deferred:** the "verdict pass, `None.`", "hunk doesn't match" and "lint fails after applying" rows (deferred-work).
  - T tests: 163 pass. Smoke run (`--runs 1 --no-judge`, both binaries): `apply_report` passed every check, including `unchanged`, in 25 turns for $0.35. `draft_report` passed in 6 turns for $0.12.
- **After the review patches:** the validator, `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries, and T's 164 tests all pass. `rpcn-author` `SKILL.md` is 4,777 characters. Smoke run of all 7 author scenarios: 7/7 pass on both binaries, $1.23 (`T/runs/20261109-100251`).

- **Commits:** R `fdd30f7`, T `01bbd33`.
- **Eval record:** `evals/results/2026-11-09-84c71b40536a.json` passed with `dirty: false`, at $13.37. Trigger accuracy was 1.0, so the 3 new report-phrasing cases were right, and the sibling negative stayed silent. All 12 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. This was the story's only full eval run.
- **Manual test (2026-11-09, user):** the user ran the apply, stale and draft fixtures by hand in `T`, with the committed skills installed. No issues found.
- **Pushed:** `e09b532..7654dbe`. CI run 42669326589 was green.

## Plan Change Log

- **2026-11-09, fixture lint count.** `multi_error.yaml` gives 4 lint errors on both 4.100.0 and 4.115.0 (`not_a_field`, the trailing `.`, `bogus_option`, `wrong_key`), not 3. The fixture report records all 4, with 5 Proposed changes (4 lint diffs plus the `heartbeat` one). Inventing a 3-error variant would break "the `multi_error.yaml` content"; the intent (lint diffs plus one non-lint diff, then `pass`) is unchanged.

## Review Triage Log

Quick pass: 0 high, 3 medium, 6 low, 1 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The owned-file list doesn't bind `<name>` to the report's pipeline, so a shared `../resources.yaml` input is skipped and a diff on another pipeline would be applied | medium | patch | Confirmed: `apply-report.md` §3 lists generic `<name>.*` patterns. The format allows a diff against any input, including a shared resources file. Fix: Author owns the report's pipeline, the report's resources inputs, and that pipeline's `.blobl` files and `.env.example`. |
| Step 7's "Then lint as in Step 6" contradicts §3's "`None.` … skip lint" | medium | patch | Confirmed: `SKILL.md`:104 against `apply-report.md` §3. Fix: drop the SKILL.md sentence. §4 already lints after the edits. |
| After applying, Step 6's `<res>` (`<dir>/<name>.resources.yaml`) drops a shared resources input | medium | patch | Confirmed: Step 6 is the only definition of `<res>` that SKILL.md carries. Fix: §4 lints with `--resources` for each resources input from §2. The sub-claim that "when there is one" widens the write flow is low and rejected: linting with an existing resources file is the right behaviour. |
| Next has no bullet for a report that fails the readiness list | low | patch | Confirmed against AD-9. The bullet becomes "Report not ready (stale, draft or incomplete): re-run rpcn-test for a fresh one." |
| `stale_report`'s comment says the draft has no scenario | low | patch | Confirmed: `draft_report` exists now. Comment corrected. (The plan's Design Notes bullet is history, and a fix that only edits the plan is rejected.) |
| The three report fixtures differ (5 against 6 items) | low | patch | Confirmed. The `stale` and `draft` reports are now copies of `apply_report`'s, with only `status` changed in `draft`, and a test keeps them in sync. |
| Item 6 diffs a file that isn't an input, which `test-report@1` doesn't allow | low | reject | Real, but the frozen matrix row "Diff on a Test-owned file" exists to test exactly that defensive skip. No format-legal fixture can express it without changing the shared formats, which the Never list forbids. |
| The scenarios don't assert `reason` or Next | low | reject | Real. `check_status` compares exact values only, so the fix would be a new runner feature (as in 2.4's triage). `blocked` and `unchanged` pin the behaviour that matters, and a binary error can't happen with the pinned binaries. |
| The `test-report-format.md` copy names `handoff-header.md` and `design-format.md`, which rpcn-author lacks | low | reject | Real, but only as context. The readiness list Author needs is in the copy, and `hash --check` enforces the header. A failed Read costs one turn. |
| A `--- /dev/null` diff that creates an owned file can never be applied | false | reject | Format §6 makes each diff "against the input file", and `hash --check` (Step 7) passes only when every input exists. A creation diff can't come from a ready report. |

## Design Notes

- **Why one two-skill loop scenario:** the ticket's check needs `rpcn-test` to re-run after Author. A scenario runs one agent session, so the session installs both skills. `[[report]] pipeline_ready = true` then proves three things on the final file at once: the new report is ready, the pipeline's hash matches it, and the verdict is `pass`. The `npx`-alone rule (epic R10) is for the trigger pair, which the existing `npx_trigger` and `npx_miss` scenarios already cover.
- **Why the fixture report is hand-written:** it's deterministic and free, and its hash comes from the real script. The loop scenario's re-test is the live `rpcn-test` run.
- **Draft report:** it's the same `hash --check` exit-1 branch as a stale one, so there's no scenario for it, to keep the eval cost down.

## Verification

**Commands:**
- `uv run tools/validate_skills.py && uv run tools/sync_shared.py --check`: exit 0, with the warnings as in the acceptance criteria.
- `for t in tools/tests/test_*.py; do uv run $t; done`, and `RPCN_TEST_BINARIES=… uv run tools/shared/rpcn_check/tests/test_rpcn_check.py`: all pass.
- In T: `uv run tests/test_run_scenarios.py`, then the author scenarios' smoke run (above).
- In T: `rpcn_check hash --check pipes/orders.test-report.md` run in `scenarios/rpcn-author__apply_report/fixtures`: `ready: true`. In `stale_report` it reports `ready: false`, with the input `changed`.
