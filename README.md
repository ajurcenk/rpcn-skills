# rpcn-skills

Agent skills for building and running [Redpanda Connect](https://docs.redpanda.com/redpanda-connect/)
pipelines. Every skill checks its work against your own `rpk connect` binary
through a bundled check script, so results match the version you actually run.

Skills in this release:

| Skill | What it does |
|---|---|
| `rpcn-author` | Writes a new pipeline from a plain request, using only the components and fields your binary reports, and lints it until clean |
| `rpcn-test` | Lints a pipeline, explains each error with a proposed fix and writes a test report; also finds your Redpanda Connect binary and reports its path and version |

## Install

With `npx skills`, for Claude Code or any agent that supports [Agent Skills](https://agentskills.io):

```bash
npx skills add ajurcenk/rpcn-skills
```

Then ask your agent to "write me a Redpanda Connect pipeline" or "lint my pipeline".

## Requirements

- [rpk](https://docs.redpanda.com/current/get-started/rpk-install/) with Redpanda Connect
  4.100.0 or newer (`rpk connect install`), or a `redpanda-connect` binary on PATH
- [uv](https://docs.astral.sh/uv/), which runs the bundled scripts
- Linux or macOS

To use a specific binary, set `RPCN_BINARY` to its path.

## Development

```bash
uv run tools/shared/rpcn_check/tests/test_rpcn_check.py
uv run tools/tests/test_sync_shared.py
```

`tools/shared/rpcn_check/rpcn_check.py` is the canonical check script. Files
under `tools/shared/` are copied into each skill as listed in its
`skills/<skill>/shared.txt`; never edit a copy by hand. After changing a
source, sync the copies, and check them the way CI does:

```bash
uv run tools/sync_shared.py          # copy every listed file into its skill
uv run tools/sync_shared.py --check  # exit 1 if any copy is missing or differs
```

The output contract is in
[`tools/shared/rpcn_check/SCHEMA.md`](tools/shared/rpcn_check/SCHEMA.md).

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [SOURCES.md](SOURCES.md).
