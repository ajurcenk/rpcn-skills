---
name: rpcn-test
description: 'Checks the Redpanda Connect binary this project will run against: finds rpk connect (or redpanda-connect), and reports its path and version against the supported 4.100.0 floor. Use when the user says "check my Redpanda Connect binary", "which rpk connect version do I have", "is Redpanda Connect installed", "test my rpk connect setup" or "rpcn-test". Not for writing, designing or deploying pipelines.'
compatibility: "Requires rpk with Redpanda Connect >= 4.100.0, and uv."
license: Apache-2.0
metadata:
  plugin-version: "0.1.0"
---

# rpcn-test

Finds the Redpanda Connect binary the user's pipelines will run against and
reports its path and version. All contact with Redpanda Connect goes through
the bundled check script; never run `rpk connect` or `redpanda-connect`
directly.

## Headless

Run headless when the prompt says the task runs unattended, headless or
non-interactively, or when the script reports `data.headless: true`. Headless
means: never ask the user anything, and end with the status block below.

## Step 1: Run the binary check

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py binary
```

If `${CLAUDE_SKILL_DIR}` is not expanded, the path is relative to the folder
that holds this SKILL.md: run `uv run <that folder>/scripts/rpcn_check.py binary`.

The script prints one JSON object:
`{"schema": 1, "ok", "command", "binary": {"path", "version"}, "errors", "data"}`.
Read it; do not parse anything else.

## Step 2: Report

- **Exit 0 (`ok: true`)**: tell the user the binary path (`binary.path`) and
  version (`binary.version`). If `binary.path` ends in `rpk`, say it runs as
  `rpk connect`. Mention the plugin version from `data.plugin_version`.
- **Exit 2 (`ok: false`)**: the environment can't run checks. Show each
  `errors[].message` as given, then the fix that matches:
  - nothing found: install rpk and run `rpk connect install`, or put
    `redpanda-connect` on PATH, or set `RPCN_BINARY` to the binary's path
  - `rpk connect` missing: run `rpk connect install`
  - version below 4.100.0: `rpk connect upgrade`, or
    `rpk connect install --connect-version <version>`
  - a usage message: the script was called wrongly; re-run exactly the
    command in Step 1
- The user can pin a specific binary with `RPCN_BINARY=<path>`; it wins over
  anything on PATH.

Never claim a binary or version that the JSON did not report.

## Next

After the user fixes the binary, re-run `rpcn-test` to confirm it.

## Status block (headless only)

End the reply with exactly one fenced `json` block, and nothing after it:

```json
{"status": "complete", "skill": "rpcn-test", "reason": null, "artifacts": [], "checks": {"lint": "skipped", "tests": "skipped"}, "open_questions": []}
```

- `status` is `"blocked"` when the script exits 2, with `reason` set to the
  first error message; otherwise `"complete"` with `reason: null`.
- Put anything you would have asked the user into `open_questions`.
