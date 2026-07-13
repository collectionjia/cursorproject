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

is_macho() {
  local f="$1"
  [ -f "$f" ] || return 1
  file -b "$f" | grep -qi 'Mach-O'
}

find_bundle_root() {
  local root="$1"

  local app
  app="$(find "$root" -maxdepth 8 -name '*.app' -type d ! -path '*/.*' 2>/dev/null | head -1 || true)"
  if [ -n "$app" ]; then
    echo "$app"
    return 0
  fi

  local macos_dir
  while IFS= read -r macos_dir; do
    local bundle
    bundle="$(dirname "$(dirname "$macos_dir")")"
    if [ -d "$bundle/Contents/MacOS" ]; then
      echo "$bundle"
      return 0
    fi
  done < <(find "$root" -maxdepth 8 -type d -path '*/Contents/MacOS' ! -path '*/.*' 2>/dev/null)

  return 1
}

find_loose_macho() {
  local root="$1"
  local best="" best_size=0 f size
  while IFS= read -r f; do
    if is_macho "$f"; then
      size="$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)"
      if [ "$size" -gt "$best_size" ]; then
        best="$f"
        best_size="$size"
      fi
    fi
  done < <(find "$root" -maxdepth 6 -type f ! -name '.*' 2>/dev/null)
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
  log "Listing mount/root: $root"
  ls -la "$root" >&2 || true
  find "$root" -maxdepth 3 \( -type f -o -type d \) ! -path '*/.*' 2>/dev/null | head -80 >&2 || true

  local bundle
  if bundle="$(find_bundle_root "$root")" && [ -n "$bundle" ] && [ -d "$bundle" ]; then
    log "Found bundle root: $bundle"
    rm -rf ./output.app
    cp -R "$bundle" ./output.app
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
  exit 1
}

attach_dmg() {
  local dmg="$1"
  local mountpoint="$2"
  mkdir -p "$mountpoint"
  if ! hdiutil attach -nobrowse -readonly -skip-license-agreement -mountpoint "$mountpoint" "$dmg" >&2; then
    hdiutil attach -nobrowse -readonly -mountpoint "$mountpoint" "$dmg" >&2
  fi
}

lower="$(echo "$fname" | tr '[:upper:]' '[:lower:]')"
ftype="$(file -b "$fname")"
if [[ "$lower" == *.dmg ]] || echo "$ftype" | grep -qi 'disk image\|xar\|zlib'; then
  log "Extracting from DMG..."
  MOUNTPOINT="$WORKDIR/mnt"
  attach_dmg "$fname" "$MOUNTPOINT"
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
