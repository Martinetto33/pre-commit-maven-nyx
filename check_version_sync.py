#!/usr/bin/env python3
"""
Pre-commit hook to validate:
1. pom.xml version == Nyx version (from JSON file)
2. Liquibase files <version>.sql and <version>_rollback.sql exist
"""

import json
import os
import sys
import xml.etree.ElementTree as elementTree
import logging
from pathlib import Path


def setup_logging():
    # Use a simple format without timestamps (cleaner for pre-commit)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout
    )
    # Prevent double logs if imported elsewhere
    logging.getLogger().handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def get_current_branch() -> str:
    try:
        return os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
    except Exception:
        return "unknown"


def load_config(config_path: Path) -> dict:
    """Load and validate configuration file."""
    if not config_path.exists():
        logging.warning(f"Config file not found: {config_path}")
        logging.warning("""
        Using default configuration; to avoid this, create a .pre-commit-maven-nyx.json file. 
        More info at https://github.com/Martinetto33/pre-commit-maven-nyx?tab=readme-ov-file#usage.
        """)
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse config file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        sys.exit(1)


def is_protected_branch(config: dict) -> bool:
    branch = get_current_branch()
    protected = config.get("protected_branches", ["master", "main"])
    return branch in protected


def load_nyx_version(nyx_file: Path) -> str:
    if not nyx_file.exists():
        logging.error(f"Nyx version file not found: {nyx_file}")
        sys.exit(1)
    try:
        data = json.loads(nyx_file.read_text())
        return data.get("version") or data.get("current_version")
    except Exception as e:
        logging.error(f"Failed to parse Nyx JSON: {e}")
        sys.exit(1)


def get_pom_version(pom_path: Path) -> str:
    if not pom_path.exists():
        logging.error(f"pom.xml not found: {pom_path}")
        sys.exit(1)

    # Handle Maven POM namespace
    namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}
    try:
        tree = elementTree.parse(pom_path)
        version_elem = tree.find(".//m:version", namespaces)
        if version_elem is not None:
            return version_elem.text.strip()
        # Try parent version if no version defined (multi-module safety)
        parent_version = tree.find(".//m:parent/m:version", namespaces)
        if parent_version is not None:
            return parent_version.text.strip()
        raise ValueError("No <version> found in pom.xml or parent")
    except Exception as e:
        logging.error(f"Failed to parse pom.xml: {e}")
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
            logging.error(f"Missing Liquibase file: {f}")
        sys.exit(1)


def main():
    setup_logging()

    # Load config file
    config_path = Path(".pre-commit-maven-nyx.json")
    config = load_config(config_path)

    # Determine current branch
    current_branch = get_current_branch()
    logging.info(f"Current branch: {current_branch}")

    # Get protected branches (default to master/main)
    protected_branches = config.get("protected_branches", ["master", "main"])
    if not isinstance(protected_branches, list):
        logging.error(
            f"Protected branches in file {config_path} must be a list of strings; got `{protected_branches}` instead.")
        sys.exit(1)

    # Skip if not on a protected branch
    if not is_protected_branch(config):
        logging.info(
            f"Branch '{current_branch}' not in protected list {protected_branches} – skipping checks"
        )
        return

    logging.info(f"Running checks on protected branch '{current_branch}'")

    # Paths (with defaults)
    nyx_file = Path(config.get("nyx_version_file", "nyx-state.json"))
    pom_file = Path(config.get("pom_file", "pom.xml"))
    lb_dir = Path(config.get("liquibase_dir", "src/main/resources/db/changelog"))

    # Enabled flags (default: True)
    check_maven = config.get("check_maven", True)
    check_liquibase = config.get("check_liquibase", True)

    # Validate types
    if not isinstance(check_maven, bool) or not isinstance(check_liquibase, bool):
        logging.error(
            f"check_maven and check_liquibase must be booleans; got check_maven={check_maven} and check_liquibase={check_liquibase} instead.")
        sys.exit(1)

    # Get Nyx version (required for both checks)
    nyx_version = load_nyx_version(nyx_file)
    logging.info(f"Next version detected by Nyx: {nyx_version}")

    # Validate Maven
    if check_maven:
        pom_version = get_pom_version(pom_file)
        if pom_version != nyx_version:
            logging.error(
                f"""
                Maven version ({pom_version}) ≠ Nyx version ({nyx_version}).
                Refusing to commit on protected branch unless versions match.
                You can disable this check by setting check_maven=false in .pre-commit-maven-nyx.json.
                """
            )
            sys.exit(1)
        logging.info("✅ Maven version matches Nyx")

    # Validate Liquibase
    if check_liquibase:
        validate_liquibase_files(nyx_version, lb_dir)
        logging.info("✅ Liquibase files present")

    logging.info("All checks passed!")


if __name__ == "__main__":
    main()
