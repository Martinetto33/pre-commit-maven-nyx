#!/usr/bin/env python3
"""
Pre-commit hook to validate:
1. pom.xml version == Nyx version (from JSON file)
2. Liquibase files <version>.sql and <version>_rollback.sql exist
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_current_branch() -> str:
    try:
        return os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
    except Exception:
        return "unknown"


def is_protected_branch(config: dict) -> bool:
    branch = get_current_branch()
    protected = config.get("protected_branches", ["master", "main"])
    return branch in protected


def load_nyx_version(nyx_file: Path) -> str:
    if not nyx_file.exists():
        print(f"::error::Nyx version file not found: {nyx_file}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(nyx_file.read_text())
        return data.get("version") or data.get("current_version")
    except Exception as e:
        print(f"::error::Failed to parse Nyx JSON: {e}", file=sys.stderr)
        sys.exit(1)


def get_pom_version(pom_path: Path) -> str:
    if not pom_path.exists():
        print(f"::error::pom.xml not found: {pom_path}", file=sys.stderr)
        sys.exit(1)

    # Handle Maven POM namespace
    namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}
    try:
        tree = ET.parse(pom_path)
        version_elem = tree.find(".//m:version", namespaces)
        if version_elem is not None:
            return version_elem.text.strip()
        # Try parent version if no version defined (multi-module safety)
        parent_version = tree.find(".//m:parent/m:version", namespaces)
        if parent_version is not None:
            return parent_version.text.strip()
        raise ValueError("No <version> found in pom.xml or parent")
    except Exception as e:
        print(f"::error::Failed to parse pom.xml: {e}", file=sys.stderr)
        sys.exit(1)


def validate_liquibase_files(version: str, lb_dir: Path):
    forward = lb_dir / f"{version}.sql"
    rollback = lb_dir / f"{version}_rollback.sql"

    missing_files = []
    if not forward.exists():
        missing_files.append(str(forward))
    if not rollback.exists():
        missing_files.append(str(rollback))

    if missing_files:
        for f in missing_files:
            print(f"::error::Missing Liquibase file: {f}", file=sys.stderr)
        sys.exit(1)


def main():
    # Load optional config file (from project root)
    config_path = Path(".pre-commit-maven-nyx.json")
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception as e:
            print(f"::error::Invalid config JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Skip if not on protected branch
    if not is_protected_branch(config):
        print("::notice::Not on protected branch – skipping checks")
        return

    # Paths from config (with defaults)
    nyx_file = Path(config.get("nyx_version_file", "nyx-state.json"))
    pom_file = Path(config.get("pom_file", "pom.xml"))
    lb_dir = Path(config.get("liquibase_dir", "src/main/resources/db/changelog"))

    # Enable flags (default: True)
    check_maven = config.get("check_maven", True)
    check_liquibase = config.get("check_liquibase", True)

    # Get canonical version from Nyx
    nyx_version = load_nyx_version(nyx_file)

    # Validate Maven version
    if check_maven:
        pom_version = get_pom_version(pom_file)
        if pom_version != nyx_version:
            print(
                f"::error::Maven version ({pom_version}) ≠ Nyx version ({nyx_version})",
                file=sys.stderr
            )
            sys.exit(1)

    # Validate Liquibase files
    if check_liquibase:
        validate_liquibase_files(nyx_version, lb_dir)

    print("::notice::✅ Version and Liquibase checks passed")


if __name__ == "__main__":
    main()
