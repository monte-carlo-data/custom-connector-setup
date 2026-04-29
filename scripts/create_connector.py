#!/usr/bin/env python3
"""Scaffold a new connector directory.

Usage:
    python scripts/create_connector.py <name>

Example:
    python scripts/create_connector.py postgres
"""
import argparse
import json
import os
import secrets
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description="Create a new connector scaffold")
    parser.add_argument("name", help="Connector name (e.g. postgres, snowflake)")
    args = parser.parse_args()

    name = args.name.lower().replace(" ", "_").replace("-", "_")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    manifest = {"connection_type": connection_type, "name": name}
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

    print(f"Created connector '{name}' at connectors/{name}/")
    print(f"  connection_type: {connection_type}")
    print()
    print("Next steps:")
    print(f"  1. Edit connectors/{name}/connector.py      — fill in the stubs")
    print(f"  2. Edit connectors/{name}/credentials.json — add credentials")
    print(f"  3. Edit connectors/{name}/requirements.txt — add database driver")
    print(f"  4. docker compose build")
    print(f"  5. CONNECTOR={name} docker compose run test -m connection")


if __name__ == "__main__":
    main()
