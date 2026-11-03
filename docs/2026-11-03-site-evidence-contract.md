# 사이트 연동 규격: 구조 제안·사진 결과

11/3 사용자 요청에 따른 현재 코드 기준 인계다. API·하드웨어를 실행하지 않고 소스와 보존 기록을
확인했다. **현재 생성되는 원본**, **사이트에서 계산할 필드**, **아직 없는 연결 단계**를 구분한다.
공식 실행·데모 선택은 [사전 등록 정책](2026-11-03-official-run-policy.json)을 따른다.

## 1. events.jsonl 공통 형식

실행마다 `<run>/events.jsonl`에 한 줄 한 JSON이다. 파일 이름의 시각과 `timestamp`는 UTC다.

```json
{
  "sequence": 42,
  "timestamp": "<UTC ISO-8601>",
  "kind": "structure_proposed",
  "payload": {},
  "previous_sha256": "<64 hex>",
  "sha256": "<64 hex>"
}
```

위 envelope는 필드 설명용이다. 실제 자료의 hash chain은 `benchmate.records.read_events`로
검사한다. 웹용 파생 파일로 줄여도 원본 run ID·event sequence·원본 해시를 보존한다.
원본에는 작업자 전용 정보가 섞일 수 있으므로 events 전체를 무조건 사이트에 복사하지 않는다.

## 2. 구조 제안 이벤트: 현재 구현됨

생산 코드: `src/benchmate/netlist_diagnosis/session.py:DiagnosisSession.propose`.
수동 회로에 대해 v2와 현재 passive runner도 이 구현을 재사용한다.

### 선행 조건

직전 `component_hypotheses_fitted.payload`에서 다음이 성립해야 한다.

```json
{
  "all_inadequate": true,
  "fitting_complete": true,
  "hypotheses": ["<nominal 및 모든 단일 R/C 변경 가설의 실제 행>"]
}
```

모든 행이 `inadequate`여야 한다. `fit_error`·예산 소진·미완료는 회로 가설이 반증됐다는 뜻이
아니므로 구조 제안의 근거로 표시하면 안 된다. 구조 제안은 최대 2개다.

### `kind: structure_proposed`

`payload` 필드:

| 필드 | 형식·뜻 |
|---|---|
| `id` | `proposal:1`, `proposal:2`. 이 실행 안에서 fit 결과와 연결하는 키 |
| `elements` | **제안한 전체 넷리스트**. 변경분 목록이 아님 |
| `elements[].name` | 부품 이름. 기존 이름은 유지하며 새 부품은 새 이름 |
| `kind` | `R`, `C`, `D` (의도 회로는 `W1` 직결도 가능) |
| `a`, `b` | `IN`, `OUT`, `REF`, `N1`, `N2` 중 연결 노드 |
| `value` | R=Ω, C=F. D는 `0.0` 자리표시이며 전압·저항값이 아님 |
| `model` | R/C=`none`, D=`generic_diode` |
| `rationale` | 모델이 쓴 제안 이유 원문 |
| `topology_sha256` | `digest(elements)`. 제안 값도 포함한 전체 요소 배열 해시 |
| `selected_by` | 실제 Spark는 `muse_spark`, 모의 제어기는 `scripted_controller` |

예: `Dextra, D, OUT, REF, 0.0, generic_diode`는 OUT에서 REF로 향한 다이오드 제안이다.
D에서 `a`는 애노드, `b`는 캐소드다. **사진의 실제 부품 위치 좌표는 이 이벤트에 없다.**
회로도 노드 사이의 가상 부품으로 점선 표시하고, 실물 위치가 확인됐다고 표시하지 않는다.

초기값과 피팅 후 값은 다를 수 있다. 기존 R/C 값은 고정하고 추가된 R/C 최대 2개와 다이오드
공유 개발 매개변수만 훈련 OUT으로 맞춘다. 다이오드 IS/N은 실제 소자의 특성 측정값이 아니다.

**05 주의:** 의도 회로의 `W1=IN–OUT`을 제거하고 직렬 R로 대체할 수 있다. 제안 `elements`를
새 전체 회로로 그려야 한다. 원래 W1을 남긴 채 R만 덧그리면 R이 단락되는 잘못된 그림이 된다.
변경 전 설계와 비교해 `added`, `removed`, `reconnected`를 사이트에서 계산한다.

### `kind: structure_fit`

`payload.id`를 `structure_proposed.payload.id`와 연결한다. 정상적으로 피팅을 마친 행:

```text
id, changed_component(null), model, status, training_checks,
optimizer_converged, parameter_at_bound, fitted_parameters,
local_parameter_rank, fitted_parameter_count, parameters_identifiable,
unique_physical_parameters_claimed, training_observations,
verification_outputs_used(0), simulator_calls
```

- `status`: `adequate` / `inadequate` / `fit_error`.
- `model.elements`: 피팅 후 전체 부품 배열. 사이트의 최종 제안값은 이것을 쓴다.
- `model.diode`: `{"is_a": <A>, "n": <dimensionless>}`.
- `fitted_parameters`: 예를 들면 `Rextra`, `diode_IS`, `diode_N`의 수치.
- `training_checks[]`: 각 훈련의 `RMS_mV`, `regions[].name/samples/RMS_mV`, `passed`,
  `source`, `purpose`. 전체와 **모든 구간**의 9 mV 기준이다.
- `adequate`는 **훈련에 맞음**이며 아직 예약 예측 통과나 유일한 회로라는 뜻이 아니다.
- `parameters_identifiable`은 국소 수치 진단이다. `unique_physical_parameters_claimed`는 false다.

실패 행은 다음처럼 `model`·`training_checks`가 없을 수 있다. 없는 값을 0이나 성공으로 채우지 않는다.

```json
{"id":"proposal:1","status":"fit_error","error":"<actual error>","simulator_calls":420}
```

### 그 뒤 실제 검증과 연결

`verification_forecast_frozen` → `verification_publication` → `reserved_prediction_scored`(2개)
→ `netlist_verification_completed` → `agent_report` 순서다.

- 동결의 `models[].id`가 `proposal:1`인지 확인한다.
- `reserved_prediction_scored.payload.conditional["proposal:1"]`에 실제 측정 IN 조건부 채점이 있다.
  `command_forecast`는 별도의 명령 입력 예측 채점이며 섞지 않는다. `OUT_refitted`는 false다.
- 최종 `survivors`와 `agent_report.verdict`가 근거다. 제안이 살아남으면 `structure_supported`일 수
  있지만 다른 생존 가설이 있으면 결과가 다를 수 있다. 사이트가 verdict를 새로 선택하지 않는다.

**정확한 원본 예시:**
`examples/site-contracts/2026-11-03/structure-events.example.json`.
보존된 개발용 **mock / scripted_controller** 이벤트 발췌다. 새 실물·Spark 구조 제안으로 쓰면 안 된다.
원본 archive/member와 event-log 해시를 같이 넣었다. 발췌 자체는 완전한 hash chain 파일이 아니다.

## 3. 사진 결과: 보존된 기존 probe 형식

이 절은 11/1 probe의 원본 형식이다. 11/3에 추가한 SAM-first 부품별 producer는
아래 7절을 따른다. 아직 새 공식 사례 사진 호출 결과를 확보했다는 뜻은 아니다.

현재 실행기 `scripts/photo_model_probe.py`의 저장 구조:

```text
<photo-run>/
  input.png                       # 모델에 보낸 metadata-free PNG
  plan.json                       # image.sha256/width/height, 프롬프트와 소스 해시
  events.jsonl
  result.json                     # outcomes[]: task, run(상대 경로), status
  vision/<vision-run>/
    input.png
    plan.json
    events.jsonl
    response-visible.json         # 모델 원본 visible 응답·usage
    arguments.txt                 # report_design 인자 원문
    result.json                   # candidate.components[], ambiguities
  sam/<sam-run>/
    events.jsonl
    response-visible.json
    output-text.txt               # SAM 원문, 임의 파싱하지 않음
    result.json
<render-dir>/                     # 별도 오프라인 render 명령의 출력
  resistor-decoded.json
  capacitor-decoded.json
  <concept>-object-<id>-mask.png
  <concept>-object-<id>-overlay.png
  <concept>-all-masks.png
  render-summary.json
```

root `result.json.outcomes[].run`으로 자식 폴더를 찾는다. 날짜 디렉터리명을 추측하지 않는다.
기존 로컬 화면의 `photo-reviews/revision-*.json`은 작업자가 남긴 관찰이다.
`model_authored_observations:0`이며 SAM/Spark 모델 결과로 표시하면 안 된다.
현재 probe는 **전체 사진 Spark 판독 1회 뒤 R/C SAM concept 2회**다. 새 방향인
**SAM→부품 crop→Spark 판독→부품 대응** 전체가 구현·검증됐다고 표시하면 안 된다.
기존 전체 사진 판독은 아직 그 crop 판독을 대신하는 개발 probe다.

### SAM: `<concept>-decoded.json.masks[]`

```json
{
  "object_id":"0",
  "bounds_half_open":[277,663,478,724],
  "confidence":0.5631399154663086,
  "raster_size":[201,61],
  "source_mask_file":"resistor-object-0-mask.png",
  "overlay_file":"resistor-object-0-overlay.png",
  "resize_to_box":false,
  "foreground_pixels":4674
}
```

이 수치는 11/1 보존 예시다. 좌표는 **정확히 그 input.png의 픽셀**, `[left,top,right,bottom)`이다.
`source_mask_file`은 원본 input.png와 같은 크기의 0/255 마스크다. `raster_size`는 SAM의 원래
부분 마스크 크기이며 전체 사진 크기와 다를 수 있다. `resize_to_box`를 숨기지 않는다.
여러 concept의 `object_id`는 겹칠 수 있으므로 `(photo/image hash, concept, object_id)`로 식별한다.
`confidence`는 분할의 점수이며 OCR 정확도나 전기적 연결 신뢰도가 아니다.

`match_count:0`도 정상적으로 보존한다. 빈 결과·실패·읽기 불가를 구분한다. 모든 마스크·오탐을
보존하고 잘 나온 것만 골라 전체 성능처럼 제시하지 않는다. `records`에는 box/mask 원본 파싱 결과,
`diagnostics`에는 파서 진단이 있다. 웹은 복잡한 mask payload 대신 생성된 PNG를 사용하면 된다.

### Spark: `vision/<vision-run>/result.json.candidate.components[]`

```json
{
  "name":"R1","kind":"R","a":"UNKNOWN","b":"UNKNOWN",
  "value_si":null,"marking":"color bands illegible",
  "evidence":"<model's observed evidence>",
  "bbox":[0.205,0.448,0.375,0.498]
}
```

- `bbox`는 동일한 입력 PNG의 **0..1 정규화** `[left,top,right,bottom]`이다. 픽셀은 W/H를 곱한다.
- **현재 native 필드에 `unreadable` enum은 없다.** R/C의 `value_si:null`을 웹에서
  `reading_status:"unreadable"`로 파생할 수 있다. 원본 null·marking·ambiguities도 보존한다.
- D는 원래 `value_si:null`이므로 null만으로 unreadable 처리하면 안 된다. 값 판독 비적용과
  표시 판독 불가를 분리한다. 현재 photo schema는 R/C/D이며 Q/LED 확장이 아직 필요하다.
- `candidate.status`는 `needs_review/incomplete/unsupported`, 바깥 `status`는
  `unverified_visual_candidate`다. 파싱/호출 실패는 `failed`이며 candidate가 없을 수 있다.
- `a/b:UNKNOWN`을 빵판 모양이나 색만 보고 채우지 않는다. 비전이 붙인 R1과 회로도의 R1,
  SAM object 0은 자동으로 같은 물체가 아니다. 대응은 별도 검토 정보로 남긴다.

**정확한 파일/필드 예시:** `examples/site-contracts/2026-11-03/photo-files.example.json`.
11/1 개발 사진의 진짜 파일 링크와 R의 null, C의 1 µF 판독을 담았다. 여섯 공식 사례 사진이 아니다.
`ui_derived_components`는 설명용 파생값이며 모델 native 출력에 필드를 추가한 것처럼 쓰지 않는다.

### Claude OpenCV 전처리와 좌표를 섞지 않기

현재 `scripts/photo/minibb.py`는 `<out>/board.json`, `board_rectified.png`, `board_debug.png`,
`objN.png`를 쓴다. `objects[].image_box`는 입력 이미지의 원래 크기 픽셀 좌표,
`rect_box`는 펼친 보드의 `[x,y,w,h]`다. `crop`은 여백을 포함한 crop 파일명이다.
전처리 object 박스는 SAM 마스크나 부품 종류·값이 아니다. hole의 `ends/touches`도 전기적
통전 확인이 아니다. producer에 이미지 SHA와 변환 정보를 붙여 동일 이미지를 참조해야 한다.
HEIC/다른 크기 원본·rectified PNG·SAM input.png의 좌표를 그대로 혼용하지 않는다.

### 새 여섯 사례에서 남은 producer 작업

SAM→crop→비전의 부품별 결과, 마스크/관측/회로도 ID 대응, Q/LED 사진 스키마는 아직 별도 연결이
필요하다. 현재 존재하지 않는 `photo_read` 이벤트나 통합 `components.json`이 이미 나온다고 약속하지
않는다. 연결 코드는 별도로 구현하고, 실제 모델 호출은 API 횟수·비용을 고지한 뒤 사용자 승인
범위에서 실행한다.
사이트는 지금 위 원본 형식과 `unreadable/failed/not_run` 상태 UI를 준비할 수 있다.

사진은 진단 뒤 공개한다. 사진 판독기에는 ADC·진단 결과·정답표·예상 부품값을 전달하지 않는다.
사이트에서 나중에 대조하더라도 별도 독립 판독의 원문·해시·수동 수정 이력을 보존한다.

## 4. 현재 사이트 추출기에 필요한 반영 요청

`site/tools/extract_runs.py`는 현재 구조 이벤트 두 종류를 처리하지 않는다. Claude가 다음을 추가해 달라.

1. `structure_proposed`를 id별 보관하고 전체 요소 배열의 변경 전/후를 표시한다.
2. `structure_fit`을 id로 연결하고 simulator_calls를 포함한다. `fit_error`에서 model이 없는 경우를 처리한다.
   현재 `hyp()`는 changed_component가 있는데 model이 없으면 KeyError가 날 수 있으므로
   `h.get('model', {}).get('elements', [])`처럼 결측을 처리해야 한다.
3. 예약 검증의 proposal id와 최종 verdict를 연결한다. 훈련 adequate를 최종 성공으로 바꾸지 않는다.
4. 공식/파일럿 분류를 CLI `--pilot` 생략 여부로 결정하지 않는다. 원본의 pilot/excluded 및 새 공식
   cohort manifest가 근거다. 알 수 없는 실행은 `counted:false`로 둔다. 과거 파일럿·QA·mock은 계속 제외한다.
5. 공식 대표 실행 선택은 아래 정책만 사용한다. 결과가 좋은 실행으로 자동 교체하지 않는다.

화면·사이트 소유 파일은 이 인계에서 Codex가 직접 수정하지 않았다.

## 5. 공식 순서·복원·데모 선택 — 결과 전 고정

기계 판독 규칙은 `docs/2026-11-03-official-run-policy.json`이다. **새 공식 실행은 아직 시작하지
않는다.** 순서와 선택 기준을 사전 등록한 것이며, 실제 runner/cohort 메타데이터·프로토콜 동결과
계측 자격·사용자 실행 승인은 별도 시작 조건이다. 현재 USB는 사용자가 분리한 상태다.

| 순서 | 고장 실행 | 이어지는 복원 재실행 |
|---|---|---|
| 1 | 01-F01 | 01-R01 |
| 2 | 04-F01 — 우선 구조 제안 대상 | 04-R01 |
| 3 | 02-F01 | 02-R01 |
| 4 | 05-F01 — 두 번째 구조 제안 대상 | 05-R01 |
| 5 | 03-F01 | 03-R01 |
| 6 | 06-F01 — LED, 별도 DC 자격 후 | 06-R01 |

각 사례의 주 화면은 **해당 상태의 첫 공식 시도**다. 실패·abstained·가드 중단이어도 더 잘된
후속 실행으로 바꾸지 않는다. 공식 시도는 사전 ledger 할당 시점부터이며, 성공한 뒤 공식으로
승격하지 않는다. 모든 공식 시도는 시도 수 집계에 남기고, 계획/시작/완료/실패/미실행 수도 구분한다.

구조 제안 spotlight는 04-F01에 실제 `structure_proposed`(selected_by=muse_spark)가 있으면
그 실행을 사용한다. 없을 때만 05-F01을 확인한다. **피팅·예약 검증 성공 여부는 선택에 쓰지 않는다.**
fit_error나 미완료도 그대로 보여준다. 둘 다 제안하지 않았으면 `coverage_not_observed`로 기록한다.
이 경우 필요한 구조 제안 증거를 아직 확보하지 못한 것이며, 제안을 강제하거나 나중의 성공 시도로
몰래 대체하지 않는다. 구조 제안 사례 하나를 확보해야 한다는 제출 요구는 별도 미충족으로 표시한다.

각 복원은 USB 분리 작업 기록과 새 Spark 문맥을 연결하고, 같은 의도 회로도로 재실행한다.
원본 runner의 `physical_repair_demonstrated:false`를 임의로 true로 바꾸지 않는다. 사이트에는
두 run과 작업자 복원 기록을 연결한 `operator restored / rerun consistent` 같은 쌍 단위 상태를
따로 표시한다. 가드 실패로 계속 진행할 수 없으면 멈추고 남은 슬롯은 미실행으로 공개한다.

이 사전 등록은 direction 문서의 과거 “본시험 중 가장 잘된 실행” 데모 선택 규칙을 사용자의
11/3 새 요청에 따라 대체한다. 기존 direction 파일의 다른 내용이나 Claude 작업은 수정하지 않았다.

## 6. 오프라인 확인과 복원 판정 문구

`python -m benchmate verify <run-folder>`의 명령·지원 이벤트·검사 한계·실제 출력은
[오프라인 검증 규격](2026-11-03-offline-verification.md)을 따른다. PASS는 기록 감사이며
실험 성공 판정이 아니다. 기록 내 동결→측정 순서를 검사하지만 작성 시각은 증명하지 않는다.

실제 Spark의 복원 재실행이 `consistent`이면 사이트·영상 문구는
**No mismatch in the tests Spark chose**로 통일한다. 모든 부품의 정상 확정이 아니다.
Spark는 훈련 실험을 고르고 예약 입력 두 개는 프로토콜이 사전 고정한다. 다른 판정이나
중단·mock에 이 문구를 붙이지 않는다. 원본 enum과 physical_repair_demonstrated는 보존한다.

## 7. 새 SAM-first producer: `scripts/photo_parts.py`

11/3 소프트웨어 구현과 오프라인 확인을 추가했다. **새 공식 사례 사진의 실호출은 아직 0회**다.
11/1 보존 SAM 응답 재생에서 저항 마스크 1개와 커패시터 match 0을 모두 보존했고,
새 저항 마스크 픽셀이 보존된 원본 마스크와 정확히 같음을 확인했다. 이 재생은 개발 검증이다.

```text
<prepared>/
  plan.json                         # 고정된 concept/순서/한도/이미지·소스 해시
  input.png                         # SAM 입력, 방향 보정·metadata 제거, 최대 1600px
  clean-full.png                    # 방향 보정·metadata 제거한 전체 해상도
  sam-outcomes.json                 # concept별 상태와 상대 run 경로
  sam/<concept>/<run>/
    events.jsonl, response-visible.json, output-text.txt, result.json
<decoded>/
  crop-manifest.json                # 모든 object 및 원본 이미지/계획 연결
  <concept>-decoded.json            # masks[], match_count, diagnostics
  <concept>-object-<id>-record-<n>-raster.png
  <concept>-object-<id>-record-<n>-mask.png
  <concept>-object-<id>-record-<n>-overlay.png
  <concept>-object-<id>-record-<n>-crop.png
  components.json                   # 각 SAM object와 독립 비전 판독의 연결
  vision/<run>/
    input.png, plan.json, events.jsonl, response-visible.json, arguments.txt, result.json
```

순서는 resistor SAM 1회 → capacitor SAM 1회 → 오프라인 decode/crop → crop별 새 Spark
판독이다. 반환된 모든 mask와 실패·match 0·파서 진단을 남긴다. 품질로 골라내지 않고,
concept 순서와 원본 record 순서상 첫 8개 crop까지만 판독한다. 초과분은
`vision_status:not_read_budget`으로 남긴다. 호출 전에 실제 mask 수와 예정 판독 수를 알린다.
기존 probe와 달리 전체 사진 비전을 먼저 부르지 않는다. 자동 재호출은 없다.

`crop-manifest.json.objects[]`의 연결 키는 `photo_component_id`다. 이 값은 입력 이미지 해시,
concept, SAM object ID와 record index를 포함한다. `schematic_ref:null`,
`association_status:unassigned`가 기본이며, 회로도 R1과 자동으로 같은 부품이라고 정하지 않는다.

좌표는 `bounds_half_open`이 정확한 SAM `input.png` 기준 픽셀이다. `raster_size`가 box 크기와
같을 때만 `source_mask_file`을 만들며, 전체 입력 크기의 마스크에 그대로 붙인다.
`mask_mapping_status:exact_no_resize`이며 마스크를 늘리지 않는다. 크기가 다르면
`raster_bounds_mismatch`, mask 파일은 null이고 원래 raster와 진단을 보존한다.
`full_pixel_crop_box`는 `clean-full.png` 좌표다. 고정 15% 여백과 두 이미지의 크기 비율로
계산하며, crop은 최대 1600px로 줄인다. crop의 해시·최종 크기도 저장한다.

`components.json.components[]`는 object 정보와 `vision_run`, `vision_status`,
`vision_components[]`를 연결한다. R/C의 `value_si:null`은 `reading_status:unreadable`,
수치가 있으면 `readable`이다. 이 표기는 모델이 수치를 제안했다는 뜻이며 정확성 검증은 아니다.
D의 null은 `observed_without_numeric_value`다. 실패에는 빈 목록과 실제 상태를 남긴다.
`records_processed`, `expected_mask_records`, `completed`는 처리 진행 상태이며
모든 부품의 판독 성공을 뜻하지 않는다. 원본 candidate의 불완전/검토 필요 상태도 유지한다.

각 비전 `bbox`는 **그 crop PNG**의 정규화 좌표다. SAM 입력 좌표와 바로 섞지 않는다.
새 producer도 Q/LED 사진 스키마와 자동 회로도 ID 대응·전기적 연결 복원을 제공하지 않는다.
이들은 후속 작업이며, 표시나 값이 안 보이면 unreadable 그대로 남긴다.

진단·설계값·ADC·정답표·파일명·원본 metadata는 비전 입력에서 제외한다. 기존 사진 판독기와
분할 호출기를 재사용하며, 이벤트는 각 자식 `events.jsonl`에 남긴다. 진단 실행의 chain 안에
없는 `photo_read` 이벤트를 만들어 원본 모델 이벤트인 것처럼 표시하지 않는다.
