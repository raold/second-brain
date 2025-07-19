#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Second Brain Dashboard Server Manager for PowerShell

.DESCRIPTION
    Provides clean start, stop, restart, status, and log viewing for the dashboard server

.PARAMETER Action
    The action to perform: start, stop, restart, status, logs

.PARAMETER Force
    Force stop the server (for stop/restart actions)

.PARAMETER Lines
    Number of log lines to show (for logs action, default: 20)

.EXAMPLE
    .\dashboard.ps1 start
    Start the dashboard server

.EXAMPLE
    .\dashboard.ps1 stop -Force
    Force stop the dashboard server

.EXAMPLE
    .\dashboard.ps1 logs -Lines 50
    Show last 50 lines of server logs
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "logs")]
    [string]$Action,
    
    [switch]$Force,
    
    [int]$Lines = 20
)

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
    $exitCode = $LASTEXITCODE
} catch {
    Write-Error "Failed to run server manager: $_"
    $exitCode = 1
}

exit $exitCode
