# VERSIONBUMP PowerShell Script
# Creates a VERSIONBUMP command for Windows PowerShell

param(
    [Parameter(Position=0)]
    [ValidateSet("major", "minor", "patch")]
    [string]$BumpType,
    
    [Parameter()]
    [switch]$DryRun
)

# Get the script directory (should be scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

# Check if bump type is provided
if (-not $BumpType) {
    Write-Host "Usage: VERSIONBUMP [major|minor|patch] [-DryRun]" -ForegroundColor Yellow
    Write-Host "Example: VERSIONBUMP patch" -ForegroundColor Yellow
    Write-Host "Example: VERSIONBUMP patch -DryRun" -ForegroundColor Yellow
    exit 1
}

try {
    if ($DryRun) {
        Write-Host "DRY RUN MODE - No changes will be made" -ForegroundColor Cyan
        Write-Host "Starting version bump: $BumpType (dry-run)" -ForegroundColor Green
    } else {
        Write-Host "Starting version bump: $BumpType" -ForegroundColor Green
    }
    Write-Host "Working directory: $RootDir" -ForegroundColor Gray
    
    # Change to root directory
    Push-Location $RootDir
    
    # Build command arguments
    $PythonArgs = @("scripts/version_bump.py", $BumpType)
    if ($DryRun) {
        $PythonArgs += "--dry-run"
    }
    
    # Execute the Python version bump script
    python @PythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        if (-not $DryRun) {
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Green
            Write-Host "VERSIONBUMP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
            Write-Host "============================================================" -ForegroundColor Green
            Write-Host "Version bumped: $BumpType" -ForegroundColor Green
            Write-Host "All files updated" -ForegroundColor Green
            Write-Host "Git operations completed" -ForegroundColor Green
            Write-Host "Release notes generated" -ForegroundColor Green
            Write-Host ""
            Write-Host "Ready to create GitHub release!" -ForegroundColor Cyan
        }
    } else {
        Write-Host "VERSIONBUMP failed!" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "VERSIONBUMP failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    # Return to original directory
    Pop-Location
}
