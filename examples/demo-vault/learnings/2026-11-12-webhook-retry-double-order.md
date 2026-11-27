---
type: learning
project: acme-shop
date: 2026-11-12
learning_type: failure
title: "A webhook retry created a second paid order"
tags: [learning, acme-shop, failure]
---

# A webhook retry created a second paid order

**What happened**: during a deploy the API answered slowly, the payment provider retried the webhook, and the order was created twice.

**Lesson**: every webhook handler must be idempotent on the provider's id.

**Root cause**: the handler assumed exactly-once delivery.

**How to apply**: any endpoint a third party calls. Led to [[2026-11-18-payments-webhook-idempotent-on-provider-id]].
