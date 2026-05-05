# Agent Instructions

The connector workflow is driven by four Claude Code skills. Run them in order:

| Step | Skill                                                         | What it does                                                              |
| ---- | ------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1    | `/create-connector <name>`                                    | Scaffold a new connector directory                                        |
| 2    | `/setup-connection <name>`                                    | Install driver, implement connection methods, verify with `-m connection` |
| 3    | `/implement-connector <name> [hybrid]`                        | Implement all template methods section by section                         |
| 4    | `/build-agent-image <name> [--mode MODE]` | Export capabilities and build Docker image                                |

Each skill file (`.claude/skills/*/SKILL.md`) contains detailed step-by-step instructions. Use `/implement-connector <name> hybrid` for connectors where metadata is pushed externally.

## System Dependencies

If a connector needs system-level packages (ODBC drivers, native libraries), add them to `connectors/<name>/Dockerfile.extra` as raw Dockerfile instructions (`RUN`, `ENV`, `ARG`), then regenerate the test Dockerfile:

```bash
python scripts/generate_test_dockerfile.py
docker compose build
```

The `Dockerfile.extra` contents are automatically included in the agent image built by `generate_agent_image.py`.

## Quick Reference: Test Commands

```bash
# Connection
CONNECTOR=<name> docker compose run --rm test -m connection

# Metadata (full mode)
CONNECTOR=<name> docker compose run --rm test -m metadata

# Custom SQL monitors
CONNECTOR=<name> docker compose run --rm test -m custom_monitors

# Query language prerequisites
CONNECTOR=<name> docker compose run --rm test -m ql_prerequisites

# Query language metrics
CONNECTOR=<name> docker compose run --rm test -m ql_metrics

# Functional validation (optional)
CONNECTOR=<name> docker compose run --rm test -m functional

# All tests
CONNECTOR=<name> docker compose run --rm test

# Single test
CONNECTOR=<name> docker compose run --rm test tests/test_ql_prerequisites.py::test_equality -v

# Export capabilities
CONNECTOR=<name> docker compose run --rm test --export
```
