# Re-trigger GitHub Actions macOS build
# Usage:
#   $env:GITHUB_TOKEN = "ghp_你的token"
#   .\trigger_macos_build.ps1              # arm64 only (faster)
#   .\trigger_macos_build.ps1 -IncludeIntel  # both architectures
#   .\trigger_macos_build.ps1 -IntelOnly     # intel only

param(
    [string]$Token = $env:GITHUB_TOKEN,
    [string]$Owner = "collectionjia",
    [string]$Repo = "cursorproject",
    [switch]$IncludeIntel,
    [switch]$IntelOnly
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
    Write-Host "Set GITHUB_TOKEN first, e.g. `$env:GITHUB_TOKEN = 'ghp_...'"
    exit 1
}

$arm64 = "https://github.com/$Owner/$Repo/releases/download/v1.0-original-arm64/AIAssistant-m-360.dmg"
$intel = "https://github.com/$Owner/$Repo/releases/download/v1.0-original-x86_64/AIAssistant-intel-360.dmg"

if ($IntelOnly) {
    $workflow = "build-macos-intel.yml"
    $body = @{ ref = "main" } | ConvertTo-Json -Depth 5
} else {
    $workflow = "build-macos.yml"
    $inputs = @{ arm64_zip_url = $arm64 }
    if ($IncludeIntel) {
        $inputs.x86_zip_url = $intel
    } else {
        $inputs.x86_zip_url = ""
    }
    $body = @{ ref = "main"; inputs = $inputs } | ConvertTo-Json -Depth 5
}
$headers = @{
    Authorization          = "Bearer $Token"
    Accept                 = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

Invoke-RestMethod `
    -Uri "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$workflow/dispatches" `
    -Headers $headers -Method Post -Body $body -ContentType "application/json"

Write-Host "Triggered $workflow. Open: https://github.com/$Owner/$Repo/actions"
if ($IntelOnly) {
    Write-Host "Intel-only build queued (macos-13 runner may take a while)."
} elseif (-not $IncludeIntel) {
    Write-Host "arm64 only — Intel job skipped (use -IncludeIntel or -IntelOnly)."
}
