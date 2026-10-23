---
tracker_id: ""
type: epic
title: "Release sync, versioning and failure modes"
parent: initiative-rpcn-skills
covers: [R10, R11, R18]
sources: []
companions: []
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
