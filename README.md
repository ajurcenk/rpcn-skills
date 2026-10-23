# rpcn-skills

Agent skills for building and running [Redpanda Connect](https://docs.redpanda.com/redpanda-connect/)
pipelines. Every skill checks its work against your own `rpk connect` binary
through a bundled check script, so results match the version you actually run.

Skills in this release:

| Skill | What it does |
|---|---|
| `rpcn-test` | Finds your Redpanda Connect binary and reports its path and version |

## Install

Claude Code, as a plugin:

```bash
claude plugin marketplace add ajurcenk/rpcn-skills
claude plugin install rpcn-skills@rpcn-skills
```

Any agent that supports [Agent Skills](https://agentskills.io), with `npx skills`:

```bash
npx skills add ajurcenk/rpcn-skills
```

Then ask your agent to "check my Redpanda Connect binary".

## Requirements

- [rpk](https://docs.redpanda.com/current/get-started/rpk-install/) with Redpanda Connect
  4.100.0 or newer (`rpk connect install`), or a `redpanda-connect` binary on PATH
- [uv](https://docs.astral.sh/uv/), which runs the bundled scripts
- Linux or macOS

To use a specific binary, set `RPCN_BINARY` to its path.

## Development

```bash
uv run tools/shared/rpcn_check/tests/test_rpcn_check.py
```

`tools/shared/rpcn_check/rpcn_check.py` is the canonical check script; each
skill carries a byte-identical copy in `scripts/`. The output contract is in
[`tools/shared/rpcn_check/SCHEMA.md`](tools/shared/rpcn_check/SCHEMA.md).

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [SOURCES.md](SOURCES.md).
