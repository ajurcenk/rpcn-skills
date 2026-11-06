---
max_turns: 2
allowed_tools: [Skill]
tags: [trigger, positive]
---

Messages arrive on an AMQP queue called payments. I want them enriched from a Redis cache keyed by customer id and then written to Redpanda. What would the Redpanda Connect config for that look like?
