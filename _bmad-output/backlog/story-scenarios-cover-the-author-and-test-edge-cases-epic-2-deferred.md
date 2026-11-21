---
id: 2
type: story
title: "Scenarios cover the Author and Test edge cases epic 2 deferred"
parent: none
covers: []
after: []
assignee: ""
refined: false
hitl: false
risk: low
---

# Scenarios cover the Author and Test edge cases epic 2 deferred

## Description

Epic 2's plans left eleven matrix rows with no scenario. Story 2.13's sweep handed them on, because adding scenarios is new test work, not cleanup. Each one becomes a pass scenario in `rpcn-test-skills`, using the runner keys that already exist (`[[run]]`, `[[file]] exists` and `lacks`, `reply_contains`, `status_nonempty`, `[[samples]]`). No skill change is expected. Each new scenario raises the cost of every future eval run.

The rows (`deferred-work.md`, epic 2 entries #1, 2, 4, 5, 6, 7, 10, 13, 14, 15, 16):
- **rpcn-author:**
  - an unknown component (`fields` close matches);
  - lint still failing after 3 revisions (headless `blocked`);
  - a report with verdict pass and `None.`;
  - a hunk that doesn't match;
  - lint still failing after applying a report;
  - a design note naming an unlisted component.
- **rpcn-test:**
  - a `.blobl` that doesn't parse;
  - a dry run that hangs;
  - unit tests with unclear intent;
  - a unit-test target that fails to start;
  - a design note that isn't ready.

## Requirements

Verify: each listed row has a scenario that passes on 4.100.0 and the newest pin, and T's tests pass.

## References

- deferred — _bmad-output/initiative-rpcn-skills/deferred-work.md, the epic-author-and-test entries above
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-refactor-sweep-plan.md, section Implementation Notes (where each item went)

## Notes

- Decision (2026-11-20): the user put the handed-off stories in the backlog, after epic 2, so the epic can close.
