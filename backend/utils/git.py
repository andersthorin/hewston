"""
Git utilities for version control operations.

This module centralizes git-related operations to avoid duplication
across the backend codebase.
"""

import subprocess
from typing import Optional


def get_git_commit_hash() -> str:
    """
    Get the current git commit hash.
    
    Returns:
        The current commit hash, or "unknown" if git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def get_git_branch() -> str:
    """
    Get the current git branch name.
    
    Returns:
        The current branch name, or "unknown" if git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def is_git_repo() -> bool:
    """Check if the current directory is a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False
