#!/bin/bash
# Extract .app from a remote zip or dmg URL (macOS only).
set -euo pipefail

URL="$1"
WORKDIR="${2:-extract_input}"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

fname="$(basename "${URL%%\?*}")"
if [ -z "$fname" ] || [ "$fname" = "/" ]; then
  fname="input.bin"
fi

echo "Downloading: $URL"
curl -fL "$URL" -o "$fname"

extract_from_dir() {
  local root="$1"
  local app
  app="$(find "$root" -name '*.app' -type d ! -path '*/.*' | head -1)"
  if [ -z "$app" ]; then
    echo "No .app found under $root"
    find "$root" -maxdepth 4 \( -type f -o -type d \) | head -50
    exit 1
  fi
  echo "Found app: $app"
  cp -R "$app" ./output.app
  echo "INPUT_APP=$(pwd)/output.app"
}

lower="$(echo "$fname" | tr '[:upper:]' '[:lower:]')"
if [[ "$lower" == *.dmg ]]; then
  echo "Extracting from DMG..."
  mount_point="$(hdiutil attach -nobrowse -readonly "$fname" | tail -1 | awk '{print $NF}')"
  trap 'hdiutil detach "$mount_point" 2>/dev/null || true' EXIT
  extract_from_dir "$mount_point"
elif [[ "$lower" == *.zip ]]; then
  echo "Extracting from ZIP..."
  unzip -q "$fname"
  extract_from_dir "."
else
  file_type="$(file -b "$fname")"
  if echo "$file_type" | grep -qi 'zip'; then
    unzip -q "$fname"
    extract_from_dir "."
  elif echo "$file_type" | grep -qi 'zlib\|xar\|disk image'; then
    mount_point="$(hdiutil attach -nobrowse -readonly "$fname" | tail -1 | awk '{print $NF}')"
    trap 'hdiutil detach "$mount_point" 2>/dev/null || true' EXIT
    extract_from_dir "$mount_point"
  else
    echo "Unsupported file type: $file_type"
    exit 1
  fi
fi
