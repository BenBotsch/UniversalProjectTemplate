<!--
Title: Conventional Commit format, for example "feat(api): add image analysis endpoint".
Keep the section headings unchanged; pull request validation reads them.
-->

## Summary

Describe the change and its purpose.

## Related Issues

<!--
Refs: #<issue-number>    links the issue without closing it (partial work, follow-ups).
Closes #<issue-number>   closes the issue on merge, but only for pull requests into the default
                         branch (main). Pull requests into develop do not close issues automatically.
No issue? Replace the line below with "No-Issue: <reason>".
-->

Refs: #<issue-number>

## Change Type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactoring
- [ ] Documentation
- [ ] CI / Build
- [ ] Security
- [ ] Breaking change

## Implementation Details

Explain relevant design decisions and affected interfaces.

## Validation

- [ ] Applicable tests were executed.
- [ ] Lint/format/type checks passed where applicable.
- [ ] Relevant security checks passed.
- [ ] Documentation and examples are updated.
- [ ] No unrelated changes are included.

### Tests Executed

~~~text
<commands and actual results>
~~~

## Risks and Rollback

Explain migration, compatibility, performance or security risks.

## Review Notes

Mention areas where reviewers should focus.
