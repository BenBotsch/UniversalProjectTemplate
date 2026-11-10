# Feature Specifications

A feature specification describes the expected behavior of a feature: objective, requirements,
technical design, acceptance criteria and test strategy. It is written when a feature is too large
or too important to be described in an issue alone.

## Specifications and Issues

- The GitHub issue is authoritative for the work: status, ownership, priority and pull requests
  (see [ADR-0001](../architecture/adr/0001-use-github-issues.md)).
- The specification is authoritative for the content: what the feature does and how it is
  verified.
- The specification lists its issues in `related_issues`; the issue links to the specification.
- Small features need no specification; the issue is enough.

## File Names and Frontmatter

Create a specification by copying [_template.md](_template.md) to
`<id>-<short-kebab-case-title>.md`, for example `FEAT-001-automatic-document-cropping.md`, and add
it to [docs/INDEX.md](../INDEX.md).

| Key | Meaning |
|---|---|
| `id` | Unique identifier, `FEAT-` followed by three digits |
| `title` | Short title of the feature |
| `status` | Document status, see below |
| `priority` | `critical`, `high`, `medium` or `low`, matching the issue priority labels |
| `created_at`, `updated_at` | ISO 8601 dates (`YYYY-MM-DD`) |
| `owner` | GitHub handle of the person responsible for the document, or empty |
| `related_issues` | Linked issues, for example `["#42"]` |
| `dependencies` | IDs of specifications this one depends on |
| `tags` | Free keywords for search |

## Document Statuses

Document statuses describe the state of the specification, not the state of the work. They are not
synchronized with issue status labels and must not be used to track progress.

| Status | Meaning |
|---|---|
| `draft` | Being written; content may change substantially |
| `planned` | Agreed and ready for implementation |
| `active` | Under implementation; the specification may still be refined |
| `implemented` | Describes behavior that exists in the product |
| `deprecated` | Behavior is being removed or replaced; kept for reference |
| `archived` | No longer relevant; kept only for history |

Update `status` and `updated_at` in the same pull request that changes the documented behavior.
