#!/bin/bash
# Extract .app from a remote zip or dmg URL (macOS only).
set -euo pipefail

log() { echo "$@" >&2; }

URL="$1"
WORKDIR="${2:-extract_input}"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

fname="$(basename "${URL%%\?*}")"
if [ -z "$fname" ] || [ "$fname" = "/" ]; then
  fname="input.bin"
fi

log "Downloading: $URL"
curl -fL "$URL" -o "$fname"
ls -lah "$fname" >&2
file "$fname" >&2

extract_from_dir() {
  local root="$1"
  log "Listing mount/root: $root"
  ls -la "$root" >&2 || true

  local app
  app="$(find "$root" -maxdepth 8 -name '*.app' -type d ! -path '*/.*' 2>/dev/null | head -1 || true)"
  if [ -z "$app" ]; then
    log "No .app found under $root"
    find "$root" -maxdepth 8 \( -type f -o -type d \) 2>/dev/null | head -80 >&2
    exit 1
  fi
  log "Found app: $app"
  cp -R "$app" ./output.app
  printf '%s\n' "$(pwd)/output.app"
}

lower="$(echo "$fname" | tr '[:upper:]' '[:lower:]')"
ftype="$(file -b "$fname")"
if [[ "$lower" == *.dmg ]] || echo "$ftype" | grep -qi 'disk image\|xar\|zlib'; then
  log "Extracting from DMG..."
  MOUNTPOINT="$WORKDIR/mnt"
  mkdir -p "$MOUNTPOINT"
  hdiutil attach -nobrowse -readonly -mountpoint "$MOUNTPOINT" "$fname" >&2
  trap 'hdiutil detach "$MOUNTPOINT" 2>/dev/null || true' EXIT
  extract_from_dir "$MOUNTPOINT"
elif [[ "$lower" == *.zip ]] || echo "$ftype" | grep -qi 'zip'; then
  log "Extracting from ZIP..."
  unzip -q "$fname"
  extract_from_dir "."
else
  log "Unsupported file type: $ftype"
  exit 1
fi
