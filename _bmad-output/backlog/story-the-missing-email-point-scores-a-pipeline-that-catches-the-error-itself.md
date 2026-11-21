---
id: 5
type: story
title: "The missing-email point scores a pipeline that catches the error itself"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# The missing-email point scores a pipeline that catches the error itself

## Description

Story 2.15's `missing_email` point scores an event without `email` when the run gives a runtime error, or when the output keeps the whole input with `email` absent. A valid pipeline that catches the error inside `pipeline.processors` and reshapes the event before routing it (wrapping it, or replacing `total`) gets no point, because the held lookup needs the whole input as a JSON subset. No arm did this in the smoke runs or in 2.18. This story lets the point find a caught event by an identity key, such as `id`, so every valid design scores. It is runner work in `rpcn-test-skills`.

## Requirements

Verify: a runner test with a wrapped or reshaped caught event scores the point, `.string()` and `.or()` builds still fail it, and the shipped `compare_write` still passes.

## References

- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-comparison-scenarios-the-binary-can-separate-plan.md, Review Triage Log (row 12) and Implementation Notes ("Risks")

## Notes

- Decision (2026-11-20): backlog, after epic 2 (user, at epic closure).
