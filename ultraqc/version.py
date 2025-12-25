# -*- coding: utf-8 -*-
"""
Version management for UltraQC.

This module provides version information by fetching the latest non-prerelease
version from GitHub releases. Falls back to local package version if GitHub
is unavailable.
"""

import functools
import logging
import os
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# GitHub repository information
GITHUB_OWNER = "Daylily-Informatics"
GITHUB_REPO = "UltraQC"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"

# Cache timeout in seconds (1 hour)
CACHE_TIMEOUT = 3600

# Cached version info
_cached_version: Optional[str] = None
_cached_time: float = 0


def _get_local_version() -> str:
    """Get version from installed package metadata."""
    try:
        from importlib.metadata import version as get_version
        return get_version("ultraqc")
    except Exception:
        return "0.0.0-dev"


def _get_git_hash() -> Tuple[Optional[str], Optional[str]]:
    """Get the current git commit hash."""
    script_path = os.path.dirname(os.path.realpath(__file__))
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=script_path,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        ).strip()
        return git_hash, git_hash[:7]
    except Exception:
        return None, None


def _fetch_github_version() -> Optional[str]:
    """
    Fetch the latest non-prerelease version from GitHub releases.
    
    Returns the version string (e.g., "1.2.3") or None if unavailable.
    """
    try:
        import urllib.request
        import json
        
        # Create request with User-Agent header (required by GitHub API)
        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "UltraQC-Version-Check",
            }
        )
        
        # Set a short timeout to avoid blocking
        with urllib.request.urlopen(request, timeout=5) as response:
            releases = json.loads(response.read().decode("utf-8"))
        
        # Find the latest non-prerelease, non-draft release
        for release in releases:
            if not release.get("prerelease", False) and not release.get("draft", False):
                tag_name = release.get("tag_name", "")
                # Remove 'v' prefix if present
                version = tag_name.lstrip("v")
                if version:
                    logger.debug(f"Found GitHub release version: {version}")
                    return version
        
        logger.debug("No non-prerelease releases found on GitHub")
        return None
        
    except Exception as e:
        logger.debug(f"Failed to fetch version from GitHub: {e}")
        return None


def get_version(include_git_hash: bool = False) -> str:
    """
    Get the current UltraQC version.
    
    Priority:
    1. Latest non-prerelease GitHub release (cached for 1 hour)
    2. Local package version from importlib.metadata
    3. Fallback to "0.0.0-dev"
    
    Args:
        include_git_hash: If True, append the short git hash to the version
        
    Returns:
        Version string (e.g., "1.2.3" or "1.2.3 (abc1234)")
    """
    import time
    global _cached_version, _cached_time
    
    current_time = time.time()
    
    # Check if cache is still valid
    if _cached_version is None or (current_time - _cached_time) > CACHE_TIMEOUT:
        # Try to fetch from GitHub first
        github_version = _fetch_github_version()
        
        if github_version:
            _cached_version = github_version
        else:
            # Fall back to local version
            _cached_version = _get_local_version()
        
        _cached_time = current_time
    
    version = _cached_version
    
    # Optionally append git hash
    if include_git_hash:
        _, git_hash_short = _get_git_hash()
        if git_hash_short:
            version = f"{version} ({git_hash_short})"
    
    return version


def get_version_info() -> dict:
    """
    Get detailed version information.
    
    Returns:
        Dictionary with version details:
        - version: The main version string
        - source: Where the version came from ("github", "local", or "fallback")
        - git_hash: Full git commit hash (if available)
        - git_hash_short: Short git commit hash (if available)
    """
    github_version = _fetch_github_version()
    local_version = _get_local_version()
    git_hash, git_hash_short = _get_git_hash()
    
    if github_version:
        source = "github"
        version = github_version
    elif local_version != "0.0.0-dev":
        source = "local"
        version = local_version
    else:
        source = "fallback"
        version = "0.0.0-dev"
    
    return {
        "version": version,
        "source": source,
        "github_version": github_version,
        "local_version": local_version,
        "git_hash": git_hash,
        "git_hash_short": git_hash_short,
    }


# Module-level version for easy import
version = get_version()
short_version = version
__version__ = version

