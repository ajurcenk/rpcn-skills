---
title: 'rpcn-test moves its detail into references'
type: 'refactor'
ticket: '3'
created: '2026-11-06'
status: 'built'
baseline_revision: 'ad21e418f7dbd8d68961e237f3dc8c3702d83f91'
route: 'oneshot'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `skills/rpcn-test/SKILL.md` is about 1,574 tokens (6,299 characters / 4), over AD-9's 1,200 limit, and epic 2 is about to make it bigger. The validator warns on it (rule `size`).

**Approach:** Move three blocks of step detail into skill-local files under `skills/rpcn-test/references/`:
- the pasted-config handling
- the Step 4 fix check
- the Step 5 report-header rules and section contents

`SKILL.md` keeps every step, every fenced `rpcn_check` command, the exit-code rules, Next and the status block, and tells the agent to read each new file at the step that needs it. The wording moves as it is, so behaviour doesn't change. `SKILL.md` must end up at 4,803 characters or less (validator `len // 4 <= 1200`).

</frozen-after-approval>

## Implementation Notes

**Why oneshot:** this moves about 50 lines of prose from `SKILL.md` into 3 new files, with no code change. The new files are skill-local, the way `references/lint-errors.md` already is. They are not listed in `shared.txt`, so `sync_shared.py` doesn't touch them. Every scenario allows `Read`, and no grader looks at the wording of `SKILL.md`.

**Out of scope:** the validator's other warning, `references/design-format.md is never named in SKILL.md`, stays. That file is a synced copy that story 2.10 (the design check) will use. The ticket's check is only "no size warning".

**Plan:**
- New `references/pasted-config.md`: the full "Pasted config" paragraph. `SKILL.md` keeps one line: when the user pastes YAML instead of naming a file, read `references/pasted-config.md` first.
- New `references/fix-check.md`: Step 4's "Check the fixes …" detail, covering the temp folder, the 2-revision cap, unverified fixes, and exit 2 leading to a draft. Step 4 keeps the per-error explanation rules and a pointer to the file.
- New `references/report-writing.md`: the Step 5 header bullet (inputs relative to the report, with the examples) and the section bullets. Step 5 keeps the file location, a pointer to `report-writing.md` and the two shared format files, the fenced `hash --check` command, and its ready/draft/blocked handling.
- Each pointer says "Read `references/<file>.md` and follow it", placed where the old text was.

**Checks:**
- `uv run tools/validate_skills.py` gives no `size` warning for `rpcn-test`, and no new `file-refs` warning.
- `uv run tools/sync_shared.py --check` exits 0.
- `rpcn-test-skills` smoke run: `uv run run_scenarios.py --source local:../rpcn-skills --scenario rpcn-test__lint_subfolder --scenario rpcn-test__lint_broken --runs 1 --no-judge` passes.
- After committing: `uv run tools/run_evals.py` passes and writes a `dirty: false` record, which is then committed.

**Built:**
- Four skill-local references: `pasted-config.md`, `fix-check.md`, `report-writing.md`, and a fourth, `binary-fixes.md`. The fourth was added because moving the three planned blocks left `SKILL.md` at 4,999 characters. The Step 1 binary-fix list was the next block of step detail. The exit-2 rule itself stays in `SKILL.md`.
- **Surprise:** `${CLAUDE_SESSION_ID}` and `${CLAUDE_SKILL_DIR}` are expanded only in `SKILL.md`. The fix-check temp path therefore stays in Step 4, and `fix-check.md` refers back to it.
- A few phrases elsewhere in `SKILL.md` were tightened without changing their meaning: Step 2's resources sentence, "Then check it", and the reply line. That brought the file to 4,799 characters, about 1,199 tokens. The margin is very small, so epic 2's growth has to go into references.
- **Smoke runs:** `lint_subfolder` and `lint_broken` each passed 1/1, before and after the review patches (`T/runs/20261106-103258`, `T/runs/20261106-103624`). The agent read each reference at its step.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 2 medium, 3 low, 1 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The binary-fix list was moved without being in the plan, and its pointer had no read verb | medium | patch | Step 1 now says "read `references/binary-fixes.md` and show its fix". The scope change is recorded in the notes above. |
| The fix-check folder was attached to "reading" and not to the write | medium | patch | Step 4 again writes the fully fixed pipeline to the temp path, then reads `fix-check.md`. |
| The pointers didn't say "read … and follow it" | low | patch | All four pointers now say to read the file. The pasted-config pointer says "first". |
| `fix-check.md` framed the check around a report, which clashes with the pasted flow | low | patch | The intro was reworded, and the draft line now applies "when a report is written". |
| The wording was restructured into lists | false | reject | Checked line by line, and no rule changed meaning. |
| Zero size margin | low | reject | The ticket's check is met. Future growth goes into references (noted). |
