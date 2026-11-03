---
reviewer: rubric-walker
target: architecture-rpcn-skills.md (status final, updated 2026-11-03, AD-1 amended)
inputs: initiative-rpcn-skills.md (R13, Boundaries, Decision 2026-11-03), epic-validation-foundation.md (R1, Notes), repo state on main (README.md, .claude-plugin/, tools/validate_skills.py, ../rpcn-test-skills/run_scenarios.py)
date: 2026-11-03
scope: the AD-1 amendment (marketplace channel dropped) and everything it touches
---

# Rubric review: AD-1 amendment (marketplace channel dropped)

## Verdict

**Accept with small fixes.** AD-1 itself now states one channel clearly, and the reasons `.claude-plugin/plugin.json` stays (AD-12 version, `--plugin-dir`, `claude plugin eval`) are named. But one section still shows the old two-channel layout, the new "not supported" rule has nothing that enforces it (and the repo already breaks it), and AD-13 says the scenario runner installs "in CI" when AD-14 says evals never run in CI. None of these lets two epics diverge badly, but the first two let the dropped channel live on in the repo.

Severity: **High** means two units will build the same thing differently, or an AD cannot be followed as written. **Medium** means a rule cannot be enforced, or a section contradicts the amended AD-1. **Low** means wording or completeness.

---

## 1. Sections that still assume the marketplace channel

**M1. Structural Seed still lists `marketplace.json`. Medium.**
- Location: Structural Seed, line 335: `.claude-plugin/` holds `marketplace.json  plugin.json`.
- The seed is the layout a new story copies. It contradicts AD-1 ("Nothing depends on `.claude-plugin/marketplace.json`") and the dropped channel. The file still exists in the repo (`.claude-plugin/marketplace.json`, which declares the `rpcn-skills` marketplace with `source: "./"`). As long as it is there, `claude plugin marketplace add ajurcenk/rpcn-skills` keeps working, so the "not supported" channel is still live and unofficially documented.
- **Fix:** change the seed to `.claude-plugin/plugin.json` only. Add to AD-1: "The repo has no `.claude-plugin/marketplace.json`." Delete the file in the story that carries R1.

**M2. The capability map still sends R13 to `.claude-plugin/`. Low.**
- Location: Capability → Architecture Map, row "R13 Install | `.claude-plugin/`, `skills/` | AD-1".
- After the amendment, `.claude-plugin/` has nothing to do with installing; it serves AD-12 and the evals. What R13 and epic R1 do rely on is `skills/`, the gitignored `.claude/skills/` and `.agents/skills/`, and `skills-lock.json`.
- **Fix:** change "Lives in" to `skills/`, `.gitignore`, `skills-lock.json`. Add `.claude-plugin/plugin.json` to the R18 row, which already names `plugin.json`, and to the R12 row for `claude plugin eval`.

**L1. "Plugin repo" wording. Low.**
- Location: frontmatter `scope` ("The RPCN Skills plugin repo"), the first mermaid diagram (`subgraph repo[Plugin repo]`).
- This is still accurate, because the repo is loadable with `--plugin-dir`. But a reader could take it as the install model. Optional: "skills repo".

**L2. Deferred doesn't record the decision. Low.**
- Location: Deferred. It lists other scope exits ("VS Code extension integration: out of scope (initiative decision 2026-10-23)"), but not this one.
- **Fix:** add "**Claude Code plugin marketplace install:** out of scope (initiative decision 2026-11-03). Re-adding it needs an AD-1 change, and a `marketplace.json` plus an install scenario in AD-13." That way nobody brings it back quietly, as a "later" item.

## 2. Rules that cannot be enforced or don't prevent their divergence

**M3. "The marketplace is not a supported channel" has no check, and user docs already break it. Medium.**
- Location: AD-1, second Rule bullet.
- Nothing in AD-14 CI or `validate_skills.py` looks at user-facing install instructions or the manifest set. `README.md` (lines 14–19) still tells users `claude plugin marketplace add ajurcenk/rpcn-skills` and `claude plugin install rpcn-skills@rpcn-skills`, as the first option. Users who follow it get the whole repo as a plugin. That is exactly AD-1's stated *Prevents* case: skills loaded with the full repo around them, so a `../` slip would not show.
- **Fix:** make the rule checkable. "README and docs give `npx skills add ajurcenk/rpcn-skills` as the only install command. The validator fails if `.claude-plugin/marketplace.json` exists." Or have the R1 story fix the README and delete the file, with a test. Keep `--plugin-dir` in contributor docs only.

**M4. "Only `rpcn-` skills are discoverable" depends on gitignore alone. Medium.**
- Location: AD-1, last Rule bullet; epic R1 ("offers `rpcn-test` and no other skill").
- The rule names two folders to ignore. It does not ban a `SKILL.md` anywhere else in tracked files, for example a fixture under `evals/`, `_bmad/` or `docs/`, which `npx skills` could also find. Now that `npx skills` is the only channel, this is the only thing that decides what users see. Today the only tracked `SKILL.md` is `skills/rpcn-test/SKILL.md`, so this holds for now, but nothing keeps it that way.
- **Fix:** add to AD-1: "No tracked `SKILL.md` exists outside `skills/rpcn-*/`. The validator fails on one." That is cheap to check with `git ls-files '**/SKILL.md'`.

**M5. AD-13 runner step 2 says the install from a git ref happens "in CI". Medium.**
- Location: AD-13, Runner step 2 ("from a local path in development or a git ref in CI").
- AD-14 says evals and scenarios run locally, and CI holds no Claude credentials. So no CI run exists to install from a ref. Step 2 also says only "the way a user would", without naming the one channel that is left. The runner already uses `npx skills add` (`../rpcn-test-skills/run_scenarios.py` docstring), so the code is right and the spine is behind it.
- **Fix:** "installs `rpcn-skills` with `npx skills add`, the only user channel (AD-1), from a local path or a git commit". Then close or reword the `[ASSUMPTION: the install-from-ref command … verified in epic 1]` tag on line 279, now that the command is known.

**L3. How benchmark arms are installed is not stated. Low.**
- Location: AD-13, Benchmark arms and Benchmark sources.
- The `connect-plugin` arm is a Claude Code plugin. With the marketplace gone from our own channel, a reader could assume that arm also can't use the marketplace, or that it must use `npx skills`. "installed from their local folders at a recorded commit" leaves the mechanism open, so two runs of the benchmark could load that arm in different ways (as a plugin with its commands and hooks, or as bare skills), and the scores would not be comparable.
- **Fix:** name the mechanism for each arm. For example, `connect-plugin` with `claude --plugin-dir <folder>`, `skills-repo` with `npx skills add <folder>`, and `ours` with `npx skills add` as in step 2. Also state that this is benchmark tooling and not a user channel.

## 3. Coverage of the driving requirements

| Requirement | Covered by | Status |
|---|---|---|
| Initiative R13: install through `npx skills`, per the Agent Skills spec | AD-1 (repo, command, self-contained folders, verified with skills 1.7.4), Stack | Covered |
| Initiative R13: marketplace install is out | AD-1 bullet 2 | Stated, not enforced (M3), seed contradicts it (M1) |
| Initiative Boundaries: "Out: installing through the Claude Code plugin marketplace" | AD-1 | Covered; missing from Deferred (L2) |
| Epic R1: `npx skills add ajurcenk/rpcn-skills` | AD-1 | Covered |
| Epic R1: only `rpcn-` skills discoverable; a clean install offers `rpcn-test` and no other | AD-1 last bullet, AD-13 scenarios | Covered, but the guard is incomplete (M4). No scenario explicitly asserts "the offered skill list is exactly `rpcn-*`". Consider an `expect.toml` field, or a runner check, for the skills that were listed |
| Epic Note 2026-11-03: manifest stays for `--plugin-dir` and `claude plugin eval` | AD-1 bullet 3, AD-12, AD-13 | Covered |

## 4. Deferred: can anything let two units diverge?

- **Running evals in CI:** fine as written. But it leaves AD-13's "git ref in CI" (M5) ahead of its time. Fix M5 so the deferral and the rule agree.
- **Load-test environment, capacity model, deployment specifics, Migrate tables, org-facts:** unchanged by the amendment. Each is tied to one owning epic and an AD-6 or AD-8 shape, so it cannot diverge.
- **The marketplace:** not listed, so its status is clear only from AD-1 (L2).

## 5. Out-of-spine notes (not spine defects)

- The initiative's Decision 2026-11-03 and the epic's Note 2026-11-03 both still say "AD-1 still names both channels and needs an update through the architect". The amendment has landed, so the PO should mark these as done.
- The epic's Decision 2026-10-23 for story 1 ("runs repo, both install channels, …") is a historical record. It can stay, but it could say it was superseded on 2026-11-03.
- `tools/clash-list.txt` names the marketplaces of the *other* sets. That is correct under AD-10 and not affected.
