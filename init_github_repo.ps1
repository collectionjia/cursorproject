param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$files = @(
    ".gitignore",
    ".github/workflows/build-macos.yml",
    "build_macos.py",
    "patch_no_renew_menu.py",
    "pyinstxtractor.py",
    "export_macos_kit.py",
    "GITHUB_ACTIONS_步骤.txt"
)

foreach ($f in $files) {
    if (-not (Test-Path $f)) {
        throw "Missing required file: $f"
    }
}

if (-not (Test-Path ".git")) {
    git init -b main
}

git add @files
$status = git status --porcelain
if (-not $status) {
    Write-Host "No changes to commit."
} else {
    git commit -m "Add macOS GitHub Actions build workflow and patch scripts"
}

$remotes = git remote 2>$null
if ($remotes -notcontains "origin") {
    git remote add origin $RepoUrl
} else {
    git remote set-url origin $RepoUrl
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. git push -u origin main"
Write-Host "  2. Open GitHub -> Actions -> Build macOS Patched App -> Run workflow"
Write-Host "  3. See GITHUB_ACTIONS_步骤.txt for details"
Write-Host ""
