# Architecture Decision Records

An Architecture Decision Record (ADR) documents one significant decision, its context and its
consequences. ADRs explain why the project looks the way it does; they are not task lists.

## When to Write an ADR

Write an ADR when a decision:

- Is hard or expensive to reverse, for example the choice of a language, framework, storage
  technology or deployment model.
- Changes a public interface, a data format or a cross-module dependency.
- Introduces or removes a significant dependency or external service.
- Changes security, privacy or compliance properties.
- Settles a recurring discussion that would otherwise be repeated.

Routine implementation choices that are easy to change do not need an ADR.

## Numbering and File Names

- ADRs are numbered sequentially with four digits: `0001`, `0002`, and so on.
- The file name is `<number>-<short-kebab-case-title>.md`, for example
  `0002-use-postgresql-for-persistence.md`.
- The `id` in the frontmatter is `ADR-<number>`, for example `ADR-0002`.
- Numbers are never reused, even if an ADR is rejected or superseded.
- `0000-adr-template.md` is the template and not a decision.

## Statuses

| Status | Meaning |
|---|---|
| `proposed` | Under discussion; not yet binding |
| `accepted` | Binding for the project |
| `superseded` | Replaced by a newer ADR; the newer ADR links back to it |
| `deprecated` | No longer relevant, without a direct replacement |

An accepted ADR is not rewritten to reflect a new decision. Write a new ADR instead, set the old one
to `superseded` and link the two in both directions.

## Process

1. Copy [0000-adr-template.md](0000-adr-template.md) to the next free number.
2. Fill in context, decision and consequences, and set the status to `proposed`.
3. Link the related issue in `related_issues` and open a pull request.
4. Set the status to `accepted` when the pull request is approved.
5. Add the new ADR to [docs/INDEX.md](../../INDEX.md).

Changes to `docs/architecture/` need particularly careful review.
