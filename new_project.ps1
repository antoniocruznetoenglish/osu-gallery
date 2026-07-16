<#
.SYNOPSIS
    Bootstrap a new project from the project_docs/ template (v2).

.DESCRIPTION
    1. Finds the template (project_docs/ next to this script, or override with -TemplateDir).
    2. Copies it into <TargetDir>/project_docs/.
    3. Copies CHANGELOG_TEMPLATE.md into <TargetDir>/CHANGELOG.md (project root, not project_docs/).
    4. Replaces the placeholder "[Project Name]" with your real project name in every .md file.
    5. Fills in today's date wherever "YYYY-MM-DD" appears as a placeholder.
    6. Prints exactly what to do next.

.PARAMETER ProjectName
    The real name of your project, e.g. "Project A".

.PARAMETER TargetDir
    Where the new project should live, e.g. "C:\dev\ProjectA" or "~/dev/ProjectA".

.PARAMETER TemplateDir
    Optional. Path to the project_docs template folder. Defaults to a
    "project_docs" folder sitting next to this script.

.EXAMPLE
    .\new_project.ps1 -ProjectName "Project A" -TargetDir "C:\dev\ProjectA"

.EXAMPLE
    .\new_project.ps1 "Project A" "C:\dev\ProjectA"
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProjectName,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$TargetDir,

    [Parameter(Mandatory = $false)]
    [string]$TemplateDir
)

$ErrorActionPreference = "Stop"

# ---- 1. Locate the template -------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $TemplateDir) {
    $TemplateDir = Join-Path $ScriptDir "project_docs"
}
$ChangelogSrc = Join-Path $ScriptDir "CHANGELOG_TEMPLATE.md"

if (-not (Test-Path -Path $TemplateDir -PathType Container)) {
    Write-Host "Error: template folder not found at: $TemplateDir" -ForegroundColor Red
    Write-Host "Put this script next to your project_docs\ template folder,"
    Write-Host "or pass -TemplateDir 'C:\path\to\project_docs'."
    exit 1
}

# ---- 2. Prepare the target ---------------------------------------------------
$TargetDir = [System.Environment]::ExpandEnvironmentVariables($TargetDir)
if ($TargetDir -eq "~" -or $TargetDir.StartsWith("~/") -or $TargetDir.StartsWith("~\")) {
    # PowerShell doesn't expand ~ automatically the way bash does; do it manually
    # so this script behaves the same as new_project.sh for anyone used to that habit.
    $TargetDir = $TargetDir -replace '^~', [System.Environment]::GetFolderPath("UserProfile")
}
$DestDocs = Join-Path $TargetDir "project_docs"

if (Test-Path -Path $DestDocs) {
    Write-Host "Error: $DestDocs already exists. Refusing to overwrite." -ForegroundColor Red
    Write-Host "Remove it or pick a different target path."
    exit 1
}

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
Copy-Item -Path $TemplateDir -Destination $DestDocs -Recurse
Write-Host "Copied template into: $DestDocs"

$DestChangelog = $null
if (Test-Path -Path $ChangelogSrc -PathType Leaf) {
    $DestChangelog = Join-Path $TargetDir "CHANGELOG.md"
    Copy-Item -Path $ChangelogSrc -Destination $DestChangelog
    Write-Host "Copied CHANGELOG.md into: $TargetDir"
}

# ---- 3. Fill in placeholders --------------------------------------------------
$Today = Get-Date -Format "yyyy-MM-dd"

$MarkdownFiles = @(Get-ChildItem -Path $DestDocs -Filter "*.md" -Recurse -File)
if ($DestChangelog) {
    $MarkdownFiles += Get-Item -Path $DestChangelog
}

foreach ($file in $MarkdownFiles) {
    $content = Get-Content -Path $file.FullName -Raw
    $content = $content.Replace("[Project Name]", $ProjectName)
    $content = $content.Replace("YYYY-MM-DD", $Today)
    # UTF8 without BOM keeps the files clean for tools that are picky about encoding.
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($file.FullName, $content, $utf8NoBom)
}

Write-Host "Replaced [Project Name] -> `"$ProjectName`" and YYYY-MM-DD -> $Today in all files."

# ---- 4. Confirm structure ------------------------------------------------------
Write-Host ""
Write-Host "Project docs ready:"
Get-ChildItem -Path $DestDocs -Filter "*.md" -Recurse -File |
    ForEach-Object { Write-Host ("  " + $_.FullName.Substring($TargetDir.Length + 1)) }
if ($DestChangelog) {
    Write-Host "  CHANGELOG.md"
}

# ---- 5. Next steps ---------------------------------------------------------
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. cd `"$TargetDir`""
Write-Host "  2. Start opencode (plan agent) in this folder."
Write-Host "  3. First prompt:"
Write-Host ""
Write-Host "     Read project_docs/00_README.md, then project_docs/01_Product.md."
Write-Host "     Interview me to fill in 01_Product.md, one question at a time."
Write-Host "     My one-line idea: [describe your project here]"
Write-Host ""
Write-Host "  4. Repeat for 02_System_Design.md, 03_Technical_Architecture.md,"
Write-Host "     and 09_Security.md (state network exposure explicitly, even if `"None`")."
Write-Host "  5. Once 03 and 09 are filled in, edit 03 and flip Design Phase to `"Frozen`"."
Write-Host "  6. Fill 04_Implementation_Roadmap.md (run the §0 Feasibility Check on your"
Write-Host "     first milestone) and copy features/TEMPLATE.md for your first P0 feature."
Write-Host "  7. Skim 10_Testing_Strategy.md, 11_Contributing.md, and 12_Coding_Standards.md —"
Write-Host "     fill what applies now, leave the rest explicitly `"N/A for now`" rather than blank."
Write-Host "  8. Fill 07_AI_Context_Brief.md by hand."
Write-Host "  9. Switch to the builder agent and start implementing."
