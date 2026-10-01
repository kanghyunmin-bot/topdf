#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
python3 scripts/build-release.py
python3 scripts/install-local.py
print 'Open the installed app once to register the Finder menu.'
