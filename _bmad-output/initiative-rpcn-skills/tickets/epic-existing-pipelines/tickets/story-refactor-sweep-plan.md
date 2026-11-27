---
title: 'Refactor sweep'
type: 'refactor'
ticket: '6'
created: '2026-11-27'
status: 'built'
baseline_revision: '4fb03b638f6c7052b599dc7a844d18a90435c4e2'
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

**Problem:** Epic 8 left rpcn-author's SKILL.md at 4,802 of 4,803 characters and rpcn-design's at 4,799, so the next change needs tightening tricks. Its five stories also added rules across several references, written one story at a time. 8.4's review already found two of them contradicting each other.

**Approach:** Cleanup only (decision, user, 2026-11-27: headroom and a contradiction sweep).
- **Headroom:** move behaviour-neutral detail from both SKILL.md files into an existing reference, each with a short pointer, until each file has at least 150 characters of room.
- **Contradiction sweep:** read epic 8's references together and fix every place where two of them disagree. Repeats stay, as in 3.10.

## Boundaries & Constraints

**Always:**
- No behaviour change. Every rule keeps its meaning and its trigger point, so a moved passage is read at the same step it was before.
- Every SKILL.md ≤ 4,803 characters and every description ≤ 1,024, measured as `len()`. Each of rpcn-author and rpcn-design ends with ≥ 150 characters of room.
- A contradiction is fixed toward the rule the later story decided, and its plan says which one that is. Any case the plans don't settle goes in the reply as a question, unfixed.
- Shared formats change only in `tools/shared/formats`, then `sync_shared.py`.

**Never:**
- Edit a description, or the Step 2 routing lines (the Step 7, `change.md`, `describe.md` and `rerun.md` pointers and the not-ready rules).
- Edit the Next list or the status-block section heading.
- Change rpcn-test, `design@1`, `change@1`'s shape, or any T scenario.
- The implementation agent never commits, and never runs `tools/run_evals.py` or the trigger suite. Leave `T/orders_benthos_test.yaml` alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Headroom | Both SKILL.md files after the move | ≥ 150 chars of room each; every moved rule is in a reference the same step reads | — |
| Contradiction | Two references disagree | One wording, the later decision; both places agree | Unsettled: a question in the reply, no edit |
| Regression | Epic 8 and core scenarios | All pass as before | A failure names the moved or edited passage |

</frozen-after-approval>

## Code Map

- `skills/rpcn-author/SKILL.md` (4,802 chars). Candidates: Step 4's fields detail and Step 6's revision detail, which move into existing references or a Step note, and Step 5's resource/env/mapping sentence, which points to `pipeline-files.md`. Step 2's routing stays.
- `skills/rpcn-design/SKILL.md` (4,799 chars). Candidates: Steps 3 and 4 (list/fields detail, which `patterns.md` and `note-writing.md` can hold) and Step 5's ordering detail, which `note-writing.md` already states.
- Epic 8's references to read together:
  - Author: `change.md`, `apply-report.md`, `change-format.md` (from `tools/shared/formats`), `design-note.md`, `status-block.md`, `questions.md`, `pipeline-files.md`;
  - Design: `describe.md`, `rerun.md`, `questions.md`, `note-writing.md`, `status-block.md`.
- Known overlaps to check:
  - the note-row procedure in `design-note.md` §3, `change.md` §1/§3/§6 and `apply-report.md` §3;
  - the not-ready-note outcome in `change.md` §1, `status-block.md` and `design-note.md` §1;
  - the refused-Edit rule in `change.md` §6 and `apply-report.md` §4;
  - describe mode's `inputs: []` rule in `describe.md` and `rerun.md`'s Header.
- The plans that decided each rule are in `_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/tickets/*-plan.md`; the later story wins.

## Tasks & Acceptance

**Execution:**
- [x] `skills/rpcn-author/SKILL.md` and its target references: headroom move.
- [x] `skills/rpcn-design/SKILL.md` and its target references: headroom move.
- [x] Epic 8's references: fix contradictions. List each one in Implementation Notes with the two places, the fix, and the deciding plan.

**Acceptance Criteria:**
- Given the edits, then the `len()` targets hold, `validate_skills.py` shows no errors or warnings, `sync_shared --check` is clean, and pytest passes on both pins.

## Implementation Notes

- Sizes after the sweep (`len()` of file text / parsed description): rpcn-author 4,649 / 922 (154 room), rpcn-design 4,625 / 961 (178 room), rpcn-test 4,735 / 1,017 (unchanged). No description, Step 2 line, Next line or status-block heading was edited.
- **Headroom, rpcn-author** (each moved rule is already stated, or now stated, in the reference the same step reads):
  - Step 1: "(headless: `blocked`)" dropped; `status-block.md` already lists "an exit 2, except from Step 2's note check".
  - Step 4: "(headless: `blocked`)" dropped from the no-close-match ask; Step 5's round (`questions.md` Headless) and `status-block.md` already end it `blocked`.
  - Step 5: the `${ENV_VAR}` sentence folded into the "plain YAML" line (the rule stays in SKILL.md; `pipeline-files.md` holds the detail).
  - Step 6: "(headless: `blocked`, `reason` the first)" moved into `status-block.md`'s lint bullet ("`reason` the first error").
  - Step 7: "(`<dir>/` its folder)" and "(§1 says when to stop)" dropped; `apply-report.md` §1, read next in the same step, states both.
- **Headroom, rpcn-design:**
  - Step 5: "header, title, then the eleven sections in order" and "`status` follows the Ready rule in `design-format.md`" dropped; `note-writing.md` (read at that point) opens with both. `design-format.md` stays named in SKILL.md's intro.
  - Step 6: "the exit (`ready` 0, `draft` 1), then the Readiness list" dropped; `note-writing.md` "Step 6: checking the note" lists the same order. Its lead-in "as SKILL.md says" became "Step 6 checks the note in this order:".
- **Contradictions fixed** (later story wins):
  1. `status-block.md` (author) "Neither does a design note … except for a design-change request (above): with a not-ready note the run ends `complete` …" read as if the `complete` outcome described the design-change exception, against its own `blocked` bullet and `change.md` §1. Reworded: the not-ready outcome first, then "The one exception is a request to apply a design change, which ends `blocked`". Decided by 8.4.
  2. `design-note.md` §1 "a missing or not-ready note never blocks (AD-8)" vs `change.md` §1 / `status-block.md` (a design-change request with no ready note ends `blocked`). Now "never blocks a build … A request to apply a design change is the one exception (`change.md` §1)". Decided by 8.4.
  3. `questions.md` (author) Headless "These still end `blocked` … an existing pipeline (Step 2 stops there)" and the asks list "the pipeline file exists (Step 2)" vs `change.md` (an existing pipeline with a change request is change mode, and `change.md` §2 reads `questions.md`). Both scoped to "on a write request (… a change request is `change.md`'s)". Decided by 8.2 (8.3 for interactive).
  4. `pipeline-files.md` "Never move an existing pipeline's inline mapping into a `.blobl` file, unless a test report proposes it" vs `change.md` §3 "unless the request asks". Now "unless a test report proposes it or a change request asks for it (`change.md`)". Decided by 8.2.
  5. `change.md` §6 "Then lint what landed" right after a refusal vs `apply-report.md` §4 "Apply no more hunks of that item, and go on with the next item … lint what landed" after the edits. `change.md` §6 now says "Apply no more hunks of that item, and go on with the next … After the last item, lint what landed". Decided by 8.3 (its review fixes; §4 is the procedure §6 points to).
  6. `rerun.md` Header "add a file the request names that the design is now made from" vs `describe.md` "`inputs: []`: the pipeline and its files are never hashed". A re-run whose request names a pipeline, or one of its files, could hash it. Now the rule goes by file type: never add a pipeline or any of its files (resources file, `.blobl` files, `.env.example`), even when the request names one, with `describe.md` as the reason; `inputs: []` stays `[]`. Any other file the request names is still added (the 3.5 rule). (Review fix: the first wording covered only "the pipeline a described note describes", which left its files open and depended on recognising a described note, which nothing in its header marks.) Decided by 8.1 (the epic's staleness decision, option (a)); `rerun.md`'s rule dates from 3.5.
- Verification (2026-11-27): `validate_skills.py` ok with no warnings; `sync_shared --check` ok; pytest on both pins (absolute `RPCN_TEST_BINARIES`, 4.100.0 first) 349 passed. Smoke from T (`--runs 1 --jobs 4 --no-judge`, sessions on 4.117.0 via `RPCN_BINARY`): 30/30 PASS (`runs/20261127-171941`): the plan's list (`change_*`, `chain_*`, `design_change_*`, `design_note`, `design_deviation`, `apply_report`, `write_*`, `describe_*`, `rerun_*`, `chain_tracer`) plus `existing_file`, `ask_existing`, `design_not_ready` and `stale_report`, which cover the other edited passages. About $12.70.
- Checked and consistent (no edit): the note-row procedure (`design-note.md` §3, `change.md` §1/§3/§6, `apply-report.md` §3), the refused-Edit rule otherwise, `change-format.md` vs `change.md` §2/§5/§7 and `apply-report.md` §1/§3, Design's `questions.md` / `describe.md` / `note-writing.md` describe-mode exceptions, and both status blocks' `artifacts` rules.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens), 2026-11-27: 1 finding, 0 high, 1 medium, 0 low, 0 false, 0 maybe-false

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | rerun.md's `inputs` rule leaves out only the described pipeline, not its resources, `.blobl` or `.env.example` files, and it depends on recognising a "described note", which no header marks | medium | patch | Confirmed at rerun.md:46-50 against describe.md Step 5 ("the pipeline and its files are never hashed"). Fix: a rule based on file type (never a pipeline or its files), with the 3.5 rule kept for other files. |

## Verification

**Commands:**
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest tools/shared/rpcn_check/tests tools/tests -q`: expected all pass.
- `uv run tools/validate_skills.py` and `uv run tools/sync_shared.py --check`: expected clean, with no warnings.
- Smoke (implementer), from T with `--runs 1 --jobs 4`, sessions on 4.117.0: run `rpcn-author__change_*`, `rpcn-author__chain_*`, `rpcn-author__design_change_*`, `rpcn-author__design_note`, `rpcn-author__design_deviation`, `rpcn-author__apply_report`, `rpcn-author__write_*` (or the write-pipeline scenario names), `rpcn-design__describe_*`, `rpcn-design__rerun_*` and `rpcn-design__chain_tracer`. Expected: all pass. The shared record (8.4 to 8.6) runs after review.
