---
title: 'Design and Author ask through the host question tool when one is offered'
type: 'feature'
ticket: ''
created: '2026-11-24'
status: 'built'
baseline_revision: '560f483909871f4afe9ec239106365c1672d6e42'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-vscode-byoc-plugin/8d4d8547-3b1a-4c6f-a1da-94e2dc5588e0/scratchpad/rpcn-skills-change-request-questions.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Redpanda Connect VS Code extension (AD-26, spike 65) runs `rpcn-skills` unchanged through the Claude Agent SDK. The SDK gives the host each `AskUserQuestion` call as data. In the spike, `rpcn-design` wrote round 1 as a plain numbered list and stopped, so the host received no structured questions and the run ended without a note.

**Approach:**
- **rpcn-design, `references/questions.md`:** when the host offers a question tool (`AskUserQuestion`), round 1 is asked through it, in one call:
  - one question per open ask, headed by its label (`Failure`, `Delivery`, `Ordering`, `Duplicates`);
  - 2 to 4 options, the pick first and labelled `(My pick)`, each with a one-line description, single choice;
  - a free-text ("Other") answer counts as that ask's answer.

  The run doesn't stop: it applies the answers, asks round 2 the same way only if an answer raised a new question, then writes. Step 2's single question about updating an existing note may use the tool too, as one question with two options: update it, or leave it. Without the tool (a terminal, a subagent, `claude -p`), the numbered list and stop are unchanged.
- **rpcn-author, `references/questions.md`:** the same rule for its one round (decision 2026-11-24, user). At most 4 questions per call, with more calls in the same round if there are more. Pick first, `(My pick)`. Then apply the answers and write. Without the tool, unchanged.
- **Start point:** the uncommitted edit to Design's `questions.md`, which already holds the request's proposed text (decision 2026-11-24, user), completed as above.

**Must not change:**
- headless (never asks);
- the four asks and their inferences;
- "After the answers" and "A choice left open", which apply to tool answers as to a typed reply;
- every `SKILL.md` and description, so the trigger evals are unaffected.

**Testing:** under `claude -p` the tool isn't offered (probe 2026-11-24: `ToolSearch` finds no `AskUserQuestion`). So every existing scenario still exercises the plain path and must pass unchanged. The tool path is checked by hand in a host that offers it, or by the extension's spike.

</frozen-after-approval>

## Implementation Notes

- Started from the uncommitted edit, as decided. It vanished from the tree partway through, presumably reverted by another session, so its text was re-added from the change request.
- **rpcn-design `questions.md`:** round 1 goes through the tool when one is offered. Answers are read as a typed reply would be, so "After the answers" and "A choice left open" apply, and there is no stop. Step 2's update question is asked as one question with two options, and "update it" goes on to the re-run.
- **rpcn-author `questions.md`:** the same rule. At most 4 questions per call, headers of at most 12 characters, and an existing file is still never written over.
- `SKILL.md` files, descriptions and headless rules are unchanged.
- **Probe (2026-11-24):** `claude -p` offers no `AskUserQuestion`, so the scenarios test the plain path.
- **Smoke** (`T/runs/20261124-124410`, both pins): every `rpcn-design__ask_*`, `rpcn-design__rerun_ask`, `rpcn-author__ask_*` and `rpcn-author__assume_headless` scenario, 9/9 PASS.
- Validator no warnings; `tools/tests skills` 146 passed.

- **First record failed** (2026-11-24, $68.82; the failed file is kept in the scratchpad): 60/61 scenarios passed 2/2, at accuracy 1.0. `rpcn-design__ask_go_ahead` was 1/2: the failure-target pick line dropped pattern 1's fixed ending "— the request named none.".
- **Fix (user: "fix wording, smoke, rerun"):** Design's "Go ahead" rule now gives the exact line, `[non-blocking] Where do failed messages go? Picked: <the DLQ> — the request named none.`. Smoke: `ask_go_ahead` 3/3 on both pins.

## Review Triage Log

Quick pass: 0 high, 3 medium, 3 low, 0 false. All six patched.
- medium: "a terminal" was listed as a host with no tool, but interactive Claude Code offers it. Removed.
- medium: Step 2's tool question still read as "stops at Step 2". Now "leave it" ends the run and "update it" goes on to the re-run.
- medium: "a free-text answer counts as the answer" overrode "After the answers" and "A choice left open". Answers are now read as a typed reply would be ("go ahead" is a pick; "not decided" or a skipped ask is left open). Author now reads free-text answers the same way.
- low: on the Author tool path, an existing file could be written under a picked name. The rule now says it is never written over, and only a name the user gives is used.
- low: Author's headers had no 12-character limit. Added.
- low: one line in Design `questions.md` was wrapped too long. Rewrapped.

## Verification

- `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check`, `uv run --with pytest pytest -q tools/tests skills`, and `rpcn_check` tests on both pins: pass
- Smoke the plain path once, on both pins: `rpcn-design__ask_*`, `rpcn-design__rerun_ask`, `rpcn-author__ask_first`, `rpcn-author__ask_existing`, `rpcn-author__assume_headless`.
- Record: `run_evals.py` at 2 runs, after review and commit (`skills/` changed). Ask before pushing.
