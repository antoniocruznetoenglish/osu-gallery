# Build script for osu gallery
# Usage: .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== osu gallery build ===" -ForegroundColor Cyan

# Check for PyInstaller
Write-Host "Checking PyInstaller..." -ForegroundColor Yellow
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Clean previous build artifacts (build/ and dist/ are the only disposable outputs)
Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Build directly from the entry point — PyInstaller regenerates osu_gallery.spec every run.
# --hidden-import flags cover PySide6's internal module references that the importer
# cannot discover statically; --collect-data includes the package's non-Py data files.
# --onedir mode keeps data/ folder next to the exe (not in temp like --onefile).
Write-Host "Building with PyInstaller..." -ForegroundColor Cyan
pyinstaller `
    --name osu-gallery `
    --windowed `
    --onedir `
    --hidden-import PySide6 `
    --hidden-import PySide6.QtCore `
    --hidden-import PySide6.QtGui `
    --hidden-import PySide6.QtWidgets `
    --collect-data osu_gallery `
    --collect-data PySide6 `
    osu_gallery/__main__.py

# Report
if (Test-Path "dist\osu-gallery.exe") {
    $exeSize = (Get-Item "dist\osu-gallery.exe").Length / 1MB
    Write-Host "Build complete! Output: dist\osu-gallery.exe ($([math]::Round($exeSize, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
