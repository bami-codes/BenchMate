# Claude용 전체 벤치 사진

사용자가 올린 전체 벤치 사진을 공유한다. Arduino·큰 계측 보드·미니보드가 함께 나온 사진으로,
장치 소개와 사이트·README·영상 구성에 활용할 수 있다.

- **소개용 권장 — 카메라 렌더링 3024×4032 PNG**: `examples/bench-photos/2026-11-04/full/camera-preview.png`
- **소개용 가벼운 1200×1600 미리보기**: `examples/bench-photos/2026-11-04/full/camera-preview-small.png`
- 이전 고정 RAW 변환 **4028×5370 PNG**: `examples/bench-photos/2026-11-04/full/render.png`
- 이전 고정 변환 미리보기: `examples/bench-photos/2026-11-04/full/preview.png`
- RAW 변환 설정·원본 해시: 같은 폴더의 `conversion.json`
- 공개 파일별 해시·해상도·미리보기 변환: 같은 폴더의 `assets.json`

첫 업로드는 기존 실험용 고정 RAW 변환을 사용했다. 카메라 WB, 자동 밝기 끔, 고정된 약한 샤프닝이었다.
사용자가 휴대폰 원본보다 어둡다고 지적해 DNG의 내장 JPEG 미리보기와 대조했고, 실제 밝기 차이를 확인했다.
소개용에는 `camera-preview.png`를 권장한다. 카메라가 이미 렌더링한 JPEG를 추출하고 ICC 색 공간을 sRGB로 변환했으며,
임의 노출·톤·추가 샤프닝은 적용하지 않았다. 원래 내장 미리보기 해상도이며 업스케일하지 않았다.
이 처리 설정·파일 해시는 `camera-preview-conversion.json`에 있다. 이전 고정 변환과 모든 실험 입력은 보존했다.
공개 PNG는 IHDR·IDAT·IEND 청크만 있고 EXIF·GPS·텍스트 메타데이터가 없다.
DNG 원본과 무샤프닝 중간 파일은 로컬에 보존한다. 전체 PNG에서 필요한 부분을 크롭할 수 있다.

용도는 전체 장치 소개다. 개별 사례의 실행 시점·고장/복원 상태는 해당 사례 기록과 사진을 참조한다.
이 공유 과정의 Spark·SAM 호출과 하드웨어 동작은 0이다. Codex는 사이트나 README를 수정하지 않았다.
