---
title: 'Re-benchmark Author and Test after the improvements'
type: 'chore'
ticket: '18'
created: '2026-11-20'
status: 'in-progress'
baseline_revision: 'f31f16153fe6e7cc0af3a1ec5b8d98b83f1f2e09'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** stories 14–17 changed the benchmark judge, the comparison points, rpcn-test (16) and rpcn-author (17). Two things are still open:
- whether `ours` now wins any comparison;
- the eval record for 16 and 17 (AD-14). Under the epic's 2026-11-18 decision, this run is that record, and 16–18 are pushed together after it.

**Approach:**
- Run `uv run tools/run_evals.py --with-compare` once on the committed tree, with absolute `RPCN_TEST_BINARIES` for 4.100.0 and 4.115.0. It costs about $55.
- Commit the record.
- In Implementation Notes, from `results.json`, record each comparison's winner, every arm's score, judge rank and cost, plus the turns and cost of the scenarios 16 aimed at, against 2.12.
- A comparison `ours` loses is recorded with the judge's evidence and accepted. No new story comes from it unless the user asks (epic decision 2026-11-18).
- No skill or runner change in this story. If the run fails, stop, record why, and ask the user.

</frozen-after-approval>

## Implementation Notes

## Review Triage Log

## Verification

- `uv run tools/eval_record_check.py` — the new record matches the current skills, `passed: true`, `dirty: false`
- `uv run --with pytest pytest -q tools/tests skills` and T's tests — pass before the push
