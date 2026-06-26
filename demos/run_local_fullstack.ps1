# Local full-stack smoke test (production-like: classic Marie + Zaha + hub).
# From repo root in PowerShell:
#   .\demos\run_local_fullstack.ps1
#   .\demos\run_local_fullstack.ps1 -SkipServer
#   .\demos\run_local_fullstack.ps1 -WithLlm

param(
    [switch]$SkipMirror,
    [switch]$SkipServer,
    [switch]$WithLlm,
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
Set-Location $Repo

$env:PYTHONPATH = $Repo
$env:DEMO_CONFIG = "fullstack"
$env:DEMO_PORT = "$Port"
$env:MARIE_FRONTEND_PROXY = "0"
$env:DEMO_FORCE_REFRESH = "false"

$Python = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Missing venv at $Python - run: python -m venv .venv; pip install -r requirements-demo.txt"
}

if (-not $SkipMirror) {
    Write-Host "==> Mirroring static assets (Zaha + Marie classic)..."
    & $Python -m demos.mirror
}

$ServerJob = $null
if (-not $SkipServer) {
    Write-Host "==> Starting demo server on http://127.0.0.1:${Port}/ ..."
    $ServerJob = Start-Job -ScriptBlock {
        param($Repo, $Port)
        Set-Location $Repo
        $env:PYTHONPATH = $Repo
        $env:DEMO_CONFIG = "fullstack"
        $env:DEMO_PORT = "$Port"
        $env:MARIE_FRONTEND_PROXY = "0"
        $env:DEMO_FORCE_REFRESH = "false"
        & (Join-Path $Repo ".venv\Scripts\python.exe") -m demos.server
    } -ArgumentList $Repo, $Port

    $deadline = (Get-Date).AddSeconds(45)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/health" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) {
        if ($ServerJob) { Receive-Job $ServerJob; Stop-Job $ServerJob; Remove-Job $ServerJob }
        Write-Error "Demo server did not become ready on port $Port"
    }
    Write-Host "    Server ready."
}

$Base = "http://127.0.0.1:${Port}"
$Failed = $false

function Run-Step {
    param([string]$Label, [string[]]$Command)
    Write-Host ""
    Write-Host "==> $Label"
    & $Python @Command
    if ($LASTEXITCODE -ne 0) {
        $script:Failed = $true
        Write-Warning "FAILED: $Label"
    }
}

Run-Step -Label "Hub + route smoke tests" -Command @("-m", "demos.test_server_hub")
Run-Step -Label "Demo cache + search API" -Command @("-m", "demos.test_demo_setup")
Run-Step -Label "Marie API contract GET" -Command @("-m", "demos.verify_marie_frontend_compat")
Run-Step -Label "Zaha page questions routing" -Command @("-m", "demos.test_zaha_page_questions")
Run-Step -Label "Marie page questions routing" -Command @("-m", "demos.test_marie_page_questions")
Run-Step -Label "Zaha HTTP smoke" -Command @("-m", "demos.test_zaha_page_questions", "--http", "--base-url", $Base)
Run-Step -Label "Marie HTTP smoke" -Command @("-m", "demos.test_marie_page_questions", "--http", "--base-url", $Base)

Write-Host ""
Write-Host "==> HTTP page checks"
$Pages = @(
    "$Base/",
    "$Base/demos/hub/",
    "$Base/demos/zaha/",
    "$Base/demos/marie-classic/",
    "$Base/demos/marie/",
    "$Base/health/cache"
)
foreach ($Url in $Pages) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
        $code = $r.StatusCode
    } catch {
        $resp = $_.Exception.Response
        if ($resp) { $code = [int]$resp.StatusCode } else { $code = "ERR" }
    }
    $ok = ($code -eq 200) -or ($code -eq 302) -or ($code -eq 308)
    Write-Host ("  {0} {1}" -f $code, $Url)
    if (-not $ok) { $Failed = $true }
}

if ($WithLlm) {
    Run-Step -Label "Zaha LLM HTTP sample" -Command @("-m", "demos.test_zaha_page_questions", "--http", "--llm", "--limit", "2", "--base-url", $Base)
    Run-Step -Label "Marie LLM HTTP sample" -Command @("-m", "demos.test_marie_page_questions", "--http", "--llm", "--limit", "2", "--base-url", $Base)
} else {
    Write-Host ""
    Write-Host "Skipping LLM round-trips (pass -WithLlm to include)."
}

if ($ServerJob) {
    Write-Host ""
    Write-Host "Stopping background demo server..."
    Stop-Job $ServerJob -ErrorAction SilentlyContinue
    Remove-Job $ServerJob -Force -ErrorAction SilentlyContinue
}

Write-Host ""
if ($Failed) {
    Write-Error "Full-stack smoke test had failures."
}
Write-Host "Full-stack smoke test passed."
Write-Host ("Manual check: open {0}/demos/hub/" -f $Base)
