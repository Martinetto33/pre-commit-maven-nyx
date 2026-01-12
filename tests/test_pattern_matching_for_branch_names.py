import pytest

from pre_commit_maven_nyx.maven_nyx_check import matches_protected_branch


@pytest.mark.parametrize(
    "branch,patterns,expected",
    [
        # Exact matches
        ("main", ["main", "master"], True),
        ("master", ["main", "master"], True),
        ("develop", ["main", "master"], False),

        # Simple wildcard
        ("release/1.0", ["release/*"], True),
        ("release/v2", ["release/*"], True),
        ("release/", ["release/*"], True),

        # Wildcard DOES cross slashes
        ("release/1.0/hotfix", ["release/*"], True),

        # Mixed patterns
        ("release/1.0", ["main", "release/*"], True),
        ("feature/foo", ["main", "release/*"], False),

        # Multiple wildcards
        ("release/1.2.3", ["release/*.*.*"], True),
        ("release/1.2", ["release/*.*.*"], False),

        # Case sensitivity
        ("Main", ["main"], False),
        ("release/ABC", ["release/*"], True),

        # Empty pattern list
        ("main", [], False),
    ],
)
def test_is_protected_branch(branch, patterns, expected):
    assert matches_protected_branch(branch, patterns) is expected

