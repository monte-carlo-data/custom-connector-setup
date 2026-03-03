import csv
import json
import os


def pytest_configure(config):
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



def _load_metrics_mapping():
    """Load the qlbase_method_metrics_mapping.csv and build method -> metrics map."""
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qlbase_method_metrics_mapping.csv")
    if not os.path.exists(csv_path):
        return {}

    method_to_metrics = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            method = row.get("qlbase_method", "").strip()
            metric_type = row.get("metric_type", "").strip()
            if method and metric_type:
                method_to_metrics.setdefault(method, set()).add(metric_type)
    return method_to_metrics


def pytest_sessionfinish(session, exitstatus):
    results = session.config._capabilities_results

    # Map template results to metrics
    method_to_metrics = _load_metrics_mapping()
    metrics = {}
    for template_name, status in results["templates"].items():
        # Strip _template suffix to match CSV method names
        method_name = template_name
        if method_name.endswith("_template"):
            method_name = method_name[: -len("_template")]

        if method_name in method_to_metrics:
            for metric_type in method_to_metrics[method_name]:
                if status == "passed":
                    metrics.setdefault(metric_type, True)
                else:
                    metrics[metric_type] = False

    output = {
        "templates": results["templates"],
        "capabilities": results["capabilities"],
        "metrics": metrics,
    }

    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "capabilities.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4, sort_keys=True)


