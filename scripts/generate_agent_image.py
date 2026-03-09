#!/usr/bin/env python3
"""Build a custom agent Docker image with integration artifacts.

Usage:
    python scripts/generate_agent_image.py --agent-type aws-generic
    python scripts/generate_agent_image.py --agent-type lambda --version 1.4.12
    python scripts/generate_agent_image.py --agent-type azure --integration postgres --integration teradata
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
INTEGRATIONS_DIR = os.path.join(REPO_ROOT, "integrations")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

REQUIRED_SOURCE_FILES = ["integration.py", "manifest.json", "requirements.txt"]


def discover_integrations():
    """Return integration names that have output directories."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(OUTPUT_DIR)
        if os.path.isdir(os.path.join(OUTPUT_DIR, name)) and name != "_base"
    )


def validate_integration(name):
    """Validate that an integration has all required artifacts. Returns list of errors."""
    errors = []

    capabilities_path = os.path.join(OUTPUT_DIR, name, "capabilities.json")
    if not os.path.isfile(capabilities_path):
        errors.append(f"  - Missing output/{name}/capabilities.json")
    else:
        with open(capabilities_path) as f:
            caps = json.load(f)
        if not caps.get("capabilities", {}).get("supports_metadata"):
            errors.append(
                f"  - Metadata collection has not been implemented — this is a requirement."
            )

    templates_dir = os.path.join(OUTPUT_DIR, name, "templates")
    if not os.path.isdir(templates_dir) or not os.listdir(templates_dir):
        errors.append(f"  - Missing or empty output/{name}/templates/")

    for filename in REQUIRED_SOURCE_FILES:
        path = os.path.join(INTEGRATIONS_DIR, name, filename)
        if not os.path.isfile(path):
            errors.append(f"  - Missing integrations/{name}/{filename}")

    return errors


def check_metric_warnings(name):
    """Return a warning string if metric monitors are unsupported but some metrics pass, else None."""
    capabilities_path = os.path.join(OUTPUT_DIR, name, "capabilities.json")
    if not os.path.isfile(capabilities_path):
        return None

    with open(capabilities_path) as f:
        caps = json.load(f)

    supports_metrics = caps.get("capabilities", {}).get("supports_metric_monitors", False)
    metrics = caps.get("metrics", {})
    passing_metrics = sorted(m for m, v in metrics.items() if v is True)

    if not supports_metrics and passing_metrics:
        lines = [
            f"  {name}:",
            f"    supports_metric_monitors = false",
            f"    {len(passing_metrics)} metric(s) have passing templates:",
        ]
        for metric in passing_metrics:
            lines.append(f"      - {metric}")
        lines.append(f"    Re-run tests to see which prerequisite templates are failing:")
        lines.append(f"      INTEGRATION={name} docker compose run test -m ql_prerequisites")
        return "\n".join(lines)
    return None


def generate_dockerfile(integrations, version, agent_type):
    """Generate Dockerfile contents for the custom agent image."""
    lines = [f"FROM montecarlodata/agent:{version}-{agent_type}", ""]

    for name in integrations:
        lines.append(f"# Integration: {name}")
        lines.append(f"COPY custom-integrations/{name}/ /opt/custom-integrations/{name}/")
        lines.append(
            f"RUN pip install --no-cache-dir -r /opt/custom-integrations/{name}/requirements.txt"
        )
        lines.append("")

    return "\n".join(lines)


def build_context(tmp_dir, integrations):
    """Copy integration artifacts into the temporary build context."""
    for name in integrations:
        dest = os.path.join(tmp_dir, "custom-integrations", name)
        os.makedirs(dest, exist_ok=True)

        # Copy source files from integrations/<name>/
        for filename in REQUIRED_SOURCE_FILES:
            shutil.copy2(os.path.join(INTEGRATIONS_DIR, name, filename), dest)

        # Copy capabilities.json from output/<name>/
        shutil.copy2(os.path.join(OUTPUT_DIR, name, "capabilities.json"), dest)

        # Copy templates from output/<name>/templates/
        shutil.copytree(
            os.path.join(OUTPUT_DIR, name, "templates"),
            os.path.join(dest, "templates"),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Build a custom agent Docker image with integration artifacts"
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
        "--integration",
        action="append",
        dest="integrations",
        help="Integration to include (repeatable). Defaults to all with output/",
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
    args = parser.parse_args()

    # Determine integrations to include
    if args.integrations:
        integrations = args.integrations
    else:
        integrations = discover_integrations()

    if not integrations:
        print(
            "Error: No integrations found. Run tests and export first, or specify --integration.",
            file=sys.stderr,
        )
        print(
            "\n  INTEGRATION=<name> docker compose run test\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate all integrations
    all_errors = {}
    for name in integrations:
        errors = validate_integration(name)
        if errors:
            all_errors[name] = errors

    if all_errors:
        print("Error: Some integrations are missing required artifacts:\n", file=sys.stderr)
        for name, errors in all_errors.items():
            print(f"  {name}:", file=sys.stderr)
            for err in errors:
                print(err, file=sys.stderr)
        print(
            "\nRun tests and export first:\n"
            "  INTEGRATION=<name> docker compose run test\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Warn when metric templates exist but prerequisite support is missing
    warnings = []
    for name in integrations:
        warning = check_metric_warnings(name)
        if warning:
            warnings.append(warning)

    if warnings:
        print(file=sys.stderr)
        print("WARNING", file=sys.stderr)
        print("-------", file=sys.stderr)
        print(
            "Some integrations have passing metric templates but metric monitors\n"
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
        dockerfile_content = generate_dockerfile(integrations, args.version, args.agent_type)
        dockerfile_path = os.path.join(tmp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Copy artifacts into build context
        build_context(tmp_dir, integrations)

        print(f"Building image '{tag}' with integrations: {', '.join(integrations)}")
        print(f"Base image: montecarlodata/agent:{args.version}-{args.agent_type}")
        print(f"Docker platform: {args.docker_platform}")
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
    print("Next steps:")
    print(f"  1. Verify: docker run --rm --entrypoint ls {tag} /opt/custom-integrations/")
    print(f"  2. Push to your container registry:")
    print(f"     docker tag {tag} <your-registry>/{tag}")
    print(f"     docker push <your-registry>/{tag}")


if __name__ == "__main__":
    main()
