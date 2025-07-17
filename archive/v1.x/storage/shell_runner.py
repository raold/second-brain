import shlex
import subprocess
from typing import Any, Dict, Optional

from app.utils.logger import get_logger

logger = get_logger()

# Define allowed commands for security
ALLOWED_COMMANDS = {
    'ls', 'pwd', 'whoami', 'date', 'uptime', 'df', 'du',
    'grep', 'find', 'cat', 'head', 'tail', 'wc', 'sort',
    'echo', 'env', 'ps', 'top', 'free', 'uname'
}

def is_command_allowed(command: str) -> bool:
    """Check if command is in the allowed list."""
    if not command:
        return False
    
    # Split command and get the first part (the command name)
    parts = shlex.split(command)
    if not parts:
        return False
    
    base_command = parts[0].lower()
    return base_command in ALLOWED_COMMANDS

def run_shell_command(cmd: str) -> Optional[Dict[str, Any]]:
    """
    Run a shell command with security restrictions.
    
    Args:
        cmd: Command to run
        
    Returns:
        Dict with result info or None if failed
        
    Raises:
        ValueError: If command is not allowed
    """
    try:
        # Validate input
        if not cmd or not isinstance(cmd, str):
            raise ValueError("Command must be a non-empty string")
        
        # Check if command is allowed
        if not is_command_allowed(cmd):
            logger.warning(f"Blocked potentially dangerous command: {cmd}")
            raise ValueError(f"Command '{cmd}' is not allowed for security reasons")
        
        logger.info(f"Running allowed command: {cmd}")
        
        # Run command safely
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Prepare result
        output = {
            'command': cmd,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
        if result.returncode == 0:
            logger.info(f"Command executed successfully: {cmd}")
        else:
            logger.warning(f"Command failed with return code {result.returncode}: {cmd}")
        
        return output
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {cmd}")
        return None
    except Exception as e:
        logger.exception(f"Failed to execute command '{cmd}': {str(e)}")
        return None
