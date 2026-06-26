# Run MarieCP Docker install on zaha-01 over SSH.
#
# Usage:
#   .\deploy\zaha-01\deploy_remote.ps1
#   .\deploy\zaha-01\deploy_remote.ps1 -Remote "xz378@203.0.113.10"
#
param(
    [string]$Remote = $env:MARIECP_REMOTE
)

if (-not $Remote) { $Remote = "xz378@zaha-01" }

Write-Host "==> Remote: $Remote"
Write-Host "==> Docker install (project mariecp-demo only)"

$remoteCmd = @"
set -euo pipefail
if [[ ! -d ~/mariecp/.git ]]; then
  git clone https://github.com/TheWorldAvatar/MarieCP.git ~/mariecp
fi
cd ~/mariecp
git fetch origin main
git checkout main
git pull --ff-only origin main
bash deploy/zaha-01/install.sh
"@

ssh -o ConnectTimeout=15 $Remote $remoteCmd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Next: merge deploy/zaha-01/nginx-mariecp-demo.conf and reload nginx after review"
