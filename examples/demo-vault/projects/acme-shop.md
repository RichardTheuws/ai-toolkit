---
type: project
status: active
repo: ~/code/acme-shop
tech: [astro, node, postgres]
deploy_target: a Mac mini behind a Cloudflare tunnel
version: 0.8.2
---

# acme-shop

A small web shop for handmade ceramics. Static pages, a checkout API, and an admin for orders.

## Current state
- Checkout runs on the new payment provider since 0.8.0; refunds still go through the old dashboard.
- Order emails are sent from the API; the confirmation template is not in the design system yet.
- Next: refunds in the admin, then move the order email into the design system.

## Decisions
- [[2026-11-18-payments-webhook-idempotent-on-provider-id]] Payment webhooks are idempotent on the provider's payment id
- [[2026-11-02-static-pages-api-only-for-checkout]] Static pages, an API only for checkout

## Lessons
- [[2026-11-20-rsync-delete-removed-server-env]] rsync --delete removed the server's .env
