<!--
Thanks for contributing to NetOpsMCP! Please fill in the sections below and
tick the checklist. See CONTRIBUTING.md for setup, test, and lint commands.
-->

## Summary

<!-- What does this PR change and why? Link any related issues (e.g. "Closes #123"). -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Documentation / CI / tooling only

## Checklist

- [ ] Tests pass locally: `uv run pytest tests/`
- [ ] Lint is clean: `ruff check src/ tests/` and `black --check src/ tests/`
- [ ] The MCP tool surface (the 26 tool names and their parameters) is unchanged,
      unless this change intentionally modifies it (and the schema snapshot tests
      were updated accordingly)
- [ ] Documentation is updated where behavior or configuration changed
      (README.md, SECURITY.md, CHANGELOG.md, or the relevant doc)
- [ ] New behavior is covered by tests (using the `_execute_command` /
      `mock_psutil` mock strategy from CONTRIBUTING.md)

## Additional notes

<!-- Anything reviewers should know: trade-offs, follow-ups, screenshots, etc. -->
