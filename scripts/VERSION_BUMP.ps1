# Production Version Bump Script for Second Brain
# PowerShell wrapper for the Python version management system

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("major", "minor", "patch")]
    [string]$BumpType,
    
    [switch]$DryRun,
    [switch]$SkipPush,
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host "📋 Second Brain Version Bump Script" -ForegroundColor Cyan
    Write-Host "="*50
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\VERSION_BUMP.ps1 patch              # Patch version bump (2.4.1 → 2.4.2)"
    Write-Host "  .\VERSION_BUMP.ps1 minor              # Minor version bump (2.4.1 → 2.5.0)"
    Write-Host "  .\VERSION_BUMP.ps1 major              # Major version bump (2.4.1 → 3.0.0)"
    Write-Host "  .\VERSION_BUMP.ps1 patch -DryRun      # Preview changes without applying"
    Write-Host "  .\VERSION_BUMP.ps1 patch -SkipPush    # Bump version but don't push to GitHub"
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -DryRun     Preview changes without making them"
    Write-Host "  -SkipPush   Don't push changes to GitHub (local only)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\VERSION_BUMP.ps1 patch              # Standard patch release"
    Write-Host "  .\VERSION_BUMP.ps1 minor -DryRun      # Preview minor version bump"
    Write-Host ""
    exit 0
}

# Script header
Write-Host "🚀 Second Brain Version Bump - PowerShell Launcher" -ForegroundColor Cyan
Write-Host "="*60
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "app\version.py")) {
    Write-Host "❌ Error: Not in Second Brain root directory" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

# Check Python availability
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python not found" -ForegroundColor Red
    Write-Host "Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
    exit 1
}

# Build command
$command = "python scripts\version_bump.py $BumpType"

if ($DryRun) {
    $command += " --dry-run"
    Write-Host "🧪 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

if ($SkipPush) {
    $command += " --skip-push"
    Write-Host "📝 LOCAL MODE - Changes won't be pushed to GitHub" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Executing: $command" -ForegroundColor Blue
Write-Host ""

# Execute the Python script
try {
    Invoke-Expression $command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "🎉 Version bump completed successfully!" -ForegroundColor Green
        
        if (-not $DryRun) {
            Write-Host ""
            Write-Host "📋 Next Steps:" -ForegroundColor Cyan
            Write-Host "1. ✅ Version updated and committed to Git" -ForegroundColor Green
            
            if (-not $SkipPush) {
                Write-Host "2. ✅ Changes pushed to GitHub" -ForegroundColor Green
                Write-Host "3. 📋 Create GitHub release at: https://github.com/raold/second-brain/releases/new" -ForegroundColor Yellow
            } else {
                Write-Host "2. 📋 Push changes: git push origin main && git push origin --tags" -ForegroundColor Yellow
                Write-Host "3. 📋 Create GitHub release at: https://github.com/raold/second-brain/releases/new" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host ""
        Write-Host "❌ Version bump failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error executing version bump: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✨ Done! Ready for production deployment." -ForegroundColor Green 