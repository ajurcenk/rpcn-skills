---
review: currency
target: ARCHITECTURE-SPINE.md (RPCN Skills, draft 2026-10-22)
lens: every committed decision web-researched or reality-checked, not asserted from training data
reviewed: 2026-10-22
verdict: mostly-current, 3 decisions need rework before build (AD-13, AD-8/AD-4 env, AD-5 pin)
---

# Currency review — RPCN Skills architecture spine

## Verdict

The named technologies all exist, and most versions and formats check out against live docs and the installed
binaries. The spine is spec-correct for the Agent Skills spec, `${CLAUDE_SKILL_DIR}`, plugin.json and marketplace.json.
It goes wrong where it assumes how `claude plugin eval` works. AD-13's trigger gate and lint gate do not fit the real
tool. AD-8's and AD-4's environment-variable signals never reach an eval run. The AD-5 "newest" pin was already three
releases old on the day the spine was written.

## Method

- **Live docs fetched:** code.claude.com/docs/en/plugin-evals, /skills, /plugins-reference (manifest),
  /plugins/marketplace-reference, agentskills.io/specification, and vercel-labs/skills docs.
- **GitHub release API** (`gh release`) for uv, redpanda-data/connect and vercel-labs/skills, plus the RPCN CHANGELOG
  for 4.112 to 4.115.
- **Local binaries:** `rpk connect` 4.112.0, a locally built `redpanda-connect` v4.100.0, the official
  `redpanda-connect_4.100.0_linux_amd64` release tarball, uv 0.12.24 and Claude Code 2.1.309. I ran the `list`,
  `lint`, `blobl` and `test` help, real lint and blobl failures, and a PEP 723 script under `uv run`.

## Spot-check ledger

| # | Claim in spine / memlog | Status | Evidence |
|---|---|---|---|
| 1 | `claude plugin eval` exists, needs Claude Code >=2.1.269. Cases are `prompt.md` + `case.yaml` + `graders/*.md`. Six grader types. 3 runs by default. A no-plugin baseline arm. Results in `evals/results/<ts>/` | **Confirmed** | https://code.claude.com/docs/en/plugin-evals; `claude plugin eval --help` (2.1.309) |
| 2 | A `tool_used` grader can assert that a specific Skill was invoked | **Confirmed, with a scoring caveat** | `type: tool_used`, `tool: Skill`, `input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<name>"'`. But in a two-arm run "Every `tool_used` grader whose `tool` is `Skill`" is **excluded from the score** in both arms and shown only as a "plugin-fired indicator", unless the grader sets `arm: both` or the run uses `--ablation none`. Negatives are written as `min: 0, max: 0` (plugin-evals, "Compare against a no-plugin baseline" and "Grader types") |
| 3 | Eval gate "trigger accuracy below 90%" | **Not supported as written** | `--threshold` is per case ("Any case below it makes the command exit 1"). No suite-level trigger-accuracy figure exists. It has to be computed from `aggregate-result.json` (`schemaVersion: 1`, per-run grader results) |
| 4 | Lint gate runs over "every file each case produced" | **Not supported as written** | Each run uses a temporary workspace. `--keep-temp` keeps it only "for debugging". `file_exists` sees only files created during the run. No artifact export is documented |
| 5 | Eval runs can use `RPCN_HEADLESS=1` / `RPCN_BINARY` | **Contradicted** | `env` keys "must match `EVAL_[A-Z0-9_]*`; any other key fails the run". Only an allowlist of the shell environment (PATH, locale, proxy, model-provider vars, `ANTHROPIC_*`, `CLAUDE_CODE_*`, `EVAL_*`) reaches the run |
| 6 | Skills can run `uv`/`rpk` inside evals | **Confirmed, with conditions** | Bash must be granted with `--allow-tools` and then runs under the OS sandbox. HOME is a temporary directory and the real home is unreadable. Linux needs `bubblewrap` and `socat`, and native Windows is refused. **Unverified:** whether `rpk` in `~/.local/bin` (with its `.rpk.managed-connect` beside it) can run under the sandbox. With a temporary HOME and no sandbox, `rpk connect --version` still works (tested) |
| 7 | Coexistence fixture "with both coexisting skill sets installed" | **Partly feasible** | In a run, "other installed plugins ... are absent". The case `plugins:` field takes plugin directories relative to the case, so the coexisting plugins must be vendored as directories |
| 8 | `${CLAUDE_SKILL_DIR}` substituted in the SKILL.md body, not in the Bash env | **Confirmed** | /docs/en/skills: substituted "in the skill's markdown content, and Bash rules in the `allowed-tools` frontmatter". Plugin variables "aren't present in the environment of commands Claude runs through the Bash tool" (plugins-reference) |
| 9 | Agent Skills `metadata` accepts `rpcn-refs-version` | **Confirmed** | agentskills.io: "A map from string keys to string values", and keys should be reasonably unique. Claude Code: a free-form map that it doesn't act on. The value must be a quoted string, which the spine already does |
| 10 | `compatibility` <=500 chars | **Confirmed** | agentskills.io and Claude Code skills docs. The spine's string is about 70 characters |
| 11 | plugin.json `"skills": "./skills/"` | **Valid but redundant** | `skills` "Adds to the default `skills/` scan", so naming `./skills/` scans the default folder a second time. Only `name` is required |
| 12 | marketplace.json `source: "./"` | **Confirmed, with a caveat** | Relative paths must start with `./`, and `"."` means the root. They resolve only for `github`/`git`/`file`/`directory` marketplace sources, not a `url` source |
| 13 | uv 0.13.5 | **Confirmed** | Tag `0.13.5`, published 2026-10-22T01:35Z (Latest). The local machine has 0.12.24 |
| 14 | PEP 723 `requires-python = ">=3.10"` under `uv run` | **Confirmed** | Tested locally: uv used Python 3.12.10. `requires-python` is a PEP 723 field |
| 15 | `rpk connect list --format jsonschema` | **Confirmed** | 4.100.0 and 4.112.0. Help lists `text, json, jsonschema, cue` |
| 16 | `json-full` format | **Exists, undocumented** | Missing from `--help` on both versions but works. Output starts `{"version":"4.112.0","date":...,"config":[...]` |
| 17 | `rpk connect lint` has no JSON output | **Confirmed** | `--format` → "flag provided but not defined". Output looks like `<path>(4,1) field foo not recognised` with exit 1. The 4.113 to 4.115 changelog has no lint change |
| 18 | Lint flags `--deprecated`, `--skip-env-var-check`, `--resources`, `--env-file`; blobl `--file`, `--env-file` | **Confirmed** | Help on 4.100.0 and 4.112.0. A blobl parse error exits 1 with an empty stdin |
| 19 | Redpanda Connect 4.100.0 and 4.112.0 exist | **Confirmed** | v4.100.0 published 2026-07-09; v4.112.0 published 2026-10-02 |
| 20 | 4.112.0 is the "newest pinned" version | **Stale** | v4.113.0 (10-09), v4.113.1 (10-14), v4.114.0 (10-16) and v4.115.0 (10-22, Latest) were all out on the spine's date |
| 21 | Version taken from the `Version:` line | **Confirmed, with a caveat** | Official binaries print `Version: 4.100.0`. A local source build prints `Version: v4.100.0`, so the parser must strip an optional `v` |
| 22 | `npx skills` 1.7.4 discovers `skills/<name>/SKILL.md`, has `-s/--skill` and `--copy` | **Confirmed** | v1.7.4 is Latest (2026-10-19); vercel-labs/skills docs/commands.md and creating-skills.md |
| 23 | Claude Code `>=2.1.269` | **Confirmed** | Installed: 2.1.309 |

## Findings

### F1 — HIGH — AD-13: the trigger gate as written cannot fail CI the way it claims

- **Issue:**
  - `tool_used: Skill` graders are excluded from the score in the default two-arm run.
  - `--threshold` gates each case, not a suite-wide accuracy.
  - So "CI fails when trigger accuracy is below 90%" has no mechanism behind it.
  - Near-miss negatives also need `min: 0, max: 0`, and those must be marked `arm: both` to count.
- **Fix:** AD-13 should state the mechanism. Either:
  - run the trigger cases as their own invocation with `--ablation none`, so nothing is excluded, or
  - mark trigger graders `arm: both`.

  Then compute trigger accuracy in `tools/` from `aggregate-result.json` (per-run grader results, `schemaVersion: 1`)
  and fail below 0.90. Keep the baseline-Δ run for quality cases.
- **Source:** https://code.claude.com/docs/en/plugin-evals (sections "Compare against a no-plugin baseline", "Grader
  types", "Command options", "JSON result")

### F2 — HIGH — AD-13 lint gate: case outputs are not persisted

- **Issue:**
  - Runs happen in temporary sandbox workspaces.
  - `--keep-temp` is a debugging flag that prints paths, and no artifact export is documented.
  - So `lint_eval_outputs.py` "over every file each case produced" has no defined input.
- **Fix:** pick one and write it into AD-13:
  - (a) Run with `--keep-temp --json`, parse the printed sandbox paths, and treat that as fragile.
  - (b) Preferred: the case prompt asks the skill to run `rpcn_check.py lint` itself. Grade it with
    `tool_used` (`tool: Bash`, `input_match: 'rpcn_check\.py (lint|blobl)'`) plus a `regex`/`llm` grader on the AD-8
    status block `checks.lint == "pass"`.
  - (c) Keep the independent re-lint by having the run write its outputs into `add_dirs`. This needs checking: the
    docs say `add_dirs` grant read access only.

  Also grant Bash narrowly, for example `--allow-tools "Bash(uv run *)"`.
- **Source:** https://code.claude.com/docs/en/plugin-evals ("Seed the workspace", "How runs are isolated",
  `--keep-temp`, "Tools are denied ... or Bash won't run")

### F3 — HIGH — AD-8 / AD-4: `RPCN_HEADLESS` and `RPCN_BINARY` never reach an eval run

- **Issue:**
  - The case `env` accepts only `EVAL_[A-Z0-9_]*` keys.
  - The inherited environment is an allowlist that leaves both variables out.
  - So the headless env trigger cannot be tested by the evals (R17).
  - And `RPCN_BINARY` cannot pick the pinned binary inside evals. CI would have to fall back on PATH order.
- **Fix:**
  - Rename the variables to `EVAL_`-compatible aliases, or also accept `EVAL_RPCN_HEADLESS` and `EVAL_RPCN_BINARY`.
  - Or rely on the prompt-phrase trigger and PATH order in evals, and say so in AD-8, AD-4 and AD-13.
  - Resolve the AD-8 `[ASSUMPTION]` this way.
- **Source:** https://code.claude.com/docs/en/plugin-evals (the `env` row of the prompt.md fields table)

### F4 — MEDIUM — AD-5 / Stack: "newest pin" 4.112.0 was three releases old on 2026-10-22

- **Issue:**
  - v4.115.0 was released 2026-10-22, after v4.114.0 (10-16), v4.113.1 (10-14) and v4.113.0 (10-09).
  - Releases come about weekly, so AD-14's "a scheduled job ... opens a PR within one week" means a pin-bump PR
    nearly every week.
  - Each bump also widens the CI matrix unless AD-5 says the newest pin *replaces* the previous one, keeping a
    floor plus the newest.
- **Fix:**
  - Pin 4.115.0, or record why 4.112.0 was chosen.
  - Restate AD-5 as "floor 4.100.0 + newest", with the newest pin rolling forward.
  - Name the release flavour: the tarball set includes the plain, `-cgo`, `-cloud` and `-fips` builds, and their
    component sets differ, which affects `gen_refs`.
- **Source:** https://github.com/redpanda-data/connect/releases (v4.115.0 Latest); `gh release view` output

### F5 — MEDIUM — AD-13 coexistence fixture and the eval sandbox environment

- **Issue:**
  - Other installed plugins are absent in eval runs, so the coexisting `redpanda-data/connect` and
    `redpanda-data/skills` must be vendored and listed in each case's `plugins:`.
  - When Bash is granted, the home directory is unreadable and Linux needs `bubblewrap` and `socat`.
  - It is unverified whether `rpk` and uv-managed Pythons under `$HOME` can run inside the sandbox.
- **Fix:**
  - State in AD-13 how the fixture is built: pinned checkouts referenced from `plugins: [...]`.
  - State in AD-14 that CI installs `rpk`/`redpanda-connect` and `uv` outside `$HOME` (for example
    `/usr/local/bin`), installs `bubblewrap` and `socat`, and runs one smoke eval to prove `rpk connect --version`
    works under the sandbox.
- **Source:** https://code.claude.com/docs/en/plugin-evals ("How runs are isolated", "Grant tools", "prompt.md
  fields: plugins"); https://code.claude.com/docs/en/sandboxing

### F6 — LOW — AD-1: `"skills": "./skills/"` in plugin.json is redundant

- **Issue:** the manifest `skills` key "Adds to the default `skills/` scan", so `./skills/` names the default folder
  twice.
- **Fix:** drop the key. Only `name` is required. Keep `marketplace.json` `source: "./"`, and note that it resolves
  only for git/github/file/directory marketplace sources.
- **Source:** https://code.claude.com/docs/en/plugins-reference (Fields: `skills`; "How each key combines with its
  default location"); https://code.claude.com/docs/en/plugins/marketplace-reference ("Relative path plugin source")

### F7 — LOW — AD-11: `json-full` is an undocumented format

- **Issue:** `--format json-full` works on 4.100.0 and 4.112.0 but is not in `--help`, which lists only
  `text, json, jsonschema, cue`. It could change without notice.
- **Fix:**
  - Have `gen_refs.py` assert that the output's top-level `version` equals the pin.
  - Have CI fail loudly if the format disappears.
  - Mention in AD-11 that the format is undocumented.
- **Source:** local `rpk connect list --help` on 4.112.0 and on the official 4.100.0 tarball

### F8 — LOW — AD-4: version parsing and the lint output contract

- **Issue:**
  - A source-built `redpanda-connect` prints `Version: v4.100.0`. Official builds print it without the `v`.
  - `lint` has no JSON mode, so `rpcn_check.py` must parse lines like `<path>(line,col) message` itself.
  - `blobl --file` runs the mapping, so lint use must feed an empty stdin.
  - The spine's `errors` shape is right, but the parsing contract is not written down.
- **Fix:**
  - In AD-4, state: strip an optional leading `v`.
  - Parse lint lines with the regex `^(?P<file>.+)\((?P<line>\d+),(?P<col>\d+)\) (?P<msg>.*)$` and treat anything
    else as a file-level error.
  - Call blobl with `</dev/null`, so that exit 1 means a parse failure.
- **Source:** local runs (`rpk connect lint`, `rpk connect blobl -f`); the official v4.100.0 release tarball

## Confirmed with no change needed

- The Agent Skills `name`, `description` (<=1024), `compatibility` (<=500), `metadata` (string to string; a
  `rpcn-refs-version` key with a quoted value is fine) and one-level file references.
  https://agentskills.io/specification
- `${CLAUDE_SKILL_DIR}` is body-substitution only, which matches AD-3's fallback sentence.
  https://code.claude.com/docs/en/skills
- uv 0.13.5 (2026-10-22) and PEP 723 `requires-python`. https://github.com/astral-sh/uv/releases/tag/0.13.5
- `npx skills` 1.7.4 with `-s/--skill` and `--copy`. https://github.com/vercel-labs/skills
- Claude Code >=2.1.269 for `claude plugin eval`.

## Unconfirmed / open

- Whether `rpk` and `.rpk.managed-connect` under `~/.local/bin` run inside the plugin-eval OS sandbox (F5).
- Whether `--keep-temp` paths appear in `--json` output in a form a script can parse (F2a).
- Whether `add_dirs` can be written to (F2c). The docs say read-only.
