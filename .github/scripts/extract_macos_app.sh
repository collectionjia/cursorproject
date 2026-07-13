#!/bin/bash
# Extract .app from a remote zip or dmg URL (macOS only).
set -euo pipefail

log() { echo "$@" >&2; }

URL="$1"
WORKDIR="${2:-extract_input}"
DEFAULT_URL="https://github.com/collectionjia/cursorproject/releases/download/v1.0-original-arm64/AIAssistant-m-360.dmg"

if [ -z "${URL}" ] || [ "${URL}" = "false" ]; then
  URL="$DEFAULT_URL"
fi

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

fname="$(basename "${URL%%\?*}")"
if [ -z "$fname" ] || [ "$fname" = "/" ]; then
  fname="input.bin"
fi

log "Downloading: $URL"
curl -fL "$URL" -o "$fname"
size="$(stat -f%z "$fname")"
log "Downloaded bytes: $size"
if [ "$size" -lt 50000000 ]; then
  log "ERROR: download looks too small (expected ~100MB dmg)"
  head -c 400 "$fname" >&2 || true
  exit 1
fi
ls -lah "$fname" >&2
file "$fname" >&2

is_macho() {
  local f="$1"
  [ -f "$f" ] || return 1
  file -b "$f" | grep -qi 'Mach-O'
}

pick_best_app() {
  local root="$1"
  local best_app="" best_size=0 app macos_dir exe size

  while IFS= read -r app; do
    macos_dir="$app/Contents/MacOS"
    [ -d "$macos_dir" ] || continue
    while IFS= read -r exe; do
      [ -f "$exe" ] || continue
      is_macho "$exe" || continue
      size="$(stat -f%z "$exe" 2>/dev/null || echo 0)"
      if [ "$size" -gt "$best_size" ]; then
        best_size="$size"
        best_app="$app"
      fi
    done < <(find "$macos_dir" -maxdepth 1 -type f ! -name '.*' 2>/dev/null)
  done < <(find "$root" -maxdepth 14 -name '*.app' -type d ! -path '*/.*' 2>/dev/null)

  if [ -n "$best_app" ]; then
    echo "$best_app"
    return 0
  fi

  return 1
}

find_bundle_root() {
  local root="$1"
  local app
  app="$(pick_best_app "$root" || true)"
  if [ -n "$app" ] && [ -d "$app" ]; then
    echo "$app"
    return 0
  fi

  local macos_dir bundle
  while IFS= read -r macos_dir; do
    bundle="$(dirname "$(dirname "$macos_dir")")"
    if [ -d "$bundle/Contents/MacOS" ]; then
      local exe_count
      exe_count="$(find "$macos_dir" -maxdepth 1 -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')"
      if [ "$exe_count" -gt 0 ]; then
        echo "$bundle"
        return 0
      fi
    fi
  done < <(find "$root" -maxdepth 14 -type d -path '*/Contents/MacOS' ! -path '*/.*' 2>/dev/null)

  return 1
}

find_loose_macho() {
  local root="$1"
  local best="" best_size=0 f size
  while IFS= read -r f; do
    if is_macho "$f"; then
      size="$(stat -f%z "$f" 2>/dev/null || echo 0)"
      if [ "$size" -gt "$best_size" ]; then
        best="$f"
        best_size="$size"
      fi
    fi
  done < <(find "$root" -maxdepth 10 -type f ! -name '.*' 2>/dev/null)
  [ -n "$best" ] || return 1
  echo "$best"
}

wrap_macho_as_app() {
  local binary="$1"
  local exe_name
  exe_name="$(basename "$binary")"
  rm -rf ./output.app
  mkdir -p "./output.app/Contents/MacOS"
  cp "$binary" "./output.app/Contents/MacOS/$exe_name"
  chmod +x "./output.app/Contents/MacOS/$exe_name"
  cat > "./output.app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>${exe_name}</string>
  <key>CFBundleIdentifier</key>
  <string>com.aiassistant360.app</string>
  <key>CFBundleName</key>
  <string>AIAssistant-360</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
</dict>
</plist>
EOF
  log "Wrapped loose Mach-O as output.app (executable=${exe_name})"
}

extract_from_dir() {
  local root="$1"
  log "Listing root: $root"
  ls -la "$root" >&2 || true
  find "$root" -maxdepth 4 \( -type f -o -type d \) ! -path '*/.*' 2>/dev/null | head -120 >&2 || true

  local bundle
  if bundle="$(find_bundle_root "$root")" && [ -n "$bundle" ] && [ -d "$bundle" ]; then
    log "Found bundle root: $bundle"
    rm -rf ./output.app
    ditto "$bundle" ./output.app
    printf '%s\n' "$(pwd)/output.app"
    return 0
  fi

  local macho
  if macho="$(find_loose_macho "$root")" && [ -n "$macho" ]; then
    log "Found loose Mach-O: $macho"
    wrap_macho_as_app "$macho"
    printf '%s\n' "$(pwd)/output.app"
    return 0
  fi

  log "No app bundle or Mach-O executable found under $root"
  return 1
}

ensure_7z() {
  if command -v 7z >/dev/null 2>&1; then
    return 0
  fi
  log "Installing p7zip via Homebrew..."
  brew install p7zip
}

extract_dmg_with_7z() {
  local dmg="$1"
  local outdir="$2"
  ensure_7z
  rm -rf "$outdir"
  mkdir -p "$outdir"
  log "Extracting dmg with 7z..."
  7z x -y "$dmg" -o"$outdir" >&2 || true
}

extract_dmg_with_hdiutil() {
  local dmg="$1"
  local mountpoint="$2"
  log "Extracting dmg with hdiutil..."
  mkdir -p "$mountpoint"
  hdiutil attach -nobrowse -readonly -skip-license-agreement -mountpoint "$mountpoint" "$dmg" >&2
}

lower="$(echo "$fname" | tr '[:upper:]' '[:lower:]')"
ftype="$(file -b "$fname")"
if [[ "$lower" == *.dmg ]] || echo "$ftype" | grep -qi 'disk image\|xar\|zlib'; then
  log "Processing DMG..."
  MOUNTPOINT="$WORKDIR/mnt"
  if extract_dmg_with_hdiutil "$fname" "$MOUNTPOINT" && extract_from_dir "$MOUNTPOINT"; then
    hdiutil detach "$MOUNTPOINT" 2>/dev/null || true
    exit 0
  fi
  hdiutil detach "$MOUNTPOINT" 2>/dev/null || true
  log "hdiutil failed, trying 7z..."
  SEVEN_OUT="$WORKDIR/7z_out"
  extract_dmg_with_7z "$fname" "$SEVEN_OUT"
  extract_from_dir "$SEVEN_OUT"
elif [[ "$lower" == *.zip ]] || echo "$ftype" | grep -qi 'zip'; then
  log "Extracting from ZIP..."
  unzip -q "$fname"
  extract_from_dir "."
else
  log "Unsupported file type: $ftype"
  exit 1
fi
