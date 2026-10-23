---
tracker_id: ""
type: epic
title: "Validation foundation"
parent: initiative-rpcn-skills
covers: [R8, R9, R12, R13, R16, R17, R19, R20]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md]
after: []
refined: true
risk: high
---

# Validation foundation

## Description

Builds the base every skill depends on: the plugin layout, the `rpcn_check` script that wraps `rpk connect`, shared-file syncing, the hand-off formats, the skill validator, the trigger evals, the `rpcn-test-skills` scenario runner with benchmark arms, local eval recording, and CI. A first, lint-only `rpcn-test` skill proves all of it end to end and ships to users. Epic 2 extends it.

## Outcome

Skill authors get one tested way to check output against the binary, hand off files, measure triggering and benchmark against the existing skill sets. RPCN developers get a working "lint my pipeline" skill (initiative R8, R12, R16, R20).

## Requirements

- R1 (parent R13; architecture AD-1): The plugin installs with `claude plugin marketplace add ajurcenk/rpcn-skills` and with `npx skills add ajurcenk/rpcn-skills`. Only `rpcn-` skills are discoverable. It is met when both installs, on a clean machine, offer `rpcn-test` and no other skill.
- R2 (parent R8; AD-3, AD-4): `rpcn_check.py` provides `binary`, `lint`, `blobl`, `list`, `fields`, `run`, `test` and `hash`, with the schema-1 JSON envelope, exit codes 0/1/2, the fixed flags and the binary lookup. It is met when its unit tests pass against 4.100.0 and the newest release.
- R3 (parent R8, R16; AD-2): `tools/sync_shared.py` copies `tools/shared/` into each skill as its `shared.txt` lists. It is met when CI fails on a copy that differs from its source.
- R4 (parent R16; AD-6, AD-7): `tools/shared/formats/` holds the shared hand-off header and readiness rules, the design-note format and the test-report format. It is met when a hand-off file whose recorded input hash no longer matches is reported as not ready.
- R5 (parent R8, R9, R17, R19; AD-8, AD-9): The lint-only `rpcn-test` lints a pipeline through `rpcn_check`, explains each error with a fix, and writes `<name>.test-report.md`. It ends with a Next step, and when headless, with the status block. It is met when a broken recipe gets a stated cause and a fix that lints clean.
- R6 (parent R9, R18 in part; AD-9, AD-10): `tools/validate_skills.py` checks the name and prefix, the clash list, retired names, description format, size, file references and the Next step. It is met when each rule rejects a skill that breaks it.
- R7 (parent R12; AD-13): Native trigger evals for `rpcn-test` include near-miss negatives and run at least 3 times. It is met when `tools/eval_gate.py` reports suite accuracy of at least 90%, with no negative triggering a skill.
- R8 (parent R12, R16, R17; AD-13): The `rpcn-test-skills` runner reads the scenario format, installs the skills from a local path or a git ref, runs Claude Code headless, lints the produced files and parses the status block. It is met when one scenario passes 3 runs.
- R9 (parent R20; AD-13): The runner supports the four benchmark arms (ours, the Connect plugin, the skills repo, no skills). It is met when one `rpcn-test` comparison scenario writes a comparison table with a winner.
- R10 (parent R12; AD-14): `uv run tools/run_evals.py` runs the trigger evals and scenarios locally and writes `evals/results/<date>-<skills-hash>.json`. It is met when CI rejects a change to skill content that has no passing record for that content.
- R11 (parent R11 in part, R12; AD-14): GitHub Actions on every pull request runs the validator, the drift check, the `rpcn_check` tests on both versions and the eval-record check. It is met when a pull request that breaks any of them cannot merge.

## Constraints

- The installed binary is the source of truth. Nothing checks fields from model knowledge (initiative Constraints).
- The tested binaries are 4.100.0 and the newest release (initiative Constraints).
- The skills follow the Agent Skills spec and use the `rpcn-` prefix, with no clash with `/rpcn:*` or `/redpanda:*` (initiative Constraints).
- Pieces copied from the existing skill sets are adapted and recorded in `SOURCES.md`, with their licence checked (initiative Decision 2026-10-23).
- Evals run locally. CI holds no Claude credentials (Decision 2026-10-23).

## Done when

- Both install channels offer `rpcn-test` and only `rpcn-test`, and it lints a broken pipeline to a clean one.
- `rpcn_check` unit tests pass on 4.100.0 and the newest release, and the shared-file drift check is green.
- The trigger evals reach at least 90% with negatives silent, and one scenario passes 3 headless runs in `rpcn-test-skills`.
- One comparison scenario reports a winner across all four arms.
- The local runner writes a results file, and CI on GitHub Actions enforces the validator, drift, script tests and eval record on every pull request.

## Boundaries

- In: plugin manifest and install channels, `rpcn_check` and its tests, `sync_shared`, the hand-off formats (shared header, design note, test report), the lint-only `rpcn-test`, `validate_skills` (base rules), the trigger evals and gate, the `rpcn-test-skills` runner with benchmark arms, `run_evals`, and CI.
- Out:
  - extending `rpcn-test` beyond lint, and `rpcn-author` (epic 2)
  - `rpcn-design` and its use of the design-note format (epic 3)
  - generating references, the deprecated-component scan, release stamps and the weekly job (epic 4)
  - every other skill
- Must not change: the architecture's AD-1 to AD-14. A conflict found while building goes back to the architecture as an update.

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`: prior art (pieces to copy and adapt)
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-1, AD-2, AD-3, AD-4, AD-5, AD-6, AD-7, AD-8, AD-9, AD-10, AD-13, AD-14

## Notes

- Decision (2026-10-23): The `npx skills` layout is answered: each skill installs alone, with no dependencies. Every skill carries a synced copy of the shared files (architecture AD-2), so no spike is needed.
- Decision (2026-10-23): The proving skill is a lint-only `rpcn-test` that ships to users. Epic 2 extends it.
- Decision (2026-10-23): Epic 1 writes the shared hand-off header and readiness rules, plus the design-note and test-report formats. Later epics add their own formats.
- Decision (2026-10-23): Evals run locally, not in CI. CI checks for a committed passing record.
- Decision (2026-10-23): Pieces of the existing skill sets may be copied and adapted, each recorded in `SOURCES.md` with its source and licence.
- Decision (2026-10-23): The tracer bullet is story 1. It runs repo, both install channels, the skill, `rpcn_check binary`, the binary itself and a one-job CI, and each later story adds its own CI step. The riskiest work comes next in each lane: lint parsing (2), then the headless runner (6) and triggering (7), both straight after the skill (5).
- Decision (2026-10-23): Until sibling skills exist, `rpcn-test`'s Next step names re-running `rpcn-test` after fixes. Epic 2 updates it under the AD-9 sibling-edit rule.
- Decision (2026-10-23): The 12-story breakdown is approved. The user didn't rank the high-risk stories, so the order assumes the headless runner (6) is the least certain. Build sessions may start the Claude Code runs in stories 6, 7 and 10 under the user's login.
