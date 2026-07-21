"""Unit tests for etl_connectors._base.validation.

Pure-logic tests — no connector, no credentials, no network. Run locally with:

    python -m pytest tests/etl/test_validation_helpers.py -v
"""

from __future__ import annotations

from etl_connectors._base.validation import (
    collect_validation_warnings,
    find_asset,
    format_for_display,
    paginate,
    recent_runs_for_job,
    redact_sensitive,
    terminology_legend,
)

TERMINOLOGY = {"group": "Project", "job": "Pipeline", "task": "Component"}


# --- find_asset -----------------------------------------------------------


def test_find_asset_returns_match():
    assets = [{"job_source_id": "a"}, {"job_source_id": "b", "name": "B"}]
    assert find_asset(assets, "b") == {"job_source_id": "b", "name": "B"}


def test_find_asset_returns_none_when_absent():
    assets = [{"job_source_id": "a"}, {"job_source_id": "b"}]
    assert find_asset(assets, "missing") is None


def test_find_asset_empty_list():
    assert find_asset([], "a") is None


# --- recent_runs_for_job --------------------------------------------------


def test_recent_runs_filters_by_job():
    runs = [
        {
            "job_source_id": "j1",
            "run_source_id": "r1",
            "event_time": "2026-07-20T10:00:00Z",
        },
        {
            "job_source_id": "j2",
            "run_source_id": "r2",
            "event_time": "2026-07-20T11:00:00Z",
        },
    ]
    result = recent_runs_for_job(runs, "j1", limit=5)
    assert [r["run_source_id"] for r in result] == ["r1"]


def test_recent_runs_no_match_returns_empty():
    runs = [
        {
            "job_source_id": "j1",
            "run_source_id": "r1",
            "event_time": "2026-07-20T10:00:00Z",
        }
    ]
    assert recent_runs_for_job(runs, "nope", limit=5) == []


def test_recent_runs_sorted_desc_and_limited():
    runs = [
        {
            "job_source_id": "j1",
            "run_source_id": "old",
            "event_time": "2026-07-18T10:00:00Z",
        },
        {
            "job_source_id": "j1",
            "run_source_id": "new",
            "event_time": "2026-07-20T10:00:00Z",
        },
        {
            "job_source_id": "j1",
            "run_source_id": "mid",
            "event_time": "2026-07-19T10:00:00Z",
        },
    ]
    result = recent_runs_for_job(runs, "j1", limit=2)
    assert [r["run_source_id"] for r in result] == ["new", "mid"]


def test_recent_runs_missing_or_none_event_time_sorts_last_without_error():
    runs = [
        {"job_source_id": "j1", "run_source_id": "no_key"},
        {
            "job_source_id": "j1",
            "run_source_id": "has_time",
            "event_time": "2026-07-20T10:00:00Z",
        },
        {"job_source_id": "j1", "run_source_id": "none_time", "event_time": None},
    ]
    result = recent_runs_for_job(runs, "j1", limit=5)
    # The dated run comes first; the two undated ones trail (order among them unspecified).
    assert result[0]["run_source_id"] == "has_time"
    assert {r["run_source_id"] for r in result[1:]} == {"no_key", "none_time"}


# --- paginate -------------------------------------------------------------


def _pager(total):
    data = [{"i": i} for i in range(total)]
    calls: list[tuple[int, int]] = []

    def fetch(limit, offset):
        calls.append((limit, offset))
        return data[offset : offset + limit]

    return fetch, calls


def test_paginate_collects_across_multiple_pages():
    fetch, calls = _pager(250)
    items = paginate(fetch, page_size=100)
    assert len(items) == 250
    # Stops on the short final page (50 < 100) — three calls, no wasted fetch.
    assert calls == [(100, 0), (100, 100), (100, 200)]


def test_paginate_terminates_on_empty_page_when_total_is_exact_multiple():
    fetch, calls = _pager(200)
    items = paginate(fetch, page_size=100)
    assert len(items) == 200
    assert calls == [(100, 0), (100, 100), (100, 200)]  # third page empty → stop


def test_paginate_empty_source():
    fetch, calls = _pager(0)
    assert paginate(fetch, page_size=100) == []
    assert calls == [(100, 0)]


def test_paginate_respects_max_pages_backstop():
    # A connector that never returns a short page must still be bounded.
    def always_full(limit, offset):
        return [{"i": offset + n} for n in range(limit)]

    items = paginate(always_full, page_size=2, max_pages=3)
    assert len(items) == 6


# --- redact_sensitive -----------------------------------------------------


def test_redact_masks_secret_query_params():
    url = "https://api.vendor.com/run?token=supersecret&job=42"
    out = redact_sensitive(url)
    assert "supersecret" not in out
    assert "job=42" in out  # non-secret param untouched
    assert "<redacted>" in out


def test_redact_masks_aws_presigned_url():
    url = (
        "https://s3.amazonaws.com/bucket/log"
        "?X-Amz-Credential=AKIA123&X-Amz-Signature=deadbeef&X-Amz-Expires=60"
    )
    out = redact_sensitive(url)
    assert "AKIA123" not in out
    assert "deadbeef" not in out
    assert "X-Amz-Expires=60" in out


def test_redact_masks_bearer_token():
    out = redact_sensitive("auth failed: Bearer abc.def.ghi")
    assert "abc.def.ghi" not in out
    assert "<redacted>" in out


def test_redact_non_string_passthrough():
    assert redact_sensitive(42) == 42
    assert redact_sensitive(None) is None


# --- terminology_legend ---------------------------------------------------


def test_legend_uses_vendor_labels_and_maps_task_to_tasks_surface():
    lines = terminology_legend(TERMINOLOGY)
    text = "\n".join(lines)
    assert "Pipeline = job" in text
    assert "Project = group" in text
    # Singular manifest key `task` maps to the plural `tasks[]` schema surface.
    assert "Component = task → tasks[].task_source_id + .name" in text


def test_legend_falls_back_to_defaults_when_missing_or_partial():
    partial = terminology_legend({"job": "Pipeline"})
    text = "\n".join(partial)
    assert "Pipeline = job" in text
    assert "Group = group" in text  # default used for the absent key
    assert "Task = task" in text

    none_text = "\n".join(terminology_legend(None))
    assert "Job = job" in none_text
    assert "Group = group" in none_text
    assert "Task = task" in none_text


# --- format_for_display ---------------------------------------------------


def test_format_shows_vendor_headers_canonical_keys_and_redacts():
    asset = {
        "job_source_id": "pipe-1",
        "name": "Daily Load",
        "tasks": [{"task_source_id": "t1", "name": "Extract"}],
    }
    runs = [
        {
            "job_source_id": "pipe-1",
            "run_source_id": "run-9",
            "status": "SUCCESS",
            "event_time": "2026-07-20T10:00:00Z",
            "run_url": "https://vendor.com/r/9?token=leakme",
        }
    ]
    out = format_for_display(asset, runs, TERMINOLOGY)
    # Vendor label in the header, but canonical schema keys are NOT rewritten.
    assert "Pipeline" in out
    assert "job_source_id" in out
    assert "task_source_id" in out
    # Secret in run_url is redacted.
    assert "leakme" not in out
    assert "<redacted>" in out


def test_format_notes_absent_runs():
    asset = {"job_source_id": "pipe-1", "name": "Idle Pipeline"}
    out = format_for_display(asset, [], TERMINOLOGY)
    assert "no runs found" in out.lower()


# --- collect_validation_warnings ------------------------------------------


def test_collect_warnings_clean_for_valid_data():
    asset = {"job_source_id": "j1", "name": "Job One"}
    runs = [
        {
            "job_source_id": "j1",
            "run_source_id": "r1",
            "status": "SUCCESS",
            "event_time": "2026-07-20T10:00:00Z",
            "end_time": "2026-07-20T10:05:00Z",
        }
    ]
    manifest = {"run_status_mapping": {"SUCCESS": "success"}}
    assert collect_validation_warnings(asset, runs, manifest) == []


def test_collect_warnings_flags_invalid_asset():
    asset = {"job_source_id": "", "name": ""}
    warnings = collect_validation_warnings(asset, [], manifest=None)
    assert warnings
    assert any(w.field == "job_source_id" for w in warnings)
