---
title: "rpcn-test's report is never ready for a pipeline in a subfolder"
type: 'bugfix'
ticket: 'bug-rpcn-test-report-never-ready-for-a-pipeline-in-a-subfolder'
created: '2026-11-03'
status: 'in-progress'
baseline_revision: 'b16d04e93e593ca502bfcc64b41c36ae98df82c3'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: ''
review_source: ''
lenses_ran: []
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

## Verification

**Commands:**
- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`: exit 0.
- `uv run run_scenarios.py --source local:../rpcn-skills --scenario rpcn-test__lint_subfolder --scenario rpcn-test__lint_subfolder_valid --runs 1 --no-judge` in `rpcn-test-skills`: PASS, as a cheap smoke check.
- `uv run tools/run_evals.py`: passes, and writes the record for the new skills hash. `uv run tools/eval_record_check.py` then exits 0.
