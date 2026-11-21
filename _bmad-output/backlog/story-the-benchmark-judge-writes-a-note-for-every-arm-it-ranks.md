---
id: 4
type: story
title: "The benchmark judge writes a note for every arm it ranks"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# The benchmark judge writes a note for every arm it ranks

## Description

In `compare_diagnose`, the blind judge ranked `ours` last without writing a note on it, in both 2.12 and 2.18. So that loss has no judge evidence. This story finds out why (for example, whether `ours`' reply reaches the judge cut short or redacted to almost nothing) and makes the runner reject or retry a judge reply whose `notes` don't cover every label. It is runner work in `rpcn-test-skills`, with no skill change.

## Requirements

Verify: a rejudge of `T/runs/20261120-171018` gives a note for every arm in every comparison, and a runner test fails a judge reply missing a label's note.

## References

- deferred — _bmad-output/initiative-rpcn-skills/deferred-work.md, epic-author-and-test entry #21 (story 2.18)
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-re-benchmark-author-and-test-after-the-improvements-plan.md, section Implementation Notes (losses)

## Notes

- Decision (2026-11-20): backlog, after epic 2 (user).
