# Upload warmed SQLite caches to zaha-01 (PowerShell wrapper).
# Requires OpenSSH scp/rsync via WSL or Git Bash for large files.
#
#   .\deploy\zaha-01\upload_caches.ps1
#   .\deploy\zaha-01\upload_caches.ps1 -Target city

param(
    [string[]]$Target = @(),
    [string]$Remote = "xz378@zaha-01",
    [string]$LocalData = "D:/mini_marie_data/data/mini_marie_cache",
    [string]$RemoteData = "/home/xz378/mini_marie_data/data/mini_marie_cache"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
    Write-Error "bash not found. Install Git for Windows or use WSL, then re-run."
}

$env:MARIECP_REMOTE = $Remote
$env:MARIECP_REMOTE_DATA = $RemoteData
$env:MINI_MARIE_DATA_DIR = (Split-Path $LocalData -Parent)

$args = @("$repo/deploy/zaha-01/upload_caches.sh")
if ($Target.Count -gt 0) { $args += $Target }

Write-Host "Starting cache upload to $Remote ..."
& bash @args
