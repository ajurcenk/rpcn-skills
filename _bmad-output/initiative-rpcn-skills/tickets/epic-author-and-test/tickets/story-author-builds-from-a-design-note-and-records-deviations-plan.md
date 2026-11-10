---
title: 'Author builds from a design note and records deviations'
type: 'feature'
ticket: '6'
created: '2026-11-09'
status: 'built'
baseline_revision: 'a2cc47bdfd3fe8854da27f68e73496e1c542ea0c'
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

**Problem:** `rpcn-author` ignores `<name>.design.md`. A pipeline written beside a ready design note can quietly differ from it (AD-7), with no record of where or why.

**Approach:**
- Before writing, Author runs `hash --check` on `<dir>/<name>.design.md`.
- **Ready note:** Author builds from it. Its components go through the usual `list`/`fields` checks. Its Error handling, Delivery and ordering, and Idempotency choices go into the pipeline. Author appends one Deviations row per deliberate departure, and changes only those rows and `updated`.
- **No note:** Author builds from the request, as today.
- **Not-ready note:** Author says so, with the reason, ignores it, and doesn't block.
- **Tests:** hand-written fixture notes in `rpcn-test-skills` test this, and entry 10 reuses them. A new runner check proves that only rows were appended.

## Boundaries & Constraints

**Always:**
- Author writes only Deviations rows (`section`, `what`, `why`, `date` today, `resolved: no`) and the `updated` line (design-format.md "Who writes what").
- The note keeps passing `hash --check` after a row is added.
- `SKILL.md` stays at 4,803 characters or less, so the new behaviour goes in a reference. The `hash --check` command stays fenced in `SKILL.md`, because placeholders expand only there.
- Shared files change only under `tools/shared/`, then `sync_shared.py` runs.
- AD-8 holds: a missing or not-ready note never blocks, because it isn't a required input.

**Never:**
- Edit any other part of the note: `status`, `inputs`, other sections, or existing rows.
- Write a design note when none exists (that's epic 3).
- Change `rpcn_check.py`, the design format, or Step 7 (apply a report).
- Push `rpcn-test-skills`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ready note, request names only the note | "build the pipeline from `pipes/order_fulfilment.design.md`" | `<name>` comes from the note's `pipeline`. The pipeline has the note's components, retries and DLQ, and lints clean. The note is byte-identical and still ready. | — |
| Ready note, forced departure | The request overrides one choice (no DLQ: drop and log instead) | The pipeline follows the request, and exactly one row is appended (`Error handling`, what, why, today, `no`). `updated` is today, nothing else in the note changes, `hash --check` is still ready, and the note is in `artifacts`. | — |
| No note | A plain request | Built from the request as today, with no mention of a note | — |
| Not-ready note (draft, stale, malformed, or a `[blocking]` open decision) | The note exists but fails `hash --check` or the readiness list | Built from the request. The reply says the note is not ready and why. The note is untouched. Headless status is `complete`, with that line in `open_questions`. | not `blocked` |
| A note component the binary doesn't list | — | `blocked`, as today (unlisted component) | — |
| Pipeline already exists | A note and an existing `<pipeline>` | `blocked`, as today | — |

**Decision (2026-11-09, user):** the plan is kept whole, over the size guideline.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `01bbd338418a59d01c0c4938021e5a528d576ca6`. `T` has one untracked file, the user's manual-test leftover `orders_benthos_test.yaml`: leave it alone.

- **`R/skills/rpcn-author/SKILL.md`** (4,777 characters now, ceiling 4,803):
  - Step 2: after naming, run the fenced `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash --check <dir>/<name>.design.md`.
    - Exit 2 for a missing file means no note: go on.
    - Exit 0 with `data.ready: true` means read `references/design-note.md`, with `references/design-format.md`.
    - Anything else means not ready: note it, build from the request, and never touch the note.
    - A request that names only a `.design.md` takes `<name>` from its `pipeline`.
    - Step 1's "Exit 2 in any step" line needs this exception.
  - Description: add "builds from a ready <name>.design.md" and one trigger phrase ("build the pipeline from its design note").
  - **To pay for it:** to stay within 4,803 characters, tighten the wording elsewhere, or let Steps 2 and 7 share one generic `hash --check <dir>/<file>` fence. Steps 3–6 behaviour is unchanged.
- **New `R/skills/rpcn-author/references/design-note.md`** (skill-local):
  - the readiness list
  - map each Components row to Steps 3–4 (a close match chosen on `fields` exit 1 is a departure)
  - build in the Error handling, Delivery and ordering, and Idempotency choices
  - what counts as a departure: the request or the binary forces something a section says otherwise
  - append the rows with Edit after the last table row, and set `updated` to today
  - the reply names each row
  - list the note in `artifacts` only when it was edited
- **`R/skills/rpcn-author/references/status-block.md`:** a not-ready note is `complete`, with a line in `open_questions`, and `artifacts` includes an edited note.
- **`R/skills/rpcn-author/shared.txt`:** add `formats/design-format.md references/design-format.md`, then run `uv run tools/sync_shared.py`.
- **`R/evals/rpcn-author__trigger_from_design_note/`:** a positive case, copied from `rpcn-author__trigger_write_pipeline`. `R/evals/README.md` gets the new counts and cost.
- **`T/run_scenarios.py`:**
  - New `[[design]]` entry in `validate_expect`, beside `report`/`lint`/`file`:
    - `file` (required)
    - `deviations_added` (int ≥ 1, required)
    - `section` (str, optional)
  - The check compares the final note with the fixture copy:
    - everything before the `## Deviations` line is identical, except the frontmatter `updated:` line
    - the fixture's rows are a prefix of the final rows
    - exactly N rows were added, each with 5 cells, an ISO `date` and `resolved` `no`, and `section` matches when given
    - nothing follows the table
  - Add it where `[[report]]`/`[[file]]` run in `run_checks`, and count it in the "reads files" fixture guard (around 256-283).
- **`T/tests/test_run_scenarios.py`:**
  - validate tests for `[[design]]`, and check tests: pass, an extra row, an edited section, an edited existing row, wrong `resolved`
  - `ShippedAuthorScenarioTests.NAMES` gains the three scenarios
- **New `T/scenarios/`**, with `install = ["rpcn-author"]`, `no_cd`, `allowed_tools` as in `write_resources_yml`, and a non-default name in `pipes/`:
  - `rpcn-author__design_note`:
    - fixture `pipes/order_fulfilment.design.md`, hand-written to design-format, `status: ready`, `inputs: []`:
      - redpanda input, mapping, fallback (http_client, retries 3, then redpanda DLQ `orders.dlq`)
      - no ordering requirement
      - an empty Deviations table
    - checks:
      - `[status] complete` and lint `pass`
      - `[[lint]] pipes/order_fulfilment.yaml ok`
      - `[[file]] contains ["fallback","http_client","orders.dlq","retries"]`
      - `unchanged` = the note
      - `[[report]]` on the note with `ready = true`
  - `rpcn-author__design_deviation`:
    - the same note
    - the prompt overrides the DLQ
    - checks:
      - status complete and lint ok
      - `[[design]] deviations_added = 1`, `section = "Error handling"`
      - `[[report]]` on the note with `ready = true`
  - `rpcn-author__design_not_ready`:
    - the note with `status: ready`, but a `[blocking]` open decision
    - the prompt asks for Redpanda to stdout
    - checks:
      - status complete
      - `[[lint]]` ok
      - `[[file]] contains ["stdout"]`
      - `unchanged` = the note
  - **Rows not covered:** "no note" is covered by the existing write scenarios. The draft and stale cases follow the `hash --check` branch that 2.5 already proved.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-author/` (`SKILL.md`, `references/design-note.md`, `references/status-block.md`, `shared.txt`), then `uv run tools/sync_shared.py`: the design-note flow, within the size limit.
- [x] `R/evals/rpcn-author__trigger_from_design_note/` and `R/evals/README.md`.
- [x] `T/run_scenarios.py` and `T/README.md`: the `[[design]]` check.
- [x] `T/scenarios/rpcn-author__design_{note,deviation,not_ready}/`, with fixture notes passing `hash --check`, run by the real script.
- [x] `T/tests/test_run_scenarios.py`: the `[[design]]` and shipped-scenario tests.

**Acceptance Criteria:**
- **Given** the repo, **when** `uv run tools/validate_skills.py` runs, **then** `rpcn-author` has no warnings and its `SKILL.md` is 4,803 characters or less.
- **Given** both cached binaries in `RPCN_TEST_BINARIES`, **when** `run_scenarios.py --source local:../rpcn-skills --scenario 'rpcn-author__*' --runs 1 --no-judge` runs, **then** all 10 author scenarios pass.
- **Given** the reviewed and committed tree, **when** `uv run tools/run_evals.py` runs (about $17), **then** the gate passes, every scenario passes 3/3, and a `dirty: false` record is committed.

## Implementation Notes

- `SKILL.md` is 4,801 characters. To pay for the Step 2 note check and the description phrase, Steps 2 and 7 share one `hash --check <file>` fence, and the intro, Steps 1, 5 and 6, Next and the description were tightened (the description drops "plus resources and .env.example files when needed"). Steps 3-6 behaviour is unchanged.
- Step 2 tells a missing note (exit 2 with "not found") from a malformed header (exit 2 otherwise, so not ready), and Step 1's exit-2 rule excepts the missing note.
- `references/design-note.md` adds one rule beyond the plan's list: one choice is one departure, so one row under the section that makes the choice (dropping the DLQ is one `Error handling` row, though the DLQ is also in Components and Outputs). Without it the deviation scenario's "exactly one row" is fragile.
- `[[design]]` also requires the final `updated:` to be an ISO date, a non-empty `section`, `what` and `why`, and its `file` to be a fixture file (a setup error otherwise). Trailing blank lines after the table are ignored.
- Matrix audit follow-up (user's choice): `T/scenarios/rpcn-author__design_draft` covers the draft-note row. Its note is `design_note`'s fixture with only `status: draft` (`hash --check` exit 1), with the same Redpanda-to-stdout prompt as `design_not_ready`, and checks `complete`, lint ok, `stdout` in the file, the note `unchanged` and `no_cd`. It passed a 1-run smoke on both binaries. The stale-note row stays covered by 2.5's `hash --check` branch.
- `rpcn-test` keeps a pre-existing validator warning (`references/design-format.md is never named in SKILL.md`); this story doesn't touch rpcn-test.
- **After the review patches:** the validator passes (`rpcn-author` has no warnings; `SKILL.md` is 4,801 characters), and so do `sync_shared --check`, all four `tools/` suites, `rpcn_check` on both binaries, and T's 190 tests. Smoke run of all 11 author scenarios: 11/11 pass on both binaries, $2.67 (`T/runs/20261109-192414`).
- **Fixture fix during the first full eval:** `design_note` run 1/3 failed `unchanged`. The fixture's Error handling said failed orders reach `orders.dlq` "with its original payload", but its own mapping adds `total_cents` first. The agent rightly recorded a Deviations row for that. The eval was stopped after the gate (accuracy 1.0). The wording in all four fixtures became "as the mapping left it" (T commit after `292e5b1`), and `design_note` then passed 3/3 ($1.29). `skills/` is unchanged.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 5 low (2 grouped as one deferral), 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A malformed note's exit 2 falls under Step 1 and status-block's `blocked` rule, which contradicts Step 2 and AD-8 | medium | patch | `_check_handoff`'s `fail()` returns `EXIT_ENV` for a bad header. Step 1 now exempts any exit 2 from Step 2's design-note check, and status-block says so. |
| `<dir>` is undefined when only a `.design.md` is named, so the note in `pipes/` is missed | medium | patch | `<dir>/` is now the folder of the file the user names. |
| `[[design]]` can't detect a missed `updated` edit, or a stale row date | medium | patch | The fixtures' `updated` was today's date. They now say `2026-10-23`, and `check_design` requires `updated` to change and to equal each added row's `date`. New failing tests. |
| Step 7 reworded, and its "state: changed means stale" hint dropped | low | patch | The hint is restored. Sharing the fence was allowed by the Code Map. |
| The scenarios don't assert `artifacts`, the `open_questions` line or the reply, and the deviation pipeline isn't checked for the dropped DLQ | low | defer | The runner's `[status]` check uses exact equality, and it has no "does not contain" check. That predates this story. Logged in `deferred-work.md`. |
| AC 2 says 10 author scenarios, but there are 11 with `design_draft` | low | reject | The fix would edit this build's plan. The extra scenario is recorded in Implementation Notes. |
| `check_design` misses line-ending, final-newline and heading-whitespace changes | low | reject | Unlikely in use, since Edit keeps line endings. A stricter compare adds complexity. |
| The "in the plural" kind-to-category rule is wrong for `metrics` | low | reject | No fixture uses it, and `list` rejects an unknown category, so the agent recovers. |

## Design Notes

- **Why the not-ready line goes in `open_questions`:** the caller should act on it (fix the note or re-run Design), but it doesn't block (AD-8). `reason` stays null for a `complete` run.
- **Why there's a new runner check:** "exactly one row" and "touching nothing else" can't be expressed with `contains` or `unchanged`. Comparing against the fixture copy is deterministic and costs nothing.
- **Why the not-ready scenario uses a `[blocking]` item:** the hash branch (draft or stale) was already proven in 2.5. The readiness-list judgment is new.

## Verification

**Commands:**
- `uv run tools/validate_skills.py` and `uv run tools/sync_shared.py --check`: exit 0.
- All four `tools/` suites, and `rpcn_check` with both binaries: pass.
- In `T`: `uv run tests/test_run_scenarios.py` passes, then the smoke run in the AC.
