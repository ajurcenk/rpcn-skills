---
id: 17
type: story
title: "rpcn-author fails loudly on a missing required field"
parent: epic-author-and-test
covers: [R12]
after: [15, 16]
refined: false
hitl: false
risk: medium
---

# rpcn-author fails loudly on a missing required field

## Description

In the 2.12 benchmark, two of three `compare_write` runs used `.string()` on `email`. So a message with no `email` passed through as `"null"` instead of reaching the DLQ the request asked for. This story makes rpcn-author treat a field the request relies on as required: its mapping fails when the field is missing, so the error path the request names catches the message. When the request leaves that open, the skill asks one short round of questions, or, headless, states its pick as an assumption. Story 15 adds the benchmark point this meets. As with 16, it is not pushed alone: 18's eval run is its record (AD-14).

## Requirements

1. **A required field fails when missing** (R12)
   **Given** a request that names a field the processing needs (here, `email` to lowercase), and a failure path for bad messages
   **When** rpcn-author writes the pipeline
   **Then** a message without that field makes the mapping fail, which a bounded run reports as a runtime error, so the request's error path takes it
   **And** no mapping turns the missing value into a string, number or default (such as `.string()` giving `"null"`) unless the request asks for a default

2. **One round of questions before writing** (R12)
   **Given** an interactive run whose request leaves open something that changes the pipeline's behaviour (whether a field it reads is required, or where a failing message goes)
   **When** rpcn-author has read the request (and the design note, if any)
   **Then** it asks those questions in one message before writing any file, each with the answer it would pick
   **And** it never asks what the binary, a ready design note or the request already answers

3. **Headless or unanswered: assume and say so** (R12)
   **Given** a headless run, or a user who answers "go ahead" or leaves a question open
   **When** rpcn-author writes the pipeline
   **Then** it uses its pick and names each such pick as an assumption in the reply (headless: in `open_questions`)
   **And** the run is not `blocked` for these questions

4. **The binary fact is sourced** (R12; AD-15)
   **Given** the guidance relies on how Bloblang treats a missing field
   **When** the story is done
   **Then** SOURCES.md has a row for it, with a real-binary test on 4.100.0 and the newest pin: `this.<f>.string()` gives `"null"` for a missing field, while a string method such as `this.<f>.lowercase()` fails with "expected string value, got null"

5. **The benchmark point is met** (R12)
   **Given** 15's missing-required-field point on `rpcn-author__compare_write`
   **When** a `--runs 1` comparison smoke runs on both binaries
   **Then** `ours` meets that point in every run
   **And** a new pass scenario with an ambiguous request checks that the interactive reply asks before writing (no pipeline file written, one question message)

## Boundaries

- Must not change: lint-clean output using only components and fields the binary reports (R1); the overwrite rule (an existing pipeline is never written over without asking); building from a ready design note (R2); applying a test report (R3).
- Must not change: `SKILL.md` stays at or under 4,803 characters, and its description at or under 1,024 (R9).
- Must not change: headless runs never ask (AD-8).
- No more than one round of questions per run.

## References

- parent — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/epic-author-and-test.md, section Requirements
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-benchmark-author-and-test-against-the-other-skill-sets-plan.md, section Implementation Notes (the 2.12 losses)
- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-comparison-scenarios-the-binary-can-separate-plan.md, section Intent (15's missing-field point)
- architecture — _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md, AD-8, AD-14, AD-15

## Notes

- Decision (2026-11-18): The user asked for criteria 2 and 3 (ask one round only for gaps that change behaviour, else assume and say so) to be added to this story rather than to a story of their own.
- Decision (2026-11-18): Refined while 15 and 16 were not yet done. `refined: true` waits until 15 is at least in review, so its point is fixed.
- Open question: whether rpcn-test's sample and unit-case writing should follow the same one-round rule. It is out of this story (rpcn-test is 16's lane); raise it at 16's start.
