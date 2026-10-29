---
max_turns: 2
allowed_tools: [Skill]
tags: [trigger, positive]
---

This Redpanda Connect config refuses to start, what is wrong with it?

```yaml
input:
  generate:
    mapping: root = {"id": uuid_v4()}
    interval: 1s
pipeline:
  processors:
    - mapping: |
        root = this
        root.ts = now(
output:
  stdout: {}
```
