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
| 1 | A check failed: `lint` when the binary reports errors, `hash --check` when the hand-off is not ready, `blobl` when the mapping does not parse, a line failed or a sample's output differs, `fields` when the component does not exist, `run` when the binary exits non-zero or there is a runtime error, `test` when a case or target fails or no tests were found |
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
  `null`, but only when the binary exited non-zero. When it exited 0, such
  lines are ignored: a clean lint can still print an `rpk` update notice.
- Errors are sorted by file, then line, then column, then message, with
  file-less errors last, so every RPCN version gives the same order.

**Exit codes:**

| Code | When |
|---|---|
| 0 | The binary exited 0 and printed no `<file>(<line>,<col>) <message>` line (other lines are ignored) |
| 1 | The binary reported errors: a `<file>(<line>,<col>) <message>` line whatever its exit code, or any non-empty line with a non-zero exit |
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
  "format": "test-report@2",
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
| `format_known` | bool | `format` is `<artifact>@<major>` for this `artifact`, the artifact is in `KNOWN_FORMATS` and the major is one of its entries |
| `inputs` | array | One entry per header `inputs` item, in header order; `[]` for `inputs: []` |
| `inputs[].file` | str | The path as recorded (relative to the hand-off file's folder) |
| `inputs[].recorded` | str | The sha256 in the header |
| `inputs[].current` | str \| null | The file's sha256 now; `null` when it is missing |
| `inputs[].state` | str | `match`, `changed` or `missing` |
| `ready` | bool | `true` only when every input is `match`, `status` is `ready` and `format_known` is `true`, and, for a `test-report`, the first input is the pipeline file `<pipeline>.yaml` or `<pipeline>.yml` (compared after path normalisation) |
| `verdict` | str \| null | For a test report, the first body line `**Verdict:** pass` or `**Verdict:** fail`, as `pass` or `fail`; `null` when there is no such line or `artifact` is not `test-report` |
| `pipeline_ready` | bool | `true` only when `ready` is `true`, the first input's `file` is `<pipeline>.yaml` or `<pipeline>.yml` (the header's `pipeline`) and it is `match`, and `verdict` is `pass`. A pipeline counts as ready only when this is `true` (AD-6) |

`verdict` and `pipeline_ready` do not change `ok`, `ready` or the exit code:
a `ready` report with the verdict `fail` still exits 0.

`ok` equals `ready`. When not ready, `errors` gives one entry per reason:

- an input `changed` or `missing`: `file` is the input path joined to the
  hand-off file's folder, `line` is `null`
- `status` not `ready`, or an unknown format: `file` is the hand-off file,
  `line` is that key's line
- a `test-report` whose `inputs` is empty or whose first input is not
  `<pipeline>.yaml` or `<pipeline>.yml`: `file` is the hand-off file, `line`
  is the `inputs` line

`KNOWN_FORMATS` is currently `{"design": (1,), "test-report": (1, 2)}`: rpcn-test
writes `test-report@2` (story 2.8 added its Dry run section), and a
`test-report@1` report stays readable.

**Exit codes:**

| Code | When |
|---|---|
| 0 | `ready` is `true` |
| 1 | Not ready: an input changed or is missing, `status` is not `ready`, the format is unknown, or a test report's first input is not its pipeline file |
| 2 | The hand-off file is missing, unreadable or not UTF-8, an input exists but cannot be read (the error's `file` is that input), or its header does not follow the strict syntax. One error, with `file` the hand-off file (or the unreadable input), `line` the 1-based line at fault for a header error (otherwise `null`), and `data` `{}` |

Header errors include: no `---` on line 1, no closing `---`, a line that is
not `key: value`, an unknown or repeated key, an empty value, a `status`
outside `draft|ready|superseded`, an `inputs` item that is not exactly
`  - file: <path>` then `    sha256: <64 lowercase hex>`, an absolute input
path, and a missing required key (reported at the closing `---` line).

## Shared rules for `blobl`, `list`, `fields`, `run` and `test`

- They use the binary lookup and the 4.100.0 floor above; a missing or too old
  binary is exit 2.
- Every file argument (mapping, config, target, `--input`, `--samples`,
  `--resources`, `--env-file`) is checked before the binary runs. A missing one is exit 2,
  with one error per missing file (its `file` set); the binary is not run and
  `binary` is `null`.
- Glob characters in `test` targets and in every `--resources` file are
  escaped as in `lint`. The `run` config and the `blobl` mapping are paths,
  not globs, and are passed as given.
- `--resources` is passed once per unique file, in the order first given,
  then `--env-file`.
- `NO_COLOR=1` is set. `-v`, `--verbose`, `-` and `--chilled` are never passed.
- Every call except `run` is bounded to 60 s; a timeout kills the whole
  process group and is exit 2 with a "timed out" error.
- Output is decoded as UTF-8, with bad bytes replaced.
- `data` keeps its shape on every error except a usage error, where it is `{}`.

## `blobl`

```
rpcn_check.py blobl <mapping> [--input <file>] [--env-file <file>]
rpcn_check.py blobl <mapping> --samples <name>.samples.json [--env-file <file>]
```

`--input` and `--samples` are mutually exclusive (a usage error, exit 2).

The binary is called as:

```
<binary> blobl [--env-file <f>] --file <mapping> [--input <file>]
```

With no `--input`, stdin is empty, so only the mapping is parsed. The input
file holds one JSON document per line (split on `\n`, as the binary does).

`data`:

```json
{
  "mapping": "double.blobl",
  "results": [
    {"line": 1, "output": "{\"doubled\":2}", "error": null},
    {"line": 2, "output": null, "error": "unable to reference message as structured …"}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `mapping` | str | The mapping file as given |
| `results` | array | One entry per input line, in order; `[]` with no `--input` or when the mapping does not parse |
| `results[].line` | int | 1-based line number in the input file |
| `results[].output` | str \| null | What the mapping printed for this line, without the final newline; `null` when it failed. A deleted message is `""` |
| `results[].error` | str \| null | The binary's `failed to execute map: <msg>` for this line, without that prefix; `null` when it succeeded |

The binary prints each line's output on stdout and each failure on stderr.
Both are read from one pipe, so they stay in input order. When the number of
printed lines differs from the number of input lines (an output that spans
several lines), each input line is run again on its own, as stdin, to match
results to lines exactly. The first run and the re-runs share one 60 s budget.
A re-run that exits non-zero without a `failed to execute map:` line gives
that line an `error` of `blobl exited <code>: <output tail>`.

**Errors.** A mapping that does not parse
(`failed to parse mapping: line L char C: <msg>`) gives one error with `file`
the mapping, `line` L, `column` C and `message` `<msg>`. Each failed input
line gives one error with `file` the input file, `line` that line, `column`
`null` and `message` the line's `error`. Any other non-zero exit gives one
error with `file` the mapping and the output tail, or "exited <code> with no
output" when it printed nothing.

**Exit codes:**

| Code | When |
|---|---|
| 0 | Every input line succeeded (or there was no input and the mapping parsed) |
| 1 | The mapping does not parse, any input line failed, or the binary exited non-zero with output |
| 2 | A missing file, no usable binary, a timeout, or a non-zero exit with no output |

### `blobl --samples`

Added in story 2.7, without a schema bump: the command, `data` and exit codes
without `--samples` are unchanged. The samples file follows
`tools/shared/formats/samples-format.md`.

1. The samples file is read and validated before the binary is looked up.
   It must be UTF-8 JSON with no repeated key and no `NaN`, `Infinity` or
   `-Infinity` (an error naming the key), and follow the format's
   rules. Its `mappings` must have a key equal to the mapping's file name
   (`os.path.basename(<mapping>)`). Otherwise exit 2, with one error whose
   `file` is the samples file: for a JSON syntax error `line` and `column`
   are the position, otherwise they are `null` and the message names the
   key, such as `mappings["orders.enrich.blobl"][1]: needs exactly one of
   output and deleted`. `binary` is `null`.
2. That mapping's samples are run as one input file, one compact JSON
   `input` per line, in the samples' order, exactly as `--input` runs
   (the fallback and budget included).
3. An empty output is a deleted message, which passes only for
   `deleted: true`. When the expected `output` is a JSON string, it is
   compared with the output text exactly as printed, unparsed: the binary
   prints a string root without quotes, so `root = "123"` prints `123`, and
   `format_json()` prints JSON text. Otherwise the output is parsed as JSON
   and compared as a JSON value: `1` equals `1.0`, `true` never equals `1`,
   key order does not count, and an output that is not JSON fails.

`data` adds four keys to the shape above:

```json
{
  "mapping": "pipes/orders.enrich.blobl",
  "results": [{"line": 1, "output": "{\"id\":\"o1\",\"total_cents\":125}", "error": null}],
  "samples_file": "pipes/orders.samples.json",
  "samples": [
    {"name": "small order", "input": "{\"id\":\"o1\",\"total\":12.5}",
     "expected": "{\"id\":\"o1\",\"total_cents\":1250}", "deleted": false,
     "actual": "{\"id\":\"o1\",\"total_cents\":125}", "error": null, "result": "fail"}
  ],
  "passed": 0,
  "failed": 1
}
```

| Field | Type | Meaning |
|---|---|---|
| `results` | array | As above; `line` is the sample's 1-based position in its mapping's array |
| `samples_file` | str | The samples file as given |
| `samples` | array | One entry per sample of this mapping, in order; `[]` when the mapping does not parse or the run failed |
| `samples[].name` | str | The sample's `name` |
| `samples[].input` | str | The sample's `input` as compact JSON with sorted keys |
| `samples[].expected` | str \| null | The expected `output` as compact JSON with sorted keys; `null` for `deleted: true` |
| `samples[].deleted` | bool | `true` when the sample expects the message deleted |
| `samples[].actual` | str \| null | What the mapping printed, as in `results[].output`; `null` when it failed |
| `samples[].error` | str \| null | As in `results[].error` |
| `samples[].result` | str | `pass` or `fail` |
| `passed`, `failed` | int | Number of samples that passed and failed; both `0` when none ran |

**Errors.** One per failed sample, with `file` the samples file, `line` and
`column` `null`, and `message` `sample '<name>': expected <expected>, got
<actual>` (or the line's error, or a note that the message was or was not
deleted). A mapping that does not parse gives the parse error as above.

**Exit codes:** 0 when every sample passed; 1 when any sample failed or the
mapping does not parse; 2 for an invalid samples file, no entry for the
mapping, and every exit 2 above.

## `list`

```
rpcn_check.py list <category> [--status stable|beta|experimental]
```

The binary is called as `<binary> list --format json [--status <s>] <category>`.

`data`:

```json
{"category": "inputs", "components": ["amqp_0_9", "generate", "stdin"]}
```

| Field | Type | Meaning |
|---|---|---|
| `category` | str | The category as given |
| `components` | array of str | Component names, in the binary's order; `[]` on an error |

`category` is first checked against the top-level keys of
`<binary> list --format json` with no category, for example `inputs`, `processors`, `outputs`, `caches`, `buffers`,
`metrics`, `tracers`, `rate-limits`, `scanners`, `bloblang-functions` or
`bloblang-methods`. An unknown category is exit 2, and the error names the
known categories. A known category that the `--status` filter leaves absent
from the output gives `components` `[]` and exit 0. A `--status` outside the
three values is a usage error.

**Exit codes:** 0 when listed; 2 for an unknown category, invalid JSON from
the binary, a non-zero exit, no usable binary or a timeout.

## `fields`

```
rpcn_check.py fields <category> <component>
```

The binary is called as `<binary> list --format json-full <category>`. The
component is found by `name` in that category, and its `config.children`
tree is flattened. This reads the installed binary, so it is the check for
whether a field exists in the user's version (R2).

`data`:

```json
{
  "category": "inputs",
  "component": "generate",
  "status": "stable",
  "fields": [
    {"path": "mapping", "type": "string", "kind": "scalar", "required": true,
     "advanced": false, "deprecated": false, "secret": false,
     "description": "A Bloblang mapping to use for generating messages."},
    {"path": "interval", "type": "string", "kind": "scalar", "required": false, "default": "1s",
     "advanced": false, "deprecated": false, "secret": false,
     "description": "The time interval at which messages should be generated, …"}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `category`, `component` | str | As given |
| `status` | str \| null | The component's status: `stable`, `beta`, `experimental` or `deprecated`; `null` when no component was found |
| `fields` | array | Every field, parents before their children, in the binary's order; `[]` on an error |
| `fields[].path` | str | Dotted path from the component's config: `tls.enabled`. Children of an array field sit under `path[]` (`tls.client_certs[].password`), of a 2D array under `path[][]`, of a map under `path.*`. When the component's config itself is an array (for example the `switch` processor) every path starts with `[].` |
| `fields[].type` | str | The binary's `type`: `string`, `int`, `bool`, `object`, … |
| `fields[].kind` | str | The binary's `kind`: `scalar`, `array`, `2darray`, `map` (may be `""`) |
| `fields[].required` | bool | `true` when the field has no `default` and is not `is_optional` |
| `fields[].default` | any | The default value; the key is absent when there is none |
| `fields[].advanced`, `deprecated`, `secret` | bool | `true` only when `is_advanced`, `is_deprecated` or `is_secret` is present and `true` (json-full leaves them out otherwise) |
| `fields[].description` | str | The first non-empty line of the description; `""` when there is none |

A component that has no config fields (its config is a plain value, or an
object with no children) has `fields` `[]`.

**Unknown component.** Exit 1, one error "component '<name>' not found in
<category>", `status` is `null`, `fields` is `[]`, and `data` also has
`components`, which holds the names in that category sharing at least the first
three characters with `<component>`, longest shared prefix first, then by
name; `[]` when none do.

The category is checked as in `list` before `json-full` is read.

**Exit codes:** 0 when found; 1 when the component does not exist; 2 for an
unknown category (as in `list`; `config` is not a category), invalid JSON, a
non-zero exit, no usable binary or a timeout.

## `run`

```
rpcn_check.py run <config> [--input <file> [--bounded]] [--resources <file>]... [--env-file <file>] [--timeout <s>]
```

A bounded dry run (AD-4). `--bounded` requires `--input`. The binary is called as:

```
<binary> run --set http.enabled=false [<bounded flags>] [--resources <f>]... [--env-file <f>] <config>
```

`--input` is passed as stdin; with no `--input`, stdin is empty, so a
`stdin` input ends at once. `--timeout` is a positive number of seconds,
default 10. On timeout the whole process group is killed.

### `run --bounded`

Added in story 2.8, without a schema bump: it is additive to AD-4's `run`.
`--bounded` adds these `<bounded flags>`, each its own `--set`, because the
binary splits a `--set` value on commas (`SOURCES.md`), so no value has one:

```
--set 'input={"stdin":{}}' --set 'output={"stdout":{}}'
--set logger.format=logfmt --set logger.level=info
--set 'output.processors=[{"mapping":"<marker mapping>"}]'
```

- The config's `input` is replaced by `stdin` and its `output` by `stdout`:
  a `--set` whose value is an object replaces the whole value at that path,
  on 4.100.0 and 4.115.0 (`SOURCES.md`). The input's and output's own
  processors, and any `switch`, `fallback` or `broker` output, go with them,
  so only `pipeline.processors` run. The pipeline file is never edited
  (AD-6).
- The logger is pinned, so a config with `logger.format: json` or
  `logger.level: none` still logs errors as logfmt.
- The marker mapping (`RUN_MARKER_MAPPING`) runs as the output's processor.
  A message that reaches it still errored (`errored()`) is replaced by one
  line `{"__rpcn_check_unhandled_error__":{"error":<error()>,"input":<content().string()>}}`;
  every other message passes unchanged.

`--bounded` without `--input` is exit 2 with a usage error and `data` `{}`.
Resources (caches, processors) are not replaced, so a pipeline that calls an
outside service still calls it; the caller decides not to run those.

`data`:

```json
{
  "config": "pipeline.yaml",
  "outputs": ["{\"doubled\":2}", "{\"doubled\":6}"],
  "exit": 0,
  "runtime_errors": []
}
```

| Field | Type | Meaning |
|---|---|---|
| `config` | str | The config file as given |
| `outputs` | array of str | The binary's stdout, one entry per line, in the order printed (logs go to stderr and are not included), without marker lines. On a timeout, the lines printed before it |
| `exit` | int \| null | The binary's exit code; `null` on a timeout or when it did not run |
| `runtime_errors` | array | `[{"path": str\|null, "message": str, "input": str\|null}]`, in the order printed; `[]` when there are none. Added in story 2.8; see below |

The order of `outputs` is the binary's: a pipeline that processes messages in
parallel may print them in any order. A processor that fails on a message
logs the error and passes the message on unchanged, flagged as failed.

**Runtime errors.** When a processor fails on a message (a mapping meets a
field of the wrong type, for example), the binary logs
`level=error msg="<error>" … label=<label> path=<path>` and still exits 0. It
logs the same line when a later `catch` handles the error (`SOURCES.md`,
4.100.0 and 4.115.0), so a log line alone does not say the message failed.
Log lines are parsed as logfmt (quoted values unescaped); `info`, `warn`
and path-less `error` lines are ignored.

- **With `--bounded`:** only unhandled errors count. Each marker line is
  moved out of `outputs` into `runtime_errors`: `message` is its `error`,
  `input` its `input` (the message as it reached the output), and `path` the
  `path=` of the first not yet matched logged error with the same message,
  else `null`. Logged errors that no marker matches (caught ones) are not
  failures and are not reported.
- **Without `--bounded`:** detection is log-based, as before: one entry per
  logged error line, `path` its `path=`, `message` its `msg`, `input`
  `null`. A caught error counts too.

**Errors.** Each runtime error gives one error with `file` the config,
`line` and `column` `null`, and `message` `<path>: <message>` (or just the
message when `path` is `null`). On a non-zero exit, each stderr log line
`level=error msg="Config lint error" lint="<file>(<l>,<c>) <msg>"` becomes
`{"file", "line", "column", "message"}`, in the order printed, before the
runtime errors. With neither, one error `run exited <code>: <stderr tail>`
(the last 10 non-empty lines). A timeout is one error
`run timed out after <s>s`, followed by any runtime errors before it.

**Exit codes:**

| Code | When |
|---|---|
| 0 | The binary exited 0 and there is no runtime error |
| 1 | The binary exited non-zero, or there is a runtime error (whatever its exit code) |
| 2 | A timeout (outputs and runtime errors so far kept), a missing file, a bad `--timeout`, `--bounded` without `--input`, or no usable binary |

## `test`

```
rpcn_check.py test <target> [--resources <file>]... [--env-file <file>]
```

Runs `rpk connect test` cases. The binary is called as:

```
<binary> test [--resources <f>]... [--env-file <f>] <target>
```

`<target>` is a config holding `tests:`, or a `<name>_benthos_test.yaml`
file, which runs its cases against `<name>.yaml` beside it (the binary's
default suffix, confirmed on 4.100.0 and 4.115.0).

`data`:

```json
{
  "targets": [{"file": "p.yaml", "passed": false}],
  "failures": [
    {"target": "p.yaml", "case": "wrong", "line": 8,
     "message": "batch 0 message 0: json_equals: JSON content mismatch\n{\n    \"doubled\": 4 => 5\n}"}
  ],
  "passed": 0,
  "failed": 1
}
```

| Field | Type | Meaning |
|---|---|---|
| `targets` | array | One entry per tested config, in the order printed |
| `targets[].file` | str | The config as the binary printed it (relative or absolute as the target was given) |
| `targets[].passed` | bool | `true` for `Test '<f>' succeeded`; `false` for `failed` or a target that failed to initialise |
| `failures` | array | One entry per failing case |
| `failures[].target` | str | The config the case ran against |
| `failures[].case` | str | The case `name` |
| `failures[].line` | int \| null | The line of the case in its test definition, from `[line N]`; `null` when the binary prints none |
| `failures[].message` | str | The detail lines under the case, joined with `\n` |
| `passed`, `failed` | int | Number of targets that passed and failed. Passing cases are not printed without `--verbose`, which is never passed, so these count targets, not cases |

**Parsing.** ANSI colour codes are stripped (the binary prints them even with
`NO_COLOR=1`). stdout and stderr are parsed separately:

- `Test '<f>' succeeded` / `Test '<f>' failed` give `targets`.
- After `Failures:`, each `--- <f> ---` starts a target's block. In it, a line
  `<case> [line N]:` (or `<case>:`) after a blank line starts a failing case,
  and the lines up to the next case or block are its detail.
- `Failed to execute test target '<f>': <msg>` marks `<f>` failed and gives an
  error with `file` `<f>`.
- `No tests were found` gives an error with `file` the target.

**Errors.** One per failing case, with `file` the case's target, `line`
`null`, and `message` `<case> [line N]: <first detail line>`; one per target
that failed to initialise; and one for `No tests were found`. A non-zero exit
with none of these gives one error with the output tail.

**Exit codes:**

| Code | When |
|---|---|
| 0 | The binary exited 0 and every target passed |
| 1 | A case failed, a target failed to initialise, no tests were found, or a non-zero exit with output |
| 2 | A missing file, no usable binary, a timeout, or a non-zero exit with no output |
