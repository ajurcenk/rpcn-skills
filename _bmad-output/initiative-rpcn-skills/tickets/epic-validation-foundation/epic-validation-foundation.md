---
tracker_id: ""
type: epic
title: "Validation foundation"
parent: initiative-rpcn-skills
covers: [R8, R9, R12, R13, R16, R17, R19]
sources: []
companions:
  - _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md
after: []
refined: false
risk: high
---

# Validation foundation

## Description

Builds the base every skill depends on: the plugin layout, check scripts that wrap `rpk connect`, the eval harness, CI, and the shared conventions (hand-off file formats, headless status, what next). A sample skill proves them end to end.

## Outcome

Skill authors get one tested way to check output against the binary, measure triggering and hand off files, so every later skill epic builds on proven ground (initiative R8, R12, R16).

## Done when

- The plugin installs through both Claude Code and `npx skills` on a clean machine.
- The check scripts return JSON and a non-zero exit on lint and Bloblang failures against both tested binaries (4.100.0 and the newest release), and their unit tests pass.
- CI runs the eval harness on every change: a sample skill's trigger and task cases run at least 3 times in a clean environment, and the results are recorded.
- The hand-off formats, headless status and what-next convention are documented, and the sample skill uses them.
- The `rpcn-test-skills` project installs the sample skill from a git ref, runs one scenario headless 3 times, and lints the files it produced.

## Boundaries

- In: plugin manifest, install through Claude Code and `npx skills`, check scripts with JSON output and unit tests, eval harness (trigger and task cases), CI running evals and check scripts on every change, hand-off file formats including the design note, headless JSON status, the what-next convention, and one sample skill using them.
- Out: the real lifecycle skills (epics 2, 3, 5, 6, 7), release sync and versioning (epic 4).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-1, AD-2, AD-3, AD-4, AD-5, AD-6, AD-8, AD-9, AD-10, AD-13, AD-14

## Notes

- Decision (2026-10-23): The `npx skills` layout is answered (each skill installs alone, no dependencies). Every skill carries a synced copy of the shared files (architecture AD-2), so no spike is needed.
