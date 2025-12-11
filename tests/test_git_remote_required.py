"""Tests for git-remote-required mode and git_remote_url parameter."""

from pathlib import Path

import pytest

from mcp_agent_mail.app import _compute_project_slug, ToolExecutionError
from mcp_agent_mail.config import get_settings


class TestGitRemoteUrlSlugDerivation:
    """Tests for slug derivation from git_remote_url parameter."""

    def test_git_remote_url_ssh_format(self, tmp_path: Path, monkeypatch) -> None:
        """SSH-style git URL should produce consistent slug."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        remote_url = "git@github.com:myorg/myrepo.git"
        slug = _compute_project_slug(str(tmp_path), git_remote_url=remote_url)

        # Slug should be based on repo name + hash of normalized URL
        assert slug.startswith("myrepo-")
        assert len(slug) > len("myrepo-")  # Has hash suffix

    def test_git_remote_url_https_format(self, tmp_path: Path, monkeypatch) -> None:
        """HTTPS-style git URL should produce consistent slug."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        remote_url = "https://github.com/myorg/myrepo.git"
        slug = _compute_project_slug(str(tmp_path), git_remote_url=remote_url)

        assert slug.startswith("myrepo-")
        assert len(slug) > len("myrepo-")

    def test_same_remote_different_paths_same_slug(self, tmp_path: Path, monkeypatch) -> None:
        """Different local paths with same git remote should get same slug."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        remote_url = "git@github.com:acme/backend.git"
        path1 = tmp_path / "alice" / "projects" / "backend"
        path2 = tmp_path / "bob" / "code" / "backend"
        path1.mkdir(parents=True, exist_ok=True)
        path2.mkdir(parents=True, exist_ok=True)

        slug1 = _compute_project_slug(str(path1), git_remote_url=remote_url)
        slug2 = _compute_project_slug(str(path2), git_remote_url=remote_url)

        assert slug1 == slug2

    def test_different_remotes_different_slugs(self, tmp_path: Path, monkeypatch) -> None:
        """Different git remotes should produce different slugs."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        slug1 = _compute_project_slug(str(tmp_path), git_remote_url="git@github.com:org/repo1.git")
        slug2 = _compute_project_slug(str(tmp_path), git_remote_url="git@github.com:org/repo2.git")

        assert slug1 != slug2

    def test_git_remote_url_without_dot_git_suffix(self, tmp_path: Path, monkeypatch) -> None:
        """Git URL without .git suffix should work."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        # With and without .git should normalize to same slug
        slug_with = _compute_project_slug(str(tmp_path), git_remote_url="git@github.com:org/repo.git")
        slug_without = _compute_project_slug(str(tmp_path), git_remote_url="git@github.com:org/repo")

        assert slug_with == slug_without

    def test_git_remote_url_takes_precedence_over_mode(self, tmp_path: Path, monkeypatch) -> None:
        """git_remote_url should override any PROJECT_IDENTITY_MODE setting."""
        monkeypatch.setenv("WORKTREES_ENABLED", "1")
        monkeypatch.setenv("PROJECT_IDENTITY_MODE", "dir")
        get_settings.cache_clear()

        remote_url = "git@github.com:test/project.git"
        slug = _compute_project_slug(str(tmp_path), git_remote_url=remote_url)

        # Should be based on remote, not path
        assert slug.startswith("project-")
        assert "tmp" not in slug.lower()


class TestGitRemoteRequiredMode:
    """Tests for PROJECT_IDENTITY_MODE=git-remote-required."""

    def test_git_remote_required_mode_without_url_raises(self, tmp_path: Path, monkeypatch) -> None:
        """When mode is git-remote-required and no URL provided, should raise error."""
        monkeypatch.setenv("WORKTREES_ENABLED", "1")
        monkeypatch.setenv("PROJECT_IDENTITY_MODE", "git-remote-required")
        get_settings.cache_clear()

        with pytest.raises(ToolExecutionError) as exc_info:
            _compute_project_slug(str(tmp_path))

        assert exc_info.value.error_type == "MISSING_REQUIRED_PARAMETER"
        assert "git_remote_url" in str(exc_info.value)
        assert "git remote get-url origin" in str(exc_info.value)

    def test_git_remote_required_mode_with_url_succeeds(self, tmp_path: Path, monkeypatch) -> None:
        """When mode is git-remote-required and URL is provided, should succeed."""
        monkeypatch.setenv("WORKTREES_ENABLED", "1")
        monkeypatch.setenv("PROJECT_IDENTITY_MODE", "git-remote-required")
        get_settings.cache_clear()

        remote_url = "git@github.com:myorg/myrepo.git"
        slug = _compute_project_slug(str(tmp_path), git_remote_url=remote_url)

        assert slug.startswith("myrepo-")

    def test_git_remote_required_mode_with_empty_url_raises(self, tmp_path: Path, monkeypatch) -> None:
        """Empty string git_remote_url should be treated as not provided."""
        monkeypatch.setenv("WORKTREES_ENABLED", "1")
        monkeypatch.setenv("PROJECT_IDENTITY_MODE", "git-remote-required")
        get_settings.cache_clear()

        with pytest.raises(ToolExecutionError) as exc_info:
            _compute_project_slug(str(tmp_path), git_remote_url="")

        assert exc_info.value.error_type == "MISSING_REQUIRED_PARAMETER"

    def test_git_remote_required_mode_with_whitespace_url_raises(self, tmp_path: Path, monkeypatch) -> None:
        """Whitespace-only git_remote_url should be treated as not provided."""
        monkeypatch.setenv("WORKTREES_ENABLED", "1")
        monkeypatch.setenv("PROJECT_IDENTITY_MODE", "git-remote-required")
        get_settings.cache_clear()

        with pytest.raises(ToolExecutionError) as exc_info:
            _compute_project_slug(str(tmp_path), git_remote_url="   ")

        assert exc_info.value.error_type == "MISSING_REQUIRED_PARAMETER"


class TestGitRemoteUrlNormalization:
    """Tests for git remote URL normalization edge cases."""

    def test_gitlab_ssh_url(self, tmp_path: Path, monkeypatch) -> None:
        """GitLab SSH URL should be normalized."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        get_settings.cache_clear()

        slug = _compute_project_slug(str(tmp_path), git_remote_url="git@gitlab.com:group/project.git")
        assert slug.startswith("project-")

    def test_bitbucket_ssh_url(self, tmp_path: Path, monkeypatch) -> None:
        """Bitbucket SSH URL should be normalized."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        get_settings.cache_clear()

        slug = _compute_project_slug(str(tmp_path), git_remote_url="git@bitbucket.org:team/repo.git")
        assert slug.startswith("repo-")

    def test_self_hosted_git_url(self, tmp_path: Path, monkeypatch) -> None:
        """Self-hosted git URL should be normalized."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        get_settings.cache_clear()

        slug = _compute_project_slug(str(tmp_path), git_remote_url="git@git.company.com:org/internal-tool.git")
        assert slug.startswith("internal-tool-")

    def test_invalid_url_falls_back_to_path(self, tmp_path: Path, monkeypatch) -> None:
        """Invalid/unparseable URL should fall back to path-based slug."""
        monkeypatch.setenv("WORKTREES_ENABLED", "0")
        monkeypatch.delenv("PROJECT_IDENTITY_MODE", raising=False)
        get_settings.cache_clear()

        # This is not a valid git URL format
        slug = _compute_project_slug(str(tmp_path), git_remote_url="not-a-valid-url")

        # Should fall back to path-based slug
        from mcp_agent_mail.utils import slugify
        assert slug == slugify(str(tmp_path))
