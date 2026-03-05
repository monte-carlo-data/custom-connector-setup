#!/usr/bin/env python3
"""Scaffold a new integration directory.

Usage:
    python scripts/create_integration.py <name>

Example:
    python scripts/create_integration.py postgres
"""
import argparse
import json
import os
import secrets
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description="Create a new integration scaffold")
    parser.add_argument("name", help="Integration name (e.g. postgres, snowflake)")
    args = parser.parse_args()

    name = args.name.lower().replace(" ", "_").replace("-", "_")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    integrations_dir = os.path.join(repo_root, "integrations")
    base_dir = os.path.join(integrations_dir, "_base")
    target_dir = os.path.join(integrations_dir, name)

    if os.path.exists(target_dir):
        print(f"Error: integration '{name}' already exists at {target_dir}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(os.path.join(base_dir, "integration.py")):
        print(f"Error: base template not found at {base_dir}/integration.py", file=sys.stderr)
        sys.exit(1)

    os.makedirs(target_dir)

    # Copy base integration.py
    shutil.copy2(
        os.path.join(base_dir, "integration.py"),
        os.path.join(target_dir, "integration.py"),
    )

    # Generate manifest.json with unique connection type
    connection_type = f"custom-integration-{secrets.token_hex(4)[:7]}"
    manifest = {"connection_type": connection_type, "name": name}
    with open(os.path.join(target_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Create empty .env
    with open(os.path.join(target_dir, ".env"), "w") as f:
        f.write("# Add your database credentials here.\n")

    # Create empty requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w") as f:
        f.write("# Add your database driver here, e.g.:\n# psycopg2-binary==2.9.9\n")

    print(f"Created integration '{name}' at integrations/{name}/")
    print(f"  connection_type: {connection_type}")
    print()
    print("Next steps:")
    print(f"  1. Edit integrations/{name}/integration.py  — fill in the stubs")
    print(f"  2. Edit integrations/{name}/.env             — add credentials")
    print(f"  3. Edit integrations/{name}/requirements.txt — add database driver")
    print(f"  4. docker compose build")
    print(f"  5. INTEGRATION={name} docker compose run test -m connection")


if __name__ == "__main__":
    main()
