# Pipeline files

Every file sits beside the pipeline, in `<dir>/` (AD-6).

## Resources file

When the pipeline uses a resource (a cache, rate limit, or a shared input,
processor or output), define it in `<dir>/<name>.resources.yaml`
(`<name>.resources.yml` for a `.yml` pipeline), not in the pipeline:

```yaml
cache_resources:
  - label: lookup
    redis:
      url: ${REDIS_URL}
```

- Top-level keys: `cache_resources`, `rate_limit_resources`,
  `input_resources`, `processor_resources`, `output_resources`. Each is a
  list of `label` plus one component.
- The pipeline refers to it by label, such as `resource: lookup` in a
  `cache` processor.
- Check the component's fields with `fields caches <component>` (or its own
  category): they come without the `cache_resources[]` wrapper.
- If the resources file already exists, never write over it: ask, or in
  headless mode stop with `blocked` as for the pipeline.

## Env vars and `.env.example`

- Every secret, password, token, address or URL that differs per
  environment is `${NAME}` in the YAML, never an inline value. Use
  `${NAME:default}` only for a non-secret default.
- Names are upper snake case, such as `REDIS_URL`.
- List every name in `<dir>/.env.example`, one `NAME=` line each with no
  value, under a `#` comment saying what it is:

  ```text
  # Redis URL for the lookup cache, such as redis://localhost:6379
  REDIS_URL=
  ```

- One `.env.example` serves every pipeline in the folder. If it exists, read
  it and add only the missing names; never remove or change a line.
- Add both files to the status block's `artifacts`.
