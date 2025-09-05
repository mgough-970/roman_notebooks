#!/usr/bin/env bash
# generate_requirements.sh
# For each folder under notebooks/ that contains a Jupyter notebook,
# run pipreqsnb to create/replace requirements.txt in that folder.

set -euo pipefail

NB_ROOT="${1:-notebooks}"   # default root dir is notebooks

if [[ ! -d "$NB_ROOT" ]]; then
  echo "Error: '$NB_ROOT' directory not found." >&2
  exit 1
fi

# Ensure pipreqsnb is installed
if ! command -v pipreqsnb &>/dev/null; then
  echo "Error: pipreqsnb not found in PATH. Install with: pip install pipreqsnb" >&2
  exit 1
fi

# Find all directories containing at least one .ipynb file
mapfile -t DIRS < <(find "$NB_ROOT" -type f -name "*.ipynb" ! -path "*/.ipynb_checkpoints/*" \
  -printf "%h\n" | sort -u)

for d in "${DIRS[@]}"; do
  echo "Generating requirements.txt in $d ..."
  pipreqsnb "$d" --force >/dev/null 2>&1 || {
    echo "Warning: pipreqsnb failed in $d" >&2
  }
done

echo "✅ Finished generating requirements.txt files."

