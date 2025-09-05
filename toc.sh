#!/usr/bin/env bash
# generate_toc.sh
# Creates _toc.yml for Jupyter Book from notebooks/ tree.
# - Groups by first-level directory under notebooks/
# - Adds README.md first (if present) per group
# - Adds all .ipynb files recursively (excluding .ipynb_checkpoints)
# - Also handles .ipynb directly under notebooks/ (caption: "Notebooks")

set -euo pipefail

ROOT_DIR="$(pwd)"
NB_ROOT="${1:-notebooks}"  # allow optional path, defaults to notebooks
TOC_FILE="${2:-_toc.yml}"

if [[ ! -d "$NB_ROOT" ]]; then
  echo "Error: '$NB_ROOT' directory not found." >&2
  exit 1
fi

# Start TOC
{
  echo "# Table of contents"
  echo "# Learn more at https://jupyterbook.org/customize/toc.html"
  echo "format: jb-book"
  echo "root: index"
  echo "parts:"
} > "$TOC_FILE"

# Helper to emit a part header
emit_part_header() {
  local caption="$1"
  {
    echo "  - caption: ${caption}"
    echo "    chapters:"
  } >> "$TOC_FILE"
}

# Helper to emit a file line (expects repo-root-relative path)
emit_file() {
  local file="$1"
  echo "    - file: ${file}" >> "$TOC_FILE"
}

# Collect top-level subdirectories under notebooks/
mapfile -t TOP_DIRS < <(find "$NB_ROOT" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | LC_ALL=C sort)

# Handle notebooks directly under notebooks/ (no subdir)
mapfile -t ROOT_NOTEBOOKS < <(find "$NB_ROOT" -maxdepth 1 -type f -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" | LC_ALL=C sort)

if (( ${#ROOT_NOTEBOOKS[@]} > 0 )); then
  emit_part_header "Notebooks"
  # Optionally include README.md at notebooks root
  if [[ -f "${NB_ROOT}/README.md" ]]; then
    emit_file "${NB_ROOT}/README.md"
  fi
  for f in "${ROOT_NOTEBOOKS[@]}"; do
    # strip leading ./ if present
    rel="${f#./}"
    emit_file "${rel}"
  done
fi

# For each top-level directory, include README.md then all .ipynb recursively
for d in "${TOP_DIRS[@]}"; do
  SUBDIR="${NB_ROOT}/${d}"

  # Gather notebooks under this subdir
  # Exclude .ipynb_checkpoints
  mapfile -d '' -t NB_FILES < <(find "$SUBDIR" -type f -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" -print0 | sort -z)
  # If none, but README exists, still create a part (useful for index pages)
  if (( ${#NB_FILES[@]} == 0 )) && [[ ! -f "${SUBDIR}/README.md" ]]; then
    continue
  fi

  emit_part_header "$d"

  # README.md first if present
  if [[ -f "${SUBDIR}/README.md" ]]; then
    emit_file "${SUBDIR}/README.md"
  fi

  # Emit notebooks
  for f in "${NB_FILES[@]}"; do
    rel="${f#./}"
    emit_file "${rel}"
  done
done

echo "Wrote TOC to ${TOC_FILE}"

