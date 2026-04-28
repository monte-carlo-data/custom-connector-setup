#!/usr/bin/env python3
"""Build a custom agent Docker image with connector artifacts.

Usage:
    python scripts/generate_agent_image.py --agent-type aws-generic
    python scripts/generate_agent_image.py --agent-type lambda --version 1.4.12
    python scripts/generate_agent_image.py --agent-type azure --connector postgres --connector teradata

Hybrid mode (metadata pushed externally — only metric monitor support required):
    python scripts/generate_agent_image.py --agent-type aws-generic --mode hybrid
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

VALID_AGENT_TYPES = ["aws-generic", "aws-proxied", "azure", "cloudrun", "lambda"]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONNECTORS_DIR = os.path.join(REPO_ROOT, "connectors")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

REQUIRED_SOURCE_FILES = ["connector.py", "manifest.json", "requirements.txt"]


def discover_connectors():
    """Return connector names that have output directories."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(OUTPUT_DIR)
        if os.path.isdir(os.path.join(OUTPUT_DIR, name)) and name != "_base"
    )


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
                    f"  - Custom SQL monitor support has not been implemented — this is a requirement for hybrid mode."
                )
            if manifest.get("capabilities", {}).get("supports_metadata"):
                errors.append(
                    f"  - Metadata is implemented but hybrid mode requires metadata to be pushed externally."
                    f" Use --mode full instead, or remove MetadataQueryTemplates."
                )
        else:
            if not manifest.get("capabilities", {}).get("supports_metadata"):
                errors.append(
                    f"  - Metadata collection has not been implemented — this is a requirement."
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

    supports_ql = manifest.get("capabilities", {}).get("supports_full_query_language", False)
    metrics = manifest.get("metrics", {})
    passing_metrics = sorted(m for m, v in metrics.items() if v is True)

    if not supports_ql and passing_metrics:
        lines = [
            f"  {name}:",
            f"    supports_full_query_language = false",
            f"    {len(passing_metrics)} metric(s) have passing templates:",
        ]
        for metric in passing_metrics:
            lines.append(f"      - {metric}")
        lines.append(f"    Re-run tests to see which prerequisite templates are failing:")
        lines.append(f"      CONNECTOR={name} docker compose run --rm test -m ql_prerequisites")
        return "\n".join(lines)
    return None


def generate_dockerfile(connectors, version, agent_type, base_image=None):
    """Generate Dockerfile contents for the custom agent image."""
    from_image = base_image or f"montecarlodata/agent:{version}-{agent_type}"
    lines = [f"FROM {from_image}", "", "ENV MCD_CUSTOM_CONNECTORS_ENABLED=true", ""]

    for name in connectors:
        lines.append(f"# Connector: {name}")
        lines.append(f"COPY custom-connectors/{name}/ /opt/custom-connectors/{name}/")
        lines.append(
            f"RUN pip install --no-cache-dir -r /opt/custom-connectors/{name}/requirements.txt"
        )
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
        "--agent-type",
        required=True,
        choices=VALID_AGENT_TYPES,
        help="Agent type (e.g. aws-generic, lambda, azure)",
    )
    parser.add_argument(
        "--version",
        default="latest",
        help="Agent base image version (default: latest)",
    )
    parser.add_argument(
        "--connector",
        action="append",
        dest="connectors",
        help="Connector to include (repeatable). Defaults to all with output/",
    )
    parser.add_argument(
        "--docker-platform",
        default="linux/amd64",
        help="Docker platform for the image (default: linux/amd64)",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Output image tag (default: custom-agent:{version}-{agent-type})",
    )
    parser.add_argument(
        "--base-image",
        default=None,
        help="Override the base Docker image (e.g. local_agent for local testing)",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "hybrid"],
        default="full",
        help="Build mode: full (default) requires metadata support; hybrid requires custom SQL monitor support only (metadata pushed externally)",
    )
    args = parser.parse_args()

    # Determine connectors to include
    if args.connectors:
        connectors = args.connectors
    else:
        connectors = discover_connectors()

    if not connectors:
        print(
            "Error: No connectors found. Run tests and export first, or specify --connector.",
            file=sys.stderr,
        )
        print(
            "\n  CONNECTOR=<name> docker compose run --rm test --export\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate all connectors
    all_errors = {}
    for name in connectors:
        errors = validate_connector(name, mode=args.mode)
        if errors:
            all_errors[name] = errors

    if all_errors:
        print("Error: Some connectors are missing required artifacts:\n", file=sys.stderr)
        for name, errors in all_errors.items():
            print(f"  {name}:", file=sys.stderr)
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

    tag = args.tag or f"custom-agent:{args.version}-{args.agent_type}"

    # Build in a temp directory
    tmp_dir = tempfile.mkdtemp(prefix="agent-build-")
    try:
        # Generate Dockerfile
        dockerfile_content = generate_dockerfile(
            connectors, args.version, args.agent_type, base_image=args.base_image
        )
        dockerfile_path = os.path.join(tmp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Copy artifacts into build context
        build_context(tmp_dir, connectors)

        base_image = args.base_image or f"montecarlodata/agent:{args.version}-{args.agent_type}"
        print(f"Building image '{tag}' with connectors: {', '.join(connectors)}")
        print(f"Base image: {base_image}")
        print(f"Docker platform: {args.docker_platform}")
        if args.mode == "hybrid":
            print(f"Mode: hybrid (metadata pushed externally)")
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
    if args.mode == "hybrid":
        print("Mode: hybrid (metadata pushed externally)")
    print()
    print("Next steps:")
    print(f"  1. Verify: docker run --rm --entrypoint ls {tag} /opt/custom-connectors/")
    print(f"  2. Push to your container registry:")
    print(f"     docker tag {tag} <your-registry>/{tag}")
    print(f"     docker push <your-registry>/{tag}")
    if args.mode == "hybrid":
        print(f"  3. Configure your external metadata pipeline to push metadata for the integrated data source")


if __name__ == "__main__":
    main()
