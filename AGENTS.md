# Agent Instructions

The integration workflow is driven by five Claude Code skills. Run them in order:

| Step | Skill | What it does |
|------|-------|-------------|
| 1 | `/create-integration <name>` | Scaffold a new integration directory |
| 2 | `/setup-connection <name>` | Install driver, implement connection methods, verify with `-m connection` |
| 3 | `/implement-integration <name> [hybrid]` | Implement all template methods section by section |
| 4 | `/build-agent-image <name> [--agent-type TYPE] [--mode MODE]` | Export capabilities and build Docker image |
| — | `/export-qlbase <name> [monolith-path]` | Convert Jinja templates to monolith QLBase class |

Each skill file (`.claude/skills/*/SKILL.md`) contains detailed step-by-step instructions. Use `/implement-integration <name> hybrid` for integrations where metadata is pushed externally.

## Quick Reference: Test Commands

```bash
# Connection
INTEGRATION=<name> docker compose run --rm test -m connection

# Metadata (full mode)
INTEGRATION=<name> docker compose run --rm test -m metadata

# Custom SQL monitors
INTEGRATION=<name> docker compose run --rm test -m custom_monitors

# Query language prerequisites
INTEGRATION=<name> docker compose run --rm test -m ql_prerequisites

# Query language metrics
INTEGRATION=<name> docker compose run --rm test -m ql_metrics

# Functional validation (optional)
INTEGRATION=<name> docker compose run --rm test -m functional

# All tests
INTEGRATION=<name> docker compose run --rm test

# Single test
INTEGRATION=<name> docker compose run --rm test tests/test_ql_prerequisites.py::test_equality -v

# Export capabilities
INTEGRATION=<name> docker compose run --rm test --export
```
