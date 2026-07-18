#!/usr/bin/env bash
#
# new_project.sh — bootstrap a new project from the project_docs/ template (v2).
#
# Usage:
#   bash new_project.sh "Project Name" /path/to/new/project
#
# What it does:
#   1. Finds the template (project_docs/ next to this script, or override with TEMPLATE_DIR).
#   2. Copies it into <target>/project_docs/.
#   3. Copies CHANGELOG_TEMPLATE.md into <target>/CHANGELOG.md (project root, not project_docs/).
#   4. Replaces the placeholder "[Project Name]" with your real project name in every .md file.
#   5. Fills in today's date wherever "YYYY-MM-DD" appears as a placeholder.
#   6. Prints exactly what to do next.

set -euo pipefail

# ---- 1. Parse arguments ----------------------------------------------------
if [ $# -lt 2 ]; then
  echo "Usage: bash new_project.sh \"Project Name\" /path/to/new/project"
  echo "Example: bash new_project.sh \"Project A\" ~/dev/ProjectA"
  exit 1
fi

PROJECT_NAME="$1"
TARGET_DIR="$2"

# ---- 2. Locate the template --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="${TEMPLATE_DIR:-"$SCRIPT_DIR/project_docs"}"
CHANGELOG_SRC="$SCRIPT_DIR/CHANGELOG_TEMPLATE.md"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "Error: template folder not found at: $TEMPLATE_DIR"
  echo "Put this script next to your project_docs/ template folder,"
  echo "or set TEMPLATE_DIR=/path/to/project_docs before running."
  exit 1
fi

# ---- 3. Prepare the target --------------------------------------------------
DEST_DOCS="$TARGET_DIR/project_docs"

if [ -e "$DEST_DOCS" ]; then
  echo "Error: $DEST_DOCS already exists. Refusing to overwrite."
  echo "Remove it or pick a different target path."
  exit 1
fi

mkdir -p "$TARGET_DIR"
cp -r "$TEMPLATE_DIR" "$DEST_DOCS"
echo "Copied template into: $DEST_DOCS"

if [ -f "$CHANGELOG_SRC" ]; then
  cp "$CHANGELOG_SRC" "$TARGET_DIR/CHANGELOG.md"
  echo "Copied CHANGELOG.md into: $TARGET_DIR"
fi

# ---- 4. Fill in placeholders -------------------------------------------------
TODAY="$(date +%Y-%m-%d)"

# Find every markdown file (including inside features/ and the root CHANGELOG.md)
# and do the replacement. Using a temp file per-edit for portability across
# sed variants (macOS/BSD vs GNU).
{
  find "$DEST_DOCS" -type f -name "*.md"
  [ -f "$TARGET_DIR/CHANGELOG.md" ] && echo "$TARGET_DIR/CHANGELOG.md"
} | while read -r file; do
  tmp="$(mktemp)"
  sed -e "s/\[Project Name\]/$PROJECT_NAME/g" \
      -e "s/YYYY-MM-DD/$TODAY/g" \
      "$file" > "$tmp"
  mv "$tmp" "$file"
done

echo "Replaced [Project Name] -> \"$PROJECT_NAME\" and YYYY-MM-DD -> $TODAY in all files."

# ---- 5. Confirm structure ----------------------------------------------------
echo ""
echo "Project docs ready:"
find "$DEST_DOCS" -type f -name "*.md" | sort | sed "s|$TARGET_DIR/|  |"
[ -f "$TARGET_DIR/CHANGELOG.md" ] && echo "  CHANGELOG.md"

# ---- 6. Next steps -------------------------------------------------------
cat << NEXT_STEPS

Next steps:
  1. cd "$TARGET_DIR"
  2. Start opencode (plan agent) in this folder.
  3. First prompt:

     Read project_docs/00_README.md, then project_docs/01_Product.md.
     Interview me to fill in 01_Product.md, one question at a time.
     My one-line idea: [describe your project here]

  4. Repeat for 02_System_Design.md, 03_Technical_Architecture.md,
     and 09_Security.md (state network exposure explicitly, even if "None").
  5. Once 03 and 09 are filled in, edit 03 and flip Design Phase to "Frozen".
  6. Fill 04_Implementation_Roadmap.md (run the §0 Feasibility Check on your
     first milestone) and copy features/TEMPLATE.md for your first P0 feature.
  7. Skim 10_Testing_Strategy.md, 11_Contributing.md, and 12_Coding_Standards.md —
     fill what applies now, leave the rest explicitly "N/A for now" rather than blank.
  8. Fill 07_AI_Context_Brief.md by hand.
  9. Switch to the builder agent and start implementing.
NEXT_STEPS
