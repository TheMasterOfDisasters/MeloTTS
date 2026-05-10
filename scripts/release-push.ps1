param(
    [string]$Version = "",
    [string]$Remote = "origin",
    [string]$Branch = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Normalize-Version([string]$value) {
    $normalized = $value.Trim()
    if (-not $normalized.StartsWith("v")) {
        $normalized = "v$normalized"
    }
    return $normalized
}

Push-Location $repoRoot
try {
    if (-not $Version) {
        $Version = git describe --tags --abbrev=0 --match "v*.*.*"
        if (-not $Version) {
            throw "Could not find a local release tag. Pass RELEASE_VERSION=vX.Y.Z."
        }
    }

    $releaseVersion = Normalize-Version $Version

    $tagExists = git tag --list $releaseVersion
    if (-not $tagExists) {
        throw "Local tag '$releaseVersion' does not exist. Run task release first."
    }

    Write-Host "Pushing release tag first so GitHub tag workflows build from $releaseVersion..."
    git push $Remote $releaseVersion

    Write-Host "Pushing $Branch after the release tag..."
    git push $Remote $Branch

    Write-Host "Published $releaseVersion. Check GitHub Actions for Docker image builds."
} finally {
    Pop-Location
}
