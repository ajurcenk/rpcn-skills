---
title: 'Refactor sweep (epic 3)'
type: 'refactor'
ticket: '10'
created: '2026-11-24'
status: 'built'
baseline_revision: '886580eaa5824c5a1887d4089a5ca95a959af946'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** stories 3.2–3.8 and the question-tool change each added text to rpcn-design and rpcn-author. Two problems came out of that:

- **No room:** rpcn-author's `SKILL.md` is at the 4,803-character limit and rpcn-design's at 4,802, so any later edit has no room.
- **Untidy text:** a read-only scan (2026-11-24) found stale or contradictory wording, overlong lines and three names for one thing.

Epic 3 deferred only two items, and neither is cleanup: multi-turn scenarios are a new runner feature, and the `fallback_error` flake was fixed in 3.4.

**Decision (2026-11-24, user):** fix the contradictions and keep the repeats. Where a rule is stated in more than one place, make every copy say the same thing, and remove none. The repetition may be what keeps the model on the exact lines.

**Approach (cleanup only; every rule stays as it is):**
1. **Contradictions and stale wording:**
   - **Step 6 order:** `note-writing.md` "Before Step 6" and `SKILL.md` Step 6 give opposite orders (Readiness list vs `hash --check`). Make them agree on `SKILL.md`'s order: hash first, then the Readiness list.
   - **`patterns.md` pattern 1:** "(interactive, with no suggestion)" and "Two cases keep the default DLQ instead" are worded unclearly. Reword both to match `questions.md`.
   - **The `[blocking]` template:** `[blocking] <the question>.` in `note-writing.md` and `questions.md` should allow the failure-target line `…? (Suggested: …)`.
   - **rpcn-author `questions.md`:** drop "as before", which refers to nothing.
   - **rpcn-author `SKILL.md`:** "(headless: `open_questions`)" for no fitting component contradicts `blocked` in its status block. Say `blocked`.
   - **rpcn-design `SKILL.md`:** write reference paths as `references/…`.
2. **Headroom:** move passages from each `SKILL.md` into an existing reference without changing a rule. The scan's candidates:
   - rpcn-design: the Step 6 fix loop goes into `note-writing.md` "Before Step 6", and the status line points at the Ready rule.
   - rpcn-author: Step 5's lead-in, and Step 7's hash-check sentence into `apply-report.md` §1.

   Target: each `SKILL.md` at or under 4,650 characters.
3. **Tidy:**
   - Reflow lines over 80 characters (not code examples), and the run-on proof list in rpcn-author's `questions.md`.
   - Name the pins the same way everywhere.
   - Give the question-tool paragraphs the same wording for the parts the two skills share.
   - Use "failure target" as the one term in rpcn-design, and keep rpcn-author's "failure path" where it means the pipeline path.

## Boundaries & Constraints

**Always:**
- No rule, trigger phrase, description, scenario or check changes.
- `SKILL.md` stays at or under 4,803, and every description at or under 1,024. The validator shows no warnings.
- The shared copies (`design-format.md`, `handoff-header.md`, `test-report-format.md`, `blobl-files.md`, `samples-format.md`, `rpcn_check.py`) are edited only through `tools/shared` and `sync_shared`. This sweep leaves them alone.
- A record at 2 runs before the push, since `skills/` changes.

**Never:**
- Removing a duplicated rule (decision above).
- A new rule or behaviour. If one is found, it becomes a backlog story.

</frozen-after-approval>

## Code Map

- `R/skills/rpcn-design/SKILL.md` (4,802 characters): Step 2 (`:52-53`), Step 5 status (`:86-88`), Step 6 (`:96-100`), and the reference paths (`:98-99`).
- `R/skills/rpcn-design/references/`:
  - `note-writing.md`: Before Step 6 `:130-133`, `[blocking]` template `:118`, overlong lines.
  - `patterns.md`: `:28-41` pattern 1 wording, `:16` pin naming, `:105` and `:145` long lines.
  - `questions.md`: `:94` long line, `:104` template, `:66-70` tool paragraph.
  - `rerun.md` and `status-block.md`: wording only, to agree with the others where they repeat.
- `R/skills/rpcn-author/SKILL.md` (4,803 characters): `:77` headless claim, `:81-82` Step 5 lead-in, `:106-108` Step 7 hash sentence, `:16-17`.
- `R/skills/rpcn-author/references/`:
  - `questions.md`: `:41-45` proof list, `:73-81` tool bullet (shared wording; keep its rules), `:97-99` "as before" and line break.
  - `apply-report.md` §1: receives the Step 7 hash-check sentence.
- `R/evals/README.md`: unchanged unless the counts move (they don't).

## Tasks & Acceptance

**Execution:**
- [x] Items 1–3 in the files above.
- [x] Checks: validator, `sync_shared --check`, `tools/tests skills`, `rpcn_check` on both pins.
- [ ] Smoke every `rpcn-design__*` and `rpcn-author__*` scenario once on both pins, plus `rpcn-test__design_*`.

**Acceptance Criteria:**
- Given the repo, when the checks run, then all pass, with rpcn-author's and rpcn-design's `SKILL.md` each at or under 4,650 characters.
- Given the smoke, when it finishes, then every scenario passes.
- Given the reviewed, committed tree, when `run_evals.py` runs (2 runs), then it passes with `dirty: false`. Then ask before pushing.

## Implementation Notes

- rpcn-design `SKILL.md` 4,802 -> 4,642; rpcn-author `SKILL.md` 4,803 -> 4,615.
- Step 6 fix loop moved to `note-writing.md` "Before Step 6", now in SKILL.md's
  order (hash first, then the Readiness list). The Step 5 status line points at
  `design-format.md`'s Ready rule; its wording is kept as a copy in
  `note-writing.md` (Header and title), so no copy of the rule is lost.
- rpcn-author: Step 5's lead-in moved to the top of `questions.md`; Step 7's
  go-on/stop sentence moved to `apply-report.md` §1 (SKILL.md keeps the
  `hash --check` call and points at §1).
- Pins named "both pins, 4.100.0 and 4.117.0" in `patterns.md` and rpcn-author
  `questions.md`. `[blocking]` template allows the headless
  `…? (Suggested: <the DLQ>.)` line in `note-writing.md`, `questions.md` and
  `patterns.md` (all now say `<the DLQ>`). Question-tool paragraphs share
  "a chosen option or free text (an "Other" choice)". `patterns.md` "failure
  path" -> "failure target".

## Plan Change Log

## Review Triage Log

Quick pass (2026-11-24): 0 high, 2 medium, 1 low, 1 rejected. The implementation agent had committed `8ffe45b` and started the record before review. That record was stopped (nothing written) and the fixes go on top.
- medium: a new parenthetical in `questions.md` let an interactive run write the `(Suggested: …)` line. Dropped; the bullet matches its earlier text.
- medium: pattern 1's `accepts ("go ahead")` narrowed acceptance, and `note-writing.md`'s copy no longer matched. Restored "an interactive pick the user accepted".
- low: the moved Step 6 loop ran `hash --check` a second time, under the heading "Before Step 6". It now starts from Step 6's result, the heading is "Step 6: checking the note", and the pointers in `SKILL.md` and `rerun.md` are updated.
- rejected: the stale plan checkbox (fixing it edits the plan).

After the fixes: a 7-scenario smoke passed 7/7 (`T/runs/20261124-230907`). Validator no warnings; `tools/tests skills` 146 and `rpcn_check` 196 passed on both pins. `SKILL.md`: rpcn-author 4,615 and rpcn-design 4,644 characters.

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run --with pytest pytest -q tools/shared/rpcn_check/tests` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 1 --no-judge --scenario 'rpcn-design__*' --scenario 'rpcn-author__*' --scenario 'rpcn-test__design_*'` -- all PASS
