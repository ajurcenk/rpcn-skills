---
title: "rpcn-test's report is never ready for a pipeline in a subfolder"
type: 'bugfix'
ticket: 'bug-rpcn-test-report-never-ready-for-a-pipeline-in-a-subfolder'
created: '2026-11-03'
status: done
baseline_revision: 'b16d04e93e593ca502bfcc64b41c36ae98df82c3'
route: 'oneshot'
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

**Problem:** `skills/rpcn-test/SKILL.md` Step 2 says "Run every call from its folder", but the skill may not `cd`. So the agent hashes `pipes/orders.yaml` from the project root and records that path in the report. `hash --check` resolves inputs against the report's own folder, finds nothing, and the report never becomes ready. Three wording gaps in the same steps also need fixing:
- The exit-2 rule overrides Step 5.
- Step 4's fix loop is unbounded and uses a shared temp path.
- Step 5's `hash --check` isn't written as a fenced command.

**Approach:** Fix it in SKILL.md only. `rpcn_check` is unchanged.
- **Paths:** the agent passes paths as the user gave them. The report header records each input by its file name alone, because every input sits beside the report (AD-6).
- **Exit 2:** it stops the run only in Steps 1–3. In Steps 4 and 5 it is handled like any other failed check.
- **The fix check:** it runs in a temp folder unique to the run, and stops after 2 revisions. A fix that still fails is marked unverified.
- **`hash --check`:** a fenced command, like every other call.
- **Tests:** two new scenarios in `rpcn-test-skills` cover a subfolder pipeline, one valid and one broken. Then `run_evals.py` runs, and its record is committed.

</frozen-after-approval>

## Implementation Notes

- **SKILL.md:**
  - Step 2 now passes paths as the user gave them, in place of "run every call from its folder", which contradicted the no-`cd` rule.
  - Step 5 records each input `file` as the file name alone. `hash --check` is now a fenced command, and exits 1 and 2 are both handled with one fix and a recheck.
  - Exit 2 stops the run only in Steps 1–3, and the status block matches.
  - The Step 4 fix check uses a per-run temp folder ending in 8 random letters, and stops after 2 revisions. Fixes that still fail are marked unverified.
  - The size warning rose from about 1,280 to about 1,371 tokens. It is still a warning only (AD-9).
- **New scenarios in `rpcn-test-skills`:** `rpcn-test__lint_subfolder` (broken, `pipes/orders.yaml`) and `rpcn-test__lint_subfolder_valid` (valid). Each passed 1 run on the fixed skill: `runs/20261103-151037`, at $0.28 and $0.19.
- **Surprise: the defect is nondeterministic.** `rpcn-test__lint_subfolder` against the old skill (`git:0fd10ca`, the same `skills/` as baseline `b16d04e`) **passed** (`runs/20261103-151201`). In that run the agent ran `cd …/pipes`. That breaks the skill's no-`cd` rule but obeys the old Step 2, after which the paths come out right. When the agent follows the no-`cd` rule instead, the report records `pipes/orders.yaml` and is never ready. That case is the deterministic reproduction in the bug (`hash --check` exits 1 with "input missing"). So the scenarios pin the fixed behaviour, but they can't reliably fail on the old skill.
- **An aside:** `git:<sha>` sources install from GitHub, so an unpushed commit (`b16d04e`) fails at install (`runs/20261103-151142`).

- **The first eval record was superseded.** `2026-11-03-c158cc24c027.json` passed: accuracy 1.0, three scenarios 3/3 each, $5.53. The review patches below change `skills/`, so it was deleted unused and the evals re-run.
- **SKILL.md after the review:**
  - The fenced commands carry `<dir>/` (the pipeline's folder, or nothing in the root).
  - The fix check uses `rpcn-test-${CLAUDE_SESSION_ID}`, falling back to 8 random letters.
  - A Step 4 exit 2 drafts the report, and headless ends `blocked`.
  - Unverified fixes end their item title with `(unverified)`.
  - A not-ready report is fixed only in its own header or format, and inputs are never re-hashed.
  - Size: about 1,446 tokens (warning).

- **Final eval record:** `evals/results/2026-11-03-93ce7031a1db.json` passed with `dirty: false`, at $5.73. Trigger accuracy was 1.0. `lint_broken` (pipeline in the root) passed 3/3, `lint_subfolder` 3/3 and `lint_subfolder_valid` 3/3.

## Review Triage Log

Quick pass: 0 high, 3 medium, 4 low, 2 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Eval record not committed, so CI would fail | false | reject | The commit step comes after review. The record is committed with the fix. |
| AC3: a Step 4 re-lint exit 2 neither drafts nor blocks | medium | patch | Confirmed at the old Step 4 and the status-block lines. Now it drafts the report with the reason, and `blocked` covers Steps 1–4. |
| AC4: the unverified marker has no place in the report | low | patch | Step 5 now says to end the item title with `(unverified)`. |
| AC4: model-picked "random" folder names repeat (`qmz…` 4 of 6 times) | medium | patch | Confirmed in `runs/20261103-152108`. The skill now uses `${CLAUDE_SESSION_ID}`, with the random letters only as a fallback. |
| The scenarios can't fail on the old skill (no check for `cd`, or for a directory part in `inputs[].file`) | medium | defer | Real, and recorded in Implementation Notes. The fix needs a new runner check type plus tests in `rpcn-test-skills`, which is not a one-line patch. Added to `deferred-work.md`. |
| AC2 names the fixture `pipes/multi_error.yaml`, but the scenario uses `pipes/orders.yaml` | low | reject | The bytes are identical to `multi_error.yaml`, and the behaviour is covered. Renaming is cosmetic. |
| SKILL.md grows past AD-9's 1,200-token warning | low | reject | The validator warns and doesn't fail, by design. Trimming the skill is epic 2's rewrite. |
| "fix the report once" invites re-hashing a stale input | low | patch | The wording now says fix only the header or format, and never re-hash or change an input's `sha256`. |
| The fenced commands show bare `<name>.yaml` while the prose says to use the path | low | patch | The fenced hash, lint and `hash --check` commands now carry `<dir>/`. |

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`: exit 0.
- `uv run run_scenarios.py --source local:../rpcn-skills --scenario rpcn-test__lint_subfolder --scenario rpcn-test__lint_subfolder_valid --runs 1 --no-judge` in `rpcn-test-skills`: PASS, as a cheap smoke check.
- `uv run tools/run_evals.py`: passes, and writes the record for the new skills hash. `uv run tools/eval_record_check.py` then exits 0.
