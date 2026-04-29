import importlib
import json
import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--export",
        action="store_true",
        default=False,
        help="Export manifest.json and passing templates (requires full test suite — cannot be used with -m)",
    )


ALL_CAPABILITIES = [
    "supports_custom_sql_monitor",
    "supports_full_query_language",
    "supports_metadata",
    "supports_volume_rows",
    "supports_volume_bytes",
    "supports_freshness",
    "supports_schema",
    "supports_query_logs",
    "supports_lineage",
    "supports_field_lineage",
]


def pytest_configure(config):
    if config.getoption("--export", default=False) and config.getoption("-m", default=""):
        raise pytest.UsageError(
            "--export requires the full test suite. Remove the -m filter and re-run."
        )

    config._capabilities_results = {
        "templates": {},
        "capabilities": {},
    }


def pytest_runtest_makereport(item, call):
    if call.when != "call":
        return

    results = item.config._capabilities_results

    # Collect template markers
    for marker in item.iter_markers("template"):
        func_name = marker.kwargs.get("func", "")
        if func_name:
            if call.excinfo is None:
                results["templates"].setdefault(func_name, "passed")
            elif call.excinfo and call.excinfo.typename == "Skipped":
                results["templates"].setdefault(func_name, "skipped")
            else:
                results["templates"][func_name] = "failed"

    # Collect capability markers
    for marker in item.iter_markers("capability"):
        for cap_name in marker.args:
            if call.excinfo is None:
                results["capabilities"].setdefault(cap_name, True)
            elif call.excinfo and call.excinfo.typename == "Skipped":
                results["capabilities"].setdefault(cap_name, False)
            else:
                results["capabilities"][cap_name] = False


# Mapping from template method name (without _template suffix) to the set of
# metric types that method enables.
METHOD_TO_METRICS = {
    "get_avg_function": {
        "numeric_mean",
    },
    "get_stddev_function": {
        "numeric_stddev",
        "text_std_length",
    },
    "get_approx_percentile_func": {
        "numeric_median",
        "percentile_20",
        "percentile_40",
        "percentile_60",
        "percentile_80",
        "approx_quantiles0",
        "approx_quantiles1",
        "approx_quantiles2",
        "approx_quantiles3",
        "approx_quantiles4",
        "approx_quantiles5",
    },
    "get_approx_quantiles_func": {
        "approx_quantiles",
    },
    "get_distinct_count_func": {
        "approx_distinct_count",
        "approx_distinctness",
    },
    "get_distinctness_func": {
        "approx_distinctness",
    },
    "get_casting_to_decimal_expression": {
        "sum",
    },
    "get_length": {
        "text_mean_length",
        "text_min_length",
        "text_max_length",
        "text_std_length",
    },
    "get_conditional_count_expression": {
        "zero_count",
        "zero_rate",
        "negative_count",
        "negative_rate",
        "nan_count",
        "nan_rate",
        "empty_string_count",
        "empty_string_rate",
        "true_count",
        "true_rate",
        "false_count",
        "false_rate",
        "text_timestamp_count",
        "text_timestamp_rate",
        "text_not_timestamp_count",
        "past_timestamp_count",
        "past_timestamp_rate",
        "future_timestamp_count",
        "future_timestamp_rate",
        "unix_zero_count",
        "unix_zero_rate",
        "text_null_keyword_count",
        "text_null_keyword_rate",
        "array_null_rate",
    },
    "get_isnan_expression": {
        "nan_count",
        "nan_rate",
    },
    "get_is_empty_string_expression": {
        "empty_string_count",
        "empty_string_rate",
    },
    "get_boolean_match_expression": {
        "true_count",
        "true_rate",
        "false_count",
        "false_rate",
    },
    "get_is_timestamp_expression": {
        "text_timestamp_count",
        "text_timestamp_rate",
    },
    "get_not_is_timestamp_expression": {
        "text_not_timestamp_count",
    },
    "get_epoch_seconds_expression": {
        "past_timestamp_count",
        "past_timestamp_rate",
        "future_timestamp_count",
        "future_timestamp_rate",
        "unix_zero_count",
        "unix_zero_rate",
    },
    "get_regexp_count_expression": {
        "text_int_count",
        "text_not_int_count",
        "text_int_rate",
        "text_number_count",
        "text_not_number_count",
        "text_number_rate",
        "text_uuid_count",
        "text_not_uuid_count",
        "text_uuid_rate",
        "text_email_address_count",
        "text_not_email_address_count",
        "text_email_address_rate",
        "text_us_state_code_count",
        "text_not_us_state_code_count",
        "text_us_state_code_rate",
        "text_us_zip_code_count",
        "text_not_us_zip_code_count",
        "text_us_zip_code_rate",
        "text_us_phone_count",
        "text_not_us_phone_count",
        "text_us_phone_rate",
        "text_ssn_count",
        "text_not_ssn_count",
        "text_ssn_rate",
        "text_all_spaces_count",
        "text_all_spaces_rate",
    },
    "get_regexp_expression": {
        "text_int_count",
        "text_not_int_count",
        "text_int_rate",
        "text_number_count",
        "text_not_number_count",
        "text_number_rate",
        "text_uuid_count",
        "text_not_uuid_count",
        "text_uuid_rate",
        "text_email_address_count",
        "text_not_email_address_count",
        "text_email_address_rate",
        "text_us_state_code_count",
        "text_not_us_state_code_count",
        "text_us_state_code_rate",
        "text_us_zip_code_count",
        "text_not_us_zip_code_count",
        "text_us_zip_code_rate",
        "text_us_phone_count",
        "text_not_us_phone_count",
        "text_us_phone_rate",
        "text_ssn_count",
        "text_not_ssn_count",
        "text_ssn_rate",
        "text_all_spaces_count",
        "text_all_spaces_rate",
    },
    "literal_regex": {
        "text_int_count",
        "text_not_int_count",
        "text_int_rate",
        "text_number_count",
        "text_not_number_count",
        "text_number_rate",
        "text_uuid_count",
        "text_not_uuid_count",
        "text_uuid_rate",
        "text_email_address_count",
        "text_not_email_address_count",
        "text_email_address_rate",
        "text_us_state_code_count",
        "text_not_us_state_code_count",
        "text_us_state_code_rate",
        "text_us_zip_code_count",
        "text_not_us_zip_code_count",
        "text_us_zip_code_rate",
        "text_us_phone_count",
        "text_not_us_phone_count",
        "text_us_phone_rate",
        "text_ssn_count",
        "text_not_ssn_count",
        "text_ssn_rate",
        "text_all_spaces_count",
        "text_all_spaces_rate",
    },
    "get_array_length_func": {
        "array_null_rate",
    },
    "convert_field_to_uppercase": {
        "text_null_keyword_count",
        "text_null_keyword_rate",
    },
    "in_values": {
        "text_null_keyword_count",
        "text_null_keyword_rate",
    },
}


def pytest_sessionfinish(session, exitstatus):
    export = session.config.getoption("--export", default=False)
    if not export:
        return

    results = session.config._capabilities_results
    root = os.path.dirname(os.path.dirname(__file__))

    # Resolve connector name (set by conftest._get_connector)
    connector_name = getattr(session.config, "_connector_name", None)

    # Read connection_type from manifest.json
    connection_type = None
    if connector_name:
        manifest_path = os.path.join(root, "connectors", connector_name, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
                connection_type = manifest.get("connection_type")

    # Extract credential keys from BaseConnector (keys only, not values)
    credential_keys = []
    if connector_name:
        try:
            module = importlib.import_module(f"connectors.{connector_name}.connector")
            credential_keys = list(module.BaseConnector().credential_env_vars().keys())
        except Exception:
            pass

    # Fill in defaults for capabilities not set by markers
    for cap in ALL_CAPABILITIES:
        results["capabilities"].setdefault(cap, False)

    # Map template results to metrics
    metrics = {}
    for template_name, status in results["templates"].items():
        method_name = template_name
        if method_name.endswith("_template"):
            method_name = method_name[: -len("_template")]

        if method_name in METHOD_TO_METRICS:
            for metric_type in METHOD_TO_METRICS[method_name]:
                if status == "passed":
                    metrics.setdefault(metric_type, True)
                else:
                    metrics[metric_type] = False

    output = {
        "connection_type": connection_type,
        "connection_name": connector_name,
        "capabilities": results["capabilities"],
        "metrics": metrics,
    }

    # Write manifest.json
    if connector_name:
        output_dir = os.path.join(root, "output", connector_name)
    else:
        output_dir = root
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "manifest.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4, sort_keys=True)

    # Write credentials template (keys only, no values)
    if credential_keys:
        creds_template = {"connect_args": {k: "<your-value>" for k in credential_keys}}
        creds_path = os.path.join(output_dir, "credentials_template.json")
        with open(creds_path, "w") as f:
            json.dump(creds_template, f, indent=4)

    # Export passing templates to .j2 files
    templates_instance = getattr(session.config, "_templates_instance", None)
    if templates_instance is None:
        return
    if connector_name:
        export_path = os.path.join(root, "output", connector_name, "templates")
    else:
        export_path = os.path.join(root, "templates")
    os.makedirs(export_path, exist_ok=True)
    for template_name, status in results["templates"].items():
        if status != "passed":
            continue
        method = getattr(templates_instance, template_name, None)
        if method is None:
            continue
        try:
            template_string = method()
        except Exception:
            continue
        if not template_string:
            continue
        filepath = os.path.join(export_path, f"{template_name}.j2")
        with open(filepath, "w") as f:
            f.write(template_string)
