---
tracker_id: ""
type: epic
title: "Existing pipelines"
parent: initiative-rpcn-skills
covers: [R21, R22]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md]
after: []
refined: true
risk: medium
---

# Existing pipelines

## Description

Most developers already have hand-written pipelines with no design note. This epic lets the skills work on those pipelines (initiative R21, R22):

- rpcn-design describes what an existing pipeline does, as a `design@1` note.
- rpcn-author changes an existing pipeline only as a reviewable change:
  - interactive: Edits the developer approves one at a time;
  - headless: a proposal file with verified diffs, which Author's apply step then applies.

The Redpanda Connect VS Code extension's assistant (its AD-26 and epic 8) needs both modes so a hand-written pipeline can take part in the Design → Author → Test flow.

## Outcome

A developer with a hand-written pipeline gets a note that describes it, and changes it through reviewable changes that leave everything else byte-identical.

## Requirements

- R1 (parent R22): rpcn-design writes a `design@1` note describing what an existing pipeline does. It reads the pipeline, its resources files and its `.blobl` files, and edits none of them. It is met when a hand-written pipeline gets a ready note that lists its components in config order and states its error handling, delivery, ordering, idempotency and batching as the config does, with every file byte-identical afterwards.
- R2 (parent R22; AD-15): a described note claims only what the config shows, read with `list` and `fields` or backed by a `SOURCES.md` row. What the config can't show is an open decision:
  - `[blocking]` only where `questions.md`'s four asks have no answer in the config, such as a sink failure with no target;
  - otherwise `[non-blocking]`, with the config's behaviour as the pick.

  It is met by a scenario with one of each.
- R3 (parent R21): headless, rpcn-author writes a proposal for a requested change, `<name>.change.md`, in a new `change@1` format, and leaves the pipeline unchanged. The proposal's items have the same shape as the test report's Proposed changes: a title, a `Cause:` line, and a verified unified diff per file. The hand-off header hashes the files the diffs apply to, so `hash --check` catches a stale proposal. Author's apply step applies a ready proposal the same way it applies a test report. It is met by a headless scenario that writes the proposal, then an apply that lints clean.
- R4 (parent R21): interactive, rpcn-author makes a requested change with Edit on the existing files, one Edit per change, never a whole-file Write. Unrelated lines stay byte-identical.
  - If the host refuses an Edit, that file stays as it was. Author lints, reports what was left out, and doesn't try the change another way.

  It is met by an interactive scenario: Edits only, unrelated lines byte-identical, lint clean.
- R5 (parent R21, R22): with a note that rpcn-design's re-run has changed, "apply the design change" brings the pipeline in line through R3 or R4, and any departure adds a Deviations row. It is met by a chain:
  1. describe;
  2. a Design re-run with a change;
  3. apply the design change;
  4. Test's Design check, which reports 0 mismatch.
- R6 (parent R12, R19): the change and describe phrases trigger the right skill. Each skill's description and Next names its siblings where their triggers collide. It is met when the trigger gate passes at accuracy 1.0, with near-miss negatives for "design …", "write …" and "test …".

## Constraints

- **Must not change** (from both change requests):
  - A new pipeline is never written over an existing file without an explicit change request.
  - Author's apply step for a test report works as today.
  - Secrets and addresses stay `${ENV}`, and only components and fields the binary reports are used.
  - rpcn-author writes only Deviations rows and `updated` in a note (`design-format.md`, "Who writes what").
  - rpcn-design writes no YAML.
  - A note that exists isn't written over: Step 2's existing-note rule applies.
  - Headless never asks.
- `design@1` is unchanged. A new format goes through `tools/shared/formats` and `sync_shared` (AD-2, AD-7).
- Every `SKILL.md` stays at or under 4,803 characters, and every description at or under 1,024. Each new mode lives in its own reference, with a short pointer from Step 2. Today rpcn-author has about 190 characters of room and rpcn-design about 160.
- Agent sessions run on the newest pin, and checks run on both pins. Eval records run 2 times per case.

## Done when

- A hand-written pipeline gets a ready note describing it, with every file byte-identical.
- An interactive change edits the pipeline through Edits only, and a headless one writes a `change@1` proposal that applies and lints clean.
- The describe → change → test chain passes, with Test's Design check reporting 0 mismatch.
- The trigger gate passes, with the new near-misses silent. Every story's skill change has a passing eval record, and CI is green.

## Boundaries

- Out: refusing an Edit can't be tested in the scenario runner, because `claude -p` approves every allowed tool. The refusal path is checked in the extension (its spike).
- Out: detecting that a note is newer than its pipeline, since a YAML file has no `inputs` header. Change mode starts only on an explicit request.
- Out: a design note for a pipeline Design can't read (outside the project, or generated at run time).
- Touch point: `tools/shared/formats` (the new `change@1`) and `rpcn_check hash --check`. Owner: this epic, under epic 1's format rules.

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, Requirements R21 and R22
- change request — `_bmad-output/initiative-rpcn-skills/change-requests-vscode-extension/change-an-existing-pipeline.md`
- change request — `_bmad-output/initiative-rpcn-skills/change-requests-vscode-extension/describe-an-existing-pipeline.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`: AD-2, AD-6, AD-7, AD-8, AD-15

## Notes

- Decision (2026-11-25, user): staleness, option (a). Describe mode names the pipeline in Purpose and leaves it out of `inputs`, so a later Author change doesn't make the note stale. Option (b), letting Author refresh `inputs` (a `design@1` change), was declined. So was (c), a re-describe after every change.
- Decision (2026-11-25, user): the headless proposal uses a new, small `change@1` format. It reuses the test report's Proposed-changes items and the shared hand-off header. A test-report-shaped file written by Author was declined, because it blurs who produced what.
- Decision (2026-11-25, user): change mode starts only on an explicit request ("change my pipeline to …", "update `<name>.yaml` so …", "apply the design change"). The "note newer than pipeline" trigger was dropped as undetectable.
- Decision (2026-11-25, user): the describe-mode note's empty Deviations section keeps the `design@1` table header and separator. The change request's "Deviations: `None.`" contradicts the format.
- Decision (2026-11-25, user): six stories in one lane, since each one edits rpcn-author or rpcn-design.
  - Story 1 is the tracer (describe mode).
  - Story 2 is the least certain (the `change@1` format), and comes next.
  - Records are grouped as in epic 3: one for story 1, one shared by 2 and 3, and one shared by 4, 5 and 6.
- The change requests cite pinned `3afb844`. `main` has moved on since (3.10 refactored rpcn-author's Steps 5 and 7), so each story rechecks the step it changes.
