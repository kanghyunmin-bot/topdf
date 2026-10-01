# TopDF — Finder에서 PDF로 변환

macOS Finder에서 파일을 우클릭해 `PDF화…`를 선택하고, 미리보기에서 페이지 범위와 용지 방향을 정한 뒤 PDF를 저장하는 앱입니다.

![앱 아이콘](Assets/AppIcon.png)

## 현재 상태

1.0.0-rc.1, 공개 출시 전 개발·검증용입니다. Apple Silicon을 대상으로 빌드하며 macOS 13을 최소 배포 대상으로 설정했습니다. 실제 검증은 개발 Mac의 macOS 26.5.2에서 수행했습니다. Developer ID 서명·Apple 공증·별도 Mac 설치 테스트는 아직 완료되지 않았습니다.

- DOCX·PPTX·XLSX 등은 내장 LibreOffice를 사용합니다.
- HWP·HWPX는 hwp-cli를 사용합니다. 복잡한 수식·차트·OLE·서식에는 제한이 있습니다.
- 이미지와 PDF는 macOS 프레임워크로 처리합니다.
- Pages·Keynote·Numbers 형식은 해당 Apple 앱이 설치되어 있어야 하며 이 경로의 실제 변환은 아직 검증하지 않았습니다.
- 원본 옆 저장 또는 저장 위치 지정, 페이지 선택, 원본 방향/A4 세로/A4 가로, macOS 인쇄창을 제공합니다.

## 빌드와 설치

Apple Silicon Mac, Xcode Command Line Tools의 Swift 컴파일러와 Python 3이 필요합니다. 이 저장소에는 대용량 엔진 바이너리와 다운로드 자료를 포함하지 않습니다.

빌드 전 아래 엔진을 준비해야 합니다.

1. The Document Foundation의 공식 LibreOffice 26.2.6.3 Apple Silicon 배포본을 `Engines/LibreOffice.app`에 그대로 놓습니다. 다운로드 SHA-256은 `legal/LibreOffice-binary.sha256`에서 확인합니다. 원본 코드·리소스·서명을 변경하지 마세요.
2. STAIxBWLB/hwp-cli v1.3.1 macOS arm64 실행 파일을 `Engines/hwp/hwp`에 놓습니다. 라이선스와 출처는 `legal/THIRD_PARTY.html`을 확인하세요.

```sh
python3 scripts/build-release.py
python3 scripts/install-local.py
open "$HOME/Applications/PDF로 변환.app"
```

앱을 한 번 실행하면 `~/Library/Services/PDF화.workflow`를 설치합니다. 로컬 설치 스크립트는 이전 앱을 `build/backups`에 보관하며 실행 중인 앱을 교체하지 않습니다.

## 검증

Python 검증 코드는 Pillow, pypdf, reportlab을 사용합니다. `tests/sample.*`은 기본 한글·영문 및 페이지 검증용 문서입니다.

```sh
python3 tests/validate_release.py
python3 tests/validate_network.py
```

현재 변환·원본 보존·페이지 범위·용지 방향·입력 오류 검사 26개 및 외부 HTTP 차단 검사를 통과했습니다. 실제 UI에서 페이지 선택 저장, 저장 창, macOS 인쇄창, Finder 빠른 동작 실행을 확인했습니다. 별도 Mac 테스트를 대체하지 않습니다.

## 라이선스와 배포

우리 앱 소스에는 아직 오픈소스 사용 허가를 부여하지 않았습니다. Git 저장소 업로드만으로 이용·수정·재배포 권리를 허가하지 않습니다. 공개 저장소나 공개 릴리스 전 앱 자체의 이용 조건을 정해야 합니다.

내장 엔진과 제3자 구성요소의 라이선스는 `legal/`에 별도로 보존합니다. LibreOffice의 MPL-2.0 및 각 의존성 라이선스 조건을 따라 대응 소스와 고지를 제공해야 합니다. `scripts/package-release.py`는 로컬에 준비한 엔진 소스 자료로 별도 소스 ZIP을 만듭니다. 해당 자료는 Git에서 제외하며, 실제 바이너리 배포 시 함께 제공해야 합니다.

`docs/개인정보 안내.html`의 운영자·지원 연락처는 공개 출시 전 확정해야 합니다. 인증서 개인 키, 비밀번호, API 토큰은 저장소에 넣지 않습니다.

## 출시 전 남은 항목

- Developer ID Application 서명과 Apple 공증, 최종 DMG 검증
- 개발 환경이 없는 별도 Mac과 최소 지원 OS에서 설치·변환·저장 검증
- 공개 운영자·지원 연락처와 개인정보 안내, 앱 배포 이용 조건 확정
- 대응 소스의 다운로드 위치와 최종 배포 파일 해시 제공

현재 DMG는 서명·공증 전 RC이며 정식 배포 파일로 표시하면 안 됩니다.
