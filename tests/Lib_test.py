from pathlib import Path

from AllGitStatus.Lib import GenerateRepos


# ----------------------------------------------------------------------
def test_GenerateRepos(fs) -> None:
    fs.create_dir("/root")
    fs.create_dir("/root/repo1/.git")
    fs.create_dir("/root/collection/repo2/.git")
    fs.create_dir("/root/collection/repo3/.git")
    fs.create_dir("/root/collection/repo4/.git")
    fs.create_dir("/root/this/one/is/deeply/nested/repo5/.git")

    assert set(GenerateRepos(Path("/root"))) == {
        Path("/root/repo1"),
        Path("/root/collection/repo2"),
        Path("/root/collection/repo3"),
        Path("/root/collection/repo4"),
        Path("/root/this/one/is/deeply/nested/repo5"),
    }
