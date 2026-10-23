# rpcn_check output schema, version 1

`rpcn_check.py` is the only code that runs `rpk connect` (AD-2, AD-4). Every
subcommand prints exactly one JSON object to stdout and nothing else. Later
subcommands add their own `data` shape here; a breaking change to any shape
bumps `schema`.

## Envelope

```json
{
  "schema": 1,
  "ok": true,
  "command": "binary",
  "binary": {"path": "/usr/local/bin/rpk", "version": "4.112.0"},
  "errors": [],
  "data": {}
}
```

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | Always `1` for this version of the contract |
| `ok` | bool | `true` only when the command succeeded |
| `command` | str | The subcommand that ran; the raw first argument on a usage error, `""` when none was given |
| `binary` | object \| null | `{"path": str, "version": str}` of the binary used; `null` when none was found or the arguments were bad |
| `errors` | array | `[{"file": str\|null, "line": int\|null, "column": int\|null, "message": str}]`; `file` is `null` for errors not tied to a file |
| `data` | object | The subcommand's result, shape below; `{}` on a usage error |

`binary.path` is the executable that was found. For `rpk` it is the `rpk`
path, and the script runs it as `rpk connect`. `binary.version` has no leading
`v`.

## Exit codes

| Code | When |
|---|---|
| 0 | `ok` is `true` |
| 1 | A check failed (reserved for `lint` and later subcommands) |
| 2 | Usage or environment error: bad arguments, no binary, binary below 4.100.0 |

## Binary lookup

1. `RPCN_BINARY`, then `EVAL_RPCN_BINARY`: a path or a command name. An
   override that does not work is an error; there is no fallback. A file
   named `rpk` runs as `rpk connect`.
2. `rpk` on PATH, run as `rpk connect`. If `rpk connect --version` fails, the
   lookup moves on and the error, if any, says to run `rpk connect install`.
3. `redpanda-connect` on PATH.

The version is read from the `Version:` line of `--version`, with a leading
`v` stripped. Versions below 4.100.0 exit 2 and still report `binary`.

## `binary`

```json
{
  "plugin_version": "0.1.0",
  "refs_version": null,
  "newer_than_refs": false,
  "headless": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `plugin_version` | str | The plugin version this copy was stamped with; matches `.claude-plugin/plugin.json` |
| `refs_version` | str \| null | The RPCN version the generated references were built from; `null` until references exist |
| `newer_than_refs` | bool | `true` when the binary is newer than `refs_version`; always `false` while `refs_version` is `null` |
| `headless` | bool | `true` when `RPCN_HEADLESS=1` or `EVAL_RPCN_HEADLESS=1` |

`data` is filled even when `ok` is `false`, so a skill can still tell whether
it runs headless.
