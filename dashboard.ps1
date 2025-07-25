#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Second Brain Dashboard Management Script for PowerShell

.DESCRIPTION
    Complete dashboard management for Second Brain research platform:
    - Development server with hot reload
    - Production builds
    - GitHub Pages deployment
    - Server management and status

.PARAMETER Command
    The command to execute: dev, build, pages, status, stop, install, legacy

.PARAMETER Port
    Port for development server (default: 8000)

.PARAMETER NoReload
    Disable hot reload for development server

.PARAMETER Force
    Force operations (used with stop, legacy modes)

.PARAMETER Lines
    Number of log lines to show (legacy mode)

.EXAMPLE
    .\dashboard.ps1 dev
    Start development server with hot reload

.EXAMPLE
    .\dashboard.ps1 dev -Port 3000 -NoReload
    Start development server on port 3000 without hot reload

.EXAMPLE
    .\dashboard.ps1 build
    Build dashboard for production

.EXAMPLE
    .\dashboard.ps1 pages
    Deploy to GitHub Pages

.EXAMPLE
    .\dashboard.ps1 legacy start
    Use legacy server manager (backwards compatibility)
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "build", "pages", "status", "stop", "install", "legacy", "help")]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$LegacyAction,
    
    [int]$Port = 8000,
    [switch]$NoReload,
    [switch]$Force,
    [int]$Lines = 20
)

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow" 
    Error = "Red"
    Info = "Cyan"
    Highlight = "Magenta"
}

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    if ($Colors.ContainsKey($Color)) {
        Write-Host $Message -ForegroundColor $Colors[$Color]
    } else {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Get-ProjectRoot {
    return $PSScriptRoot
}

function Test-PythonEnvironment {
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Python found: $pythonVersion" "Success"
            return $true
        }
    } catch {
        Write-ColorOutput "❌ Python not found in PATH" "Error"
        Write-ColorOutput "Please install Python 3.11+ and add it to your PATH" "Warning"
        return $false
    }
    return $false
}

function Invoke-LegacyServerManager {
    # Legacy compatibility - use old server_manager.py approach
    param([string]$Action)
    
    if (-not $Action) {
        Write-ColorOutput "❌ Legacy mode requires an action (start, stop, restart, status, logs)" "Error"
        return
    }
    
    Write-ColorOutput "🔄 Using legacy server manager..." "Warning"
    
    # Build arguments for Python script
    $pythonArgs = @($Action)
    
    if ($Force) {
        $pythonArgs += "--force"
    }
    
    if ($Action -eq "logs" -and $Lines -ne 20) {
        $pythonArgs += "--lines", $Lines
    }
    
    # Run the Python server manager
    try {
        & python server_manager.py @pythonArgs
        return $LASTEXITCODE
    } catch {
        Write-ColorOutput "❌ Failed to run legacy server manager: $_" "Error"
        return 1
    }
}

function Install-Dependencies {
    Write-ColorOutput "📦 Installing required dependencies..." "Info"
    
    $requirements = @(
        "watchdog",
        "gitpython", 
        "python-dateutil"
    )
    
    foreach ($package in $requirements) {
        Write-ColorOutput "Installing $package..." "Info"
        python -m pip install $package
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ Failed to install $package" "Error"
            return $false
        }
    }
    
    Write-ColorOutput "✅ All dependencies installed successfully" "Success"
    return $true
}

function Start-DevServer {
    $projectRoot = Get-ProjectRoot
    $devScript = Join-Path $projectRoot "scripts\dashboard\dev_server.py"
    
    if (-not (Test-Path $devScript)) {
        Write-ColorOutput "❌ Development server script not found: $devScript" "Error"
        Write-ColorOutput "💡 Try running: .\dashboard.ps1 install" "Info"
        return
    }
    
    $args = @("$devScript", "--port", $Port)
    if ($NoReload) {
        $args += "--no-reload"
    }
    
    Write-ColorOutput "🚀 Starting development server on port $Port..." "Highlight"
    Write-ColorOutput "📊 Dashboard will be available at: http://localhost:$Port/" "Info"
    Write-ColorOutput "✋ Press Ctrl+C to stop the server" "Warning"
    
    try {
        Set-Location $projectRoot
        python @args
    } catch {
        Write-ColorOutput "❌ Failed to start development server: $_" "Error"
    }
}

function Invoke-DeployScript {
    param([string]$Action, [string[]]$ExtraArgs = @())
    
    $projectRoot = Get-ProjectRoot
    $deployScript = Join-Path $projectRoot "scripts\dashboard\deploy.py"
    
    if (-not (Test-Path $deployScript)) {
        Write-ColorOutput "❌ Deploy script not found: $deployScript" "Error"
        return $false
    }
    
    Set-Location $projectRoot
    $allArgs = @($deployScript, $Action) + $ExtraArgs
    python @allArgs
    
    return ($LASTEXITCODE -eq 0)
}

function Stop-DashboardServers {
    Write-ColorOutput "🛑 Stopping dashboard servers..." "Warning"
    
    # Find processes on common dashboard ports
    $ports = @(8000, 3000, 8080, 5000)
    
    foreach ($port in $ports) {
        try {
            $connections = netstat -ano | Select-String ":$port "
            if ($connections) {
                foreach ($connection in $connections) {
                    $parts = $connection.Line -split '\s+' | Where-Object { $_ -ne '' }
                    if ($parts.Count -ge 5) {
                        $pid = $parts[4]
                        try {
                            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                            if ($process) {
                                $processName = $process.ProcessName
                                Write-ColorOutput "🔍 Found process on port $port`: $processName (PID: $pid)" "Info"
                                
                                # Kill Python processes (likely our dashboard)
                                if ($processName -eq "python") {
                                    Write-ColorOutput "🛑 Stopping dashboard server (PID: $pid)..." "Warning"
                                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                                    Write-ColorOutput "✅ Server stopped" "Success"
                                }
                            }
                        } catch {
                            # Process might have already exited
                        }
                    }
                }
            }
        } catch {
            # Port not in use, continue
        }
    }
    
    Write-ColorOutput "✅ Dashboard server cleanup completed" "Success"
}

function Show-Help {
    Write-ColorOutput "🧠 Second Brain Dashboard Management" "Highlight"
    Write-ColorOutput "=================================" "Highlight"
    Write-Host ""
    
    Write-ColorOutput "Usage: .\dashboard.ps1 <command> [options]" "Info"
    Write-Host ""
    
    Write-ColorOutput "Modern Commands:" "Info"
    Write-ColorOutput "  dev      Start development server with hot reload" "White"
    Write-ColorOutput "  build    Build dashboard for production deployment" "White"
    Write-ColorOutput "  pages    Deploy to GitHub Pages" "White"
    Write-ColorOutput "  status   Check deployment status" "White"
    Write-ColorOutput "  stop     Stop running dashboard servers" "White"
    Write-ColorOutput "  install  Install required dependencies" "White"
    Write-Host ""
    
    Write-ColorOutput "Legacy Commands:" "Info"
    Write-ColorOutput "  legacy <action>  Use old server manager (start, stop, restart, status, logs)" "White"
    Write-Host ""
    
    Write-ColorOutput "Options:" "Info"
    Write-ColorOutput "  -Port <number>    Specify port for dev server (default: 8000)" "White"
    Write-ColorOutput "  -NoReload         Disable hot reload for dev server" "White"
    Write-ColorOutput "  -Force            Force operations" "White"
    Write-Host ""
    
    Write-ColorOutput "Examples:" "Info"
    Write-ColorOutput "  .\dashboard.ps1 dev                 # Start dev server with hot reload" "White"
    Write-ColorOutput "  .\dashboard.ps1 dev -Port 3000      # Start on port 3000" "White"
    Write-ColorOutput "  .\dashboard.ps1 build               # Build for production" "White"
    Write-ColorOutput "  .\dashboard.ps1 pages               # Deploy to GitHub Pages" "White"
    Write-ColorOutput "  .\dashboard.ps1 legacy start        # Use legacy server" "White"
}

# Main execution
Write-ColorOutput "🧠 Second Brain Dashboard Manager v2.0" "Highlight"
Write-Host ""

# Check Python environment (except for help)
if ($Command -ne "help" -and -not (Test-PythonEnvironment)) {
    exit 1
}

# Execute command
switch ($Command) {
    "dev" {
        Start-DevServer
    }
    "build" {
        if (Invoke-DeployScript "build") {
            Write-ColorOutput "✅ Production build completed successfully" "Success"
            $buildDir = Join-Path (Get-ProjectRoot) "build\dashboard"
            Write-ColorOutput "📁 Build output: $buildDir" "Info"
        } else {
            Write-ColorOutput "❌ Production build failed" "Error"
        }
    }
    "pages" {
        Write-ColorOutput "🚀 Deploying to GitHub Pages..." "Highlight"
        if (Invoke-DeployScript "pages") {
            Write-ColorOutput "✅ Deployment initiated successfully" "Success"
            Write-ColorOutput "🌐 Dashboard will be available at: https://raold.github.io/second-brain/" "Info"
            Write-ColorOutput "⏱️ Deployment may take a few minutes to complete" "Warning"
        } else {
            Write-ColorOutput "❌ Deployment failed" "Error"
        }
    }
    "status" {
        Write-ColorOutput "📊 Checking deployment status..." "Highlight"
        Invoke-DeployScript "status" | Out-Null
    }
    "stop" {
        Stop-DashboardServers
    }
    "install" {
        Install-Dependencies | Out-Null
    }
    "legacy" {
        $exitCode = Invoke-LegacyServerManager $LegacyAction
        exit $exitCode
    }
    "help" {
        Show-Help
    }
    default {
        # Check if first parameter looks like legacy action
        if ($Command -in @("start", "stop", "restart", "status", "logs")) {
            Write-ColorOutput "🔄 Detected legacy command, using legacy mode..." "Warning"
            $exitCode = Invoke-LegacyServerManager $Command
            exit $exitCode
        } else {
            Write-ColorOutput "❌ Unknown command: $Command" "Error"
            Show-Help
            exit 1
        }
    }
}
