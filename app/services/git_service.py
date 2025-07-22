"""
Git Service - Enhanced with commit activity metrics by branch and time period.
Provides branch status, features, versioning, commit information, and activity tracking.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GitCommitMetrics:
    """Commit activity metrics for a specific time period."""

    branch_name: str
    period_days: int
    commit_count: int
    lines_added: int
    lines_deleted: int
    files_changed: int
    authors: list[str]
    first_commit_date: datetime | None = None
    last_commit_date: datetime | None = None


@dataclass
class GitBranchInfo:
    """Information about a git branch."""

    name: str
    is_current: bool = False
    is_remote: bool = False
    last_commit_hash: str | None = None
    last_commit_message: str | None = None
    last_commit_author: str | None = None
    last_commit_date: datetime | None = None
    ahead: int | None = None
    behind: int | None = None
    status: str = "active"  # active, merged, stale
    features: list[str] | None = None
    version: str | None = None

    # New commit metrics
    metrics_24h: GitCommitMetrics | None = None
    metrics_7d: GitCommitMetrics | None = None
    metrics_30d: GitCommitMetrics | None = None

    def __post_init__(self):
        if self.features is None:
            self.features = []

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "current": self.is_current,
            "remote": self.is_remote,
            "status": self.status,
            "commit_hash": self.last_commit_hash,
            "commit_message": self.last_commit_message,
            "commit_author": self.last_commit_author,
            "last_activity": self.last_commit_date.isoformat() if self.last_commit_date else None,
            "ahead": self.ahead,
            "behind": self.behind,
            "features": self.features,
            "version": self.version,
            "metrics_24h": self.metrics_24h.__dict__ if self.metrics_24h else None,
            "metrics_7d": self.metrics_7d.__dict__ if self.metrics_7d else None,
            "metrics_30d": self.metrics_30d.__dict__ if self.metrics_30d else None,
        }


@dataclass
class GitRepositoryStatus:
    """Overall repository status information."""

    current_branch: str
    total_branches: int
    dirty: bool  # Has uncommitted changes
    stash_count: int
    total_commits: int
    contributors: int
    last_commit: datetime
    repository_size: str
    branches: list[GitBranchInfo]

    # New aggregate metrics
    total_commits_24h: int = 0
    total_commits_7d: int = 0
    total_commits_30d: int = 0
    total_lines_added_24h: int = 0
    total_lines_added_7d: int = 0
    total_lines_added_30d: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "current_branch": self.current_branch,
            "total_branches": self.total_branches,
            "dirty": self.dirty,
            "stash_count": self.stash_count,
            "total_commits": self.total_commits,
            "contributors": self.contributors,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
            "repository_size": self.repository_size,
            "branches": [branch.to_dict() for branch in self.branches],
            "total_commits_24h": self.total_commits_24h,
            "total_commits_7d": self.total_commits_7d,
            "total_commits_30d": self.total_commits_30d,
            "total_lines_added_24h": self.total_lines_added_24h,
            "total_lines_added_7d": self.total_lines_added_7d,
            "total_lines_added_30d": self.total_lines_added_30d,
        }


class GitService:
    """Service for git repository operations with commit activity tracking."""

    def __init__(self, repo_path: str | None = None):
        """Initialize GitService."""
        self.repo_path = repo_path or os.getcwd()
        self.logger = logger

    def _run_git_command(self, command: list[str]) -> str | None:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,  # Increased timeout for stat commands
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.warning(f"Git command failed: {' '.join(command)} - {result.stderr}")
                return None
        except Exception as e:
            self.logger.error(f"Error running git command {command}: {e}")
            return None

    def get_commit_metrics(self, branch_name: str, days: int) -> GitCommitMetrics | None:
        """Get commit metrics for a branch within specified days."""
        try:
            # Calculate date threshold
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.strftime("%Y-%m-%d")

            # Get commit count
            commit_count_cmd = ["rev-list", "--count", f"--since={since_str}", branch_name]
            commit_count_output = self._run_git_command(commit_count_cmd)
            commit_count = int(commit_count_output) if commit_count_output and commit_count_output.isdigit() else 0

            if commit_count == 0:
                return GitCommitMetrics(
                    branch_name=branch_name,
                    period_days=days,
                    commit_count=0,
                    lines_added=0,
                    lines_deleted=0,
                    files_changed=0,
                    authors=[],
                )

            # Get stats (lines added/deleted, files changed)
            stat_cmd = ["log", f"--since={since_str}", "--pretty=format:", "--numstat", branch_name]
            stat_output = self._run_git_command(stat_cmd)

            lines_added = 0
            lines_deleted = 0
            files_changed = set()

            if stat_output:
                for line in stat_output.split("\n"):
                    line = line.strip()
                    if line and "\t" in line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            try:
                                added = int(parts[0]) if parts[0] != "-" else 0
                                deleted = int(parts[1]) if parts[1] != "-" else 0
                                filename = parts[2]

                                lines_added += added
                                lines_deleted += deleted
                                files_changed.add(filename)
                            except ValueError:
                                continue

            # Get unique authors
            authors_cmd = ["log", f"--since={since_str}", "--pretty=format:%an", branch_name]
            authors_output = self._run_git_command(authors_cmd)
            authors = list(set(authors_output.split("\n"))) if authors_output else []
            authors = [a.strip() for a in authors if a.strip()]

            return GitCommitMetrics(
                branch_name=branch_name,
                period_days=days,
                commit_count=commit_count,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                files_changed=len(files_changed),
                authors=authors,
            )

        except Exception as e:
            self.logger.error(f"Error getting commit metrics for {branch_name} ({days}d): {e}")
            return None

    def get_commit_activity_summary(self) -> dict[str, Any]:
        """Get a summary of commit activity across all branches."""
        try:
            # Get all branches
            branches = ["testing", "main", "develop"]  # Focus on key branches first
            all_branches_output = self._run_git_command(["branch", "-a"])
            if all_branches_output:
                for line in all_branches_output.split("\n"):
                    line = line.strip().replace("*", "").strip()
                    if line and not line.startswith("remotes/") and line not in branches:
                        branches.append(line)

            branch_metrics = []
            total_commits_24h = 0
            total_commits_7d = 0
            total_commits_30d = 0
            total_lines_24h = 0
            total_lines_7d = 0
            total_lines_30d = 0

            for branch in branches[:10]:  # Limit to top 10 branches to avoid timeout
                metrics_24h = self.get_commit_metrics(branch, 1)
                metrics_7d = self.get_commit_metrics(branch, 7)
                metrics_30d = self.get_commit_metrics(branch, 30)

                if metrics_24h or metrics_7d or metrics_30d:
                    branch_data = {
                        "branch": branch,
                        "commits_24h": metrics_24h.commit_count if metrics_24h else 0,
                        "commits_7d": metrics_7d.commit_count if metrics_7d else 0,
                        "commits_30d": metrics_30d.commit_count if metrics_30d else 0,
                        "lines_added_24h": metrics_24h.lines_added if metrics_24h else 0,
                        "lines_added_7d": metrics_7d.lines_added if metrics_7d else 0,
                        "lines_added_30d": metrics_30d.lines_added if metrics_30d else 0,
                        "files_changed_24h": metrics_24h.files_changed if metrics_24h else 0,
                        "files_changed_7d": metrics_7d.files_changed if metrics_7d else 0,
                        "files_changed_30d": metrics_30d.files_changed if metrics_30d else 0,
                        "authors_24h": len(metrics_24h.authors) if metrics_24h else 0,
                        "authors_7d": len(metrics_7d.authors) if metrics_7d else 0,
                        "authors_30d": len(metrics_30d.authors) if metrics_30d else 0,
                    }
                    branch_metrics.append(branch_data)

                    # Aggregate totals
                    total_commits_24h += branch_data["commits_24h"]
                    total_commits_7d += branch_data["commits_7d"]
                    total_commits_30d += branch_data["commits_30d"]
                    total_lines_24h += branch_data["lines_added_24h"]
                    total_lines_7d += branch_data["lines_added_7d"]
                    total_lines_30d += branch_data["lines_added_30d"]

            # Sort by recent activity
            branch_metrics.sort(key=lambda x: x["commits_24h"] + x["commits_7d"], reverse=True)

            return {
                "repository_totals": {
                    "commits_24h": total_commits_24h,
                    "commits_7d": total_commits_7d,
                    "commits_30d": total_commits_30d,
                    "lines_added_24h": total_lines_24h,
                    "lines_added_7d": total_lines_7d,
                    "lines_added_30d": total_lines_30d,
                },
                "branch_activity": branch_metrics,
                "most_active_branches": {
                    "24h": branch_metrics[0] if branch_metrics and branch_metrics[0]["commits_24h"] > 0 else None,
                    "7d": max(
                        [b for b in branch_metrics if b["commits_7d"] > 0], key=lambda x: x["commits_7d"], default=None
                    ),
                    "30d": max(
                        [b for b in branch_metrics if b["commits_30d"] > 0],
                        key=lambda x: x["commits_30d"],
                        default=None,
                    ),
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting commit activity summary: {e}")
            return {
                "repository_totals": {
                    "commits_24h": 0,
                    "commits_7d": 0,
                    "commits_30d": 0,
                    "lines_added_24h": 0,
                    "lines_added_7d": 0,
                    "lines_added_30d": 0,
                },
                "branch_activity": [],
                "most_active_branches": {"24h": None, "7d": None, "30d": None},
            }

    def get_current_branch(self) -> str | None:
        """Get the current branch name."""
        return self._run_git_command(["branch", "--show-current"])

    def get_all_branches(self) -> list[str]:
        """Get all local and remote branches."""
        result = self._run_git_command(["branch", "-a"])
        if not result:
            return []

        branches = []
        for line in result.split("\n"):
            line = line.strip()
            if line and not line.startswith("*"):
                branch = line.replace("*", "").strip()
                if branch.startswith("remotes/"):
                    branch = branch[8:]  # Remove 'remotes/'
                if branch and "->" not in branch:  # Skip HEAD -> origin/main
                    branches.append(branch)
            elif line.startswith("*"):
                branch = line[2:].strip()  # Remove '* '
                branches.append(branch)

        return list(set(branches))  # Remove duplicates

    def get_repository_status(self) -> GitRepositoryStatus:
        """Get basic repository status with commit metrics."""
        try:
            current_branch = self.get_current_branch() or "unknown"
            all_branches = self.get_all_branches()

            # Get basic status
            status_output = self._run_git_command(["status", "--porcelain"])
            is_dirty = bool(status_output and status_output.strip())

            return GitRepositoryStatus(
                current_branch=current_branch,
                total_branches=len(all_branches),
                dirty=is_dirty,
                stash_count=0,
                total_commits=0,
                contributors=0,
                last_commit=datetime.now(),
                repository_size="unknown",
                branches=[],
            )

        except Exception as e:
            self.logger.error(f"Error getting repository status: {e}")
            return GitRepositoryStatus(
                current_branch="unknown",
                total_branches=0,
                dirty=False,
                stash_count=0,
                total_commits=0,
                contributors=0,
                last_commit=datetime.now(),
                repository_size="unknown",
                branches=[],
            )

    def get_d3_visualization_data(self) -> dict:
        """Get basic visualization data."""
        repo_status = self.get_repository_status()

        return {
            "nodes": [{"id": branch, "name": branch, "group": 1} for branch in repo_status.current_branch],
            "links": [],
            "repository": repo_status.to_dict(),
            "summary": {
                "total_branches": repo_status.total_branches,
                "current_branch": repo_status.current_branch,
                "has_uncommitted_changes": repo_status.dirty,
            },
        }
