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
| `binary` | object \| null | `{"path": str, "version": str}` of the binary used; `null` when none was found or the arguments were bad, and always `null` for `hash` |
| `errors` | array | `[{"file": str\|null, "line": int\|null, "column": int\|null, "message": str}]`; `file` is `null` for errors not tied to a file |
| `data` | object | The subcommand's result, shape below; `{}` on a usage error |

`binary.path` is the executable that was found. For `rpk` it is the `rpk`
path, and the script runs it as `rpk connect`. `binary.version` has no leading
`v`.

## Exit codes

| Code | When |
|---|---|
| 0 | `ok` is `true` |
| 1 | A check failed: `lint` when the binary reports errors, `hash --check` when the hand-off is not ready |
| 2 | Usage or environment error: bad arguments, a missing input file, no binary, binary below 4.100.0, or a check that could not run (timeout, silent failure) |

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

## `lint`

```
rpcn_check.py lint <file>... [--resources <file>]... [--env-file <file>]
```

Options and files may be mixed in any order. The binary is always called as:

```
<binary> lint --deprecated --skip-env-var-check [--resources <f>]... [--env-file <f>] <file>...
```

- `--resources` once per unique file, in the order first given.
- Glob characters (`\ * ? [ ] { }`) in targets and resources files are escaped with
  `\`, so `a[1].yaml` lints exactly that file.
- `NO_COLOR=1` is set. `-v`, `--verbose`, `-` and `--chilled` are never passed.
- Every target, resources file and env file is checked before the binary runs.
  A missing one is exit 2, with one error per missing file (its `file` set);
  the binary is not run and `binary` is `null`.
- The lint is bounded to 60 s.

`data`:

```json
{"files": ["pipeline.yaml"], "error_count": 0}
```

| Field | Type | Meaning |
|---|---|---|
| `files` | array of str | The targets as given on the command line |
| `error_count` | int | Number of errors the binary reported; `0` when lint passed or did not run |

`data` is `{}` on a usage error (for example no targets).

**Errors.** `rpk connect lint` has no JSON output, so its text (stdout and
stderr) is parsed line by line:

- A line matching `^(?P<file>.+)\((?P<line>\d+),(?P<col>\d+)\) (?P<message>.*)$`
  becomes `{"file", "line", "column", "message"}`. The file part is greedy, so a
  path with parentheses splits on the last `(line,col)`. `file` is the path as
  the binary printed it, which is the target as given.
- Any other non-empty line becomes an error with `file`, `line` and `column`
  `null`.
- Errors are sorted by file, then line, then column, then message, with
  file-less errors last, so every RPCN version gives the same order.

**Exit codes:**

| Code | When |
|---|---|
| 0 | The binary exited 0 and printed nothing that parsed as an error |
| 1 | The binary reported errors (any parsed line, whatever its exit code) |
| 2 | No targets, a missing target, resources or env file, no usable binary, a timeout ("timed out"), or a non-zero exit with no output (the message gives the exit code) |

## `hash`

```
rpcn_check.py hash <file>...
rpcn_check.py hash --check <handoff.md>
```

Hashes files, or checks whether a hand-off file is still ready (AD-6). Neither
mode needs the Redpanda Connect binary: it is never looked up, and `binary` is
always `null`. Giving both files and `--check`, or neither, is a usage error
(exit 2, `data` `{}`).

### `hash <file>...`

`data`:

```json
{"hashes": [{"file": "orders.yaml", "sha256": "77c752d3…(64 hex)"}]}
```

| Field | Type | Meaning |
|---|---|---|
| `hashes` | array | One entry per file, in the order given (repeats kept) |
| `hashes[].file` | str | The path as given |
| `hashes[].sha256` | str | 64 lowercase hex characters over the file's exact bytes |

Every file is checked first. A missing file, or a path that is not a regular
file, is exit 2 with one error per such file (its `file` set) and `hashes`
`[]`. Exit 0 otherwise.

### `hash --check <handoff.md>`

Reads the hand-off header (the strict syntax in
`tools/shared/formats/handoff-header.md`), hashes each recorded input and
compares. Input `file` paths are resolved against the hand-off file's
folder, not the working directory.

`data`:

```json
{
  "artifact": "test-report",
  "status": "ready",
  "format": "test-report@1",
  "format_known": true,
  "inputs": [
    {"file": "orders.yaml", "recorded": "77c7…", "current": "77c7…", "state": "match"}
  ],
  "ready": true,
  "verdict": "pass",
  "pipeline_ready": true
}
```

| Field | Type | Meaning |
|---|---|---|
| `artifact` | str | The header's `artifact` |
| `status` | str | The header's `status`: `draft`, `ready` or `superseded` |
| `format` | str | The header's `format`, as written |
| `format_known` | bool | `format` is `<artifact>@<major>` for this `artifact`, the artifact is in `KNOWN_FORMATS` and the major equals its entry |
| `inputs` | array | One entry per header `inputs` item, in header order; `[]` for `inputs: []` |
| `inputs[].file` | str | The path as recorded (relative to the hand-off file's folder) |
| `inputs[].recorded` | str | The sha256 in the header |
| `inputs[].current` | str \| null | The file's sha256 now; `null` when it is missing |
| `inputs[].state` | str | `match`, `changed` or `missing` |
| `ready` | bool | `true` only when every input is `match`, `status` is `ready` and `format_known` is `true` |
| `verdict` | str \| null | For a test report, the first body line `**Verdict:** pass` or `**Verdict:** fail`, as `pass` or `fail`; `null` when there is no such line or `artifact` is not `test-report` |
| `pipeline_ready` | bool | `true` only when `ready` is `true`, an input whose `file` is `<pipeline>.yaml` (the header's `pipeline`) is `match`, and `verdict` is `pass`. A pipeline counts as ready only when this is `true` (AD-6) |

`verdict` and `pipeline_ready` do not change `ok`, `ready` or the exit code:
a `ready` report with the verdict `fail` still exits 0.

`ok` equals `ready`. When not ready, `errors` gives one entry per reason:

- an input `changed` or `missing`: `file` is the input path joined to the
  hand-off file's folder, `line` is `null`
- `status` not `ready`, or an unknown format: `file` is the hand-off file,
  `line` is that key's line

`KNOWN_FORMATS` is currently `{"design": 1, "test-report": 1}`.

**Exit codes:**

| Code | When |
|---|---|
| 0 | `ready` is `true` |
| 1 | Not ready: an input changed or is missing, `status` is not `ready`, or the format is unknown |
| 2 | The hand-off file is missing, unreadable or not UTF-8, an input exists but cannot be read (the error's `file` is that input), or its header does not follow the strict syntax. One error, with `file` the hand-off file (or the unreadable input), `line` the 1-based line at fault for a header error (otherwise `null`), and `data` `{}` |

Header errors include: no `---` on line 1, no closing `---`, a line that is
not `key: value`, an unknown or repeated key, an empty value, a `status`
outside `draft|ready|superseded`, an `inputs` item that is not exactly
`  - file: <path>` then `    sha256: <64 lowercase hex>`, an absolute input
path, and a missing required key (reported at the closing `---` line).
