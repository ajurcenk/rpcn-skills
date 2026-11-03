---
id: 1
type: bug
title: "rpcn-test's report is never ready for a pipeline in a subfolder"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
severity: P2
---

# rpcn-test's report is never ready for a pipeline in a subfolder

## Description

When the pipeline sits below the project root, for example `pipes/orders.yaml`, rpcn-test writes `pipes/orders.test-report.md`, but `hash --check` never reports it ready. The run then ends with a draft report, or headless with `blocked`. A pipeline in the project root works.

Three smaller defects are in the same steps of the skill, and the same build fixes them:
- **An exit-code rule clash.** The rule "exit 2 from any call → write no report" overrides Step 5's "fix the header once, then draft". So a malformed header, or a re-lint that times out, aborts a run whose lint already finished.
- **The fix-check loop has no limit.** Step 4's "revise until it is clean" can run until the turn limit, with no report and no status block.
- **A shared temp path.** The fix check writes to a fixed `/tmp/rpcn-test-fixcheck/`, so two runs at the same time collide. Related to this, Step 5's `hash --check` is the only script call not written as the exact `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py …` command.

## Reproduction

Environment: `rpcn-test` at `0fd10ca`, `rpk connect` 4.112.0.

1. Put a valid pipeline at `<project>/pipes/orders.yaml`.
2. From `<project>`, run `rpcn_check.py hash pipes/orders.yaml`. It records `file: pipes/orders.yaml`, which is what the skill's Step 2 does, because the skill can't `cd`.
3. Write `pipes/orders.test-report.md` with that input in its header (the format's example report, with its inputs replaced).
4. Run `rpcn_check.py hash --check pipes/orders.test-report.md`.

**Actual:** exit 1, with `ready: false` and the error `input missing: pipes/orders.yaml`.

**Expected:** `ready: true`. With the input recorded as `orders.yaml`, relative to the report's folder, the same report comes back `ready: true` and `pipeline_ready: true`. This was reproduced on 2026-11-03.

## Cause Hypothesis

`hash --check` resolves each input relative to the report's own folder. The skill, though, records the paths exactly as it passed them to `hash`, relative to the project root. The two disagree whenever the report is not in the root. The other three defects are wording gaps in `SKILL.md` Steps 1, 4 and 5, found by the epic 1 retrospective.

## Acceptance Criteria

1. **A subfolder pipeline gets a ready report**
   **Given** a valid pipeline at `pipes/orders.yaml` in a fresh project
   **When** rpcn-test runs headless on it from the project root
   **Then** `pipes/orders.test-report.md` exists, `hash --check` reports it ready with verdict `pass`, and the status block is `complete`
2. **A broken subfolder pipeline gets a ready failing report**
   **Given** the broken fixture at `pipes/multi_error.yaml`
   **When** the same run happens
   **Then** the report is ready with verdict `fail`, the pipeline file is unchanged, and the status block is `complete`, with `checks.lint` set to `fail`
3. **A late script failure doesn't discard the report**
   **Given** lint has run, and a later call (the header check or the fix re-lint) exits 2
   **When** the skill continues
   **Then** it still writes the report, as `draft` with the reason, and headless ends `blocked` with that reason, instead of writing nothing
4. **The fix check is bounded and private to the run**
   **Given** an error whose fix can't be made to lint clean
   **When** the skill checks its proposed fix
   **Then** it stops after at most 2 revisions, marks that fix as unverified in the report, and uses a temp location no other run shares
5. **Tests cover the condition found and fixed**
   **Given** the eval suite and the `rpcn-test-skills` scenarios
   **When** they run
   **Then** a scenario with the pipeline in a subfolder passes 3 runs, the existing scenarios and trigger evals still pass, and a passing eval record is committed for the new skill content
6. **Or: no change is needed, with proof**
   **Given** the reproduction
   **When** it is run on the current code
   **Then** the expected behavior already holds, with the evidence recorded in Notes — this supersedes 1 to 5

## References

- parent — none (found by the epic 1 retrospective)
- retrospective — `_bmad-output/initiative-rpcn-skills/tickets/epic-validation-foundation/epic-validation-foundation-retrospective.md`, findings F1–F5 and action item A1
- format — `tools/shared/formats/handoff-header.md`, section Header fields (`inputs`)
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`, AD-6 (hand-off files) and AD-8 (status block)

## Notes

- Decision (2026-11-03): the user asked to fix this before epic 2 (retrospective Q2).
- Assumption: risk `medium` and severity P2. Reports for subfolder pipelines are broken, and moving the pipeline to the root is the workaround.
