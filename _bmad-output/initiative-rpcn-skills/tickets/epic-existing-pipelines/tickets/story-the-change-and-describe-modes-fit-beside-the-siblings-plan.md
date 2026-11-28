---
title: 'The change and describe modes fit beside the siblings'
type: 'feature'
ticket: '5'
created: '2026-11-27'
status: 'done'
baseline_revision: '38d34863e60d79e64efa006723f6ecdf596d822f'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/epic-existing-pipelines.md'
  - '{project-root}/evals/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Describe mode (8.1) and change mode (8.2 to 8.4) give rpcn-design and rpcn-author phrases that collide:
- rpcn-design owns "describe my pipeline …" and "update my design note", but rpcn-author fires on a described data flow;
- rpcn-author owns "change my pipeline to …" and "apply the design change …", and "design change" reads as rpcn-design's;
- "test my pipeline …" belongs to rpcn-test alone.

No trigger case covers the change phrases, and neither skill's Next points to the other's new mode.

**Approach:** Each skill's description gains its new phrases and a "Not for …" naming the sibling where they collide. Each gets a Next line for its new mode's outcome. New trigger cases (positives and sibling near-misses) prove the split, and the trigger gate passes at accuracy 1.0. The room comes from tightening SKILL.md wording, with no rule dropped.

## Boundaries & Constraints

**Always:**
- Every SKILL.md ≤ 4,803 chars and every description ≤ 1,024. Measure them as `len()` of the file text and of the parsed description. Today rpcn-author is at 4,802 (description 851), rpcn-design at 4,764 (910) and rpcn-test at 4,735 (1,017).
- Make room by shortening wording, or by moving a passage into an existing reference with a pointer. Never drop a rule, and never change a Step's behaviour.
- New cases follow `evals/README.md`:
  - `max_turns: 2`, `allowed_tools: [Skill]`, and `tags`;
  - `graders/fired.md`, or a sibling `graders/not-fired.md` (only that case's own skill silent, `min: 0`, `max: 0`, `arm: both`);
  - the README's case tables and counts updated.
- `validate_skills.py` shows no errors and no warnings for the three skills.
- Each new positive uses its phrase as it stands in its description: verbatim, or a close paraphrase recorded in the README phrase table.

**Never:**
- Change the behaviour of any mode.
- Touch rpcn-test's description, which has 7 chars of room. Test only takes new sibling near-misses.
- Use `claude plugin eval` without `--no-publish`.
- The implementation agent never commits, and never runs `tools/run_evals.py` or the trigger suite. Leave `T/orders_benthos_test.yaml` alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Change, positive | "Change my pipeline `pipes/orders.yaml` to drop test orders" | rpcn-author fires | — |
| Design change, positive | "Apply the design change in `pipes/orders.design.md` to my pipeline" | rpcn-author fires | — |
| Describe, positive | "Describe my pipeline …" (existing case) plus one paraphrase ("what does my pipeline `x.yaml` do, as a design note") | rpcn-design fires | — |
| Describe, near-miss for Author | "Describe my pipeline `pipes/orders.yaml` as a design note" | rpcn-author silent | — |
| Change, near-miss for Design and Test | "Change my pipeline … to retry the API 5 times" | rpcn-design and rpcn-test silent | — |
| Design change, near-miss for Design | "Apply the design change in … to …" | rpcn-design silent | — |
| Test, near-miss for both | "Test my pipeline `pipes/orders.yaml` against its design note" | rpcn-author and rpcn-design silent | — |
| Existing cases | All current trigger and miss cases | Unchanged results | — |

</frozen-after-approval>

## Code Map

- `skills/rpcn-author/SKILL.md`:
  - description: add "apply the design change …", and "Not for … describing an existing pipeline as a design note (use rpcn-design)";
  - Next: one line for a change made (interactive) or applied, "test it with rpcn-test" (it may merge with the first line).
  - Body room: 1 char. Shorten wording elsewhere, for example Step 2's or Step 7's wording; the 8.4 rules live in `references/change.md`.
- `skills/rpcn-design/SKILL.md`:
  - description: add "Not for changing an existing pipeline or applying a design change to it (use rpcn-author)";
  - Next: "Note describes or updates an existing pipeline: apply the design change with rpcn-author".
  - Room: 39 chars.
- `skills/rpcn-test/SKILL.md`: unchanged.
- `evals/`: one folder per case, `prompt.md` plus `graders/`. Copy the shape of `rpcn-author__trigger_write_pipeline` (fired) and `rpcn-author__miss_design_pipeline` (sibling not-fired). The existing `rpcn-design__trigger_describe_pipeline`, `rpcn-author__miss_design_pipeline` and `rpcn-design__miss_write_yaml` already cover "design …" (not Author) and "write …" (not Design).
- New cases:
  - `rpcn-author__trigger_change_pipeline`
  - `rpcn-author__trigger_apply_design_change`
  - `rpcn-design__trigger_describe_existing`
  - `rpcn-author__miss_describe_pipeline`
  - `rpcn-design__miss_change_pipeline`
  - `rpcn-design__miss_apply_design_change`
  - `rpcn-test__miss_change_pipeline`
  - `rpcn-author__miss_test_pipeline`
  - `rpcn-design__miss_test_pipeline`
- `evals/README.md`: the case tables (counts, sibling-negative lists), the phrase table, and the cost line (trigger suite ~$6.00, scaled by the new case count).
- `tools/tests/`: check whether a test counts cases or reads the README tables. Update it only if it does.

## Tasks & Acceptance

**Execution:**
- [x] `skills/rpcn-author/SKILL.md`: description phrases, Next line, and room made by tightening wording.
- [x] `skills/rpcn-design/SKILL.md`: the same.
- [x] `evals/<9 new cases>/`: prompt and grader.
- [x] `evals/README.md`: tables, phrase table, costs.

**Acceptance Criteria:**
- Given the edits, then the `len()` limits hold, `validate_skills.py` reports no errors or warnings, `sync_shared --check` is clean, and the pytest suites pass on both pins.
- Given the trigger suite, run by the orchestrator after review (`claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish --trust-plugin --json <out>`, then `tools/eval_gate.py`), then accuracy is 1.0.

## Implementation Notes

- Sizes after the change (`len()` of file text / parsed description): rpcn-author 4,802 / 922, rpcn-design 4,803 / 961, rpcn-test 4,735 / 1,017 (unchanged).
- Room came from wording only, no rule dropped: "the installed binary reports" became "the binary reports" in both descriptions; Author's Step 1 "design-note check" became "note check", Step 2's `<dir>/` parenthetical and "the file the user names" were tightened, Step 4's close-match and `required: true` sentences, Step 6's `<res>` and revision sentences, and Step 7's heading and file wording were shortened; Design dropped "Run", ", here and below", "of the flow"/"the" in Step 3, tightened Step 4's exit 0/1 lines, Step 2's not-found bullet, two Next lines and the status-block sentence.
- `tools/tests/test_eval_gate.py` reads the real `evals/` folders dynamically, so no test change was needed.
- README phrase table gained a second table for the change and describe positives; trigger cost scaled from 43 to 52 cases (~$7.30 at 2 runs, default run ~$75.80).

## Plan Change Log

## Review Triage Log

### Pass 1 (quick lens), 2026-11-27: 5 findings, 0 high, 1 medium, 4 low, 0 false, 0 maybe-false

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | Author Step 1 says "note check"; status-block.md:13 still says "design-note check" | low | patch | Confirmed by grep. Fix: status-block.md uses Step 1's name (no SKILL.md room needed). |
| 2 | Design Step 4's "(a retry count)" reads as a definition, which narrows the rule | low | patch | Confirmed in the diff ("such as" dropped). Fix: restore it and find the room elsewhere. |
| 3 | Design Next: a ready describe note matches "build it", and the new line is muddled ("updates an existing pipeline") | medium | patch | Confirmed: describe.md writes `status: ready`, so line 1 points to building over an existing file. Fix: one next step per outcome (not built / re-run with a change / described). It is a wording-only fix, so it routes to patch, not a plan loop. |
| 4 | README labels trigger_describe_existing "close paraphrase" | low | patch | Confirmed: the prompt shares neither the verb nor the shape. Fix: label it "new phrasing". |
| 5 | The README phrase-table intro says "story 8.5" but lists the 8.1 case | low | patch | Confirmed. Fix: "stories 8.1 and 8.5", with bare slugs. |

## Verification

**Commands:**
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest tools/shared/rpcn_check/tests tools/tests -q`: expected all pass.
- `uv run tools/validate_skills.py` and `uv run tools/sync_shared.py --check`: expected clean, with no warnings.
- Smoke (implementer): from T, run `uv run run_scenarios.py --runs 1` on `rpcn-author__change_propose`, `rpcn-author__chain_design_change` and `rpcn-design__describe_pipeline`, to confirm the reworded SKILL.md files still route their modes. Expected: pass.

- Trigger gate (orchestrator, 2026-11-27): `claude plugin eval . --ablation none --runs 2 --tag trigger --no-publish`, then `eval_gate.py`: accuracy 1.0, 104/104 runs (60 positive, 44 negative), no failed runs.
- **Pushed:** `9ed7b07..1a8bb56`, with 8.4, 8.5, 8.6 and `run_evals --resume` together; record `2026-11-28-eb28fcbb4e92.json` (accuracy 1.0, 77 scenarios 2/2). CI run 46165299566 was green. T commits stay local.

