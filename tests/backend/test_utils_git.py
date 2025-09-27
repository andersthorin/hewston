"""
Tests for backend/utils/git.py utility functions.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.utils.git import (
    get_git_commit_hash,
    get_git_branch,
    is_git_repo,
)


class TestGitUtilities:
    """Test suite for git utility functions."""

    def test_get_git_commit_hash_success(self):
        """Test get_git_commit_hash returns commit hash when git command succeeds."""
        mock_hash = "abc123def456"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_hash,
                stderr=""
            )
            
            result = get_git_commit_hash()
            
            assert result == mock_hash
            mock_run.assert_called_once_with(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=False
            )

    def test_get_git_commit_hash_failure(self):
        """Test get_git_commit_hash returns None when git command fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository"
            )
            
            result = get_git_commit_hash()
            
            assert result is None

    def test_get_git_commit_hash_exception(self):
        """Test get_git_commit_hash returns None when subprocess raises exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
            
            result = get_git_commit_hash()
            
            assert result is None

    def test_get_git_commit_hash_file_not_found(self):
        """Test get_git_commit_hash returns None when git command not found."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("git command not found")
            
            result = get_git_commit_hash()
            
            assert result is None

    def test_get_git_branch_success(self):
        """Test get_git_branch returns branch name when git command succeeds."""
        mock_branch = "main"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_branch,
                stderr=""
            )
            
            result = get_git_branch()
            
            assert result == mock_branch
            mock_run.assert_called_once_with(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                check=False
            )

    def test_get_git_branch_failure(self):
        """Test get_git_branch returns None when git command fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository"
            )
            
            result = get_git_branch()
            
            assert result is None

    def test_get_git_branch_detached_head(self):
        """Test get_git_branch handles detached HEAD state."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="HEAD",
                stderr=""
            )
            
            result = get_git_branch()
            
            assert result == "HEAD"

    def test_is_git_repo_true(self):
        """Test is_git_repo returns True when in a git repository."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="/path/to/repo/.git",
                stderr=""
            )
            
            result = is_git_repo()
            
            assert result is True
            mock_run.assert_called_once_with(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                check=False
            )

    def test_is_git_repo_false(self):
        """Test is_git_repo returns False when not in a git repository."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository"
            )
            
            result = is_git_repo()
            
            assert result is False

    def test_is_git_repo_exception(self):
        """Test is_git_repo returns False when subprocess raises exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("git command not found")
            
            result = is_git_repo()
            
            assert result is False

    def test_git_functions_strip_whitespace(self):
        """Test that git functions properly strip whitespace from output."""
        mock_hash_with_whitespace = "  abc123def456  \n"
        mock_branch_with_whitespace = "\n  feature-branch  \n"
        
        with patch('subprocess.run') as mock_run:
            # Test commit hash
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_hash_with_whitespace,
                stderr=""
            )
            
            result = get_git_commit_hash()
            assert result == "abc123def456"
            
            # Test branch name
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_branch_with_whitespace,
                stderr=""
            )
            
            result = get_git_branch()
            assert result == "feature-branch"

    def test_git_functions_empty_output(self):
        """Test git functions handle empty output gracefully."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )
            
            # Empty output should return None or empty string
            hash_result = get_git_commit_hash()
            branch_result = get_git_branch()
            
            # Both should handle empty output gracefully
            assert hash_result in [None, ""]
            assert branch_result in [None, ""]

    def test_git_functions_integration(self):
        """Test that git functions work together logically."""
        # If we're in a git repo, we should be able to get commit and branch
        # If not, all should return None/False consistently
        
        with patch('subprocess.run') as mock_run:
            # Simulate being in a git repo
            def mock_git_command(cmd, **kwargs):
                if 'rev-parse' in cmd and '--git-dir' in cmd:
                    return MagicMock(returncode=0, stdout=".git", stderr="")
                elif 'rev-parse' in cmd and 'HEAD' in cmd:
                    return MagicMock(returncode=0, stdout="abc123", stderr="")
                elif 'rev-parse' in cmd and '--abbrev-ref' in cmd:
                    return MagicMock(returncode=0, stdout="main", stderr="")
                else:
                    return MagicMock(returncode=1, stdout="", stderr="error")
            
            mock_run.side_effect = mock_git_command
            
            is_repo = is_git_repo()
            commit_hash = get_git_commit_hash()
            branch = get_git_branch()
            
            assert is_repo is True
            assert commit_hash == "abc123"
            assert branch == "main"

    def test_git_functions_not_in_repo(self):
        """Test git functions when not in a git repository."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository"
            )
            
            is_repo = is_git_repo()
            commit_hash = get_git_commit_hash()
            branch = get_git_branch()
            
            assert is_repo is False
            assert commit_hash is None
            assert branch is None
