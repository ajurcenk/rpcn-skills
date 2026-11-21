---
tracker_id: ""
type: epic
title: "Author and Test skills"
parent: initiative-rpcn-skills
covers: [R2, R3]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md]
after: []
refined: true
risk: medium
status: done
---

# Author and Test skills

## Description

Delivers `rpcn-author`, and extends the lint-only `rpcn-test` from epic 1. Author writes pipeline YAML and Bloblang from the installed binary's fields, building from a design note when one exists. Test lints, runs samples, does dry runs, writes `rpk connect test` cases and diagnoses failures.

## Outcome

RPCN developers get pipelines that lint clean on their binary and come with samples, unit tests and a test report (initiative R2, R3).

## Requirements

- R1 (parent R2; AD-4, AD-6): `rpcn-author` writes the pipeline files (`<name>.yaml`, `<name>.resources.yaml`, `<name>.<label>.blobl`, `.env.example`) using only the components and fields the installed binary reports. It is met when every config the eval cases generate lints clean on 4.100.0 and the newest release, with no field that `rpcn_check fields` doesn't report.
- R2 (parent R2, R1, R16; AD-7): When a ready design note exists, Author builds from it and records each departure as a Deviations row. Without a note, it builds from the request. It is met when a fixture note's components and error-handling choices appear in the pipeline, and a deliberate departure adds one row.
- R3 (parent R2, R3, R16; AD-6): Author applies the proposed changes in a ready test report. It is met when applying a failing report's diffs gives a pipeline that lints clean, and a re-test passes.
- R4 (parent R3; AD-4, AD-6): `rpcn-test` runs each Bloblang mapping against its samples in `<name>.samples.json`, in the format that `samples-format.md` defines. It is met when expected outputs pass, and a wrong mapping is reported with the sample, the expected output and the actual output.
- R5 (parent R3; AD-4): `rpcn-test` dry-runs a pipeline with bounded input through `rpcn_check run`. It is met when a working pipeline's run is reported as passing, and a pipeline that fails at runtime is reported with its error.
- R6 (parent R3; AD-6): `rpcn-test` writes `<name>_benthos_test.yaml` cases and runs them through `rpcn_check test`. It is met when the cases pass on a correct pipeline and fail on a broken one.
- R7 (parent R3; AD-7): `rpcn-test` checks the pipeline against the note's Error handling, Delivery and ordering, and Idempotency sections. It is met when a fixture mismatch is reported as `mismatch`, and one covered by an unresolved Deviations row as `deviation-recorded`.
- R8 (parent R3): `rpcn-test` diagnoses lint, sample, dry-run and test failures. It is met when a failing pipeline gets a stated cause and a proposed fix that passes the check it failed.
- R9 (parent R9, R12, R17, R19; AD-8, AD-9): Both skills meet epic 1's conventions:
  - `SKILL.md` is 1,200 tokens or less, with references loaded at the step that needs them.
  - Each description names the other skill in its "Not for" line.
  - There is a Next step for each situation.
  - Headless runs end with the status block.

  It is met when the validator reports no warnings for either skill, and the trigger gate passes with negatives silent.
- R10 (parent R12; AD-13): The trigger gate measures what users install:
  - Negatives assert that no `rpcn-` skill fired.
  - `eval_gate` checks the expected case list.
  - Each skill has a positive case and a near-miss case on an `npx` install of that skill alone.
  - Sessions record which skills were visible, and fail on an unexpected one.
  - `run_evals` runs the `rpcn-test-skills` tests first.

  It is met when dropping a case, or loading an extra skill, fails the run.
- R11 (parent R8, R16): `rpcn_check`'s hand-off checks hold for real projects:
  - Output lines that are not lint errors are not counted as errors.
  - `.yml` pipelines and shared resources files are handled.
  - A report with no pipeline input is not ready.
  - Scenarios can assert that no `cd` was used and that report inputs are bare file names.

  It is met when each case has a passing unit test or scenario.
- R12 (parent R20; AD-13): One comparison scenario each, for Author and for Test, runs in the four arms. It is met when the results file names each winner. Any scenario another arm wins becomes an improvement story.

## Constraints

- The installed binary is the source of truth, and the tested binaries are 4.100.0 and the newest release (initiative Constraints).
- Skills follow the Agent Skills spec, use the `rpcn-` prefix, avoid the clash list, and install alone through `npx skills` (initiative Constraints; AD-1, AD-10).
- Evals run locally. Every change under `skills/` needs a passing record before it merges (AD-14).
- Every skill story's scenarios include a pipeline outside the project root and one with a non-default name (Decision 2026-11-05).

## Done when

- Every config the eval cases generate lints clean on the tested binaries, with no field absent from `rpk connect list`.
- A failing pipeline gets a stated cause and a fix that passes.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions, and the validator reports no warnings for either skill.
- The trigger gate fails when a case is dropped or an extra skill is visible, and each skill passes it on an `npx` install of that skill alone.
- The Author and Test comparison scenarios name a winner across the four arms.

## Boundaries

- In: `rpcn-author`, `rpcn-test`, the design-note reading and updating in Author, checking against the note in Test, and Bloblang sample files.
- Out: writing design notes (epic 3), capacity and deployment (epic 5), and any VS Code extension integration.

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`: AD-1, AD-4, AD-6, AD-7, AD-8, AD-9, AD-10, AD-13, AD-14

## Notes

- Decision (2026-11-05): Refined, and the user accepted the picks:
  - **Size:** both `SKILL.md` files are 1,200 tokens or less by the epic's end, with detail in references loaded at their step.
  - **Trigger setup:** one early story before `rpcn-author` lands (retrospective A4, spine Deferred).
  - **Hand-off hardening:** one `rpcn_check` story before any reader relies on `pipeline_ready` (retrospective D1).
  - **Scenarios:** every skill story's scenarios include a pipeline outside the project root and a non-default name (retrospective L1).
  - **Benchmark:** the comparisons run once, at the epic's end.
  - **Order:** skill edits are grouped to limit eval runs, at about $5.50 per run.
  - **Spine:** reconciled through `bmad-architecture` before the stories build (retrospective A2).
  - **`rpcn-test-skills`:** stays local, and its tests run first in `run_evals` (retrospective F10).

- Decision (2026-10-23): `rpcn-test` starts in epic 1 as a lint-only skill. This epic extends it with samples, dry runs, `rpk connect test` cases and failure diagnosis.
- Decision (2026-11-05): The breakdown has 13 stories.
  - **Tracer bullet:** story 4 (rpcn-author writes a pipeline that lints clean). Stories 1–3 come first by the refinement decisions: the trigger gate before a second skill, the hand-off hardening before `pipeline_ready` readers, and the size refactor before the skill grows.
  - **Least certain:** story 5, the Author and Test loop.
  - **Lanes:** rpcn-author runs 4 → 5 → 6 → 7, then rpcn-test runs 8 → 9 → 10 → 11.
- Decision (2026-11-05): Test applies fixes to the files it owns (`<name>.samples.json`, `<name>_benthos_test.yaml`) itself. Fixes to Author's files are proposed diffs (AD-6, one writer per file).
- Decision (2026-11-05): Settled AD-6's open point. `redpanda-connect test ./...` finds `orders_benthos_test.yaml` beside `orders.yaml` with no extra flags, and passes it, on both 4.100.0 and 4.115.0.
- Decision (2026-11-05): The user approved the 13-story breakdown as drafted, with no merges, which accepts an estimated $60–80 in eval runs over the epic plus about $8 for the story 12 benchmark.
- Decision (2026-11-18): Re-slice after the story 12 benchmark (`ours` lost all three comparisons on judge rank). The user approved the picks. Five improvement stories are added before the refactor sweep, in this build order: 14 (the benchmark judges every arm fairly), 15 (comparison scenarios the binary can separate), 16 (rpcn-test replies say only what the user needs, at lower cost), 17 (rpcn-author fails loudly on a missing required field), 18 (re-benchmark), then 13 (refactor sweep, which now also waits on 14–18). The epic grows from 13 stories to 18 and keeps them, as entry 12 asked ("an improvement story in this epic"). 16 may run alongside 14 and 15; 15 is the least certain. Evidence: the 2.12 plan's Implementation Notes, and the two judge entries in `deferred-work.md` of 2026-11-13.
- Decision (2026-11-18): The comparisons run once more, in story 18 (about $55). This replaces the 2026-11-05 "comparisons run once, at the epic's end"; the actual cost of 12's run was $54.24, against the $8 accepted then. 18's `run_evals --with-compare` is also the AD-14 eval record for 16 and 17, so 16–18 are pushed together after it, and 16 and 17 only smoke-run their scenarios.
- Decision (2026-11-18): Any comparison another arm still wins after 18 is recorded with its evidence and accepted as the epic's result. New stories come from it only if the user asks, so the benchmark does not loop.
- Decision (2026-11-20, user): Story 2.16's `unit_bug` turn count (26.7 against 26.7 in 2.12) is accepted as unchanged, because its cost fell from $0.50 to $0.40.
- Decision (2026-11-20, user): Epic closed. The closure check met R1–R12 and every Done when line: the validator is clean, and `evals/results/2026-11-20-83e2eea0bd76.json` matches the skills, with accuracy 1.0 and 38 scenarios 3/3. The user confirmed:
  - `ours` wins 1 of 3 comparisons (`compare_lint`), and the `compare_write` and `compare_diagnose` losses to `skills-repo` stand (Decision 2026-11-18). The `compare_diagnose` loss has no judge note (backlog story 4).
  - 4.115.0 counts as the newest release for this epic; the roll to 4.117.0 stays open.
  - The 2.13 hand-offs are backlog stories 2–5 in `_bmad-output/backlog/`, outside this epic. Story 2 covers 11 matrix rows that are specified but have no scenario.
