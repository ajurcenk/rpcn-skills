---
epic: epic-existing-pipelines
date: 2026-11-28
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Epic 8, Existing pipelines: retrospective

State: Phases 1 (Gather) and 2 (Analyze) are done. Phase 3 (team discussion) was not asked for. Phase 4 (Decide) and Phase 5 (Finalize) have not run, so their sections below are placeholders.

## Epic summary

- **Epic:** `epic-existing-pipelines` (id 8), covering initiative R21 and R22. The epic file declares Requirements R1–R6, Constraints and Done when, so the verdict criteria are **declared**.
- **Tickets** (`tickets.py status`, in build order): all six are `done`. None is at `built`, and `pending_tickets` is empty.

  | Ref | Title | Risk | Status |
  |---|---|---|---|
  | 8.1 | Tracer: rpcn-design describes a hand-written pipeline | high | done |
  | 8.2 | Author proposes a change as a change@1 file when headless | high | done |
  | 8.3 | Author changes a pipeline interactively through Edits | medium | done |
  | 8.4 | Apply a design change to an existing pipeline | medium | done |
  | 8.5 | The change and describe modes fit beside the siblings | medium | done |
  | 8.6 | Refactor sweep | low (plan says medium) | done |

- **Also in scope:** `_bmad-output/initiative-rpcn-skills/plan-eval-resume.md` (`run_evals --resume`). It was built during the epic and is not a ticket, so it gets its own range.
- **Going-in concern (user):** weight the story seams, where one story's output feeds another's and no single build session saw both sides:
  1. 8.1's describe note feeding rpcn-design's re-run and 8.4;
  2. 8.2's and 8.3's change mode feeding 8.4;
  3. the SKILL.md cuts in 8.5 and 8.6 against the rules earlier stories put there.

### Ranges (from the plans' `baseline_revision`, oldest first)

| Plan | Range | Commits (rpcn-skills) | Notes |
|---|---|---|---|
| 8.1 | `9bc1695..64f13c5` | `cc6c727` feat, `1483688` record, `64f13c5` mark done | |
| 8.2 | `64f13c5..3e007ff` | `3e007ff` feat | 8.3's baseline is 8.2's own commit, so 8.2's range ends there |
| 8.3 | `3e007ff..9ed7b07` | `a675074` feat, `15aebfb` fix (rpcn-test, no ticket), `491e126` record 8.2+8.3, `9ed7b07` mark done | |
| 8.4 | `9ed7b07..38d3486` | `38d3486` feat | |
| 8.5 | `38d3486..4fb03b6` | `4fb03b6` feat | |
| 8.6 | `4fb03b6..df8ef84` | `df8ef84` refactor | |
| eval resume | `df8ef84..41acfd7` (inferred: HEAD = `41acfd7`, the last epic commit) | `7188d01` feat, `1a8bb56` record 8.4–8.6, `41acfd7` mark done | The 8.4–8.6 record and the mark-done commit fall in this range. By subject they belong to 8.4–8.6 |

There are no merges in any range (`merge_count` 0 everywhere), and no binary revisions. `git_evidence.py` ran once per range, and its output is in the session scratchpad.

**Test repo `rpcn-test-skills`** (local only, read-only here): its epic-8 commits are `8687729` (8.1 scenarios), `64ef6f4` (8.1 describe_missing fix), `8e7fbfb` (8.2 scenarios), `4f62a8c` (8.3 `write_lacks` and change_edit), `41786dd` (8.4 six scenarios) and `2dda27c` (runner `--resume`). 8.5 and 8.6 have no T commits: 8.5's trigger cases live in rpcn-skills `evals/`, and 8.6 changed no scenario. Across `5c05827..2dda27c` there are 72 files, +4,450/−20.

### Evidence inventory

| Evidence | Available | Notes |
|---|---|---|
| Epic file | yes | Requirements R1–R6, Constraints, Done when, Boundaries, Notes (5 user decisions) |
| Story files | none | No ticket was pulled. `tickets.toml` holds each description and verify |
| Plans | 6 + eval-resume | All `status: done`. Each has a Review Triage Log with one quick pass, plus Implementation Notes and Verification. Plan Change Logs are all empty |
| Run folders | none | No `<type>-*/` folders in the epic folder |
| Companions | architecture | `architecture-rpcn-skills.md`. AD-6 and AD-8 were opened for findings |
| Eval records | 3 | `evals/results/2026-11-25-fa87b4f80a78.json` (8.1: 66 scenarios, git_head `cc6c727`); `2026-11-27-1978440ab31a.json` (8.2+8.3: 71 scenarios, git_head `15aebfb`); `2026-11-28-eb28fcbb4e92.json` (8.4–8.6: 77 scenarios, git_head `7188d01`). All three have `dirty: false`, `passed: true`, trigger accuracy 1.0 and every scenario 2/2 |
| CI | 3 runs | `45742525191` (head `1483688`), `46060786787` (`491e126`) and `46165299566` (`1a8bb56`), all `success` (checked with `gh run view`) |
| Validator / sync | run now | `validate_skills.py` and `sync_shared.py --check`: no errors. Sizes: rpcn-author 4,649 (154 room, description 922), rpcn-design 4,625 (178 room, 961), rpcn-test 4,735 (68 room, 1,017) |
| Previous retrospective | none | The previous epic in `epics` order is `epic-design`, and it has no `epic-design-retrospective.md`. The only retro in the initiative is epic 1's |
| Session logs | **missing** | The conversation transcripts were not available. Process-lesson analysis is narrowed to what the plans' Review Triage Logs and Implementation Notes record |

**Gaps:**
- 8.4's plan names no T baseline and no T commit. 8.1–8.3 each give a T baseline. Its T commit `41786dd` is attributed here by its subject.
- 8.4's smoke names no run folder (8.1 and 8.6 do).
- The eval records carry no test-project HEAD (see F12).

## Findings

Scope of this pass:
- **Aggregate views:** computed inline from the `git_evidence.py` output and from reading the current files.
- **Diff-scope review:** an **inline, narrowed pass**. Per the user's instruction, `bmad-review` was not invoked and no subagents were spawned. The adversarial, edge-case and verification-gap lenses were run by reading over the epic's skill-text diff, focused on the three seams above. Tooling code (`run_evals.py`, T `run_scenarios.py`) got only a light read, for the record-provenance findings.

Dispositions are suggestions for Phase 4: **fix-now**, **backlog**, **process lesson** or **no action**.

### Seam 1: 8.1's describe note feeding the re-run and 8.4

**F1. "Apply the design change" can lose a `.yml` pipeline (edge case, inferred from the text)**
- **The gap:**
  - 8.1's describe mode takes `<name>.yaml` or `.yml` (`skills/rpcn-design/references/describe.md:3-4`).
  - The note's `pipeline` header is `<name>` with no extension (`tools/shared/formats/handoff-header.md:23`). Only Purpose names the file (`describe.md:69-70`), and nothing reads Purpose mechanically.
  - When only a `.design.md` is named, rpcn-author's Step 2 takes `<name>` from the note and defaults `<pipeline>` to `<name>.yaml` (`skills/rpcn-author/SKILL.md:36-38`).
  - Change mode's "named pipeline doesn't exist: build it new" (`skills/rpcn-author/references/change.md:24-25`) would then build a second `<name>.yaml` beside the hand-written `.yml`.
- **Evidence:** no T scenario uses a `.yml` pipeline in describe, change or the chains (a `find` over `scenarios/` matched none). This was not observed in a run.
- **Suggested:** backlog. Add a `.yml` chain scenario. The rule fix is Step 2 or `change.md` looking for `<name>.yml` too.

**F2. An interactive describe answer that differs from the config leaves text no downstream reader handles (edge case)**
- **The gap:**
  - `describe.md:136-139` (8.1 review fix 2) records such an answer as "the config does X; intended: Y" inside the section.
  - 8.4's design change reads each section as what the pipeline must do (`change.md:46-58`).
  - rpcn-test's Design check reads the same section text (`skills/rpcn-test/references/design-check.md` §2).
  - Neither says how to treat "intended:". A grep for `intended` over the skill references hits only describe.md and the unrelated design-format.md:37.
- **Evidence:** all five `rpcn-design__describe_*` prompts are headless ("This run is unattended"), so this path has no scenario.
- **Suggested:** backlog. Decide whether an "intended" line is a design to apply or a note to ignore, and add an interactive describe→change scenario.

**F3. rerun.md's "never hash a pipeline or its files" rule (8.6 fix 6) has no scenario (verification gap)**
- **The gap:** the rule is at `skills/rpcn-design/references/rerun.md:46-52`.
  - In `rpcn-author__chain_design_change`, step 2 names only the note (`step2.md`), and its `expect.toml` doesn't check `inputs: []` after the re-run.
  - No `rpcn-design__rerun_*` `expect.toml` checks `inputs` (grep).
- **Evidence:** 8.6's smoke (`story-refactor-sweep-plan.md:96`) re-ran scenarios that predate the rule.
- **Suggested:** backlog. Add a re-run whose request names the described pipeline, expecting `inputs: []`.

**Checked and clean on this seam:**
- The describe note's empty Deviations table (header plus separator) is what `design-note.md` §3 and `change.md` §3 append after.
- `inputs: []` holds, and the note becomes a proposal input only when a departure's diff changes it (`change-format.md:34-40`). This is proved end to end by `chain_design_change` and `chain_change_departs` in record `2026-11-28-eb28fcbb4e92.json`.
- rpcn-design's Next sends a described note to rpcn-author (`skills/rpcn-design/SKILL.md:100-103`).

### Seam 2: 8.2's and 8.3's change mode feeding 8.4

**F4. "Which files does a pipeline load" is answered three different ways (duplication, adversarial)**
- **The three answers:**
  - `describe.md:20-31` (8.1, widened in review): inline `*_resources`, any project resources file defining a label the pipeline references, `from` and `import`, and transitive `.blobl` imports.
  - `change.md:30-44` (8.2): only `<name>.resources.yaml` and `from` lines in the pipeline.
  - `change-format.md:25-36` and its Readiness list `:111-113`: "each resources file and each `.blobl` file the pipeline loads", with `../resources.yaml` as an example.
- **The risk:** a described pipeline that uses a shared resources file can get a proposal whose `inputs` miss that file. The apply lint would then run without `--resources`, or the proposal would fail its own Readiness item.
- **Evidence:** 8.6's sweep compared `change-format.md` with `change.md` §2/§5/§7 but not §1 against `describe.md` (`story-refactor-sweep-plan.md:97`).
- **Suggested:** backlog. Align `change.md` §1 with describe.md's read list. This changes behaviour, so it needs an eval record.

**F5. 8.4's six T scenarios shipped without the per-scenario unit tests 8.1–8.3 added (pattern divergence, verification gap)**
- **Evidence:**
  - T commit `41786dd` touches no `tests/` file.
  - `ShippedAuthorScenarioTests.NAMES` stops at `rpcn-author__change_edit` (`rpcn-test-skills/tests/test_run_scenarios.py:3453-3458`).
  - The 8.4 scenarios get only the generic load check (`:4239-4243`), so no test proves their stray-file globs or that their fixtures lint clean.
  - 8.1–8.3 each shipped them (`8687729`, `8e7fbfb`, `4f62a8c`). 8.4's Code Map didn't ask for them (`story-apply-a-design-change-to-an-existing-pipeline-plan.md`, Code Map).
- **Suggested:** backlog for the tests. The process lesson is under F10.

**F6. Review fixes were spliced in without re-wrapping (pattern divergence, prose)**
- **Where:**
  - `change.md:118` (from `3e007ff`) and `change.md:180` (from `38d3486`): lines of 104 characters.
  - `apply-report.md:121`: 130 characters (`38d3486`).
  - `tools/shared/formats/change-format.md:33`: a blank line that splits the `inputs` list (`3e007ff`/`38d3486`).
  - `change-format.md:87-88`: an orphaned "row hunk). Its" (`38d3486`).
- **Suggested:** backlog. Do a reflow-only sweep. `change-format.md` goes through `sync_shared`, and its example's pinned sha256 is unaffected.

**Checked and clean on this seam:**
- The departure row's shape and placement agree across `design-note.md` §3, `change.md` §3/§6, `apply-report.md` §3 and `change-format.md:82-90`.
- The note is a target only for proposals, and only for the row and `updated` hunks (`apply-report.md:61-69`).
- The refused-Edit rule is the same in `change.md` §6 and `apply-report.md` §4, after 8.6 fix 5.
- The not-ready note outcome and the one design-change exception agree in `status-block.md:32-36`, `design-note.md` §1 and `change.md` §1, after 8.6 fixes 1–2.

### Seam 3: the 8.5 and 8.6 SKILL.md cuts against earlier rules

Each cut in `4fb03b6` and `df8ef84` was checked against the reference that now holds the rule. **All hold:**
- Author Step 1's "(headless: `blocked`)": covered by `status-block.md` "an exit 2, except from Step 2's note check".
- Step 4's "(headless: `blocked`)": covered by `questions.md` Headless ("no listed component that fits") and `status-block.md`.
- Step 6's "`reason` the first": now in the `status-block.md` lint bullet.
- Step 7's "(`<dir>/` its folder)" and "(§1 says when to stop)": in `apply-report.md` §1.
- Design Step 5's "eleven sections" and the Ready rule: `note-writing.md:3-5, 28-30`.
- Design Step 6's exit order: `note-writing.md` "Step 6: checking the note".
- 8.5's Step 2 rewording ("the named file's folder") still covers a named `.design.md`.

No finding: **no action**.

### Aggregate views

**F7. AD-6 doesn't name `change@1` (spec reconciliation)**
- **The gap:** the architecture's AD-6 writer table and `artifact:` list (`architecture-rpcn-skills.md:131-145`) have no `<name>.change.md` and no `change`.
- **Wrong as written:** "Proposing changes: Test, Tune and Deploy … put proposed diffs in their own report" now leaves out rpcn-author's own proposals.
- **Evidence:** 8.2 flagged this and deferred it (`story-author-proposes-a-change-as-a-change-1-file-when-headless-plan.md:144`). No later story picked it up: 8.6's scope was skill references only.
- **Suggested:** fix-now. It is a doc-only reconciliation, proposed in Phase 4.

**F8. `change.md` is the epic's hotspot (size growth)**
- **Growth:** it went from 125 to 200 lines across 8.2, 8.3, 8.4 and 8.6 (git_evidence net +125, +32, +42, +1). It now holds headless, interactive, design-change and departure rules.
- **Where the contradictions were:** five of 8.6's six contradiction fixes involved change mode's rules (`story-refactor-sweep-plan.md` Implementation Notes 1–5).
- **Verdict:** it is not a god-file at 200 lines, but it is where cross-story drift collected.
- **Other growth:** `tools/run_evals.py` grew from 407 to 701 lines (+294, in the resume range). T's `run_scenarios.py` is 3,954 lines and grew in two epic commits.
- **Suggested:** no action now. Watch it (see F10).

**F9. Spec-to-implementation, R1 "components in config order" isn't checked (verification gap)**
- **The gap:** `rpcn-design__describe_pipeline/expect.toml:31` checks that each row is present, not their order.
- **Evidence:** 8.1's review flagged this (`story-tracer-…-plan.md:150`, finding 6), but its fix tied only the ordering pick line.
- **The rest of R1–R6 maps to passing evidence:**
  - R1: the describe scenarios, with every file `unchanged`.
  - R2: `describe_pipeline` and `describe_no_target`/`describe_unlisted`.
  - R3: `change_propose`, `change_apply` and `change_stale`.
  - R4: `change_edit` with `write_lacks`. The refusal path is out of scope by the epic's Boundaries.
  - R5: `chain_design_change`, with "0 mismatch".
  - R6: the trigger gate at 104/104, with nine new cases.
- **Suggested:** backlog. Add an ordered multi-line `contains`, as 8.3's `change_edit` does.

### Process (from plans only, since session logs are missing)

**F10. Per-story quick reviews didn't catch cross-reference drift (process)**
- **Evidence:**
  - Every plan, including the two high-risk stories, ran only the pinned quick lens (`lenses_ran: ['quick']` at line 13 of each plan).
  - 8.4's review found two contradictions between stories (`story-refactor-sweep-plan.md:23`).
  - 8.6 found six more.
  - The seam gaps above (F1, F2, F4, F5) each sit where a later story built on an earlier story's reference without re-reading it.
- **Suggested:** process lesson. When a story edits a reference another story wrote, its review reads the pair together. A Code Map should also list the earlier story's scenario-test pattern to follow (F5).

**F11. An out-of-ticket rpcn-test fix landed mid-epic (no action)**
- **What:** `15aebfb` changed `skills/rpcn-test/SKILL.md` with no plan. It fixed a latent bug that surfaced as a record failure on `rpcn-test__dry_run_error`.
- **Where it's recorded:** only in 8.2's and 8.3's Implementation Notes.
- **Coverage:** record `2026-11-27-1978440ab31a.json` (git_head `15aebfb`) covers it.
- **Suggested:** no action (accept).

**F12. Committed records can't be tied to the scenarios that produced them (evidence durability)**
- **Evidence:**
  - Every plan says "T commits stay local" (5 plans).
  - The records carry `git_head` for rpcn-skills only. `test_project_head` exists only in run_evals' resume state (`tools/run_evals.py:620`), not in the record.
- **Effect:** apart from this machine, nothing shows which scenario definitions a record passed.
- **Suggested:** backlog (record the T HEAD in the record) or process lesson (push T). The user decides.

**F13. The 8.4–8.6 record was produced by eval tooling changed in the same push, and `--resume` hasn't had a real use yet (verification gap)**
- **Evidence:**
  - The record's `git_head` is `7188d01`, the `--resume` commit, run with T at `2dda27c`.
  - The record has no `resumed` key, so it ran in one go. The plan expected this record to be resume's first real use (`plan-eval-resume.md:147`).
- **Mitigation:** `eval_record_check` and CI `46165299566` accepted the record, and resume's matrix is covered by fake-`claude` tests only.
- **Suggested:** no action. Note it, and check the first resumed record when one happens.

## Behavior verification

No skill session was run in this retrospective, by instruction: no paid Claude session, and no scenario runner against Claude. Runtime behaviour is covered by the committed eval records and CI:
- Records:
  - `evals/results/2026-11-25-fa87b4f80a78.json` (8.1)
  - `2026-11-27-1978440ab31a.json` (8.2+8.3)
  - `2026-11-28-eb28fcbb4e92.json` (8.4–8.6: accuracy 1.0, 104/104 trigger runs, 77 scenarios 2/2, sessions on 4.117.0, checks on 4.100.0 and 4.117.0)
- CI: runs `45742525191`, `46060786787` and `46165299566`, all success.

This run executed only the deterministic checks `validate_skills.py` and `sync_shared.py --check`, both clean. The paths in F1 and F2 were not exercised by any record.

## Previous-retro follow-through

No previous retrospective: `epic-design` (the previous epic in order) has none. Nothing to check.

## Action items

Each finding was re-checked against its primary source before routing. F1 and F4 were re-read in `describe.md`, rpcn-author `SKILL.md` Step 2 and `change.md` §1, and both hold.

| # | Action | Owner | Kind | Source |
|---|---|---|---|---|
| 1 | Add `change@1` and rpcn-author's change proposals to AD-6 (who writes which hand-off file) in `architecture-rpcn-skills.md` | Architect (`bmad-agent-architect`), with the user | fix now; a proposed spec reconciliation, not applied here | F7 |

Every other finding, with the user's decision (2026-11-28):

| Finding | Instance | Prevent the next one |
|---|---|---|
| F1 `.yml` pipeline missed by a design change | defer, untracked: the user approved no backlog story | the "files a pipeline loads" rule should name the extension (see F4) |
| F4 three answers to "which files a pipeline loads" | defer, untracked: a behaviour change needing a record | one shared definition, read by describe and change mode |
| F2 describe mode's "intended: Y" answers | defer, untracked | an open question below |
| F3, F5, F9 coverage gaps | defer, untracked | — |
| F6 lines spliced in by review fixes | defer, untracked | — |
| F10 quick-only reviews let drift between stories pile up | process lesson proposed, not adopted by the user | a thorough review on an epic's closing story |
| F12 records not traceable to T's scenarios | process lesson proposed, not adopted by the user | the rpcn-test-skills HEAD in each eval record |
| F8 `change.md` hotspot | accept, noted | watch its growth in the next epic touching change mode |
| F11 rpcn-test fix with no ticket (`15aebfb`) | accept: a record covers it | — |
| F13 record made with tooling changed in the same push; `--resume` not yet used for real | accept, noted | — |

"Defer, untracked" means no ticket exists. Each finding's entry above holds enough context to be picked up later without re-investigating.

## Decision records

Proposed and approved by the user (2026-11-28), and written:

- `docs/decisions/adr-described-notes-keep-the-pipeline-out-of-inputs.md`: from the epic Notes (user, 2026-11-25, staleness option (a)), the story 8.1 plan, commit `cc6c727`, and the 8.6 `rerun.md` rule, commit `df8ef84`.
- `docs/decisions/adr-a-departure-is-a-note-diff-inside-the-change-proposal.md`: from the story 8.4 plan's frozen Approach (user, 2026-11-27), commit `38d3486`.

Considered and not proposed:
- The other epic Notes decisions: the new `change@1` format, explicit-request-only change mode, the Deviations header row, and the six-story lane. They are recorded in the epic file and in AD-6's pending update (action 1), or are planning choices.
- 8.6's "later story wins" rule, which is a process convention.

The ADR files are not committed; committing them is the user's call.

## Acceptance verdict

**accepted-with-open-items**: the machine verdict, confirmed by the user (2026-11-28). Criteria: **declared** (epic Requirements R1–R6 and Done when).

Evidence:
- **Tickets:** all six done (`tickets.py status`, `pending_tickets` empty).
- **R1, R2:** `describe_*` scenarios.
- **R3, R4:** `change_*` scenarios.
- **R5:** `chain_design_change`, whose Design check reports 0 mismatch.
- **R6:** trigger accuracy 1.0, with the new near-misses silent.
- **Records:** three passing, all `dirty: false`: 8.1's `1483688`, 8.2+8.3's `491e126`, and 8.4–8.6's `2026-11-28-eb28fcbb4e92.json` (77 scenarios 2/2).
- **CI:** green on `1a8bb56` (run 46165299566).

Open items: F1, F4 and F2 (change-mode correctness) and F3, F5, F9 and F6 (coverage and tidiness). They are deferred and untracked; none breaks a declared criterion.

## Open questions

- F2: in a design change, is a describe-mode "intended: Y" line a design to apply, or a note to ignore?
- F12: should T be pushed, or its HEAD written into each record?
- F1: is a `.yml` hand-written pipeline in scope for the design-change chain? The epic and describe.md imply yes.
