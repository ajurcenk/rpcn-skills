---
type: review
lens: adversarial (compliant-but-incompatible units), focused on the AD-1 amendment of 2026-11-03
target: _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md
inputs:
  - _bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md
  - _bmad-output/initiative-rpcn-skills/deferred-work.md
  - .claude-plugin/plugin.json, .claude-plugin/marketplace.json, README.md
  - tools/run_evals.py, tools/eval_record.py, tools/eval_record_check.py, .github/workflows/ci.yml
  - evals/rpcn-test__*/ (case.yaml, graders)
  - ../rpcn-test-skills/run_scenarios.py, arms.toml, scenarios/*/expect.toml
created: '2026-11-03'
verdict: 'Revise AD-1, AD-12, AD-13 and AD-14 before epic 2 adds a second skill: the amendment makes `npx skills` the only shipped path, but the trigger gate, the release identity and the eval record are still defined against the `--plugin-dir` path, so compliant units can disagree about what was tested and what was released.'
---

# Adversarial Review — AD-1 amendment (2026-11-03)

## Verdict

**Revise before the next skill lands.** The amendment is right in direction: one user channel, and the plugin manifest kept only as a version source and a dev harness. But the spine now has two runtimes for the same skill folder, and it only pins the behaviour of one of them:

- **Dev path** (`claude --plugin-dir .`, `claude plugin eval .`): the whole repo loads as one plugin, every skill is present, names are namespaced (`rpcn-skills:rpcn-test`), plugin variables such as `${CLAUDE_PLUGIN_ROOT}` exist, and the repo's own `.claude/skills/` may sit beside it.
- **User path** (`npx skills add ajurcenk/rpcn-skills`): each skill folder is copied or symlinked alone into an agent folder, possibly a subset, from the default branch HEAD, with no plugin variables and no atomic update.

The 90% trigger gate, the release tag and the eval record are all defined on the dev path or on neither. The pairs below each obey every AD and still produce pieces that don't fit.

Severity: **High** means a user gets behaviour no gate measured, or a release that cannot pass its own checks. **Medium** means rework or misleading records. **Low** means friction or wording.

## Summary

| # | Sev | Units in conflict | Hole | Closing rule (short) |
|---|---|---|---|---|
| A1 | High | release-sync stamp job (AD-12) vs eval-record check (AD-14) | The stamp commit edits every SKILL.md, which changes the skills hash, so the release commit has no passing record and `main` goes red | AD-14: the skills hash ignores the `metadata` stamp keys (validator checks them instead), or stamping happens inside the change PR before evals run |
| A2 | High | AD-12 tag-based release vs `npx skills` installing `main` HEAD | Users never install a tag. Between releases they get new content under the old version stamp, so `produced_by` and `binary.plugin_version` don't identify what ran | AD-12: every merge that changes `skills/` is a release (version bump required, CI-checked), or the README pins `#v<version>` and that ref syntax is verified |
| A3 | High | trigger suite (`claude plugin eval .`, AD-13) vs scenario runner (`npx skills add`, AD-13) | The accuracy gate runs on the plugin path only: all skills loaded, namespaced, plugin variables present. Users get a subset of un-namespaced skills with none of that | AD-13: trigger positives also run on an `npx` install with only that skill; AD-1: validator bans plugin-only variables; one fixed name pattern for graders |
| A4 | Med-High | scenario runner vs README vs developer machine | "Installs the way a user would" doesn't fix scope (project/global), mode (copy/symlink) or agent, and nothing stops skills from `~/.claude/skills` or the repo's `.claude/skills/` (BMad) from joining a run | AD-13: one fixed user-path install command, and every run records and checks the list of skills the session actually saw |
| A5 | Medium | AD-1 ("not a supported channel") vs Structural Seed and README | `marketplace.json` is still in the repo and in the seed, and the README still documents the marketplace install, so the unsupported channel keeps working and stays advertised | AD-1: delete `marketplace.json`, drop it from the seed, validator fails if it exists, README gives one install command |
| A6 | Medium | AD-12 `retired.toml` and AD-9 sibling edits vs per-skill `npx` installs | Under `npx` a renamed skill's old folder stays installed, and old siblings keep stale "Not for" lines, so a retired name and its replacement can trigger on the same phrase | AD-12: an update and retirement procedure for the user path (remove step, or a retired stub), and the README says update all skills together |
| A7 | Medium | eval record (AD-14) vs eval cases and the test project | The record's hash covers only `skills/`. Changing graders, cases, the gate or the scenarios needs no new record, and the scenario project commit isn't recorded | AD-14: hash covers `skills/`, `evals/*/` and `tools/eval_gate.py`; the record stores the test-project HEAD and a clean flag |
| A8 | Low | AD-13 runner step 2 ("a git ref in CI") vs AD-14 ("evals run locally, not in CI") | Two contradictory statements about where the git-ref install runs. A release is never evaluated from the bytes users will install | AD-13: `git:<commit>` is used by the release check on the stamp commit; `local:` only for pre-merge runs |
| A9 | Low | AD-12 "copies both into rpcn_check" vs AD-2 "never edit a copy" | One build stamps the synced copies and fails the drift check, another stamps the source | AD-12: the stamp edits `tools/shared/rpcn_check/rpcn_check.py` and then runs `sync_shared.py` |

---

## A1 — The release stamp invalidates its own eval record (High)

**Rules involved:** AD-12 (a release commit stamps every SKILL.md with `metadata.plugin-version` and `rpcn-refs-version`, then tags it on `main`). AD-14 (every change must carry a passing record for its current skill content; release runs only from a green `main`). `tools/eval_record.py` hashes every byte of every file under `skills/`.

**Compliant but incompatible build:**
- **epic-release-sync** writes the stamp job exactly as AD-12 says. It edits `metadata:` in each SKILL.md and the constants in `rpcn_check`, then commits.
- **epic-validation-foundation** (already shipped) hashes `skills/` byte for byte. The stamp changed bytes, so the hash is new and no record matches. `eval_record_check.py` fails on the stamp commit.
- Either the release can't run from green `main`, or every release costs a full local eval run (about $4.20 plus ~3 runs of wall time) for a metadata-only edit, run by hand between the merge and the tag. Both units obey their ADs.

The weekly job (AD-14) has the same problem: rolling the newest pin regenerates `tools/shared/generated/`. That syncs into every skill's `references/`, which changes the hash, and the bot PR can't carry a record because CI has no Claude credentials.

**Closing rule — AD-14 tightened:**
- The skills hash normalises SKILL.md frontmatter by dropping the `metadata.plugin-version` and `metadata.rpcn-refs-version` values, and the matching constants in `rpcn_check`, before hashing. The validator already checks that the stamps equal `plugin.json`, so they don't need the record too.
- State explicitly that a pin-roll PR (generated references changed) needs a human-run eval record before merge, and the weekly job only opens the PR. Or exclude `references/generated-*.json` from the hash and rely on the deprecated scan. Choose one and write it down.

## A2 — Users install `main` HEAD, not the tag (High)

**Rules involved:** AD-12 ("Release: a git tag `v<version>` on the stamp commit on `main`. `npx skills` installs from `main`."). AD-6 (`produced_by: rpcn-<job>@<plugin version>`). AD-4 (`binary` returns `plugin_version`).

**Compliant but incompatible build:**
- A feature PR changes `rpcn-test`'s readiness logic and merges to `main`. It obeys AD-14 (it carries a record) and doesn't stamp, because stamping is the release's job.
- A user runs `npx skills add ajurcenk/rpcn-skills` that afternoon and gets the new content. `rpcn_check binary` reports `plugin_version: 0.1.0` and the hand-off files say `produced_by: rpcn-test@0.1.0`, the same as files made by the tagged 0.1.0, which behaves differently.
- A bug report quoting `rpcn-test@0.1.0` can't be reproduced from the tag. The tag exists only on the plugin path, and that path is no longer shipped.

Under the old dual channel the marketplace gave the tag some meaning. After the amendment, AD-12's release step has no user-facing effect.

**Closing rule — AD-12 tightened (pick one):**
- **(a) Every skill change is a release.** A PR that changes the skills hash must bump `plugin.json` and restamp, and CI fails when the hash differs from `main` but the version doesn't. The tag is then created on merge. Combined with A1, the record is computed over the normalised content, so the bump doesn't need a re-run.
- **(b) Users pin the tag.** The README installs `npx skills add ajurcenk/rpcn-skills#v<version>` (or whatever ref syntax vercel-labs/skills 1.7.4 supports, which must be verified as AD-1's other claims were), and `main` may run ahead of the stamp.

## A3 — The trigger gate measures a configuration no user has (High)

**Rules involved:** AD-1 (users get only `npx skills`; skills are self-contained). AD-13 (trigger cases use `claude plugin eval` with `tool: Skill` `input_match`; the 90% gate; near-miss negatives for each "Not for" sibling). AD-9 ("Not for … use rpcn-<sibling>").

**Compliant but incompatible build:**
- **Trigger suite (epic 1, any later skill epic):** `claude plugin eval .` loads the repo as one plugin. Every rpcn skill is present at once, under names like `rpcn-skills:rpcn-test`. The grader regex `(?:[\w-]+:)?rpcn-test` hides the namespace. Near-miss negatives score well because the sibling is there to take the prompt.
- **User:** installs `-s rpcn-test rpcn-author` (AD-1 says subsets are supported). No `rpcn-design` is present, so "design a pipeline for orders" has no better match and goes to `rpcn-author`. No gate measured that.
- **Skill epic author:** writes a step using `${CLAUDE_PLUGIN_ROOT}/skills/rpcn-x/references/...`, or a script reading `../../.claude-plugin/plugin.json` through an env var or `git rev-parse`. It passes the validator's static "file references" check, triggers correctly under `plugin eval`, and breaks under `npx`. It only gets caught if that skill happens to have a scenario covering that step.
- A second epic writes graders that match only the bare name `"rpcn-x"` (correct for `npx`). Under `plugin eval` the Skill input is namespaced, so that epic's accuracy is understated or zero. Both grader styles obey AD-13.

**Closing rule — AD-13 and AD-1 tightened:**
- AD-13: the trigger suite is labelled a **plugin-path proxy**. Each skill also has at least one positive and one near-miss case that runs through `run_scenarios.py` on an `npx` install **containing only that skill** (`allowed_tools = [Skill]`, low `max_turns`). These count toward the R12 gate.
- AD-13: one grader pattern is fixed in the spine: `"skill"\s*:\s*"(?:rpcn-skills:)?<skill>"`, so that both paths match and no other prefix does.
- AD-1: the validator fails on `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `.claude-plugin`, `git rev-parse` and any path that leaves the skill folder, in SKILL.md, references and scripts. `${CLAUDE_SKILL_DIR}` is the only allowed variable.
- AD-9: "Not for" lines must make sense when the named sibling isn't installed (say what the sibling does, not only its name).

## A4 — "The way a user would" is unpinned, and runs are not isolated (Medium-High)

**Rules involved:** AD-13 step 2 ("installs `rpcn-skills` there the way a user would"). AD-1 (BMad skills are gitignored and restored into `.claude/skills/` and `.agents/skills/`). The README (`npx skills add ajurcenk/rpcn-skills`, interactive defaults).

**Compliant but incompatible build:**
- **Runner:** `npx -y skills add <src> -s <skill> -a claude-code -y --copy`, project scope, checks `.claude/skills/<s>/SKILL.md`.
- **README user:** runs the bare command. That prompts for agents and scope and may symlink from a canonical `.agents/skills/` folder, or install globally. `${CLAUDE_SKILL_DIR}` then resolves through a symlink, and the skill is tested only as a copy. Both installs obey AD-1.
- **Developer machine:** a contributor has rpcn-skills (or the competitor skills) installed globally in `~/.claude/skills/`. The `bare` and `connect-plugin` benchmark arms (R20) then see our skills too. In this repo, `claude plugin eval .` runs from a cwd whose `.claude/skills/` holds about 40 restored BMad skills (for example `bmad-review`, `bmad-build`) that can compete for "review/test/build my pipeline" prompts, unless the eval sandbox hides them. That isn't verified. Records from two machines aren't comparable, and nothing in the record shows it.

**Closing rule — AD-13 tightened:**
- The spine fixes the user-path install command (scope, `-a`, copy or symlink), and the README uses exactly that command. If symlink is the default, the runner tests symlink mode.
- Every scenario run and the trigger run record the skills list from the session's init event. The run fails if any skill outside the arm's expected set is visible (no `bmad-*`, and no `rpcn-*` in non-`ours` arms).
- Verify, and record in AD-13, whether `claude plugin eval` and `claude -p --setting-sources project,local` load `~/.claude/skills` and the cwd's `.claude/skills/`.

## A5 — The unsupported channel is still shipped and advertised (Medium)

**Rules involved:** AD-1 ("not a supported channel … Nothing depends on `marketplace.json`"). Structural Seed (still lists `marketplace.json  plugin.json`). R13.

**Compliant but incompatible build:**
- `.claude-plugin/marketplace.json` is still committed, so `claude plugin marketplace add ajurcenk/rpcn-skills` still works. `README.md` lines 16–20 still give it as the first install method.
- A docs story keeps the README as is ("nothing depends on it" is true). A validator story removes nothing ("the seed lists it"). Users install through the marketplace and get namespaced skills, plugin-cache paths and plugin-version-keyed updates. Nothing tests any of it, and bug reports arrive from a channel the spine says doesn't exist.

**Closing rule — AD-1 tightened:** delete `.claude-plugin/marketplace.json` and remove it from the Structural Seed. `validate_skills.py` fails if it exists. The README has exactly one install command. `plugin.json` stays, with a one-line comment in the README Development section saying it is for `--plugin-dir` and `plugin eval` only.

## A6 — Retired names and stale siblings live on in users' folders (Medium)

**Rules involved:** AD-12 (`retired.toml`; a retired name is never reused). AD-9 (the epic adding a skill updates siblings' "Not for" and "Next"). AD-1 (per-folder installs).

**Compliant but incompatible build:**
- On the plugin path an update replaces the whole plugin, so a renamed skill disappears and every sibling moves forward together.
- On the `npx` path, epic N renames `rpcn-x` to `rpcn-y` and lists `rpcn-x` in `retired.toml`. A user who runs `npx skills add` again (or `update`) gets `rpcn-y`, and `rpcn-x/` stays in `.claude/skills/`. Two skills now claim the same phrases.
- In the same way, a user who added only `rpcn-test` in 0.1 and later adds `rpcn-deploy` in 0.4 has an old `rpcn-test` whose "Not for" lines don't mention Deploy. AD-9's sibling edit was made in the repo but never reached the user's copy.

**Closing rule — AD-12 tightened:** define the user-path update: the README says to update all rpcn skills together (and gives the command). A retired name ships for one release as a stub skill whose description says "Retired — use rpcn-y" with `disable-model-invocation`, or the release notes give the remove command. Optionally, `rpcn_check binary` warns when sibling skills in the same parent folder report a different `plugin_version`.

## A7 — The eval record covers less than the eval (Medium)

**Rules involved:** AD-14 (the change carries a passing record "for its current commit's skill content"). AD-13 (gate definitions, case folders, `rpcn-test-skills` scenarios).

**Compliant but incompatible build:**
- PR 1 loosens a grader in `evals/rpcn-test__miss_*/graders/` (or deletes a near-miss case, or relaxes `eval_gate.py`). `skills/` is unchanged, so the old record still matches and CI is green with no new run.
- PR 2 changes a scenario's `expect.toml` in `rpcn-test-skills`. The record doesn't store that project's commit, so nobody can tell which scenarios a record proved.

Both PRs obey AD-14 as written.

**Closing rule — AD-14 tightened:** the record hash covers `skills/`, `evals/*/` (cases and graders) and `tools/eval_gate.py`. The record stores `test_project_head` and `test_project_dirty`, and a record from a dirty tree can't pass.

## A8 — Where the git-ref install runs is contradictory (Low)

AD-13 says the runner installs "from a local path in development or a git ref in CI". AD-14 says evals never run in CI. `run_evals.py` uses only `local:`, which copies the working tree, dirty or not. So no run ever installs the bytes users get from GitHub.

**Closing rule — AD-13:** drop "in CI". The release check (A2) runs the scenario set with `--source git:<stamp commit>` before tagging, and the record stores the source kind.

## A9 — Which `rpcn_check` the stamp edits (Low)

AD-12 says the release "copies both into `rpcn_check`". AD-2 forbids editing copies, and CI fails on drift. The source currently holds `PLUGIN_VERSION = "0.1.0"` as a constant. One build stamps the per-skill copies and fails the drift check. Another stamps the source and forgets to sync.

**Closing rule — AD-12:** the stamp edits `tools/shared/rpcn_check/rpcn_check.py` and runs `sync_shared.py` in the same commit. The validator also checks that constant against `plugin.json`.

## Other observations

- AD-1's "Prevents" line still describes the old two-channel problem ("works only when the whole repo is loaded as a plugin"). After the amendment the plugin path exists only for development, so the risk is the reverse: a skill that passes dev-path gates but fails on the user path (A3). Reword it.
- Capability map row R13 says "`.claude-plugin/`, `skills/`". R13 now lives in `skills/` and the README. `.claude-plugin/plugin.json` belongs under R18 only.
- Stack: pin the Claude Code version used for `--plugin-dir` scenario arms too, not only `claude plugin eval`. The competitor arms load through `--plugin-dir`, while ours loads through `npx`, and that asymmetry should be stated as intended (each arm in its own native channel).
