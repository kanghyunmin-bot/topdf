#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
: "${TOPDF_SIGN_IDENTITY:?Developer ID Application identity required}"
: "${TOPDF_NOTARY_PROFILE:?Existing notarytool keychain profile required}"
: "${TOPDF_SUPPORT_CONTACT:?Public support contact required}"
[[ "${TOPDF_CLEAN_MAC_VERIFIED:-0}" == 1 ]] || { print -u2 'Independent clean Mac validation must be completed first.'; exit 1; }
security find-identity -v -p codesigning | /usr/bin/grep -F "$TOPDF_SIGN_IDENTITY" >/dev/null || { print -u2 'Signing identity is not present.'; exit 1; }
# Rebuild with Developer ID; never put credentials or private keys in the repository.
python3 scripts/build-release.py
codesign --verify --deep --strict 'build/release/PDF로 변환.app'
ditto -c -k --keepParent 'build/release/PDF로 변환.app' build/notarization.zip
xcrun notarytool submit build/notarization.zip --keychain-profile "$TOPDF_NOTARY_PROFILE" --wait
xcrun stapler staple 'build/release/PDF로 변환.app'
xcrun stapler validate 'build/release/PDF로 변환.app'
spctl --assess --type execute --verbose=2 'build/release/PDF로 변환.app'
print 'App notarization completed. Create the final DMG only after updating RC notices, public contact, and final verification report.'
