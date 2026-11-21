---
id: 3
type: story
title: "rpcn-author places a mapping that calls now() or uuid_v4() by one clear rule"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: medium
---

# rpcn-author places a mapping that calls now() or uuid_v4() by one clear rule

## Description

rpcn-author's `.blobl` rule doesn't say what wins when the user asks for one mapping processor that also needs `now()` or `uuid_v4()`, which rpcn-test can't sample. Today Author keeps it in one file, and rpcn-test reports `Not run: non-deterministic`. This story settles the rule in rpcn-author's references (for example, split the non-deterministic part into its own processor, or keep it whole and say why), with a scenario. It is a skill change, so it needs a passing eval record (AD-14).

## Requirements

Verify: a scenario asking for one mapping with a timestamp follows the settled rule on both binaries, and the eval record passes.

## References

- deferred — _bmad-output/initiative-rpcn-skills/deferred-work.md, epic-author-and-test entry #12 (story 2.7)
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-refactor-sweep-plan.md, section Implementation Notes

## Notes

- Open question: which rule wins (split the processor, or keep it whole). It is answered at refinement.
- Decision (2026-11-20): backlog, after epic 2 (user).
