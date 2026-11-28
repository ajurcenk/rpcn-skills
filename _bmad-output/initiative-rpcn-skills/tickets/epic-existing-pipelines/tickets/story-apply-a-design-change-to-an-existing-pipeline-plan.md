---
title: 'Apply a design change to an existing pipeline'
type: 'feature'
ticket: '4'
created: '2026-11-27'
status: 'done'
baseline_revision: '9ed7b070a03934caca2efe6adf123d882828a93d'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/epic-existing-pipelines.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After rpcn-design re-runs a note with a change, nothing brings the existing pipeline in line with it. Change mode has no "apply the design change" trigger. A departure from a ready note is only an Open decisions line ("No Deviations row"), so rpcn-test's Design check later reports it as `mismatch`.

**Approach:** "apply the design change" (or "bring `<pipeline>` in line with its design note") becomes a change-mode request. The change is what the pipeline needs to do what the ready note says, except departures already recorded in an open (`resolved: no`) Deviations row. It goes through the existing paths: a change@1 proposal when headless, Edits when interactive. A departure from a ready note, in any change-mode run, now records a Deviations row as `design-note.md` §3 says. Headless records it as an item in the proposal: a diff against `<name>.design.md` that appends the row and sets `updated`. It lands at apply time and is reviewed with the change (decision, user, 2026-11-27). change@1 then lists the note in `inputs` when a diff changes it. This is an additive wording change, so no major bump. `apply-report.md` accepts the note as a target for proposals only, and only for that diff shape.

## Boundaries & Constraints

**Always:**
- The epic's Must-not-change list applies. Author writes only Deviations rows and `updated` in a note. Headless never asks. Applying a test report works as today.
- An "apply the design change" request with no ready note changes nothing. It says why (no note, or not ready and the failing item). Headless ends `blocked`, `reason` naming it.
- Each change item's `Cause:` names the note's section and what it says.
- AD-15: any new behaviour claim gets a SOURCES.md row proved on 4.100.0 and 4.117.0.
- SKILL.md ≤ 4,803 chars. rpcn-author has about 1 char of room, so put the rules in references. Formats change only in `tools/shared/formats`, then `sync_shared.py`.
- Agent sessions run on 4.117.0, and lint checks run on both pins.

**Never:**
- Change `design@1`, rpcn-test's Design check or rpcn-design's re-run.
- Edit a note section other than Deviations and `updated`.
- Detect "note newer than pipeline".
- The implementation agent never commits and never runs `tools/run_evals.py`. Leave the untracked `T/orders_benthos_test.yaml` alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Design change, headless | Ready note re-run with "retry a failed post 5 times"; pipeline lacks it | `<name>.change.md` ready, its items `Cause:` the note section; pipeline untouched; apply, then Test: Design check 0 mismatch | — |
| Design change, interactive | Same | Edits per hunk, no proposal | Refused Edit as 8.3 |
| Already in line | Pipeline does what the note says | No proposal, no Edit; headless `complete`, `artifacts: []` | — |
| No / not-ready note | "apply the design change", no ready note | Writes nothing, says why | Headless `blocked` |
| Departure, headless | Ready note says in order, `max_in_flight: 1`; request "post 8 at a time" | Proposal carries the change, plus the Deviations row as a note diff; after apply, Test: `1 deviation-recorded, 0 mismatch` | — |
| Departure, interactive | Same, interactive | Pipeline Edits, then the row and `updated` Edits on the note after the departing item lands | Item refused: no row |
| Recorded deviation | Open row covers a departure | Left as is, no item | — |

</frozen-after-approval>

## Code Map

- `skills/rpcn-author/references/change.md`:
  - triggers (lines 3–7): add the design-change phrases, and what "the change" means for them;
  - §1, lines 36–46: replace the "No Deviations row" rule;
  - §4: a note diff needs no lint;
  - §5: inputs;
  - §6: the note Edits;
  - §7: the reply names each row.
- `skills/rpcn-author/references/design-note.md` §3: the row shape and the Edit procedure. Reuse it; don't copy it.
- `tools/shared/formats/change-format.md`:
  - Header `inputs` ("A design note … is not an input either");
  - Open decisions line 80;
  - Readiness list.
  - Keep the example and its sha256 (the rpcn_check tests check it).
- `skills/rpcn-author/references/apply-report.md` §3: the target list (line ~54), and the proposal-only note target.
- `skills/rpcn-author/SKILL.md` Step 2: routing already sends "change it" to change.md. Don't edit it unless a smoke shows misrouting.
- `skills/rpcn-test/references/design-check.md` §3: the `deviation-recorded` rule the chain relies on. Read only.
- `skills/rpcn-design/references/rerun.md`: keeps the rows and `inputs: []`. Read only.
- `tools/sync_shared.py` and per-skill `shared.txt`: re-sync after the format edit.
- T `scenarios/rpcn-design__describe_pipeline/fixtures/relay/`: `order_push.yaml` plus `.env.example`. Reuse it for the chain.
- T `scenarios/rpcn-design__chain_dlq_retry/expect.toml`: the `[[step]]` chain layout.
- T `scenarios/rpcn-author__change_propose/expect.toml`: the no-other-file globs and `unchanged`.
- T `scenarios/rpcn-author__design_deviation`: an existing Deviations-row check to mirror.

## Tasks & Acceptance

**Execution:**
- [ ] `tools/shared/formats/change-format.md`: the note as an input when a diff changes it; departures as a note-diff item, not an Open decisions line. Then run `uv run tools/sync_shared.py`.
- [ ] `skills/rpcn-author/references/change.md`:
  - the design-change trigger and its meaning;
  - the no-ready-note stop;
  - departures as Deviations rows (headless a note-diff item; interactive Edits after the item lands);
  - the reply.
- [ ] `skills/rpcn-author/references/apply-report.md`: the note target (proposal only, row and `updated` hunks only; any other note hunk skips the item).
- [ ] T `scenarios/rpcn-author__chain_design_change/` (fixture `relay/order_push.yaml`, `.env.example`):
  - Steps:
    1. Design describes the pipeline.
    2. Design updates the note: "retry a failed post 5 times before `orders.dlq`".
    3. Author: "apply the design change in `relay/order_push.design.md`".
    4. Author applies `relay/order_push.change.md`.
    5. Test runs.
  - Checks:
    - step 3 artifacts are the proposal;
    - the pipeline contains `retries: 5`;
    - lint ok;
    - the report has `0 mismatch`;
    - the note has no `| no |` row.
- [ ] T `scenarios/rpcn-author__chain_change_departs/`: a fixture with a ready note (in order, `max_in_flight: 1`) and its pipeline.
  - Steps:
    1. Headless "post 8 at a time".
    2. Apply.
    3. Test.
  - Checks:
    - the proposal is ready;
    - the note has a `| Delivery and ordering |` row with `| no |`;
    - the pipeline has `max_in_flight: 8`;
    - the report has `1 deviation-recorded, 0 mismatch`.
- [ ] T `scenarios/rpcn-author__change_departs_edit/`: the same fixture, interactive. Checks:
  - the note gains the row via Edit;
  - `write_lacks` covers the note and the pipeline;
  - the other note lines are unchanged.
- [ ] `SOURCES.md`: a row only if a new behaviour claim is made (for example `http_client.retries`), proved on both pins.

**Acceptance Criteria:**
- Given the existing `change_*`, `design_deviation` and `apply_report` scenarios, when re-run, then they still pass.
- Given the edited files, then the SKILL.md and description limits hold, and `sync_shared --check` is clean.

## Implementation Notes

- `status-block.md` also changed (not in the Code Map): it lists the new `blocked` case (a design-change request with no ready note) and the AD-8 exception. SKILL.md is untouched (4,802 chars); routing worked in the smoke.
- apply-report.md skips a note item when the item it records was not applied (or only partly), which mirrors the interactive "item refused: no row" rule.
- No SOURCES.md row: the references make no new component or field claim.
- The departs prompts say `max_in_flight: 8` outright. The plain "post 8 orders at a time" was read as `batching.count: 8` once (change_departs_edit: a Batching row, `max_in_flight: 1` kept to protect ordering). That was a fair reading, so the prompt was fixed and the skill left as it was.
- Smoke on 4.117.0 (checks on 4.100.0 and 4.117.0): all 8 scenarios pass (change_departs_edit 2/2 after the prompt fix, chain_change_departs 1/1 on both prompts). Pytest 349 passed; sync_shared --check and validate_skills are clean.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens), 2026-11-27: 6 findings, 0 high, 2 medium, 3 low, 1 rejected low, 0 false, 0 maybe-false

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The format's Readiness list refuses the whole proposal on a bad note hunk; apply-report §3 skips only the item; §1's summary leaves the new item out | medium | patch | Confirmed at apply-report.md §1 (lines 26–30) and §3. Fix: §1 lists the item, and §3 refers a bad note hunk to §1 (not ready, change nothing). |
| 2 | The `updated:` hunk/Edit is a no-op when the line already says today (two departures, or a same-day re-run), and Edit rejects `old_string == new_string` | medium | patch | Confirmed: change.md §3 requires two hunks; design-note.md §3 line 77 requires one more Edit. Fix: leave out the `updated:` hunk/Edit when it already says today. |
| 3 | design_change_no_note never checks the block reason | low | patch | Confirmed: only `status`/`artifacts`. Fix: add a `reply_contains` naming the note. |
| 4 | chain_change_departs can't catch step 1 writing the note or the pipeline | low | patch | Confirmed: no `write_lacks`/`bash_lacks`. Fix: add both, as change_departs_edit does. |
| 5 | chain_design_change's note `contains` "5" is nearly empty | low | reject | Weak, but the later `Error handling` Cause and the pipeline's `retries: 5` (driven by the note) prove the re-run. The fix is not a plain correction. |
| 6 | The evals/README cost line is miscalculated | low | patch | Confirmed: 59.30 + 9.18 = 68.48, about $74.50 in all. Fix: correct both numbers. |

## Design Notes

"The change" for a design-change request is a reading, not a request text. For each section Author builds from (Components, Inputs, Outputs, Error handling, Delivery and ordering, Idempotency, Batching), the pipeline either does what the section says or gets an item. Open Deviations rows are accepted departures and are skipped. Otherwise §2 to §7 run unchanged. The proposal's Request quotes the user's words ("apply the design change …").

## Verification

**Commands:**
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest tools/shared/rpcn_check/tests tools/tests -q`: expected all pass.
- `uv run tools/sync_shared.py --check` and `uv run tools/validate_skills.py`: expected clean.
- From T, smoke once on 4.117.0: run the three new scenarios, plus `rpcn-author__change_propose`, `change_apply`, `change_edit`, `design_deviation` and `apply_report`. Expected: all pass. No record here; it is shared with 8.5 and 8.6.
- **Pushed:** `9ed7b07..1a8bb56`, with 8.4, 8.5, 8.6 and `run_evals --resume` together; record `2026-11-28-eb28fcbb4e92.json` (accuracy 1.0, 77 scenarios 2/2). CI run 46165299566 was green. T commits stay local.

