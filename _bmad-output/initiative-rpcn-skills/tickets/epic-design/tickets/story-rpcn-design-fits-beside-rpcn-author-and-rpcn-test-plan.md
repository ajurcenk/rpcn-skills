---
title: 'rpcn-design fits beside rpcn-author and rpcn-test'
type: 'feature'
ticket: '7'
created: '2026-11-23'
status: 'done'
baseline_revision: 'c22157cc782f07897d442f7057413974f8bf76da'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'evals/README.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** epic R9 (AD-9) asks that the sibling skills name rpcn-design wherever their triggers collide. Today rpcn-author's description and Next never mention rpcn-design, and rpcn-test's mention only "designing … them". No trigger case checks that "design a pipeline" stays out of rpcn-author and rpcn-test. Epic 1's conventions (size, references read at their step, a Next line for each situation, headless status) also need a final check for rpcn-design.

**Approach:**
- **rpcn-author:**
  - The description's "Not for" names rpcn-design for designing a pipeline before it is built.
  - Next adds a line for a draft or not-ready note: answer it with rpcn-design.
- **rpcn-test:**
  - The description's "Not for" names rpcn-design.
  - Next adds a line for a Design check `mismatch` that the design should absorb: update the note with rpcn-design, then rebuild with rpcn-author.
- **rpcn-design:**
  - Check each convention. Fix only what fails, for example a situation in Steps 2–6 with no Next line, such as a blocked headless run.
- **New sibling near-miss negatives:**
  - `rpcn-author__miss_design_pipeline`: "design a pipeline … before we write it" must not fire rpcn-author.
  - `rpcn-test__miss_design_note`: a design-note request must not fire rpcn-test.
- **README:** update the trigger table counts.
- **Decision (2026-11-23, user):** 3.7 joins the 3.9 group. It gets a trigger-suite smoke and the affected scenarios once, and is committed locally. One `--with-compare` record at 3.9 covers 3.6, 3.7, 3.8 and 3.9, and all four are pushed together.
- **Size:** every `SKILL.md` stays at or under 4,803 characters, and every description at or under 1,024. rpcn-author has 6 characters to spare, so its additions need trims elsewhere in the same file that keep the meaning.

## Boundaries & Constraints

**Always:**
- The validator shows no warnings for the three skills.
- The trigger gate passes (accuracy 1.0), with each sibling negative silent for the wrong skill.
- Every existing trigger phrase stays in its description.
- `design@1` is unchanged.

**Never:**
- Changing what a skill does. Only descriptions, Next lines, the trims and trigger cases change.
- Removing a trigger phrase to make room.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| "Design a pipeline … before we write it" | trigger suite | rpcn-design fires; rpcn-author and rpcn-test don't | — |
| "Write a pipeline …" | trigger suite | rpcn-author fires; rpcn-design doesn't (existing `miss_write_yaml`) | — |
| A draft note, Author run | Author's reply | its Next points at rpcn-design | — |
| A Design check mismatch | Test's reply | its Next names rpcn-design for a design change | — |

</frozen-after-approval>

## Code Map

- **`R/skills/rpcn-author/SKILL.md`** (4,797 characters; description 756): description "Not for …" and `## Next` (line ~112). Trim elsewhere in the same file to fit, without changing a rule.
- **`R/skills/rpcn-test/SKILL.md`** (4,761 characters; description 994, so 30 to spare): description "Not for …" and `## Next`.
- **`R/skills/rpcn-design/SKILL.md`** (4,795): the conventions check. Its Next has lines for ready, draft, existing note and binary. Check Step 2's bad-header and headless-blocked cases, and Step 6's header-fix limit.
- **New `R/evals/rpcn-author__miss_design_pipeline/`, `R/evals/rpcn-test__miss_design_note/`:** a `prompt.md` with `tags: [trigger, negative]`, `max_turns: 2` and `allowed_tools: [Skill]`, plus `graders/not-fired.md` for that skill (`min: 0`, `max: 0`, `arm: both`). Copy `R/evals/rpcn-author__miss_lint_pipeline/` for the shape.
- **`R/evals/README.md`** lines 12–20: the sibling-negative rows and counts.
- **Validator and trigger gate:** `uv run tools/validate_skills.py`. The trigger suite is `claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish --trust-plugin --json <out>`, gated by `tools/eval_gate.py`.

## Tasks & Acceptance

**Execution:**
- [x] rpcn-author and rpcn-test descriptions and Next, with the trims -- R9.
- [x] The rpcn-design conventions check, fixing any gap.
- [x] The two negative cases and the README counts.
- [x] Smoke: the trigger suite at `--runs 2` through the gate (accuracy 1.0), plus the scenarios whose replies carry a changed Next once on both pins: `rpcn-author__design_draft`, `rpcn-author__design_not_ready`, `rpcn-test__design_mismatch` and `rpcn-design__chain_tracer`.

**Acceptance Criteria:**
- Given the repo, when the validator, `sync_shared --check` and all `tools/` suites run, then all pass with no warnings.
- Given the trigger suite, when it runs through the gate, then accuracy is 1.0 and both new negatives are silent.
- Given the reviewed tree, when it is committed, then it stays local until 3.9's record (decision above).

## Implementation Notes

- **Sizes (characters, `len`):** rpcn-author 4,801 (description 802), rpcn-test 4,717 (description 1,017), rpcn-design 4,799 (description 874). Validator: no warnings.
- **rpcn-author trims (wording only):** the unexpanded `${CLAUDE_SKILL_DIR}` line takes rpcn-test's shorter form; "Calls print JSON"; "One `uv run …`"; "or nothing (project root)"; `(`tls.enabled`, `a[].b`)`; "each field with `required: true`"; "fix each `errors` entry (check new fields per Step 4)"; `.resources.yml` for `.yml`; the status-block line drops "written and"; the description says "applies a <name>.test-report.md's proposed changes". The Next line is "Design note not ready: answer it with rpcn-design" (a draft note is a not-ready note in Step 2).
- **rpcn-test trim:** the 102 characters over the limit could not come from wording alone, so the status block JSON template moved from SKILL.md into `references/status-block.md` (the shape rpcn-author and rpcn-design already use). SKILL.md says "End with exactly one fenced `json` block, then nothing, written and filled as `references/status-block.md` says." The template is byte-identical.
- **rpcn-design conventions check:** Steps 2 (other exit 2, a bad header) and 6 (the header fix limit) had no Next line; added "Note header error: fix it, re-run." Trimmed the `${CLAUDE_SKILL_DIR}` line and "Calls print JSON" to fit. The headless-blocked existing note is covered by "Note exists: ask to update it."
- **Trigger smoke (2026-11-23):** 42 cases x 2 runs, gate ok, accuracy 1.0 (84/84; negatives 32/32).
- **Scenario smoke:** `rpcn-author__design_draft`, `rpcn-author__design_not_ready`, `rpcn-test__design_mismatch`, `rpcn-design__chain_tracer` PASS 1/1 (lint on 4.100.0 and 4.117.0). Both Author replies point at rpcn-design. The `design_mismatch` fixture's mismatch is a pipeline error, so Test's Next rightly says apply with rpcn-author; its "keep the drop" alternative still says to record a Deviations row with rpcn-author, not to update the note with rpcn-design (the wording comes from rpcn-test's references, which this story does not change).

- **Final verification (2026-11-23, after the review patches):** validator no warnings; `sync_shared --check` clean; `tools/tests skills` 146 passed; `rpcn_check` on both pins 193 passed. Sizes: rpcn-author 4,803, rpcn-test 4,709, rpcn-design 4,802. The descriptions are unchanged since the trigger gate run, which passed at accuracy 1.0 with both new negatives silent. Smoke: every `rpcn-test__*` scenario once, 21/21, checking the moved status-block template (`T/runs/20261123-165018`). After the patches: `rpcn-design__rerun_bad_header`, `rpcn-test__design_mismatch` and `rpcn-author__design_not_ready`, each 1/1 (`T/runs/20261123-171215`).
- **Not done here:** the record (3.9's `--with-compare` run, which covers 3.6–3.9) and the push.

- **Pushed:** `72cf82a..560f483`, with 3.6–3.9 together. CI run 45450913995 was green. The record is `evals/results/2026-11-23-d38b0a5cc8a4.json`. T commits stay local.

## Plan Change Log

## Review Triage Log

- Fixed (review 1): rpcn-test's mismatch Next now says re-run rpcn-test (Author never writes over an existing pipeline); `design-check.md` §4 gives each `mismatch` a third line (update the note with rpcn-design, then re-run rpcn-test); rpcn-design's Next says "Note can't be read: fix it by hand, re-run."; rpcn-author's Next says "update it with rpcn-design" and Step 1 keeps "here and below" (room from "`<dir>/` is the named file's folder"). Sizes: author 4,803, design 4,802, test 4,709. Validator clean; `rpcn-design__rerun_bad_header`, `rpcn-test__design_mismatch`, `rpcn-author__design_not_ready` PASS 1/1 (runs/20261123-171215).

Quick pass (2026-11-23): 0 high, 3 medium, 3 low, 0 false. All six route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | rpcn-test's Next "update the note with rpcn-design, then rebuild with rpcn-author" sends the user down a path Author refuses | medium | patch | Author Step 2 never writes over an existing pipeline, so a headless rebuild ends `blocked`. Next becomes: update the note with rpcn-design, then re-run rpcn-test. |
| 2 | Test's Next and `design-check.md` §4 point a mismatch at different skills | medium | patch | §4 gives only the `diff` or an Author Deviations row. Add a third outcome: the design changes (rpcn-design updates the note, then rpcn-test runs again). |
| 3 | rpcn-design's "Note header error: fix it, re-run" reads as leave to rewrite the header, which `rerun.md` forbids, and it misses the other Step 2 exit-2 errors | medium | patch | Reword it to say the user fixes the note or file by hand, covering any Step 2 read error. |
| 4 | rpcn-author's "answer it with rpcn-design" doesn't fit a stale or changed-input note | low | patch | Reword it to "update it with rpcn-design". |
| 5 | The rpcn-author trim dropped "here and below" from the `${CLAUDE_SKILL_DIR}` fallback | low | patch | Restore the scope, finding the room elsewhere and staying at or under 4,803. |
| 6 | The smoke missed `rpcn-design__rerun_bad_header`, the reply that carries the new Next line | low | patch | Add it to the smoke. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills` -- pass, no warnings
- `claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish --trust-plugin --json <out>.json`, then `uv run tools/eval_gate.py <out>.json` -- accuracy 1.0
- `cd T && RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run run_scenarios.py --source local:<R> --runs 1 --no-judge --scenario <each above>` -- PASS
