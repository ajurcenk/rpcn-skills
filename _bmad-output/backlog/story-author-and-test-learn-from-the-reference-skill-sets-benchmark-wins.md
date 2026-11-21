---
id: 6
type: story
title: "Author and Test learn from the reference skill sets' benchmark wins"
parent: none
covers: []
after: [4]
assignee: ""
refined: false
hitl: false
risk: medium
---

# Author and Test learn from the reference skill sets' benchmark wins

## Description

In the 2.18 benchmark, `skills-repo` (`redpanda-data/skills`) beat `ours` on `compare_write` and `compare_diagnose` on judge rank at equal score. `connect-plugin` reached the same scores at a third of our cost. This story compares their winning replies and pipelines with ours, using the saved runs. It then adds what explains the gap to rpcn-author's and rpcn-test's guidance. The judge's notes point at:
- mappings that reject a missing, null *or empty* required field;
- keeping the DLQ event unchanged;
- running the pipeline on sample messages before replying;
- a reply that leads with the fix and states its limits;
- fewer tool calls for the same checks.

Every piece adapted from a reference set gets a SOURCES.md row with its source, commit and licence (initiative decision 2026-10-23). Every RPCN fact is still proved against the binary (AD-15). It is a skill change, so it needs a passing eval record (AD-14), which is also the re-benchmark that shows whether the gap closed.

## Requirements

Verify:
- **Findings:** a short written comparison, in the plan, of each lost comparison's winning replies and files against ours, citing `T/runs/20261120-171018`.
- **Each change rests on one finding:** a guidance change in rpcn-author or rpcn-test for each finding the user accepts, with a SOURCES.md row for anything adapted.
- **Record:** a passing `run_evals.py --with-compare` record, with each comparison's result written down beside 2.18's.

## References

- plan — _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-re-benchmark-author-and-test-after-the-improvements-plan.md, section Implementation Notes (2.18 results and the judge's notes)
- research — _bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md, sections Prior art A and Prior art B
- reference — `redpanda-data/skills` at commit `a4562333b774d963066e11dfa1282646b8490550` (the `connect` and `connect-debugging` skills), and the connect repo's `.claude-plugin` at commit `f15e3064a4e4aa4edc47f3b0f87c53d1572189fc` (the paths in `rpcn-test-skills/arms.toml`)
- architecture — _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md, AD-13, AD-14, AD-15

## Notes

- Decision (2026-11-20, user): the reference skill sets are to be used as sources to learn from, not only as benchmark opponents. This story is the first such use.
- Open question: which findings to adopt. Answered at refinement, after the comparison is written.
- Open question: whether it should come before epic 3 (Design), since Design will set the reply and question conventions that Author follows.
- Waits on 4 because: the judge must write a note on every arm first, so the `compare_diagnose` loss has judge evidence to study.
