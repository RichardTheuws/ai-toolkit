---
type: decision
project: acme-shop
date: 2026-11-02
status: accepted
title: "Static pages, an API only for checkout"
tags: [decision, acme-shop]
---

# Static pages, an API only for checkout

## Context
Product pages change a few times a week; checkout changes per visitor.

## Decision
Build the pages statically and keep one small API for cart, checkout and webhooks.

## Consequences
Pages are fast and cacheable. Stock shown on a page can be minutes old; checkout checks it again.
