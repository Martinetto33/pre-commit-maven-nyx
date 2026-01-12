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
import fnmatch


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[1;31m",  # Bold red
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool):
        super().__init__("%(levelname)s: %(message)s")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if not self.use_color:
            return msg

        color = self.COLORS.get(record.levelno)
        if not color:
            return msg

        return f"{color}{msg}{self.RESET}"


def _supports_color() -> bool:
    """
    Returns True if the current stdout supports ANSI colors.
    """
    if not sys.stdout.isatty():
        return False

    # Windows: modern terminals support ANSI; older cmd.exe may not
    if os.name == "nt":
        return "WT_SESSION" in os.environ or "ANSICON" in os.environ

    return True


def setup_logging():
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter(use_color=_supports_color()))

    root.addHandler(handler)
    root.setLevel(logging.INFO)


import subprocess


def get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch != "HEAD" else "DETACHED"
    except Exception:
        return "unknown"


def load_config(config_path: Path) -> dict:
    """Load and validate configuration file."""
    if not config_path.exists():
        logging.warning(f"Config file not found: {config_path}")
        logging.warning(
            "Using default configuration; to avoid this, create a .pre-commit-maven-nyx.json file. "
            "More info at https://github.com/Martinetto33/pre-commit-maven-nyx?tab=readme-ov-file#usage."
        )
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse config file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        sys.exit(1)


def matches_protected_branch(branch: str, patterns: list[str]) -> bool:
    """Checks whether the given branch matches any of the given patterns (by also performing
    * expansion and ? expansion as in fnmatch)."""
    return any(fnmatch.fnmatchcase(branch, p) for p in patterns)


def is_protected_branch(config: dict) -> bool:
    branch = get_current_branch()
    protected = config.get("protected_branches", ["master", "main"])
    return matches_protected_branch(branch, protected)


def load_nyx_version(nyx_file: Path) -> str:
    if not nyx_file.exists():
        logging.error(f"Nyx version file not found: {nyx_file}")
        sys.exit(1)
    try:
        data = json.loads(nyx_file.read_text())
        return read_nyx_version(nyx_file, data)
    except Exception as e:
        logging.error(f"Failed to parse Nyx JSON: {e}")
        sys.exit(1)


def read_nyx_version(nyx_file: Path, nyx_json_data: dict) -> str:
    # Ensuring Major, Minor and Patch are present
    if not nyx_json_data.get("versionMajorNumber") or not nyx_json_data.get(
            "versionMinorNumber") or not nyx_json_data.get("versionPatchNumber"):
        logging.error(
            f"Failed to parse Nyx JSON: Missing Major, Minor or Patch version. Check your {nyx_file} for fields: versionMajorNumber, versionMinorNumber and versionPatchNumber")
        sys.exit(1)
    return f"{nyx_json_data.get('versionMajorNumber')}.{nyx_json_data.get('versionMinorNumber')}.{nyx_json_data.get('versionPatchNumber')}"


def get_pom_version(pom_path: Path) -> str:
    if not pom_path.exists():
        logging.error(f"pom.xml not found: {pom_path}")
        sys.exit(1)

    # Handle Maven POM namespace
    namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}
    try:
        tree = elementTree.parse(pom_path)
        root = tree.getroot()
        version_elem = root.find("m:version", namespaces)
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
    """Attempts to find Liquibase files for the given version. Breaks execution if not found."""
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
        else:
            logging.error(
                f"Liquibase files missing for version {version} (checked directory: {lb_dir}). "
                f"Expected files: {forward} and {rollback}. "
                "Refusing to commit on protected branch without Liquibase files. "
                "You can disable this check by setting check_liquibase=false in .pre-commit-maven-nyx.json."
            )
        sys.exit(1)


def main(argv: list[str] | None = None) -> int:
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
            f"Branch '{current_branch}' not in protected list {protected_branches} - skipping checks"
        )
        return 0

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
                f"Maven version ({pom_version}) != Nyx version ({nyx_version}). "
                "Refusing to commit on protected branch unless versions match. "
                "You can disable this check by setting check_maven=false in .pre-commit-maven-nyx.json. "
            )
            sys.exit(1)
        logging.info("Maven version matches Nyx")

    # Validate Liquibase
    if check_liquibase:
        validate_liquibase_files(nyx_version, lb_dir)
        logging.info("Liquibase files present")

    logging.info("All checks passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
