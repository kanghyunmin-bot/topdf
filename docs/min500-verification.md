# RC4 local verification snapshot

Installed application payload: ARM 476,872,704 bytes; Intel 493,117,440 bytes. Limit: 500,000,000 bytes. Both signatures and DMG checksums verified. These are ad hoc signed, unnotarized local artifacts.

All 135 original LibreOffice font files remain byte-identical. NanumGothic Regular/Bold are additional, unmodified OFL fonts. Missing explicit font names use NanumGothic in modern Office/ODF and HWP/HWPX; available fonts remain requested. Legacy Office fallback and unsupported glyph fallback remain engine-controlled.

Both architectures passed 26 app regression checks and DOCX missing/available-font and HWPX missing-font checks. The final Intel artifact was built and tested on the GitHub Intel macOS 15 runner; this is not an independent physical Intel Mac installation test. Network test: no outbound HTTP requests.

The full and compact engines, using the same new font policy, produced identical extracted text and 72-DPI rendered page pixels for 17 supported fixtures; EPUB was rejected by both. This confirms compaction parity on these fixtures, not Microsoft Office or Hancom layout parity for every document.

HWP source validation passed `scripts/check.sh` with Python 3.12 and Homebrew Bash 5.3.20. The macOS bundled Bash 3 is incompatible with the unmodified upstream regression script. Rust fmt/clippy/workspace tests and 33 Python runner tests passed. 47 fixture-dependent cases were skipped (4 optional), and the pinned public Poppler parity gate was skipped. The exact final line is:

```text
== check: OK (fmt/clippy/test/crate-edges/pdf-runner/structured-corpus/claims/doc-surface/release-block/readiness-selfcheck/skip-accounting/public-parity=skipped) skipped-for-missing-fixtures=47 (optional=4) ==
```

This local snapshot predates the final packaged release; final cross-platform artifact evidence is in [rc4-verification.json](rc4-verification.json). The running local installed app was not replaced with the final artifact.

Detailed local results: [min500-verification.json](min500-verification.json).
