# Eval cases: migration-review

Rerun these when the skill or the model changes.

## Case: missing-rollback
- Type: positive
- Prompt: "Review this PR. It adds services/invoicing/migrations/0002_add_due_date.sql with no down file."
- Expect:
  - Reports the missing 0002_add_due_date.down.sql as blocking.
  - Does not approve the PR.

## Case: destructive-rename
- Type: positive
- Prompt: "Review a migration that renames invoices.customer_ref to invoices.customer_id in one step."
- Expect:
  - Classifies the rename as destructive.
  - Reads references/rollback.md and asks for an expand and contract plan.

## Case: float-money-column
- Type: positive
- Prompt: "Review a migration that adds discount_amount DOUBLE PRECISION to invoices."
- Expect:
  - Flags the float money column and suggests BIGINT discount_minor.

## Case: data-fix-script
- Type: negative
- Prompt: "Write a one-off script to correct the customer_ref on three invoices."
- Expect:
  - Does not activate this skill.
