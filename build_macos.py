#!/usr/bin/env python3
"""Build patched AIAssistant-360 macOS bundles for Apple Silicon and Intel.

Run this script on macOS with Python 3.12:

  # Apple Silicon (M1/M2/M3...)
  python3.12 build_macos.py --arch arm64 \\
      --input AIAssistant-360-arm64.app \\
      --output AIAssistant-360-no-renew-arm64.app

  # Intel Mac
  python3.12 build_macos.py --arch x86_64 \\
      --input AIAssistant-360-x86_64.app \\
      --output AIAssistant-360-no-renew-x86_64.app

Requirements:
  - macOS host (cannot cross-build a runnable .app from Windows)
  - Python 3.12 (same major version as the original bundle)
  - pyinstaller: pip install pyinstaller
  - Original unpatched .app for each CPU architecture
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import patch_no_renew_menu as patcher

ROOT = Path(__file__).resolve().parent
PYINST_EXTRACTOR = ROOT / "pyinstxtractor.py"


def ensure_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit(
            "This script must run on macOS. Windows/Linux cannot produce runnable .app bundles."
        )


def find_app_binary(app_path: Path) -> Path:
    macos_dir = app_path / "Contents" / "MacOS"
    if not macos_dir.is_dir():
        raise FileNotFoundError(f"Missing Contents/MacOS in {app_path}")
    candidates = [
        p
        for p in macos_dir.iterdir()
        if p.is_file() and p.name != ".DS_Store" and not p.name.startswith("._")
    ]
    if not candidates:
        raise FileNotFoundError(f"No executable found in {macos_dir}")
    if len(candidates) > 1:
        candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def verify_arch(binary: Path, arch: str) -> None:
    proc = subprocess.run(
        ["lipo", "-info", str(binary)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"warning: could not verify arch with lipo: {proc.stderr.strip()}")
        return
    info = proc.stdout.strip()
    print(info)
    if arch == "arm64" and "arm64" not in info:
        raise SystemExit(f"{binary} does not look like an arm64 build")
    if arch == "x86_64" and "x86_64" not in info:
        raise SystemExit(f"{binary} does not look like an x86_64 build")


def extract_bundle(binary: Path) -> Path:
    if not PYINST_EXTRACTOR.exists():
        raise FileNotFoundError(f"Missing {PYINST_EXTRACTOR}")
    before = {p.name for p in binary.parent.iterdir()}
    subprocess.run([sys.executable, str(PYINST_EXTRACTOR), str(binary)], check=True)
    after = [p for p in binary.parent.iterdir() if p.is_dir() and p.name.endswith("_extracted")]
    new_dirs = [p for p in after if p.name not in before]
    if not new_dirs:
        guess = binary.parent / f"{binary.name}_extracted"
        if guess.is_dir():
            return guess
        raise FileNotFoundError(f"Extractor did not create *_extracted next to {binary}")
    return new_dirs[0]


def remove_quarantine(app_path: Path) -> None:
    subprocess.run(["xattr", "-cr", str(app_path)], check=False)


def codesign_app(app_path: Path) -> None:
    proc = subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"warning: codesign failed: {proc.stderr.strip()}")
    else:
        print(f"codesigned {app_path}")


def build_app(input_app: Path, output_app: Path, arch: str, *, force: bool) -> None:
    ensure_macos()
    if not input_app.exists():
        raise FileNotFoundError(f"Input app not found: {input_app}")
    if output_app.exists():
        if not force:
            raise SystemExit(f"Output already exists: {output_app} (use --force)")
        if output_app.is_dir():
            shutil.rmtree(output_app)
        else:
            output_app.unlink()

    shutil.copytree(input_app, output_app, symlinks=True)
    binary = find_app_binary(output_app)
    verify_arch(binary, arch)

    extracted = extract_bundle(binary)
    patcher.build_patched_bundle(binary, binary, extracted)
    remove_quarantine(output_app)
    codesign_app(output_app)
    print(f"Built {output_app}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch AIAssistant-360 macOS app bundle")
    parser.add_argument(
        "--arch",
        required=True,
        choices=["arm64", "x86_64"],
        help="Expected CPU architecture of the input .app",
    )
    parser.add_argument("--input", required=True, type=Path, help="Original .app bundle")
    parser.add_argument("--output", required=True, type=Path, help="Patched .app output path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output .app")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"host={platform.platform()}")
    build_app(args.input.resolve(), args.output.resolve(), args.arch, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
