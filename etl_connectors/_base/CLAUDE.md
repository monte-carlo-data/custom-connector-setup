# ETL Connector Base Module

Shared foundation for all ETL connectors. Connector implementations live in sibling directories (e.g. `etl_connectors/coalesce/`); this `_base/` module provides the template and validation logic they depend on.

## Key Files

| File | Purpose |
|------|---------|
| `connector.py` | Abstract `Connector` class — defines the interface every ETL connector must implement (`setup_connection`, `close_connection`, `fetch_metadata`, `fetch_run_details`) |
| `validators.py` | `validate_run_events()` and `validate_metadata_events()` — cross-field validation used by integration tests to verify connector output |
| `__init__.py` | Re-exports pycarlo model classes (`EtlAsset`, `EtlRunEvent`, etc.) and validators for convenient imports |

## Conventions

- Connectors return `list[dict]`, not model objects. The dict schemas match pycarlo's `EtlAsset` and `EtlRunEvent` dataclasses.
- Validators enforce required fields and cross-field rules (e.g. terminal statuses require `end_time`, timestamps must be timezone-aware ISO 8601). See `validators.py` docstrings for the full rule set.
- `_TERMINAL_STATUSES` in `validators.py` defines which status values require `end_time` and which trigger the error-object check.
