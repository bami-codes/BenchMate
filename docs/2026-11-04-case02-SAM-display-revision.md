# Case02 SAM 표시 필터 변경 — 11/4 결과 확인 후 정한 표시 전용 규칙

고장·복원 사진과 SAM 결과를 **본 뒤**, 작업자가 요청한 포함 관계 기준을
두 사진에 동일하게 적용했다. 사전 등록된 식별 규칙이나 SAM 성능 개선으로
취급하지 않는다. 진단·읽기·부품 대응·판정·집계에는 적용하지 않는다.

## 표시 규칙

다른 SAM 마스크 **2개 이상**의 바운딩박스를 완전히 포함하는 바운딩박스를
가진 마스크는 표시에서 제외한다. 원본 `bounds_half_open` 좌표를 사용하고,
자기 자신은 세지 않으며, 경계가 같은 경우도 포함으로 센다. 픽셀 마스크의
포함 비율이나 면적 임계값, 신뢰도, 부품 값은 사용하지 않는다.

이 규칙의 “바탕”은 표시상 분류다. 실제 보드나 부품 종류를 확인한 것이
아니며, 일반적으로 중첩된 부품도 제외될 수 있다. 모든 원본은 남긴다.

표시 대상은 **마스크마다 별도로 외곽선**을 그린다. OpenCV `RETR_EXTERNAL`,
`CHAIN_APPROX_SIMPLE`, 3px `LINE_8`, RGB(30,190,120)을 양쪽에 똑같이 쓴다.
합집합 테두리나 마스크 내부 구멍의 테두리는 그리지 않는다. 마스크를
수정·늘림·새로 생성하지 않고 원래 사진의 전체 프레임을 유지한다.

## 실제 적용 결과

| 사진 | 원본 마스크 | 표시 | 제외 |
| --- | ---: | ---: | --- |
| 고장 | 7 | 7 | 없음 |
| 복원 | 8 | 7 | object 5: object 1·3·6·7의 바운딩박스 4개를 완전히 포함 |

복원 object 5가 나머지 7개를 모두 포함한다는 설명은 좌표와 달랐다.
다른 3개는 위쪽 경계 밖으로 나와 있다. 실제 포함 개수 4개로도 요청한
“2개 이상” 조건이 충족된다. 25% 면적 기준은 사용하지 않았다.

## 파일과 재현

- [새 전후 비교 그림](../examples/SAM-display/2026-11-04/case02-v2/before-after-SAM.png)
- [고장 그림](../examples/SAM-display/2026-11-04/case02-v2/faulted-SAM-overview.png)
- [복원 그림](../examples/SAM-display/2026-11-04/case02-v2/restored-SAM-overview.png)
- [출처·개별 포함 관계·제외 사유·해시 manifest](../examples/SAM-display/2026-11-04/case02-v2/manifest.json)
- [오프라인 렌더러](../scripts/render_sam_display.py)

Pillow 12.3.0, NumPy 2.2.6, OpenCV 4.12.0으로 생성했다. 해당 의존성이 설치된
Python에서 다음 명령으로 새 출력 폴더에 재현할 수 있다. 기존 폴더를
덮어쓰는 실행은 거부한다.

```sh
python scripts/render_sam_display.py \
  --faulted examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7/photo-faulted \
  --restored examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/photo-restored \
  --output examples/SAM-display/2026-11-04/case02-reproduced
```

완료된 실행 폴더 밖에 새 그림만 추가했다. 기존 비교 그림, 동결 렌더러,
원본 마스크·SAM 응답·이벤트·진단 결과는 보존했다. 두 사진 폴더의 원본
136개 파일과 완료된 복원 실행의 108개 파일을 변경 전후 해시로 대조했다.
새 PNG 3개는 EXIF/GPS/XMP 등 메타데이터가 없는 것도 확인했다.

원래 감사 명령의 결과는 그대로다.

```text
PASS events=574 forecasts=10 measurements=12 order_checks=43 prediction_files=4 run_status=run_completed head_sha256=ad05d5914d22d2333f9eddf8be546e0c2ec207ba094d0d81dc54ea5972a16ed8 scope=internal_integrity+recorded_order creation_time=unproven
```

이번 변경은 **Spark 0회 · SAM 0회 · 하드웨어 동작 0회 · 추가 비용 $0**다.
OpenCV는 외곽선을 그리는 데만 사용했으며 분할 폴백은 없다. C1/C2 대응이나
값·존재 여부의 증거를 새로 만들지 않았다. 최종 캡션은 그대로
**No mismatch in the tests Spark chose**다.
