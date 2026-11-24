#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Build this app on macOS; Linux cannot validate or create a native Mac application."
  exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "The first package targets Apple Silicon. Intel packaging/performance is not validated."
  exit 1
fi
python3 -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name "Invention Disclosure Generator" --osx-bundle-identifier "ai.verdugolabs.inventiondisclosure" \
  --paths . --add-data "local_app/static:local_app/static" \
  --add-data "skills/inventor-brief-v2:skills/inventor-brief-v2" \
  packaging/launch.py
APP="dist/Invention Disclosure Generator.app"
if [[ -n "${MAC_SIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --sign "$MAC_SIGN_IDENTITY" "$APP"
  codesign --verify --deep --strict "$APP"
fi
# Smoke-check resource layout without launching an unbounded GUI process.
find "$APP" -path '*skills/inventor-brief-v2/scripts/render_report.py' | head -1 | grep -q .
find "$APP" -path '*local_app/static/index.html' | head -1 | grep -q .
"$APP/Contents/MacOS/Invention Disclosure Generator" --self-check
mkdir -p build/dmg-content
cp -R "$APP" build/dmg-content/
ln -sfn /Applications build/dmg-content/Applications
DMG="dist/Invention-Disclosure-Generator-arm64.dmg"
hdiutil create -volname "Invention Disclosure Generator" -srcfolder build/dmg-content -ov -format UDZO "$DMG"
if [[ -n "${MAC_NOTARY_PROFILE:-}" ]]; then
  if [[ -z "${MAC_SIGN_IDENTITY:-}" ]]; then echo "Notarization requires Developer ID signing."; exit 1; fi
  xcrun notarytool submit "$DMG" --keychain-profile "$MAC_NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi
shasum -a 256 "$DMG" > "$DMG.sha256"
echo "Created $DMG. Signing/notarization status depends on the supplied credentials."
