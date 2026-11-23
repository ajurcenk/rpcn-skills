---
title: "A Design re-run keeps Author's Deviations"
type: 'feature'
ticket: '5'
created: '2026-11-23'
status: 'done'
baseline_revision: '311fdb0b41caf1bd3795672fde35b6b90ca6acbe'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'tools/shared/formats/design-format.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** rpcn-design stops at Step 2 whenever the note already exists ("re-running over an existing note is not supported yet"). So when a design changes, Author's Deviations rows can only be lost (a new note under a new name) or left stale. Epic R6 and `design-format.md` ("Who writes what") ask for a re-run that rewrites the note. It must keep every Deviations row, and mark each row the rewrite absorbs `resolved: yes`, never removing one.

**Approach:**
- **New reference:** `skills/rpcn-design/references/rerun.md`, read from Step 2 when the note exists and the request asks to change it (see the decision below):
  - Read the existing note. It is the starting point, and the request's changes win.
  - Re-run Steps 3 and 4 for every component the rewrite names.
  - Copy every Deviations row in its original order, changing only `resolved`.
  - Mark a row `yes` when the rewritten section now says what the pipeline does (the row's `what`). Otherwise it stays as it was.
  - Refresh `updated`, `produced_by` and `rpcn_version`. Keep `inputs` as `handoff-header.md` says.
  - Check with `hash --check` as for a new note.
- **SKILL.md Step 2:** the "a note exists" branch points at `rerun.md`. It stays within the size limit.
- **The reply** names each row it marked `resolved`, and each row it kept open.

**Decision (2026-11-23, user):** a re-run happens only when the request asks to change the note, for example "update", "revise", "re-run the design", or a stated change such as "the API now …". A plain "design X" over an existing note keeps today's stop: `blocked` headless, with nothing written. An interactive run asks in round 1 whether to update the note, and writes nothing until the user answers. `rpcn-design__existing_note` stays as it is.

## Boundaries & Constraints

**Always:**
- A Deviations row is never deleted, reordered or reworded. Only `resolved` changes, and only from `no` to `yes`.
- The `design@1` format is unchanged.
- `SKILL.md` stays at or under 4,803 characters, with no validator warnings for the three skills.
- The headless or interactive rules of 3.3 and 3.4 apply to the rewrite's open decisions.

**Never:**
- Changing rpcn-author or rpcn-test.
- Writing pipeline YAML.
- Marking a row resolved that the rewrite doesn't absorb.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Re-run absorbs one of two rows | a note with two `resolved: no` rows; the request adopts one row's `what` | both rows kept in order; the absorbed one `yes`, the other `no`; the note `ready` | — |
| Re-run absorbs none | the request changes another section | every row kept, all still `no` | — |
| A row already `yes` | — | kept as `yes` | — |
| Note has a bad header | `hash --check` exits 2 with another error | stop, write nothing (`blocked` headless) | as Step 1 |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, baseline `0d5bf956cefb5e2406546f084516ee16860592d5`; leave the untracked `orders_benthos_test.yaml` alone).

- **`R/skills/rpcn-design/SKILL.md`** (4,770 characters): Step 2's second bullet ("Anything else: a note exists … not supported yet") and Next's "Note exists" line.
- **New `R/skills/rpcn-design/references/rerun.md`:** the rules above.
- **`R/skills/rpcn-design/references/note-writing.md`, "Sections" item 11:** a re-run copies the rows (`rerun.md`) instead of writing an empty table.
- **`R/skills/rpcn-design/references/status-block.md`:** on a re-run, `artifacts` lists the note. Today's `blocked` for an existing note applies only to a run that isn't a re-run.
- **`R/tools/shared/formats/design-format.md`:** already has the rule. Don't edit it.
- **T, new `rpcn-design__rerun_deviations`** (a subfolder with a non-default name, headless):
  - **Fixture:** a ready note with two `resolved: no` rows on distinct dates. One is Delivery and ordering (`max_in_flight: 8`, as in `design-format.md`'s example); the other is a second section.
  - **Request:** adopts the first row ("posts may now go 8 at a time; order doesn't matter").
  - **Checks:** `[[report]] ready = true`. The note contains both rows' `what` text, the first row's line ending `| <its date> | yes |` and the second's `| <its date> | no |`. Status `complete`, with the note in `artifacts`. No YAML.
- **T, `rpcn-design__existing_note`:** unchanged; it must keep passing (a plain request is no re-run).
- **T, new `rpcn-design__rerun_ask` (interactive):** the same fixture shape, with a plain "design X" request. The reply asks whether to update the note (`reply_contains` `?` and the note's name), and the note stays `unchanged`.
- **`T/tests/test_run_scenarios.py`:** shipped-scenario tests.
- **`R/evals/README.md`:** the count and cost.

## Tasks & Acceptance

**Execution:**
- [x] `rerun.md`, `SKILL.md` Step 2 and Next, `note-writing.md` item 11, and `status-block.md` -- R6.
- [x] T: the two scenarios and their tests; README count.
- [x] Smoke: the two new scenarios at `--runs 2` on both pins, then every `rpcn-design__*` scenario once.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check`, all `tools/` suites and T's tests run, then all pass.
- Given the smoke run, when it finishes, then every `rpcn-design__*` scenario passes.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs), then it passes with `dirty: false` and the record is committed.

## Implementation Notes

- `SKILL.md` is 4,783 bytes (validator: no warnings). To fit, Step 2's existing-note bullet drops "(`reason` names it)" (status-block.md still says it), and Next's draft line became "answer each `[blocking]` item in an update" now that a re-run exists.
- Step 2 now splits "other exit 2" (stop as Step 1, the bad-header row) from "a note exists".
- `questions.md`'s opening line, which said an existing note always stops with no question, now matches the decision: interactive asks only whether to update the note.
- T fixtures: `posts/order_push.design.md` (re-run) and `hooks/order_feed.design.md` (ask); both hold a Delivery and ordering row dated 2026-10-23 and an Error handling row ("retries 5 times, not 3") dated 2026-11-02. The re-run check matches each row's `section | what` cells verbatim.
- Smoke (first pass): `rerun_deviations` and `rerun_ask` PASS 2/2 on both pins (`runs/20261123-115025`); every `rpcn-design__*` scenario once, 19/19 PASS (`runs/20261123-115130`).
- Matrix audit (coordinator): three rows had no scenario.
  - "A row already yes": `rerun_deviations`' fixture gained a first row, Batching, dated 2026-09-15 and already `yes`; the check wants it still ending `| 2026-09-15 | yes |`.
  - "Re-run absorbs none": new headless `rpcn-design__rerun_none` (`relay/order_hook.design.md`, the request changes only the peak rate to 400/s); both rows stay `no`.
  - "Note has a bad header": new headless `rpcn-design__rerun_bad_header` (`broken/order_tap.design.md`, `updated 2026-11-02` with no colon, so `hash --check` exits 2; `format: design@9` only exits 1, so it wasn't used). Expects `blocked`, the note unchanged.
  - The first smoke failed `rerun_bad_header` 1 of 2: the agent read status-block.md's "a re-run is not blocked by the note it rewrites" as leave to repair the header. Fixed in the skill text: `rerun.md` now opens with "a re-run needs exit 0 or 1; an exit 2 other than not-found stops, never fix the header by rewriting", and `status-block.md` lists that exit 2 as `blocked` on a re-run too. `SKILL.md` unchanged (4,783 bytes).
  - After the fix, at `--runs 2` on both pins (`runs/20261123-120500`): `rerun_deviations`, `rerun_none`, `rerun_bad_header`, `rerun_ask` and `existing_note` all PASS 2/2.

- **Final verification (2026-11-23, after the review patches):** validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` tests on both pins 192 passed; T 378 passed, 3 skipped. Smoke (all 21 `rpcn-design__*` once): 20/21. `rerun_none` failed: the session edited the note with Edit and never invoked rpcn-design, because the request "Update the design note …: peak traffic is now 400" matched no trigger in the description.
- **Trigger fix (outside the Code Map):** the description now names "update my design note" and "an existing note updated". It was shortened elsewhere to fit, keeping every trigger phrase: 874 characters, `SKILL.md` 4,795, no validator warnings. New positive trigger case `evals/rpcn-design__trigger_update_note`. Smoke: `rerun_none` 2/2, `rerun_deviations` 1/1, `npx_trigger` 1/1.

- **Eval record:** `evals/results/2026-11-23-a64ae9f6227e.json` passed with `dirty: false` on the first run, at $46.50. Trigger accuracy was 1.0, including the new update-note case. All 56 pass scenarios passed 2/2, linted on 4.100.0 and 4.117.0 with sessions on 4.117.0.
- **Pushed:** `b50f2a4..72cf82a`. CI run 45234490562 was green. The T commit (`125c0d0`) stays local.

## Plan Change Log

## Review Triage Log

Quick pass (2026-11-23): 0 high, 3 medium, 4 low, 0 false. All seven route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | `rerun_deviations` and `rerun_none` check row prefixes and date endings as separate substrings, so a reorder or a reworded `why` passes | medium | patch | Check each table as one multi-line `contains` string (the full rows in order), so order and every cell are checked. |
| 2 | `rerun_deviations` can mark a row `yes` without its section being rewritten | medium | patch | Add a `contains` on the rewritten Delivery and ordering text (`max_in_flight: 8`), as `rerun_none` does with `400`. |
| 3 | The interactive "yes, update it" follow-up is unspecified: whether a yes counts as a change request, and whether that question uses up a round | medium | patch | State in `rerun.md` and `questions.md` that a yes to that question is a request to change the note (a re-run), and that it isn't one of the two rounds. |
| 4 | The "by its path" rule sits in `questions.md`, which the Step 2 stop path never reads | low | patch | SKILL.md Step 2 says to ask whether to update `<note>`. |
| 5 | The second-note guard `[!o]*` misses `order_feed_v2…` and `.bak` | low | patch | Add the `<name>[!.]*` and `<name>.[!d]*` globs to `rerun_ask`, `rerun_deviations` and `rerun_none`, as `rerun_bad_header` has. |
| 6 | "story 5" where every neighbour says "story 3.5" | low | patch | Rename it in the README, the scenario comments and the test docstring. |
| 7 | An extra blank line before `ShippedDesignRerunScenarioTests` | low | patch | Remove it. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 1 --no-judge --scenario 'rpcn-design__*'` -- all PASS
