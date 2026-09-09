# BI Connector Base Module

Shared foundation for all BI connectors. Connector implementations live in sibling directories (e.g. `bi_connectors/looker/`). This `_base/` module is **authoring-time only**: `connector.py` is the template the scaffold copies into each new connector, and `validators.py` runs in tests. Nothing here ships in the agent image — connector code must never import `bi_connectors._base` (the import fails in the agent with `No module named 'bi_connectors'`).

## Key Files

| File | Purpose |
|------|---------|
| `connector.py` | Abstract `Connector` class — defines the single-method interface every BI connector must implement (`setup_connection`, `close_connection`, `fetch_metadata`). Unlike ETL, there is no `fetch_run_details` and no webhook — BI assets have no run pipeline. |
| `validators.py` | `validate_bi_metadata_events()` — cross-field validation used by integration tests to verify connector output. Complements the ingestion gateway's Cerberus schema (which enforces per-field shape). |
| `__init__.py` | Re-exports pycarlo BI model classes (`BiAsset`, `BiAssetRef`, `BiOwner`, `BI_RELATIONSHIP_TYPE_VALUES`), the shared ETL `AssetRef` constants, and validators for convenient imports |

## Conventions

- Connectors return `list[dict]`, not model objects. The dict schema matches pycarlo's `pycarlo.features.ingestion.bi.BiAsset` dataclass.
- No runs, no webhooks: a BI connector exposes only `fetch_metadata()`. BI assets have no execution pipeline.
- `asset_source_id` is the identity seed — it must be vendor-stable across renames and moves, or Monte Carlo treats the asset as new.
- BI-to-BI lineage uses `upstream_assets` / `downstream_assets` lists of `{asset_source_id, relationship_type?}` refs, where `relationship_type` is one of `BI_RELATIONSHIP_TYPE_VALUES` (`CONTAINED_IN`, `DERIVES_FROM`, `REFERENCES`). `container_source_id` is unsupported in v1 (dropped server-side) — never set it.
- Table lineage uses `inputs` — a list of the shared ETL `AssetRef` dicts with `role` = `INPUT` and at least one identifier (`mcon` and/or `fully_qualified_name`).
- Validators enforce required fields and cross-field rules (timezone-aware ISO-8601 timestamps, non-negative int `view_count`, bool flags, BI ref shape, owner keys within `{email, name, source_id}`, `properties` items with a non-empty `key`). See `validators.py` docstrings for the full rule set.
- Requires pycarlo >= 0.15.240 for the `pycarlo.features.ingestion.bi` subpackage.
