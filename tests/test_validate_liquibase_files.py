import pytest

from pre_commit_maven_nyx.maven_nyx_check import validate_liquibase_files


def test_validate_liquibase_files_missing(tmp_path):
    lb_dir = tmp_path / "changelog"
    lb_dir.mkdir()
    # do not create files
    with pytest.raises(SystemExit):
        validate_liquibase_files("1.2.3", lb_dir)

def test_validate_liquibase_files_present(tmp_path):
    lb_dir = tmp_path / "changelog"
    lb_dir.mkdir()
    (lb_dir / "1.2.3.sql").write_text("-- changelog")
    (lb_dir / "1.2.3_rollback.sql").write_text("-- rollback")
    # Should not raise
    validate_liquibase_files("1.2.3", lb_dir)
