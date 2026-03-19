param(
    [switch]$SkipSync,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $SkipSync) {
    uv sync --group dev
}

uv run pyinstaller packaging/windows/darkfactory.spec --noconfirm --clean

if ($SkipInstaller) {
    Write-Host "Executable build complete. Skipping installer generation."
    exit 0
}

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 was not found at '$Iscc'. Install it or rerun with -SkipInstaller."
}

& $Iscc packaging/windows/darkfactory.iss
Write-Host "Windows installer build complete."
