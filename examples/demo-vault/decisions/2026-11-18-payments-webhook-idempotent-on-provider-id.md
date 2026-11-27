---
type: decision
project: acme-shop
date: 2026-11-18
status: accepted
title: "Payment webhooks are idempotent on the provider's payment id"
tags: [decision, acme-shop]
---

# Payment webhooks are idempotent on the provider's payment id

## Context
The payment provider retries a webhook until it gets a 200. A slow response during a deploy produced two paid orders for one payment.

## Decision
Store the provider's payment id with a unique constraint and return 200 for a repeat without doing anything.

## Alternatives
- **Deduplicate on order id**: one order can have several payment attempts.
- **Lock per request**: does not survive a restart.

## Consequences
Retries are harmless. A failed handler must not write the payment id, or the retry is swallowed.
