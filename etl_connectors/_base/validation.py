"""Helpers for the interactive ETL connector setup-validation step.

These functions back ``scripts/validate_etl_connector.py`` — the post-implementation
gate that lets a connector author (human or AI) inspect how a single job is mapped
into Monte Carlo's ETL model before an agent image is built.

Everything here is pure and side-effect free (no network, no I/O) so it can be
unit-tested locally without a live vendor connection. The script owns the I/O:
paginated ``fetch_metadata``/``fetch_run_details`` calls, prompting, printing.

Design notes:
- The display **relabels** the concept keys of the connector contract
  (``EtlAsset``/``EtlRunEvent`` dicts) using the integration's own terminology
  from ``manifest.json`` — e.g. ``job_source_id`` → ``pipeline_source_id``,
  ``tasks`` → ``components``, ``group`` → ``project`` — so a connector author
  reads the mapping in their vendor's vocabulary. This is a display-only
  transform; schema validation (:func:`collect_validation_warnings`) always runs
  on the original canonical dicts.
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

# Generic fallbacks when the manifest omits a terminology label for a concept.
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


def _run_sort_key(event: dict) -> tuple:
    """Order runs by ``event_time``; missing/empty times sort last under ``reverse=True``."""
    return (bool(event.get("event_time")), event.get("event_time") or "")


def choose_job(
    assets: list[dict], run_events: list[dict]
) -> tuple[dict | None, str | None]:
    """Pick the single job to inspect, returning ``(asset, job_source_id)``.

    Prefers the job whose most recent run is newest across the whole window, so the
    inspection always lands on a job that actually ran (an idle first-listed job is a
    useless thing to show). Falls back to the first asset — by the connector's own
    ordering — when there are no runs, or when the most-recent runs reference jobs
    ``fetch_metadata`` didn't return. Returns ``(None, None)`` only when the connector
    reported no jobs at all.
    """
    if not assets:
        return None, None
    by_id = {a.get("job_source_id"): a for a in assets}
    for event in sorted(run_events, key=_run_sort_key, reverse=True):
        job_id = event.get("job_source_id")
        if job_id in by_id:
            return by_id[job_id], job_id
    first = assets[0]
    return first, first.get("job_source_id")


def recent_runs_for_job(
    run_events: list[dict], job_source_id: str, limit: int
) -> list[dict]:
    """Runs for ``job_source_id``, most recent first, capped at ``limit``.

    Sorted by ``event_time`` descending. Events with a missing/empty ``event_time``
    sort last (and never raise), since real vendor data can omit the field.
    """
    matching = [e for e in run_events if e.get("job_source_id") == job_source_id]
    matching.sort(key=_run_sort_key, reverse=True)
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


def _slug(label: str) -> str:
    """Turn a vendor label into a JSON-key-friendly token (``"Data Pipeline"`` → ``data_pipeline``)."""
    return label.strip().lower().replace(" ", "_")


def build_keymap(terminology: dict | None) -> dict:
    """Map canonical concept keys to vendor-labelled keys from the manifest.

    Only the job/group/task *concept* keys are relabelled; leaf identifiers that
    aren't part of the terminology (``run_source_id``, a group's inner
    ``source_id``, ``name``, ``status``, timestamps, ...) are left untouched. When
    a concept has no manifest label, its default slug yields the original key, so
    the mapping is a no-op for that concept.
    """
    job = _slug(_label(terminology, "job"))
    group = _slug(_label(terminology, "group"))
    task = _slug(_label(terminology, "task"))
    return {
        "job_source_id": f"{job}_source_id",
        "group": group,
        "tasks": f"{task}s",
        "task_source_id": f"{task}_source_id",
        "task_runs": f"{task}_runs",
    }


def _relabel_keys(obj, keymap: dict):
    """Recursively copy ``obj``, renaming any dict key found in ``keymap``."""
    if isinstance(obj, dict):
        return {keymap.get(k, k): _relabel_keys(v, keymap) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_relabel_keys(item, keymap) for item in obj]
    return obj


def _dump(obj) -> str:
    return json.dumps(_redact_deep(obj), indent=2, sort_keys=True, default=str)


def format_for_display(asset: dict, runs: list[dict], terminology: dict | None) -> str:
    """Render the job's asset and recent runs for terminal inspection.

    Concept keys are relabelled to the connector's terminology (display only);
    secret-looking values are redacted. No canonical-schema legend — the vendor
    terms are the keys.
    """
    keymap = build_keymap(terminology)
    job_label = _label(terminology, key="job")
    sections = [
        f"=== {job_label}: {asset.get('name')} ===\n{_dump(_relabel_keys(asset, keymap))}"
    ]
    if runs:
        header = f"=== {len(runs)} most recent {job_label} run(s) ==="
        sections.append(f"{header}\n{_dump(_relabel_keys(runs, keymap))}")
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
