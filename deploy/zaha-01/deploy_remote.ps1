# Run MarieCP install on zaha-01 over SSH (safe: no Docker / no nginx reload).
#
# Usage (VPN / hosts entry for zaha-01 must work):
#   .\deploy\zaha-01\deploy_remote.ps1
#   .\deploy\zaha-01\deploy_remote.ps1 -Remote "xz378@203.0.113.10"
#   .\deploy\zaha-01\deploy_remote.ps1 -InstallSystemd
#
param(
    [string]$Remote = $env:MARIECP_REMOTE,
    [switch]$InstallSystemd,
    [switch]$SkipMirror
)

if (-not $Remote) { $Remote = "xz378@zaha-01" }

$repo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$installSh = Join-Path $PSScriptRoot "install.sh"

$flags = @()
if ($InstallSystemd) { $flags += "INSTALL_SYSTEMD=1" }
if ($SkipMirror) { $flags += "SKIP_MIRROR=1" }
$prefix = if ($flags.Count) { ($flags -join " ") + " " } else { "" }

Write-Host "==> Remote: $Remote"
Write-Host "==> Safe install (mariecp-demo only; Docker untouched)"

$remoteCmd = @"
set -euo pipefail
if [[ ! -d ~/mariecp/.git ]]; then
  git clone https://github.com/TheWorldAvatar/MarieCP.git ~/mariecp
fi
cd ~/mariecp
git fetch origin main
git checkout main
git pull --ff-only origin main
${prefix}bash deploy/zaha-01/install.sh
"@

ssh -o ConnectTimeout=15 $Remote $remoteCmd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Next (manual, avoids disturbing other stacks):"
Write-Host "  1. Ensure ~/mariecp/.env has REMOTE_API_KEY"
Write-Host "  2. Merge deploy/zaha-01/nginx-mariecp-demo.conf into www.theworldavatar.io nginx"
Write-Host "  3. nginx -t && sudo systemctl reload nginx   # only after config review"
