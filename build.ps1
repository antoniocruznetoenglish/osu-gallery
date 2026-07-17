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

# Clean previous build artifacts
Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "osu_gallery.spec") { Remove-Item "osu_gallery.spec" }

# Build
Write-Host "Building with PyInstaller..." -ForegroundColor Cyan
pyinstaller osu_gallery.spec --clean

# Report
if (Test-Path "dist\osu-gallery.exe") {
    $exeSize = (Get-Item "dist\osu-gallery.exe").Length / 1MB
    Write-Host "Build complete! Output: dist\osu-gallery.exe ($([math]::Round($exeSize, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
