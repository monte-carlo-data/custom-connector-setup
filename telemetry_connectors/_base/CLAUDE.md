# Telemetry Connector Base Module

Shared foundation for all telemetry connectors — the custom-agent leg of on-demand runtime log and telemetry retrieval. Connector implementations live in sibling directories (e.g. `telemetry_connectors/datadog/`); this `_base/` module provides the template and validation logic they depend on.

A telemetry connector is **not** on a collection schedule. It is invoked synchronously, at investigation time, by Monolith through the Data Collector, and its result is returned to the caller without being stored.

## Key Files

| File | Purpose |
|------|---------|
| `connector.py` | Template `Connector` class — `setup_connection`, `close_connection`, `fetch_logs`, `fetch_telemetry`. |
| `validators.py` | `validate_log_page()` and `validate_telemetry_page()` — envelope and item-shape checks used by `scripts/validate_telemetry_connector.py`. |
| `__init__.py` | Re-exports the validators for convenient imports. |

## Conventions

- Connectors return plain `dict` pages, not model objects: `{"items": [...], "next_cursor": str | None}`.
- Log items: `timestamp` (tz-aware ISO 8601), `message`, optional `severity`. Telemetry items: `timestamp`, `name`, `value`, optional `attributes`.
- Items are ordered by `timestamp` ascending so the agent reads a failure in the order it happened.
- **Capability declaration:** `capabilities.supports_logs` / `capabilities.supports_telemetry` in `manifest.json` are the source of truth. Monte Carlo only calls a method the manifest advertises; it never probes for support. A capability advertised but not implemented surfaces as `TELEMETRY_INTEGRATION_UNAVAILABLE`.
- `resource_id` is vendor-native and scopes every query. Monolith resolves the telemetry connection from the resource, so the connector never guesses which resource to read.
- `cursor` / `next_cursor` are opaque to Monte Carlo — pass back whatever your vendor's pagination needs. `None` means last page.
- `idempotency_key` is stable across retries of the same logical retrieval. Reads are naturally idempotent, so most connectors only log it for correlation.
- An empty `items` list is a valid, correct result meaning "queried, nothing matched" — never raise for no results.
