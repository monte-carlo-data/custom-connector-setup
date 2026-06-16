# ETL Connector Base Module

Shared foundation for all ETL connectors. Connector implementations live in sibling directories (e.g. `etl_connectors/coalesce/`); this `_base/` module provides the template and validation logic they depend on.

## Key Files

| File | Purpose |
|------|---------|
| `connector.py` | Abstract `Connector` class — defines the interface every ETL connector must implement (`setup_connection`, `close_connection`, `fetch_metadata`, `fetch_run_details`). |
| `validators.py` | `validate_run_events()` and `validate_metadata_events()` — cross-field validation used by integration tests to verify connector output. When a status mapping is supplied (from `manifest.json`), `validate_run_events()` normalizes vendor statuses via `_normalize_status()` (case-insensitive key lookup) before applying cross-field checks (terminal-status → end_time, failed → error object). Unmapped vendor statuses normalize to `"unknown"` and are reported as validation errors. |
| `__init__.py` | Re-exports pycarlo model classes (`EtlAsset`, `EtlRunEvent`, etc.) and validators for convenient imports |

## Conventions

- Connectors return `list[dict]`, not model objects. The dict schemas match pycarlo's `EtlAsset` and `EtlRunEvent` dataclasses.
- `EtlAsset` uses a nested `group` dict (with `source_id` required) instead of flat `group_source_id`. Assets can also carry a `tasks` list (each task needs `task_source_id` and `name`).
- Validators enforce required fields and cross-field rules (e.g. terminal statuses require `end_time`, timestamps must be timezone-aware ISO 8601, `group.source_id` required when group is present, `inputs`/`outputs` asset refs have valid `asset_type`, `role`, and at least one identifier). See `validators.py` docstrings for the full rule set.
- `_TERMINAL_STATUSES` in `validators.py` defines which status values require `end_time` and which trigger the error-object check.
- **Status mapping:** `run_status_mapping` in `manifest.json` maps vendor-native status strings to Monte Carlo canonical statuses (`ETL_RUN_STATUS_VALUES`). It is required — the scaffold stubs it empty, and the test framework fails if it's missing or empty. `task_run_status_mapping` is optional; when absent, task-run validation falls back to `run_status_mapping`.
