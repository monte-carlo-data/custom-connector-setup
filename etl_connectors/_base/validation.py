"""Helpers for the interactive ETL connector setup-validation step.

These functions back ``scripts/validate_etl_connector.py`` — the post-implementation
gate that lets a connector author (human or AI) inspect how a single job is mapped
into Monte Carlo's ETL model before an agent image is built.

Everything here is pure and side-effect free (no network, no I/O) so it can be
unit-tested locally without a live vendor connection. The script owns the I/O:
paginated ``fetch_metadata``/``fetch_run_details`` calls, prompting, printing.

Design notes:
- The connector contract (``EtlAsset``/``EtlRunEvent`` dicts) is displayed
  **unmodified** — we never rewrite schema keys. Integration-specific terminology
  is surfaced only via section headers and a legend, so the output stays honest
  about the real schema the ingestion pipeline sees.
- ``run_url`` / ``error.message`` (and similar free-text fields) are connector-
  supplied and can carry secrets (presigned URLs, tokens in stack traces). They
  are passed through :func:`redact_sensitive` before display, since this output
  predictably lands in terminals, CI logs, and AI transcripts.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from etl_connectors._base.validators import (
    ValidationError,
    validate_metadata_events,
    validate_run_events,
)

DEFAULT_PAGE_SIZE = 100
# Safety backstop only — pagination normally stops on a short/empty page. This
# caps a misbehaving connector that never returns a short page. At the default
# page size this is 100k items; the caller should surface if it is ever hit.
DEFAULT_MAX_PAGES = 1000

# The manifest ``terminology`` block uses singular keys; each maps to a distinct
# surface of the canonical schema. Order controls legend rendering.
_TERM_SURFACES = (
    ("job", "job_source_id + name"),
    ("group", "group.source_id + group.name"),
    ("task", "tasks[].task_source_id + .name"),
)
_TERM_DEFAULTS = {"job": "Job", "group": "Group", "task": "Task"}

# Keys whose string values are free-form/connector-supplied and may embed secrets.
_REDACT_KEYS = frozenset({"run_url", "url", "message"})

# Query-string params whose names hint at a secret (covers AWS presigned URLs:
# X-Amz-Signature, X-Amz-Credential, X-Amz-Security-Token).
_SECRET_QS_RE = re.compile(
    r"([?&][^=&\s]*(?:token|key|secret|password|signature|sig|credential|auth|access)"
    r"[^=&\s]*=)[^&\s]+",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)
_REDACTION = "<redacted>"


def paginate(
    fetch_page: Callable[[int, int], list],
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> list:
    """Collect all items from a paginated ``fetch_page(limit, offset)`` callable.

    Stops when a page is empty or shorter than ``page_size`` (the last page), or
    when ``max_pages`` is reached (safety backstop). Returns the flat list of items.
    """
    items: list = []
    for page_num in range(max_pages):
        page = fetch_page(page_size, page_num * page_size)
        if not page:
            break
        items.extend(page)
        if len(page) < page_size:
            break
    return items


def find_asset(assets: list[dict], job_source_id: str) -> dict | None:
    """Return the asset whose ``job_source_id`` matches, or ``None`` if absent."""
    for asset in assets:
        if asset.get("job_source_id") == job_source_id:
            return asset
    return None


def recent_runs_for_job(
    run_events: list[dict], job_source_id: str, limit: int
) -> list[dict]:
    """Runs for ``job_source_id``, most recent first, capped at ``limit``.

    Sorted by ``event_time`` descending. Events with a missing/empty ``event_time``
    sort last (and never raise), since real vendor data can omit the field.
    """
    matching = [e for e in run_events if e.get("job_source_id") == job_source_id]
    matching.sort(
        key=lambda e: (bool(e.get("event_time")), e.get("event_time") or ""),
        reverse=True,
    )
    return matching[:limit]


def redact_sensitive(value):
    """Mask secret-looking query-string params and bearer tokens in a string.

    Accepts any value; non-strings are returned unchanged. Redacts only the
    sensitive *values*, so the surrounding structure (URL host/path, error
    prose) stays readable.
    """
    if not isinstance(value, str):
        return value
    redacted = _SECRET_QS_RE.sub(rf"\1{_REDACTION}", value)
    redacted = _BEARER_RE.sub(rf"\1{_REDACTION}", redacted)
    return redacted


def _redact_deep(obj):
    """Recursively copy ``obj``, redacting string values under :data:`_REDACT_KEYS`."""
    if isinstance(obj, dict):
        return {
            k: redact_sensitive(v)
            if k in _REDACT_KEYS and isinstance(v, str)
            else _redact_deep(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_deep(item) for item in obj]
    return obj


def _label(terminology: dict | None, key: str) -> str:
    """Vendor label for a terminology key, falling back to the generic default."""
    label = (terminology or {}).get(key)
    return label if label else _TERM_DEFAULTS[key]


def terminology_legend(terminology: dict | None) -> list[str]:
    """Legend lines mapping each vendor term to its canonical schema surface.

    Uses vendor labels when the manifest supplies them, generic defaults otherwise.
    Always renders all three surfaces so the reader sees the full mapping.
    """
    lines = ["Terminology (this integration → Monte Carlo schema):"]
    for key, surface in _TERM_SURFACES:
        lines.append(f"  {_label(terminology, key)} = {key} → {surface}")
    return lines


def _dump(obj) -> str:
    return json.dumps(_redact_deep(obj), indent=2, sort_keys=True, default=str)


def format_for_display(asset: dict, runs: list[dict], terminology: dict | None) -> str:
    """Render the job's asset and recent runs for terminal inspection.

    Canonical JSON is shown unmodified (after secret redaction); vendor terminology
    appears only in the section headers and legend.
    """
    job_label = _label(terminology, key="job")
    sections: list[str] = []
    sections.append("\n".join(terminology_legend(terminology)))
    sections.append(
        f"=== {job_label} (job_source_id={asset.get('job_source_id')!r}) ===\n{_dump(asset)}"
    )
    if runs:
        header = f"=== {len(runs)} most recent {job_label} run(s) ==="
        sections.append(f"{header}\n{_dump(runs)}")
    else:
        sections.append(
            f"=== {job_label} runs ===\n(no runs found in the collection window)"
        )
    return "\n\n".join(sections)


def collect_validation_warnings(
    asset: dict, runs: list[dict], manifest: dict | None
) -> list[ValidationError]:
    """Run the standard ETL validators over the chosen asset + runs.

    Returns the combined list of :class:`ValidationError` (empty when clean).
    Surfaced by the script as a warning banner — the schema validity of the
    inspected data, not a hard failure.
    """
    manifest = manifest or {}
    errors = list(validate_metadata_events([asset]))
    errors.extend(
        validate_run_events(
            runs,
            run_status_mapping=manifest.get("run_status_mapping"),
            task_run_status_mapping=manifest.get("task_run_status_mapping"),
        )
    )
    return errors
