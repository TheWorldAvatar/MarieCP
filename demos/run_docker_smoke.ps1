# Build + start MarieCP demo Docker stack and run smoke tests.
# From repo root:
#   .\demos\run_docker_smoke.ps1
#   .\demos\run_docker_smoke.ps1 -DataDir "D:\mini_marie_data\data"

param(
    [string]$DataDir = "",
    [int]$Port = 3001,
    [string]$PublishHost = "0.0.0.0",
    [switch]$Down
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
Set-Location $Repo

$Compose = @("compose", "--env-file", "configs/demo_docker.env", "-f", "docker/compose.demo.yml", "-p", "mariecp-demo")

if ($Down) {
    docker @Compose down
    exit 0
}

if (-not $DataDir) {
    foreach ($c in @("D:\mini_marie_data\data", "$env:USERPROFILE\mini_marie_data\data", ".\data")) {
        if (Test-Path (Join-Path $c "mini_marie_cache\chemistry\chemistry_cache.sqlite")) {
            $DataDir = $c
            break
        }
    }
}
if (-not $DataDir) {
    Write-Warning "No warmed cache found - set -DataDir; cache API tests may be skipped"
    $DataDir = ".\data"
}

$env:MARIECP_DATA = $DataDir
$env:MARIECP_PORT = "$Port"
$env:MARIECP_PUBLISH_HOST = $PublishHost

Write-Host "==> Publish: ${PublishHost}:${Port} -> container :8080"
Write-Host "==> Cache mount: $DataDir -> /data"
Write-Host "==> docker compose build"
docker @Compose build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> docker compose up -d"
docker @Compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$deadline = (Get-Date).AddMinutes(2)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/health" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
    docker @Compose logs mariecp-demo
    throw "Container did not become healthy on port $Port"
}
Write-Host "==> Health OK"

Write-Host "==> Hub smoke (in container)"
docker @Compose exec -T mariecp-demo python -m demos.test_server_hub
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$cacheDb = Join-Path $DataDir "mini_marie_cache\chemistry\chemistry_cache.sqlite"
if (Test-Path $cacheDb) {
    Write-Host "==> Cache + search API smoke (in container)"
    docker @Compose exec -T mariecp-demo python -m demos.test_demo_setup
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "==> Skipping cache tests (no chemistry_cache.sqlite)"
}

Write-Host "==> HTTP hub check"
(Invoke-WebRequest -Uri "http://127.0.0.1:${Port}/demos/hub/" -UseBasicParsing).StatusCode

$lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -match '^192\.|^10\.' } | Select-Object -First 1).IPAddress
if ($lanIp -and $PublishHost -eq "0.0.0.0") {
    Write-Host "==> External bind check on ${lanIp}:${Port}"
    (Invoke-WebRequest -Uri "http://${lanIp}:${Port}/health" -UseBasicParsing).StatusCode
}

Write-Host ""
Write-Host "Docker smoke passed. Stack still up on http://127.0.0.1:${Port}/"
Write-Host 'Stop with: .\demos\run_docker_smoke.ps1 -Down'
