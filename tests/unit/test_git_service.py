"""
Test the GitService implementation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import subprocess

from app.services.git_service import GitService


class TestGitService:
    """Test GitService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.git_service = GitService(self.mock_db)
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_git_status_clean(self, mock_subprocess):
        """Test git status when repository is clean"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        status = await self.git_service.get_git_status()
        
        assert status["is_clean"] is True
        assert status["branch"] is not None
        assert len(status["modified_files"]) == 0
        assert len(status["untracked_files"]) == 0
        mock_subprocess.assert_called()
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_git_status_with_changes(self, mock_subprocess):
        """Test git status with modified and untracked files"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=" M app/services/memory_service.py\n?? new_file.py\n A  added_file.py",
            stderr=""
        )
        
        status = await self.git_service.get_git_status()
        
        assert status["is_clean"] is False
        assert "app/services/memory_service.py" in status["modified_files"]
        assert "new_file.py" in status["untracked_files"]
        assert "added_file.py" in status["staged_files"]
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_current_branch(self, mock_subprocess):
        """Test getting current git branch"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )
        
        branch = await self.git_service.get_current_branch()
        
        assert branch == "main"
        mock_subprocess.assert_called_with(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=None
        )
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_recent_commits(self, mock_subprocess):
        """Test getting recent commits"""
        commit_log = """commit abc123def456
Author: Test User <test@example.com>
Date: Mon Jan 1 12:00:00 2024 +0000

    Add new feature

commit def456abc123
Author: Test User <test@example.com>
Date: Sun Dec 31 18:00:00 2023 +0000

    Fix bug in memory service"""
        
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=commit_log,
            stderr=""
        )
        
        commits = await self.git_service.get_recent_commits(limit=2)
        
        assert len(commits) == 2
        assert commits[0]["hash"] == "abc123def456"
        assert commits[0]["message"] == "Add new feature"
        assert commits[0]["author"] == "Test User <test@example.com>"
        assert commits[1]["hash"] == "def456abc123"
        assert commits[1]["message"] == "Fix bug in memory service"
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_commit_info(self, mock_subprocess):
        """Test getting specific commit information"""
        commit_info = """commit abc123def456
Author: Test User <test@example.com>
Date: Mon Jan 1 12:00:00 2024 +0000

    Add comprehensive test suite
    
    - Added unit tests for all services
    - Improved test coverage
    - Fixed existing test issues"""
        
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=commit_info,
            stderr=""
        )
        
        commit = await self.git_service.get_commit_info("abc123def456")
        
        assert commit["hash"] == "abc123def456"
        assert commit["author"] == "Test User <test@example.com>"
        assert "Add comprehensive test suite" in commit["message"]
        assert "Added unit tests for all services" in commit["message"]
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_file_history(self, mock_subprocess):
        """Test getting file history"""
        file_log = """commit abc123def456
Author: Test User <test@example.com>
Date: Mon Jan 1 12:00:00 2024 +0000

    Update memory service

commit def456abc123
Author: Test User <test@example.com>
Date: Sun Dec 31 18:00:00 2023 +0000

    Initial memory service implementation"""
        
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=file_log,
            stderr=""
        )
        
        history = await self.git_service.get_file_history("app/services/memory_service.py", limit=5)
        
        assert len(history) == 2
        assert history[0]["hash"] == "abc123def456"
        assert history[0]["message"] == "Update memory service"
        mock_subprocess.assert_called_with(
            ["git", "log", "--format=fuller", "-n", "5", "--", "app/services/memory_service.py"],
            capture_output=True,
            text=True,
            cwd=None
        )
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_diff(self, mock_subprocess):
        """Test getting diff between commits"""
        diff_output = """diff --git a/app/services/memory_service.py b/app/services/memory_service.py
index abc123..def456 100644
--- a/app/services/memory_service.py
+++ b/app/services/memory_service.py
@@ -10,6 +10,7 @@ class MemoryService:
     def __init__(self, database):
         self.database = database
+        self.cache = {}
     
     async def create_memory(self, content, metadata):
         return await self.database.store_memory(content, metadata)"""
        
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=diff_output,
            stderr=""
        )
        
        diff = await self.git_service.get_diff("abc123", "def456")
        
        assert "app/services/memory_service.py" in diff
        assert "+        self.cache = {}" in diff
        mock_subprocess.assert_called_with(
            ["git", "diff", "abc123", "def456"],
            capture_output=True,
            text=True,
            cwd=None
        )
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_repository_stats(self, mock_subprocess):
        """Test getting repository statistics"""
        # Mock multiple subprocess calls for different stats
        def mock_subprocess_side_effect(*args, **kwargs):
            command = args[0]
            if "rev-list" in command and "--count" in command:
                return MagicMock(returncode=0, stdout="245\n", stderr="")
            elif "shortlog" in command:
                return MagicMock(returncode=0, stdout="   150  Test User\n    95  Other User\n", stderr="")
            elif "ls-files" in command:
                return MagicMock(returncode=0, stdout="file1.py\nfile2.py\nfile3.py\n", stderr="")
            elif "log" in command and "--since" in command:
                return MagicMock(returncode=0, stdout="commit1\ncommit2\n", stderr="")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        mock_subprocess.side_effect = mock_subprocess_side_effect
        
        stats = await self.git_service.get_repository_stats()
        
        assert stats["total_commits"] == 245
        assert stats["total_files"] == 3
        assert len(stats["top_contributors"]) == 2
        assert stats["top_contributors"][0]["name"] == "Test User"
        assert stats["top_contributors"][0]["commits"] == 150
        assert stats["commits_last_30_days"] == 2
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_git_command_failure(self, mock_subprocess):
        """Test handling of git command failures"""
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        
        with pytest.raises(Exception, match="Git command failed"):
            await self.git_service.get_git_status()
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_get_branch_info(self, mock_subprocess):
        """Test getting branch information"""
        branch_output = """* main                abc123d [origin/main] Latest commit
  feature/new-tests   def456a [origin/feature/new-tests: ahead 2] Add tests
  hotfix/bug-fix      ghi789b Fix critical bug"""
        
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=branch_output,
            stderr=""
        )
        
        branches = await self.git_service.get_branch_info()
        
        assert len(branches) == 3
        assert branches[0]["name"] == "main"
        assert branches[0]["is_current"] is True
        assert branches[0]["commit"] == "abc123d"
        assert branches[1]["name"] == "feature/new-tests"
        assert branches[1]["is_current"] is False
        assert "ahead 2" in branches[1]["status"]
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_check_repository_health(self, mock_subprocess):
        """Test repository health check"""
        def mock_subprocess_side_effect(*args, **kwargs):
            command = args[0]
            if "status" in command and "--porcelain" in command:
                return MagicMock(returncode=0, stdout="", stderr="")  # Clean repo
            elif "fsck" in command:
                return MagicMock(returncode=0, stdout="", stderr="")  # No issues
            elif "remote" in command:
                return MagicMock(returncode=0, stdout="origin\n", stderr="")
            elif "fetch" in command and "--dry-run" in command:
                return MagicMock(returncode=0, stdout="", stderr="")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        mock_subprocess.side_effect = mock_subprocess_side_effect
        
        health = await self.git_service.check_repository_health()
        
        assert health["is_healthy"] is True
        assert health["is_clean"] is True
        assert health["has_remotes"] is True
        assert len(health["issues"]) == 0


class TestGitServiceErrorHandling:
    """Test error handling in GitService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = AsyncMock()
        self.git_service = GitService(self.mock_db)
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_subprocess_timeout(self, mock_subprocess):
        """Test handling of subprocess timeouts"""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "status"],
            timeout=30
        )
        
        with pytest.raises(Exception, match="Git command timed out"):
            await self.git_service.get_git_status()
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_invalid_repository(self, mock_subprocess):
        """Test handling of invalid repository"""
        mock_subprocess.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository (or any of the parent directories): .git"
        )
        
        with pytest.raises(Exception, match="Git command failed"):
            await self.git_service.get_current_branch()
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_permission_denied(self, mock_subprocess):
        """Test handling of permission errors"""
        mock_subprocess.side_effect = PermissionError("Permission denied")
        
        with pytest.raises(PermissionError):
            await self.git_service.get_git_status()


class TestGitServiceIntegration:
    """Integration tests for GitService"""
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_complete_git_workflow(self, mock_subprocess):
        """Test complete git information gathering workflow"""
        # Mock all git commands for a realistic workflow
        def mock_subprocess_side_effect(*args, **kwargs):
            command = args[0]
            if "status" in command and "--porcelain" in command:
                return MagicMock(returncode=0, stdout=" M modified.py\n?? untracked.py", stderr="")
            elif "branch" in command and "--show-current" in command:
                return MagicMock(returncode=0, stdout="feature/test-suite\n", stderr="")
            elif "log" in command and "--format=fuller" in command:
                return MagicMock(
                    returncode=0,
                    stdout="commit abc123\nAuthor: Test User <test@example.com>\nDate: Mon Jan 1 12:00:00 2024 +0000\n\n    Add tests\n\n",
                    stderr=""
                )
            elif "branch" in command and "-v" in command:
                return MagicMock(
                    returncode=0,
                    stdout="* feature/test-suite abc123d Add tests\n  main              def456a Latest commit\n",
                    stderr=""
                )
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        mock_subprocess.side_effect = mock_subprocess_side_effect
        
        mock_db = AsyncMock()
        git_service = GitService(mock_db)
        
        # Gather all git information
        status = await git_service.get_git_status()
        branch = await git_service.get_current_branch()
        commits = await git_service.get_recent_commits(limit=1)
        branches = await git_service.get_branch_info()
        
        # Verify all information is gathered correctly
        assert status["is_clean"] is False
        assert "modified.py" in status["modified_files"]
        assert "untracked.py" in status["untracked_files"]
        assert branch == "feature/test-suite"
        assert len(commits) == 1
        assert commits[0]["hash"] == "abc123"
        assert len(branches) == 2
        assert branches[0]["name"] == "feature/test-suite"
        assert branches[0]["is_current"] is True
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_git_service_with_repository_path(self, mock_subprocess):
        """Test git service with custom repository path"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )
        
        mock_db = AsyncMock()
        git_service = GitService(mock_db, repository_path="/custom/repo/path")
        
        branch = await git_service.get_current_branch()
        
        assert branch == "main"
        # Verify subprocess was called with custom working directory
        mock_subprocess.assert_called_with(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd="/custom/repo/path"
        )