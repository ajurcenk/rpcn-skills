---
id: 17
type: story
title: "rpcn-author fails loudly on a missing required field"
parent: epic-author-and-test
covers: [R12, R1, R9]
after: [15, 16]
refined: true
hitl: false
risk: medium
---

# rpcn-author fails loudly on a missing required field

## Description

In the 2.12 benchmark, two of three `compare_write` runs used `.string()` on `email`. The request only implied that email was required, so a message with no `email` passed through as `"null"` instead of reaching the DLQ the request named. This story makes rpcn-author treat a field the processing needs as required, so a message missing it never passes with a made-up value. When the request leaves a behaviour choice open, the skill asks one short round of questions, or, headless, states its picks as assumptions. A new pass scenario, where the requirement is only implied, proves it. As with 16, it is not pushed alone: 18's eval run is its record (AD-14).

## Requirements

1. **A required field never passes with a made-up value** (R12, R1)
   **Given** a request whose processing needs a field (here, `email` to lowercase), and a failure path for bad messages
   **When** rpcn-author writes the pipeline
   **Then** a message without that field fails processing, or comes out with the field absent, so the request's error path can take it
   **And** no mapping turns the missing value into a string, number or default (such as `.string()` giving `"null"`) unless the request asks for a default

2. **One round of questions before writing** (R9)
   **Given** an interactive run whose request leaves open a choice that changes behaviour: whether a field the pipeline reads but does not need is required (a field it only passes through, say), or where a failing message goes
   **When** rpcn-author has read the request (and the design note, if any)
   **Then** it asks those questions in one message before writing any file, each with the answer it would pick
   **And** any question the skill already asks before writing (the pipeline file exists, or no listed component clearly fits) goes in that same message
   **And** it never asks what the binary, a ready design note or the request already answers

3. **Headless or unanswered: assume and say so** (R9; AD-8)
   **Given** a headless run, or a user who answers "go ahead" or leaves a question open
   **When** rpcn-author writes the pipeline
   **Then** it uses its pick and names each such pick as an assumption in the reply (headless: in `open_questions`)
   **And** the run ends `complete`, not `blocked`, for these questions

4. **The guidance rests on the sourced binary fact** (R1; AD-15)
   **Given** the 2.15 SOURCES.md row: `this.<f>.string()` gives `"null"` for a missing field, while `this.<f>.lowercase()` fails ("expected string value, got null"), proved by `RealBinaryCommandsTest.test_run_deleted_root_and_missing_field` on 4.100.0 and 4.115.0
   **When** rpcn-author's guidance relies on it
   **Then** it cites that row, and the row's notes column names the rpcn-author reference that uses it. No new binary fact is stated without a row of its own.

5. **Proved with an implied requirement** (R12)
   **Given** a new pass scenario whose request only implies the field is required (lowercase each event's email; failures go to a DLQ; nothing said about a missing email), with its pipeline outside the project root and a non-default name (epic decision 2026-11-05)
   **When** it runs on both binaries
   **Then** a bounded run of an event without `email` fails or leaves `email` absent, and a `.string()`-style build would fail the check
   **And** `rpcn-author__compare_write` still meets its missing-email point, as a regression check

6. **Asking and assuming are checked** (R9)
   **Given** two more pass scenarios on an ambiguous request: one interactive, one headless
   **When** they run
   **Then** the interactive one writes no pipeline file and ends with one question message. This needs a new runner check that a file was not written; how "one question message" is judged is stated in the build plan.
   **And** the headless one ends `complete`, with each pick in `open_questions`

## Boundaries

- Must not change: lint-clean output using only components and fields the binary reports (R1); the overwrite rule (an existing pipeline is never written over without asking); building from a ready design note (R2); applying a test report (R3).
- Must not change: `SKILL.md` stays at or under 4,803 characters, and its description at or under 1,024 (R9). It has about 11 characters free, so the new rules make room by moving wording into a reference, as 16 did, never by cutting a rule.
- Must not change: headless runs never ask (AD-8).
- No more than one round of questions per run.

## References

- parent — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/epic-author-and-test.md, section Requirements
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-benchmark-author-and-test-against-the-other-skill-sets-plan.md, section Implementation Notes (the 2.12 losses)
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-comparison-scenarios-the-binary-can-separate-plan.md, sections Intent ("Missing-email point (2026-11-20, review loop 1)") and Implementation Notes (second build: `run.errors` and `run.absent`)
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-rpcn-test-replies-say-only-what-the-user-needs-at-lower-cost-plan.md, section Intent (Decision 2026-11-20 on rpcn-test asking)
- sources — SOURCES.md, the 2.15 Bloblang row
- architecture — _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md, AD-8, AD-14, AD-15

## Notes

- Decision (2026-11-18): The user asked for criteria 2 and 3 (one round of questions, only for gaps that change behaviour, else assume and say so) to be added to this story rather than to a story of their own.
- Decision (2026-11-20): rpcn-test does not follow this rule. It leaves unclear samples and unit cases out and asks after the run (16's plan, Intent).
- Decision (2026-11-20): This story is proved by a new scenario where the requirement is only implied, because 2.15 made `compare_write` state that email is required, and `ours` already meets that point. `compare_write` stays as a regression check.
- Decision (2026-11-20): Covers R12 (the benchmark-driven fix), R1 (correct pipelines) and R9 (asking and headless conventions); each criterion names its own.
- Decision (2026-11-20): The ticket check's fixes were applied. Criterion 1 now matches 2.15's point (fail, or field absent). The existing asks share the one round. Criterion 4 rests on the existing 2.15 row.
