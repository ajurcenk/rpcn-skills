---
tracker_id: ""
type: epic
title: "Release sync, versioning and failure modes"
parent: initiative-rpcn-skills
covers: [R10, R11, R18]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md]
after: []
refined: false
risk: medium
---

# Release sync, versioning and failure modes

## Description

Keeps the version 1 skills accurate over time. References regenerate for each RPCN release. CI blocks removed components and invalid skills. Releases carry a version stamp and a list of retired names. Failure-mode entries mined from `redpanda-data/connect` GitHub issues ship in the skills.

## Outcome

Developers can trust that the skills match the current RPCN release and know real pitfalls (initiative R10, R11, R18).

## Done when

- After an RPCN release, references are regenerated within a week, and a change that mentions a removed component is blocked in CI.
- A skill warns when the installed binary is newer than its references' stamp.
- The validator blocks a merge with an invalid name, description or file reference.
- At least one curated failure-mode entry per version 1 skill ships, each naming its GitHub issue.

## Boundaries

- In: reference regeneration, the deprecated-component gate, the release stamp and binary-newer warning, the retired-names list, the skill validator in CI, and failure-mode entries curated by Aleksej.
- Out: new lifecycle skills, and failure-mode sources beyond GitHub.

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`: AD-5, AD-11, AD-12, AD-14

## Notes

- AD-11's deprecated-component scan must not flag the plain phrase "Kafka Connect" in two trigger negatives, or must exempt them: `evals/rpcn-test__miss_kafka_connect/prompt.md` (deferred from story 1.7) and `evals/rpcn-author__miss_kafka_connect/prompt.md` (deferred from story 2.4). Both are in `_bmad-output/initiative-rpcn-skills/deferred-work.md`; the second was handed here by epic 2's refactor sweep (2026-11-20).
