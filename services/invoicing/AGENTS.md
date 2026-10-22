# AGENTS.md (services/invoicing)

This file overrides the root AGENTS.md for everything under `services/invoicing/`.
Root rules still apply where this file says nothing.

## What this is
A tiny example invoicing library: line items in, invoice totals out.
It exists to show a per-package AGENTS.md. It is not a real service.

## Commands
- Test only this package: `make test-invoicing`
- Run before proposing a change: `make test-invoicing lint`

## Rules for this package
- Amounts are integers in minor units (cents). Never use float for money.
  See decisions.md, 2026-10-14.
- Rounding happens once, on the tax line, with half-up rounding. Do not round per item.
- Any change to `invoicing/totals.py` needs a new or updated test in `tests/`.
- Schema changes under `migrations/` must follow the `migration-review` skill.

## Do not
- Do not add third-party dependencies. The package is standard library only.
- Do not change public function signatures without a note in decisions.md.
