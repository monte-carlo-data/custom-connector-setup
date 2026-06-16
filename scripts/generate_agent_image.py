#!/usr/bin/env python3
"""Build a custom agent Docker image with connector artifacts.

Usage:
    python scripts/generate_agent_image.py
    python scripts/generate_agent_image.py postgres coalesce
    python scripts/generate_agent_image.py --version 0.0.11
    python scripts/generate_agent_image.py --mode hybrid postgres
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

AGENT_TYPE = "generic"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONNECTORS_DIR = os.path.join(REPO_ROOT, "connectors")
ETL_CONNECTORS_DIR = os.path.join(REPO_ROOT, "etl_connectors")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

REQUIRED_SOURCE_FILES = ["connector.py", "manifest.json", "requirements.txt"]
ETL_REQUIRED_SOURCE_FILES = ["connector.py", "manifest.json", "requirements.txt"]


def read_dockerfile_extra(base_dir, name):
    """Read a connector's Dockerfile.extra, returning content or None.

    Returns None if the file doesn't exist or contains only comments/whitespace.
    """
    path = os.path.join(base_dir, name, "Dockerfile.extra")
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        content = f.read()
    # Check if there are any non-comment, non-blank lines
    has_instructions = any(
        line.strip() and not line.strip().startswith("#")
        for line in content.splitlines()
    )
    if not has_instructions:
        return None
    return content.strip()


def resolve_connector_dir(name):
    """Return (base_dir, connector_type) for a connector name.

    Checks connectors/<name>/ and etl_connectors/<name>/.
    """
    dw_path = os.path.join(CONNECTORS_DIR, name)
    etl_path = os.path.join(ETL_CONNECTORS_DIR, name)
    if os.path.isdir(dw_path):
        return CONNECTORS_DIR, "dw"
    if os.path.isdir(etl_path):
        return ETL_CONNECTORS_DIR, "etl"
    return None, None


def discover_etl_connectors():
    """Return ETL connector names from the etl_connectors/ directory."""
    if not os.path.isdir(ETL_CONNECTORS_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(ETL_CONNECTORS_DIR)
        if not name.startswith("_")
        and not name.startswith(".")
        and os.path.isdir(os.path.join(ETL_CONNECTORS_DIR, name))
    )


def validate_etl_connector(name):
    """Validate that an ETL connector has all required artifacts. Returns list of errors."""
    errors = []

    for filename in ETL_REQUIRED_SOURCE_FILES:
        path = os.path.join(ETL_CONNECTORS_DIR, name, filename)
        if not os.path.isfile(path):
            errors.append(f"  - Missing etl_connectors/{name}/{filename}")

    manifest_path = os.path.join(ETL_CONNECTORS_DIR, name, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        connection_type = manifest.get("connection_type", "")
        if not connection_type.startswith("custom-etl-connector-"):
            errors.append(
                f"  - manifest.json connection_type must match 'custom-etl-connector-*', "
                f"got '{connection_type}'"
            )
        if "terminology" not in manifest:
            errors.append("  - manifest.json is missing required 'terminology' key")
        creds_schema = manifest.get("credentials_schema")
        if creds_schema is not None and not isinstance(creds_schema, dict):
            errors.append(
                f"  - manifest.json 'credentials_schema' must be a dict, "
                f"got {type(creds_schema).__name__}"
            )

    # Require exported manifest (produced by --export)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exported_manifest = os.path.join(repo_root, "output", name, "manifest.json")
    if not os.path.isfile(exported_manifest):
        errors.append(
            f"  - Exported manifest not found at output/{name}/manifest.json. "
            f"Run: CONNECTOR={name} docker compose run --rm test --export"
        )

    return errors


def build_etl_context(tmp_dir, connectors):
    """Copy ETL connector artifacts into the temporary build context.

    Copies only the files needed for the image — credentials.json and .env
    are explicitly excluded to prevent secrets from being baked into images.

    Uses the exported manifest from ``output/<name>/manifest.json`` (produced
    by ``--export``) which includes status mappings merged from the Connector
    class.
    """
    _ETL_EXCLUDE = {"credentials.json", ".env"}
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in connectors:
        src = os.path.join(ETL_CONNECTORS_DIR, name)
        dest = os.path.join(tmp_dir, "custom-etl-connectors", name)
        shutil.copytree(
            src,
            dest,
            ignore=shutil.ignore_patterns(*_ETL_EXCLUDE),
        )
        # Replace source manifest with the exported one (has status mappings merged).
        exported_manifest = os.path.join(repo_root, "output", name, "manifest.json")
        shutil.copy2(exported_manifest, os.path.join(dest, "manifest.json"))


def discover_connectors():
    """Return connector names that have output directories."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(OUTPUT_DIR)
        if os.path.isdir(os.path.join(OUTPUT_DIR, name)) and name != "_base"
    )


def detect_connector_mode(name):
    """Auto-detect whether a connector should use full or hybrid mode."""
    manifest_path = os.path.join(OUTPUT_DIR, name, "manifest.json")
    if not os.path.isfile(manifest_path):
        return "full"
    with open(manifest_path) as f:
        manifest = json.load(f)
    if manifest.get("capabilities", {}).get("supports_metadata"):
        return "full"
    return "hybrid"


def resolve_connector_mode(name, global_mode):
    """Resolve the effective mode for a connector given the global --mode flag."""
    if global_mode == "auto":
        return detect_connector_mode(name)
    return global_mode


def validate_connector(name, mode="full"):
    """Validate that a connector has all required artifacts. Returns list of errors."""
    errors = []

    manifest_path = os.path.join(OUTPUT_DIR, name, "manifest.json")
    if not os.path.isfile(manifest_path):
        errors.append(f"  - Missing output/{name}/manifest.json")
    else:
        with open(manifest_path) as f:
            manifest = json.load(f)
        if mode == "hybrid":
            if not manifest.get("capabilities", {}).get("supports_custom_sql_monitor"):
                errors.append(
                    "  - Custom SQL monitor support has not been implemented — this is a requirement for hybrid mode."
                )
            if manifest.get("capabilities", {}).get("supports_metadata"):
                errors.append(
                    "  - Metadata is implemented but hybrid mode requires metadata to be pushed externally."
                    " Use --mode full instead, or remove MetadataQueryTemplates."
                )
        else:
            if not manifest.get("capabilities", {}).get("supports_metadata"):
                errors.append(
                    "  - Metadata collection has not been implemented — this is a requirement."
                )
        creds_schema = manifest.get("credentials_schema")
        if creds_schema is not None and not isinstance(creds_schema, dict):
            errors.append(
                f"  - manifest.json 'credentials_schema' must be a dict, "
                f"got {type(creds_schema).__name__}"
            )

    templates_dir = os.path.join(OUTPUT_DIR, name, "templates")
    if not os.path.isdir(templates_dir) or not os.listdir(templates_dir):
        errors.append(f"  - Missing or empty output/{name}/templates/")

    for filename in REQUIRED_SOURCE_FILES:
        path = os.path.join(CONNECTORS_DIR, name, filename)
        if not os.path.isfile(path):
            errors.append(f"  - Missing connectors/{name}/{filename}")

    return errors


def check_metric_warnings(name):
    """Return a warning string if metric monitors are unsupported but some metrics pass, else None."""
    manifest_path = os.path.join(OUTPUT_DIR, name, "manifest.json")
    if not os.path.isfile(manifest_path):
        return None

    with open(manifest_path) as f:
        manifest = json.load(f)

    supports_ql = manifest.get("capabilities", {}).get(
        "supports_full_query_language", False
    )
    metrics = manifest.get("metrics", {})
    passing_metrics = sorted(m for m, v in metrics.items() if v is True)

    if not supports_ql and passing_metrics:
        lines = [
            f"  {name}:",
            "    supports_full_query_language = false",
            f"    {len(passing_metrics)} metric(s) have passing templates:",
        ]
        for metric in passing_metrics:
            lines.append(f"      - {metric}")
        lines.append(
            "    Re-run tests to see which prerequisite templates are failing:"
        )
        lines.append(
            f"      CONNECTOR={name} docker compose run --rm test -m ql_prerequisites"
        )
        return "\n".join(lines)
    return None


def generate_dockerfile(connectors, version, base_image=None, etl_connectors=None):
    """Generate Dockerfile contents for the custom agent image."""
    from_image = base_image or f"montecarlodata/agent:{version}-{AGENT_TYPE}"
    lines = [f"FROM {from_image}", "", "ENV MCD_CUSTOM_CONNECTORS_ENABLED=true", ""]

    # The base agent image runs as a non-root user; switch to root for
    # package installation (apt-get, pip) then restore at the end.
    lines.append("USER root")
    lines.append("")

    for name in connectors:
        lines.append(f"# Connector: {name}")
        extra_content = read_dockerfile_extra(CONNECTORS_DIR, name)
        if extra_content:
            lines.append(extra_content)
        lines.append(f"COPY custom-connectors/{name}/ /opt/custom-connectors/{name}/")
        lines.append(
            f"RUN pip install --no-cache-dir -r /opt/custom-connectors/{name}/requirements.txt"
        )
        lines.append("")

    for name in etl_connectors or []:
        lines.append(f"# ETL Connector: {name}")
        extra_content = read_dockerfile_extra(ETL_CONNECTORS_DIR, name)
        if extra_content:
            lines.append(extra_content)
        lines.append(
            f"COPY custom-etl-connectors/{name}/ /opt/custom-etl-connectors/{name}/"
        )
        lines.append(
            f"RUN pip install --no-cache-dir -r /opt/custom-etl-connectors/{name}/requirements.txt"
        )
        lines.append("")

    lines.append("USER mcdagent")
    lines.append("")

    return "\n".join(lines)


def build_context(tmp_dir, connectors):
    """Copy connector artifacts into the temporary build context."""
    for name in connectors:
        dest = os.path.join(tmp_dir, "custom-connectors", name)
        os.makedirs(dest, exist_ok=True)

        # Copy source files from connectors/<name>/
        for filename in REQUIRED_SOURCE_FILES:
            shutil.copy2(os.path.join(CONNECTORS_DIR, name, filename), dest)

        # Copy Dockerfile.extra if present
        extra_path = os.path.join(CONNECTORS_DIR, name, "Dockerfile.extra")
        if os.path.isfile(extra_path):
            shutil.copy2(extra_path, dest)

        # Copy manifest.json from output/<name>/
        shutil.copy2(os.path.join(OUTPUT_DIR, name, "manifest.json"), dest)

        # Copy templates from output/<name>/templates/
        shutil.copytree(
            os.path.join(OUTPUT_DIR, name, "templates"),
            os.path.join(dest, "templates"),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Build a custom agent Docker image with connector artifacts"
    )
    parser.add_argument(
        "--version",
        default="latest",
        help="Agent base image version (default: latest)",
    )
    parser.add_argument(
        "names",
        nargs="*",
        help="Connector names to include. Auto-discovers from connectors/ and etl_connectors/ if omitted.",
    )
    parser.add_argument(
        "--docker-platform",
        default="linux/amd64",
        help="Docker platform for the image (default: linux/amd64)",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Output image tag (default: custom-agent:{version}-generic)",
    )
    parser.add_argument(
        "--base-image",
        default=None,
        help="Override the base Docker image (e.g. local_agent for local testing)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "full", "hybrid"],
        default="auto",
        help="Build mode: auto (default) detects per connector from manifest; full requires metadata support; hybrid requires custom SQL monitor support only (metadata pushed externally)",
    )
    args = parser.parse_args()

    # Determine connectors to include.
    # When names are given, resolve each to its directory. Otherwise auto-discover both.
    if args.names:
        connectors = []
        etl_connectors = []
        for name in args.names:
            base_dir, connector_type = resolve_connector_dir(name)
            if connector_type == "dw":
                connectors.append(name)
            elif connector_type == "etl":
                etl_connectors.append(name)
            else:
                print(
                    f"Error: '{name}' not found in connectors/ or etl_connectors/.",
                    file=sys.stderr,
                )
                sys.exit(1)
    else:
        connectors = discover_connectors()
        etl_connectors = discover_etl_connectors()

    if not connectors and not etl_connectors:
        print(
            "Error: No connectors found. Run tests and export first, or pass connector names.",
            file=sys.stderr,
        )
        print(
            "\n  CONNECTOR=<name> docker compose run --rm test --export\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve per-connector modes and validate DW connectors
    connector_modes = {}
    for name in connectors:
        connector_modes[name] = resolve_connector_mode(name, args.mode)

    all_errors = {}
    for name in connectors:
        errors = validate_connector(name, mode=connector_modes[name])
        if errors:
            all_errors[name] = errors

    # Validate ETL connectors
    for name in etl_connectors:
        errors = validate_etl_connector(name)
        if errors:
            all_errors[name] = errors

    if all_errors:
        print(
            "Error: Some connectors are missing required artifacts:\n", file=sys.stderr
        )
        for name, errors in all_errors.items():
            if name in connector_modes:
                print(f"  {name} (mode: {connector_modes[name]}):", file=sys.stderr)
            else:
                print(f"  {name} (etl):", file=sys.stderr)
            for err in errors:
                print(err, file=sys.stderr)
        print(
            "\nRun the full test suite and export first:\n"
            "  CONNECTOR=<name> docker compose run --rm test --export\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Warn when metric templates exist but prerequisite support is missing
    warnings = []
    for name in connectors:
        warning = check_metric_warnings(name)
        if warning:
            warnings.append(warning)

    if warnings:
        print(file=sys.stderr)
        print("WARNING", file=sys.stderr)
        print("-------", file=sys.stderr)
        print(
            "Some connectors have passing metric templates but metric monitors\n"
            "will NOT be supported because prerequisite templates are incomplete.\n",
            file=sys.stderr,
        )
        for warning in warnings:
            print(warning, file=sys.stderr)
        print(file=sys.stderr)
        try:
            response = input("Continue anyway? [y/N] ")
        except EOFError:
            response = ""
        if response.lower() not in ("y", "yes"):
            print("Aborted.", file=sys.stderr)
            sys.exit(1)
        print()

    tag = args.tag or f"custom-agent:{args.version}-{AGENT_TYPE}"

    # Build in a temp directory
    tmp_dir = tempfile.mkdtemp(prefix="agent-build-")
    try:
        # Generate Dockerfile
        dockerfile_content = generate_dockerfile(
            connectors,
            args.version,
            base_image=args.base_image,
            etl_connectors=etl_connectors,
        )
        dockerfile_path = os.path.join(tmp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Copy artifacts into build context
        if connectors:
            build_context(tmp_dir, connectors)
        if etl_connectors:
            build_etl_context(tmp_dir, etl_connectors)

        base_image = (
            args.base_image or f"montecarlodata/agent:{args.version}-{AGENT_TYPE}"
        )

        # Build summary
        all_connector_names = []
        if connectors:
            all_connector_names.extend(connectors)
        if etl_connectors:
            all_connector_names.extend(f"{n} (etl)" for n in etl_connectors)
        print(
            f"Building image '{tag}' with connectors: {', '.join(all_connector_names)}"
        )
        print(f"Base image: {base_image}")
        print(f"Docker platform: {args.docker_platform}")
        for name in connectors:
            mode = connector_modes[name]
            mode_label = (
                "hybrid (metadata pushed externally)" if mode == "hybrid" else "full"
            )
            print(f"  {name}: {mode_label}")
        for name in etl_connectors:
            print(f"  {name}: etl")
        print()

        # Run docker build
        result = subprocess.run(
            ["docker", "build", "--platform", args.docker_platform, "-t", tag, "."],
            cwd=tmp_dir,
            check=False,
        )
        if result.returncode != 0:
            print("\nError: Docker build failed.", file=sys.stderr)
            sys.exit(result.returncode)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\nSuccess! Image built: {tag}")
    print()
    if connectors:
        print("Connector modes:")
        hybrid_connectors = []
        for name in connectors:
            mode = connector_modes[name]
            mode_label = (
                "hybrid (metadata pushed externally)" if mode == "hybrid" else "full"
            )
            print(f"  {name}: {mode_label}")
            if mode == "hybrid":
                hybrid_connectors.append(name)
        print()
    else:
        hybrid_connectors = []
    if etl_connectors:
        print("ETL connectors:")
        for name in etl_connectors:
            print(f"  {name}")
        print()
    print("Next steps:")
    step = 1
    if connectors:
        print(
            f"  {step}. Verify DW connectors: docker run --rm --entrypoint ls {tag} /opt/custom-connectors/"
        )
        step += 1
    if etl_connectors:
        print(
            f"  {step}. Verify ETL connectors: docker run --rm --entrypoint ls {tag} /opt/custom-etl-connectors/"
        )
        step += 1
    print(f"  {step}. Push to your container registry:")
    print(f"     docker tag {tag} <your-registry>/{tag}")
    print(f"     docker push <your-registry>/{tag}")
    if hybrid_connectors:
        step += 1
        print(
            f"  {step}. Configure your external metadata pipeline to push metadata for: {', '.join(hybrid_connectors)}"
        )

    # Point users to credentials.json for self-hosted setup
    creds_files = []
    for name in connectors:
        creds_path = os.path.join(CONNECTORS_DIR, name, "credentials.json")
        if os.path.isfile(creds_path):
            creds_files.append(creds_path)
    for name in etl_connectors:
        creds_path = os.path.join(ETL_CONNECTORS_DIR, name, "credentials.json")
        if os.path.isfile(creds_path):
            creds_files.append(creds_path)

    if creds_files:
        print()
        print("Self-hosted credentials")
        print("-----------------------")
        print("Use your credentials.json as the self-hosted credentials in Monte Carlo")
        print("(swap in production values if you used dev/test credentials):")
        for path in creds_files:
            print(f"  {os.path.relpath(path, REPO_ROOT)}")
        print()
        print("See: https://docs.getmontecarlo.com/docs/self-hosted-credentials")


if __name__ == "__main__":
    main()
