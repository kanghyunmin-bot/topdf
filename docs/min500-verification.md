# RC4 local verification

Installed application payload: ARM 476,872,704 bytes; Intel 493,166,592 bytes. Limit: 500,000,000 bytes. Both signatures and DMG checksums verified. These are ad hoc signed, unnotarized local artifacts.

All 135 original LibreOffice font files remain byte-identical. NanumGothic Regular/Bold are additional, unmodified OFL fonts. Missing explicit font names use NanumGothic in modern Office/ODF and HWP/HWPX; available fonts remain requested. Legacy Office fallback and unsupported glyph fallback remain engine-controlled.

Both architectures passed 26 app regression checks and DOCX missing/available-font and HWPX missing-font checks. Intel was executed under Rosetta on Apple Silicon, not an independent Intel Mac. Network test: no outbound HTTP requests.

The full and compact engines, using the same new font policy, produced identical extracted text and 72-DPI rendered page pixels for 17 supported fixtures; EPUB was rejected by both. This confirms compaction parity on these fixtures, not Microsoft Office or Hancom layout parity for every document.

HWP source validation ran scripts/check.sh. Rust fmt/clippy/workspace tests and 33 Python runner tests passed. The complete check failed at the original, unmodified hancom-regression shell gate: /bin/bash -n reports unexpected end of file on both the original source and modified copy. 47 fixture-dependent cases were skipped (4 optional), and the pinned public Poppler parity gate was skipped. The exact final line is:

```text
== check: FAILED (위 게이트 중 실패 있음) skipped-for-missing-fixtures=47 (optional=4) ==
```

Detailed results: [min500-verification.json](min500-verification.json).
