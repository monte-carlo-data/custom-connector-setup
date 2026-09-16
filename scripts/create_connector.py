#!/usr/bin/env python3
"""Scaffold a new connector directory.

Usage:
    python scripts/create_connector.py <name>            # data-warehouse connector
    python scripts/create_connector.py <name> --etl      # ETL connector
    python scripts/create_connector.py <name> --bi       # BI connector

Example:
    python scripts/create_connector.py postgres
    python scripts/create_connector.py coalesce --etl
    python scripts/create_connector.py looker --bi
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys


def _regenerate_test_dockerfile(repo_root):
    """Run generate_test_dockerfile.py to regenerate the root Dockerfile."""
    script = os.path.join(repo_root, "scripts", "generate_test_dockerfile.py")
    if os.path.isfile(script):
        subprocess.run([sys.executable, script], check=False)


def _prompt(message, default=""):
    """Prompt user for input with a default value."""
    if default:
        response = input(f"{message} (default: {default}): ").strip()
        return response or default
    return input(f"{message}: ").strip()


def _create_db_connector(name, repo_root):
    """Create a data-warehouse connector scaffold."""
    connectors_dir = os.path.join(repo_root, "connectors")
    base_dir = os.path.join(connectors_dir, "_base")
    target_dir = os.path.join(connectors_dir, name)

    if os.path.exists(target_dir):
        print(f"Error: connector '{name}' already exists at {target_dir}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(os.path.join(base_dir, "connector.py")):
        print(f"Error: base template not found at {base_dir}/connector.py", file=sys.stderr)
        sys.exit(1)

    os.makedirs(target_dir)

    # Copy base connector.py
    shutil.copy2(
        os.path.join(base_dir, "connector.py"),
        os.path.join(target_dir, "connector.py"),
    )

    # Generate manifest.json with unique connector type
    connection_type = f"custom-connector-{secrets.token_hex(4)[:7]}"
    manifest = {"connection_type": connection_type, "connection_name": name, "asset_class": "warehouse", "credentials_schema": {}}
    with open(os.path.join(target_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Create credentials.json template
    creds = {"connect_args": {}}
    with open(os.path.join(target_dir, "credentials.json"), "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")

    # Create empty requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w") as f:
        f.write("# Add your database driver here, e.g.:\n# psycopg2-binary==2.9.9\n")

    # Create empty Dockerfile.extra for system dependencies
    with open(os.path.join(target_dir, "Dockerfile.extra"), "w") as f:
        f.write(
            "# Add Docker instructions for system dependencies needed by your driver.\n"
            "# For example, to install the Microsoft ODBC driver:\n"
            "#\n"
            "#   RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            "#       unixodbc-dev \\\n"
            "#       && apt-get clean && rm -rf /var/lib/apt/lists/*\n"
            "#\n"
            "# After editing, regenerate the test Dockerfile:\n"
            "#   python scripts/generate_test_dockerfile.py\n"
        )

    # Regenerate the test Dockerfile to pick up the new connector
    _regenerate_test_dockerfile(repo_root)

    print(f"Created connector '{name}' at connectors/{name}/")
    print(f"  connection_type: {connection_type}")
    print()
    print("Next steps:")
    print(f"  1. Edit connectors/{name}/connector.py        — fill in the stubs")
    print(f"  2. Edit connectors/{name}/credentials.json   — add credentials")
    print(f"  3. Edit connectors/{name}/manifest.json      — add credentials_schema (optional, cerberus format)")
    print(f"  4. Edit connectors/{name}/requirements.txt   — add database driver")
    print(f"  5. Edit connectors/{name}/Dockerfile.extra   — add system deps (if needed)")
    print(f"  6. docker compose build")
    print(f"  7. CONNECTOR={name} docker compose run test -m connection")


def _create_etl_connector(name, repo_root):
    """Create an ETL connector scaffold with interactive terminology prompts."""
    etl_dir = os.path.join(repo_root, "etl_connectors")
    target_dir = os.path.join(etl_dir, name)

    if os.path.exists(target_dir):
        print(f"Error: ETL connector '{name}' already exists at {target_dir}", file=sys.stderr)
        sys.exit(1)

    # Interactive terminology prompts
    print(f"Creating ETL connector '{name}'...")
    print()
    print(
        "'Group' is optional — only set it if the tool can host the same job in\n"
        "multiple named environments (e.g. Dev and Prod) and you need to tell them\n"
        "apart. Leave it blank if the tool has no such concept."
    )
    group_label = _prompt("What does this tool call a group of jobs? (optional, blank to skip)", "")
    job_label = _prompt("What does this tool call a job?", "Job")
    task_label = _prompt("What does this tool call a task?", "Task")
    icon_url = _prompt("Icon URL (leave blank to skip)", "")
    print()

    base_dir = os.path.join(etl_dir, "_base")
    if not os.path.exists(os.path.join(base_dir, "connector.py")):
        print(f"Error: base template not found at {base_dir}/connector.py", file=sys.stderr)
        sys.exit(1)

    os.makedirs(target_dir)

    # Copy base connector.py template
    shutil.copy2(
        os.path.join(base_dir, "connector.py"),
        os.path.join(target_dir, "connector.py"),
    )

    # Generate manifest.json with unique connector type and terminology
    connection_type = f"custom-etl-connector-{secrets.token_hex(4)[:7]}"
    manifest = {
        "connection_type": connection_type,
        "connection_name": name,
        "asset_class": "etl",
        "terminology": {
            "job": job_label,
            "task": task_label,
        },
    }
    # group is optional — only include it when the vendor has a group concept
    if group_label:
        manifest["terminology"]["group"] = group_label
    manifest["run_status_mapping"] = {}
    manifest["credentials_schema"] = {}
    if icon_url:
        manifest["icon_url"] = icon_url
    with open(os.path.join(target_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Create credentials.json template (vendor creds only — no MC keys)
    creds = {
        "connect_args": {
            "api_key": "",
            "api_url": "",
        }
    }
    with open(os.path.join(target_dir, "credentials.json"), "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")

    # Create empty requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w") as f:
        f.write("# Add your vendor API client library here, e.g.:\n# coalesce-sdk==1.0.0\n")

    # Create empty Dockerfile.extra for system dependencies
    with open(os.path.join(target_dir, "Dockerfile.extra"), "w") as f:
        f.write(
            "# Add Docker instructions for system dependencies needed by your connector.\n"
            "#\n"
            "# After editing, regenerate the test Dockerfile:\n"
            "#   python scripts/generate_test_dockerfile.py\n"
        )

    # Regenerate the test Dockerfile to pick up the new connector
    _regenerate_test_dockerfile(repo_root)

    print(f"Created ETL connector '{name}' at etl_connectors/{name}/")
    print(f"  connection_type: {connection_type}")
    group_summary = group_label if group_label else "(none)"
    print(f"  terminology: group={group_summary}, job={job_label}, task={task_label}")
    print()
    print("Next steps:")
    print(f"  1. Edit etl_connectors/{name}/connector.py      — implement fetch_metadata & fetch_run_details")
    print(f"  2. Edit etl_connectors/{name}/credentials.json  — add vendor API credentials")
    print(f"  3. Edit etl_connectors/{name}/manifest.json     — add credentials_schema (optional, cerberus format)")
    print(f"  4. Edit etl_connectors/{name}/requirements.txt  — add vendor client library")
    print(f"  5. Edit etl_connectors/{name}/Dockerfile.extra  — add system deps (if needed)")
    print(f"  6. docker compose build")
    print(f"  7. CONNECTOR={name} docker compose run test -m etl_connection")


def _create_bi_connector(name, repo_root):
    """Create a BI connector scaffold."""
    bi_dir = os.path.join(repo_root, "bi_connectors")
    target_dir = os.path.join(bi_dir, name)

    if os.path.exists(target_dir):
        print(f"Error: BI connector '{name}' already exists at {target_dir}", file=sys.stderr)
        sys.exit(1)

    # Interactive icon prompt (BI is metadata-only — asset types are per-asset
    # display data on the returned dicts, not manifest-level terminology)
    print(f"Creating BI connector '{name}'...")
    print()
    icon_url = _prompt("Icon URL (leave blank to skip)", "")
    print()

    base_dir = os.path.join(bi_dir, "_base")
    if not os.path.exists(os.path.join(base_dir, "connector.py")):
        print(f"Error: base template not found at {base_dir}/connector.py", file=sys.stderr)
        sys.exit(1)

    os.makedirs(target_dir)

    # Copy base connector.py template
    shutil.copy2(
        os.path.join(base_dir, "connector.py"),
        os.path.join(target_dir, "connector.py"),
    )

    # Generate manifest.json with unique connector type
    connection_type = f"custom-bi-connector-{secrets.token_hex(4)[:7]}"
    manifest = {
        "connection_type": connection_type,
        "connection_name": name,
        "asset_class": "bi",
    }
    manifest["credentials_schema"] = {}
    if icon_url:
        manifest["icon_url"] = icon_url
    with open(os.path.join(target_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Create credentials.json template (vendor creds only — no MC keys)
    creds = {
        "connect_args": {
            "api_key": "",
            "api_url": "",
        }
    }
    with open(os.path.join(target_dir, "credentials.json"), "w") as f:
        json.dump(creds, f, indent=2)
        f.write("\n")

    # Create empty requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w") as f:
        f.write("# Add your vendor API client library here, e.g.:\n# requests==2.32.0\n")

    # Create empty Dockerfile.extra for system dependencies
    with open(os.path.join(target_dir, "Dockerfile.extra"), "w") as f:
        f.write(
            "# Add Docker instructions for system dependencies needed by your connector.\n"
            "#\n"
            "# After editing, regenerate the test Dockerfile:\n"
            "#   python scripts/generate_test_dockerfile.py\n"
        )

    # Regenerate the test Dockerfile to pick up the new connector
    _regenerate_test_dockerfile(repo_root)

    print(f"Created BI connector '{name}' at bi_connectors/{name}/")
    print(f"  connection_type: {connection_type}")
    print()
    print("Next steps:")
    print(f"  1. Edit bi_connectors/{name}/connector.py      — implement fetch_metadata")
    print(f"  2. Edit bi_connectors/{name}/credentials.json  — add vendor API credentials")
    print(f"  3. Edit bi_connectors/{name}/manifest.json     — add credentials_schema (optional, cerberus format)")
    print(f"  4. Edit bi_connectors/{name}/requirements.txt  — add vendor client library")
    print(f"  5. Edit bi_connectors/{name}/Dockerfile.extra  — add system deps (if needed)")
    print(f"  6. docker compose build")
    print(f"  7. CONNECTOR={name} docker compose run test -m bi_connection")


def main():
    parser = argparse.ArgumentParser(description="Create a new connector scaffold")
    parser.add_argument("name", help="Connector name (e.g. postgres, coalesce)")
    # A connector is exactly one family — passing two type flags is an error,
    # not a silent pick of whichever branch runs first.
    type_group = parser.add_mutually_exclusive_group()
    type_group.add_argument(
        "--etl",
        action="store_true",
        help="Create an ETL pipeline connector instead of a data-warehouse connector",
    )
    type_group.add_argument(
        "--bi",
        action="store_true",
        help="Create a BI connector instead of a data-warehouse connector",
    )
    args = parser.parse_args()

    name = args.name.lower().replace(" ", "_").replace("-", "_")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.etl:
        _create_etl_connector(name, repo_root)
    elif args.bi:
        _create_bi_connector(name, repo_root)
    else:
        _create_db_connector(name, repo_root)


if __name__ == "__main__":
    main()
