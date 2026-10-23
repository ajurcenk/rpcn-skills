---
tracker_id: ""
type: epic
title: "Author and Test skills"
parent: initiative-rpcn-skills
covers: [R2, R3]
sources: []
companions:
  - _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md
after: []
refined: false
risk: medium
---

# Author and Test skills

## Description

Delivers `rpcn-author` and `rpcn-test`. Author writes pipeline YAML and Bloblang from the installed binary's fields, building from a design note when one exists. Test lints, runs samples, does dry runs, writes `rpk connect test` cases and diagnoses failures.

## Outcome

RPCN developers get pipelines that lint clean on their binary and come with samples, unit tests and a test report (initiative R2, R3).

## Done when

- Every config the eval cases generate lints clean on the tested binaries, with no field absent from `rpk connect list`.
- A failing pipeline gets a stated cause and a fix that passes.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-author`, `rpcn-test`, the design-note reading and updating in Author, checking against the note in Test, and Bloblang sample files.
- Out: writing design notes (epic 3), capacity and deployment (epic 5), and any VS Code extension integration.

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-4, AD-6, AD-7, AD-8, AD-9
