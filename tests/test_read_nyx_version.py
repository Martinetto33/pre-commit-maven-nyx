import json

import pytest

from pre_commit_maven_nyx.maven_nyx_check import load_nyx_version


def test_read_nyx_version_valid(tmp_path):
    data = {
        "versionMajorNumber": 1,
        "versionMinorNumber": 2,
        "versionPatchNumber": 3
    }
    p = tmp_path / "nyx.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_nyx_version(p)
    assert loaded == "1.2.3"

def test_read_nyx_version_missing_field(tmp_path):
    data = {
        "versionMajorNumber": 1,
        "versionMinorNumber": 2
        # missing patch
    }
    p = tmp_path / "nyx.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit):
        load_nyx_version(p)
