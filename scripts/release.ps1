param(
    [string]$Version = "",
    [string]$NextVersion = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$versionFile = Join-Path $repoRoot "VERSION"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Normalize-Version([string]$value) {
    $normalized = $value.Trim()
    if (-not $normalized.StartsWith("v")) {
        $normalized = "v$normalized"
    }
    return $normalized
}

function Get-NextPatchSnapshot([string]$releaseVersion) {
    if ($releaseVersion -notmatch "^v(\d+)\.(\d+)\.(\d+)$") {
        throw "Release version must look like v0.0.8. Got '$releaseVersion'."
    }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    $patch = [int]$Matches[3] + 1
    return "v$major.$minor.$patch-SNAPSHOT"
}

function Assert-Releasable-WorkingTree {
    $statusLines = @(git status --porcelain=v1)
    $blockingChanges = @()
    $trackedTodoChanges = @()

    foreach ($line in $statusLines) {
        if ($line.Length -lt 4) {
            continue
        }

        $path = $line.Substring(3)
        $isTodoPath = $path -eq "todo" -or $path.StartsWith("todo/") -or $path.StartsWith("todo\")

        if ($isTodoPath) {
            if (-not $line.StartsWith("?? ")) {
                $trackedTodoChanges += $line
            }
            continue
        }

        $blockingChanges += $line
    }

    if ($trackedTodoChanges) {
        throw "todo/ files are local-only and must not be staged or tracked before release:`n$($trackedTodoChanges -join "`n")"
    }

    if ($blockingChanges) {
        throw "Working tree must be clean before release, except untracked todo/ files:`n$($blockingChanges -join "`n")"
    }
}

Push-Location $repoRoot
try {
    Assert-Releasable-WorkingTree

    $currentVersion = Normalize-Version (Get-Content -Raw -LiteralPath $versionFile)
    if (-not $Version) {
        if ($currentVersion -notmatch "-SNAPSHOT$") {
            throw "VERSION must be a snapshot when RELEASE_VERSION is omitted. Got '$currentVersion'."
        }
        $releaseVersion = $currentVersion -replace "-SNAPSHOT$", ""
    } else {
        $releaseVersion = Normalize-Version $Version
    }

    if ($currentVersion -ne "$releaseVersion-SNAPSHOT") {
        throw "VERSION is '$currentVersion', which does not match release snapshot '$releaseVersion-SNAPSHOT'."
    }

    if (-not $NextVersion) {
        $NextVersion = Get-NextPatchSnapshot $releaseVersion
    } else {
        $NextVersion = Normalize-Version $NextVersion
        if ($NextVersion -notmatch "-SNAPSHOT$") {
            $NextVersion = "$NextVersion-SNAPSHOT"
        }
    }

    [System.IO.File]::WriteAllText($versionFile, "$releaseVersion`n", $utf8NoBom)
    git add VERSION
    git commit -m "Release $releaseVersion"
    git tag $releaseVersion

    [System.IO.File]::WriteAllText($versionFile, "$NextVersion`n", $utf8NoBom)
    git add VERSION
    git commit -m "Start $NextVersion"

    Write-Host "Prepared release $releaseVersion and next development version $NextVersion."
    Write-Host "Publish with: task releasepush RELEASE_VERSION=$releaseVersion"
} finally {
    Pop-Location
}
