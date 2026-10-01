# TopDF Android — embedded offline engines

Android 8 (API 26) and later; ARM64 and x86_64 engines. No INTERNET permission, server, account, API key, analytics SDK, or runtime engine download. All conversions run in an isolated `:engine` process under the Android application sandbox. Cancellation terminates that process. Originals are copied into private temporary storage and never edited.

Supported inputs: PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, ODT/ODS/ODP, RTF, CSV/TSV, UTF-8 text, HTML, EPUB, HWP/HWPX, JPEG/PNG/BMP/GIF/WebP/HEIC (device decoder support), and multipage TIFF. Unsupported/encrypted/corrupt documents produce an error. This does not guarantee pixel-identical rendering of every Office/Hancom feature. External linked resources must be embedded in the source document for offline use. Apple Pages/Keynote/Numbers native formats are currently a macOS-only route requiring those installed applications.

Use the file picker or another file app's Share menu. Preview, select page range and original size/A4 portrait/A4 landscape, then choose a destination with the Android document picker. Print opens Android's native print UI. A network printer may itself require a network; creating a PDF does not.

## Reproducible build

Build host currently macOS with Python 3.12+, JDK 11, Android SDK platform 35/build-tools 35.0.0, NDK r29, Rust 1.98.1 and targets `aarch64-linux-android`, `x86_64-linux-android`. Build tools may need downloads; the installed application does not.

1. `python3 scripts/fetch-android-inputs.py` downloads pinned APKs and Maven artifacts with SHA-256 verification, plus hwp-cli v1.3.1 source to `build/upstream/hwp-cli-1.3.1`. Engine native libraries and asset resources are copied unchanged from the two F-Droid LibreOffice 26.2.6.3 APKs.
2. Set `ANDROID_NDK_HOME` to NDK r29 and install both Rust targets. `python3 scripts/build-android-native.py` compiles the JNI HWP/TIFF wrapper for both ABIs. Cargo.lock pins all registry dependencies.
3. `python3 scripts/build-android.py` builds the APK using SDK tools. Set `ANDROID_SDK_ROOT` and `JAVA_HOME` when those differ from the script defaults.
4. APK signing uses a persistent private preview key under ignored `build/private-keys`. For distribution signing, provide `TOPDF_ANDROID_KEYSTORE` and `TOPDF_ANDROID_PASSWORD_FILE`; retain the signing key for compatible updates. Never commit keys or passwords.

The Java LibreOfficeKit bindings retain MPL-2.0 headers; `LibreOfficeKit.init` was adapted from Activity to Context. TopDF's MIT license applies to its own code, not those bindings or embedded third-party engines. Notices are available in the application's Help → Licenses screen and `legal/android/THIRD_PARTY.html`. Android sources accompany the RC release; original LibreOffice Android source is also available from https://f-droid.org/repo/org.documentfoundation.libreoffice_131_src.tar.gz and https://f-droid.org/repo/org.documentfoundation.libreoffice_129_src.tar.gz. Android 192 registry archive hashes/licenses are recorded separately from desktop hwp-cli's 276-archive dependency set.

## Validation boundaries

ARM64 Android 15 emulator, Wi-Fi/mobile data disabled, no application INTERNET permission: DOCX/PPTX/XLSX/HWP/HWPX/TXT/PNG/multipage TIFF converted; Korean text and expected pages checked; selected page and all three layout modes checked using PDFBox text extraction and geometry. Independent physical Android devices, Android 8, actual print hardware and store distribution remain unverified. The x86_64 JNI build is verified by compilation, not device execution.
