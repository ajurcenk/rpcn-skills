# Currency review: architecture-rpcn-skills (AD-1 amendment), 2026-11-03

**Lens:** is every committed decision checked against the web, the repo, or the live tool, rather than taken from memory?
**Scope:** AD-1 as amended today, plus the Stack table, Structural Seed, AD-12 and AD-13 where they repeat AD-1's claims.
**Verdict:** The main install path holds up against the live tool. Two AD-1 claims are wrong today: the contributor restore command, and the pinned `npx skills` version. Fix both before more stories build on them.

## How each claim was checked

| AD-1 claim | Checked against | Result |
|---|---|---|
| Users install with `npx skills add ajurcenk/rpcn-skills` | Ran `npx -y skills@1.7.6 add ajurcenk/rpcn-skills --list` against the public repo (default branch `main`, pushed 2026-11-03) | **Confirmed.** It finds 1 skill, `rpcn-test`. |
| `npx skills` installs each skill folder alone | Ran `add ... --skill rpcn-test -a claude-code -y` in an empty scratch project | **Confirmed.** It copied the whole `skills/rpcn-test/` folder (SKILL.md, `scripts/`, `references/`, `shared.txt`) into `.claude/skills/rpcn-test/` and wrote a `skills-lock.json` entry |
| `npx skills` scans `.claude/skills/` and `.agents/skills/` | `docs/creating-skills.md` "Skill Discovery" in skills 1.7.4 and 1.7.6 | **Confirmed, but the list is longer.** About 55 agent folders are scanned (`.cursor`-style, `.windsurf/skills/`, `.kiro/skills/`, `data/skills/`, `agent/skills/` …), plus the root `SKILL.md`, `skills/.curated|.experimental|.system/`, and any `skills.sh.json` `paths` |
| Those folders are gitignored | `.gitignore` lines 3–4; `git check-ignore` | **Confirmed.** Neither folder is tracked |
| `skills-lock.json` committed; contributors restore with `npx skills install` | `git ls-files`; CLI source `dist/cli.mjs:9479-9482`; ran `npx skills@1.7.6 install` | **Wrong.** `install` and `i` are aliases of `add`, and with no source the command fails with `ERROR Missing required argument: source`. The lock-file restore command is `npx skills experimental_install` (README "Experimental Features"; `docs/commands.md` "Restore skills from the project lock file") |
| "verified, vercel-labs/skills 1.7.4" | `npm view skills time` | **Out of date.** 1.7.5 came out 2026-11-02 and 1.7.6 on 2026-11-03 (latest). `npx skills` with no version runs 1.7.6, not the version the spine pins |
| `.claude-plugin/plugin.json` kept for `claude --plugin-dir` and `claude plugin eval` | `claude --help` and `claude plugin eval --help` on Claude Code 2.1.317; `tools/run_evals.py:113-132` | **Confirmed the commands exist** and `--ablation none`, `--json`, `--no-publish`, `--trust-plugin` and `aggregate-result.json` match. Note that the eval help says "installed **and skills-dir** plugins both resolve", and Claude Code plugins auto-discover components without a manifest. So `plugin.json` is needed as the version source (AD-12, `run_evals.py`), not for these runs to work |
| "Nothing depends on `.claude-plugin/marketplace.json`" | skills `docs/creating-skills.md` "Plugin Manifest Discovery"; the file in the repo | **Not quite.** `npx skills` reads `marketplace.json` and `plugin.json` when they exist, and adds any `skills` paths they declare to discovery. The current file declares none (`source: "./"`), so it does no harm today. But the file still exists, and the Structural Seed still lists it |
| Claude Code `>=2.1.269` for `claude plugin eval` | Local binary 2.1.317 only | **Not checked as a minimum.** The flags exist on 2.1.317. No changelog or release note backs the 2.1.269 floor |

## Findings

### F1 — Wrong restore command (high)
**Where:** AD-1, last bullet ("contributors restore the BMad skills with `npx skills install`"). `.gitignore` line 2 repeats the mistake.
**Problem:** `npx skills install` is `add` and needs a source, so it errors out. The real command is `npx skills experimental_install`, which is a preview: "names, options, and behavior may change or be removed in any release without notice". Three more points from its docs: it restores only into `.agents/skills/`, "does not … create agent-specific links", and fails in CI unless every hash matches (`--frozen-lockfile` is the CI default). A Claude Code contributor who runs it gets no `.claude/skills/`.
**Fix:** Change the command to `npx skills experimental_install` (pinned, see F2), mark it [EXPERIMENTAL], and say how contributors get `.claude/skills/`, for example by re-running `npx skills add bmad-code-org/BMAD-METHOD -a claude-code` or with the BMad installer. Fix the `.gitignore` comment to match.

### F2 — Pinned `npx skills` version is out of date and not enforced (medium)
**Where:** AD-1 ("verified, vercel-labs/skills 1.7.4"), Stack table row `vercel-labs/skills (npx skills) | 1.7.4`.
**Problem:** Two releases have shipped since 1.7.4 (1.7.5 on 2026-11-02, 1.7.6 today). Users run `npx skills` without a version, so they always get the latest. The pin records what was tested, but nothing guards against a change in discovery or install behaviour. Between 1.7.4 and 1.7.6 the docs added `skills.sh.json` custom paths and lockfile flags. This review re-ran discovery and folder install on 1.7.6, and both still hold.
**Fix:** Change the row to "tested 1.7.6 (2026-11-03); users get latest". Add an install smoke check to the `rpcn-test-skills` install checks (AD-13) that runs `npx -y skills@latest add <repo> --list` and fails if anything other than `rpcn-*` shows up.

### F3 — "Only `rpcn-` skills are discoverable" rests on two folders out of about 55 (medium)
**Where:** AD-1, last bullet.
**Problem:** The rule names only `.claude/skills/` and `.agents/skills/`. `npx skills` also scans the root `SKILL.md`, `skills/.curated|.experimental|.system/`, about 55 agent folders, manifest-declared paths and `skills.sh.json` paths, and "if no skills are found in standard locations, a recursive search is performed". Gitignore covers the two BMad folders, but nothing stops a future tracked folder (for example a skill fixture under `evals/` or `tools/`, or an agent folder such as `.cursor/skills/`) from being offered to users.
**Fix:** Write the rule as an outcome: "`npx skills add <repo> --list` returns only `rpcn-*`". Enforce it with the smoke check in F2, or with a `validate_skills.py` rule that rejects any tracked `SKILL.md` outside `skills/rpcn-*/`.

### F4 — `marketplace.json` is described as inert but still lives in the repo (low)
**Where:** AD-1 bullet 3 ("Nothing depends on `.claude-plugin/marketplace.json`"), and the Structural Seed (`marketplace.json  plugin.json`).
**Problem:** `npx skills` does read the file for discovery. Keeping a marketplace manifest also invites the plugin-marketplace install that AD-1 now rules out (`/plugin marketplace add ajurcenk/rpcn-skills` would still work).
**Fix:** Delete `.claude-plugin/marketplace.json` and drop it from the Structural Seed. If it stays, say why, and add that it must never declare `skills` paths.

### F5 — Reason given for keeping `plugin.json` is partly assumed; lock already drifts (low)
**Where:** AD-1 bullet 3; Stack row `Claude Code >=2.1.269`; `skills-lock.json`.
**Problem:**
- `--plugin-dir` and `claude plugin eval` both resolve a directory with no manifest ("skills-dir plugins"), so they don't need `plugin.json`. The 2.1.269 floor is not backed by any source; only 2.1.317 was checked.
- In the repo, `bmad-retrospective` is in `.claude/skills/` and `.agents/skills/` but missing from `skills-lock.json`, so a restore would quietly leave it out.

**Fix:**
- Give `plugin.json`'s reason as "version source (AD-12) and plugin name for eval targets".
- Cite a changelog entry for 2.1.269, or change the floor to "tested 2.1.317".
- Regenerate `skills-lock.json` so it lists all 31 BMad skills.

## What holds up
- The repo is public, `main` is the default branch, and the install command works today.
- Installing one skill folder alone works. `rpcn-test` installs with its `scripts/rpcn_check.py` and `references/`, which matches AD-1's self-contained rule and AD-2's copy-in model.
- The gitignore exclusion works: live discovery of the remote returns only `rpcn-test`.
- The `claude plugin eval` flags that AD-13 and `tools/run_evals.py` use all exist on the current Claude Code.
