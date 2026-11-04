# Claude용 전체 벤치 사진

사용자가 올린 전체 벤치 사진을 공유한다. Arduino·큰 계측 보드·미니보드가 함께 나온 사진으로,
장치 소개와 사이트·README·영상 구성에 활용할 수 있다.

- 전체 해상도 **4028×5370 PNG**: `examples/bench-photos/2026-11-04/full/render.png`
- 가벼운 **1200×1600 미리보기**: `examples/bench-photos/2026-11-04/full/preview.png`
- RAW 변환 설정·원본 해시: 같은 폴더의 `conversion.json`
- 공개 파일별 해시·해상도·미리보기 변환: 같은 폴더의 `assets.json`

기존 고정 RAW 변환을 사용했다. 카메라 WB, 자동 밝기 끔, 고정된 약한 샤프닝이며 추가 노출·색 조정은 없다.
공개 PNG는 IHDR·IDAT·IEND 청크만 있고 EXIF·GPS·텍스트 메타데이터가 없다.
DNG 원본과 무샤프닝 중간 파일은 로컬에 보존한다. 전체 PNG에서 필요한 부분을 크롭할 수 있다.

용도는 전체 장치 소개다. 개별 사례의 실행 시점·고장/복원 상태는 해당 사례 기록과 사진을 참조한다.
이 공유 과정의 Spark·SAM 호출과 하드웨어 동작은 0이다. Codex는 사이트나 README를 수정하지 않았다.
