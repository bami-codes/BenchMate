# SAM 후보 지목 검토 — case02 표시 수정 요청과 후속 출력 계약 제안

2026-11-04. 기존 로그·코드·그림을 읽어 확인했다. 새 모델 호출이나 하드웨어
동작은 없었다. 아래 후속 계약은 **설계 제안**이며 아직 런타임에 구현하거나
05·03의 프로토콜로 동결한 것은 아니다. 기존 동결 소스와 실행은 수정하지 않았다.

## 확인된 case02 기록

원래 지목 도구는 `sam_body` 하나 또는 null과 `reason`만 받는다. 종류 판정이나
복수 후보 ID를 담을 필드가 없다(`src/benchmate/reading_photo.py:80`).

Spark 원문은 다음과 같다.

```json
{
  "sam_body": "null",
  "reason": "Both box-geometry capacitors are wired as identical parallel shunts to the same two nodes, so layout/wiring cannot distinguish C1 from C2."
}
```

Spark가 두 커패시터의 배선상 대응 모호성을 설명했지만, 어느 SAM ID가
커패시터인지 정식으로 반환하지는 않았다. 따라서 이유 문장만으로 sam-2·sam-3
선정을 Spark의 작업이라고 복원할 수 없다. 문자열 null 때문에 생긴 원래
형식 실패도 그대로 보존한다.

후속 `body-group.json`에는 실제로 다음이 기록돼 있다.

```json
{
  "sam_bodies": ["sam-2", "sam-3"],
  "correspondence": "unresolved",
  "candidate_group_chosen_by": "Codex_visual_review_requested_by_operator",
  "Spark_chose_group": false
}
```

두 단품 관측 뒤, 동결 구간의 모든 일대일 대응을 시험하여 C1↔sam-2,
C2↔sam-3만 남았다. 이는 살아남은 changed:C1 설명에 조건부인 코드 판정이다.
사진만으로 Spark가 C1을 지목한 결과나, 값에 가장 가까운 몸체를 붙인 결과가 아니다.

## Claude에게 남기는 case02 화면 수정 요청

현재 재생 데이터에는 두 후보 라벨이 있지만 `photo.image.file`은 7개 윤곽이
전부 그려진 `case02-faulted-sam.png`다. 전체 SAM 개요와 실제 측정 후보를
가리키는 장면을 구별할 필요가 있다.

- SAM 결과 소개에서는 원본 전체 영역을 보여줄 수 있다.
- **후보 지목·읽기 요청 장면에서는 sam-2·sam-3만 강조**한다. 다른 윤곽은
  감추거나 약하게 표시하되 원본 마스크는 보존한다.
- 두 라벨은 읽기 전까지 `C1 or C2`다. C1/C2 개별 이름은 읽기 점수 뒤에 붙인다.
- 선정 출처는 기존 기록 그대로 `Codex visual review, requested by operator`다.
  Spark의 작업은 “배선으로 두 부품의 대응을 구분할 수 없다고 설명함”이다.
- 복원 사진의 전후 비교 윤곽은 documentary 표시다. 별도 식별 요청이 없었으므로
  같은 두 몸체를 Spark가 추적·식별했다고 표시하지 않는다.

이미 두 후보만 강조한 기존 그림이 있다. 추가 API 없이 사용할 수 있고,
새 스타일이 필요하면 이 그림의 선정 ID·기존 마스크를 표시 입력으로 쓸 수 있다.

[기존 두 후보 그림](../examples/reading-groups/2026-11-04/records/20261103T174217-008035637b/capacitor-candidates.png)

[선정 출처](../examples/reading-groups/2026-11-04/records/20261103T174217-008035637b/body-group.json)

[원본 Spark 출력](../examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7/photo-faulted/binding/20261103T171947-e7fe864df7/result.json)

## 05·03부터 적용할 출력 계약 제안

한 번의 Spark 지목 호출 안에서 **몸체 종류·후보 집합 선정**과 **개별 회로도
부품 대응**을 분리한다. 추가 종류 판정 호출을 만들 필요는 없다. 다음은
원하는 형태를 설명하는 가상 예시이며, case02에서 실제 받은 응답이 아니다.

```json
{
  "component": "C1",
  "candidate_bodies": [
    {"sam_body": "sam-2", "kind": "C", "reason": "Visible capacitor body and leads."},
    {"sam_body": "sam-3", "kind": "C", "reason": "Visible capacitor body and leads."}
  ],
  "candidate_selection_status": "proposed",
  "mapping_status": "ambiguous",
  "sam_body": null,
  "reason": "Both candidates share the same two nodes; geometry does not distinguish C1 and C2."
}
```

필수 구현·검증 조건:

1. 후보 ID는 실제 전달한 SAM/몸체 manifest에 존재해야 하고 중복을 거부한다.
   종류는 R/C/D/Q/wire/connector/other/unknown 등 명시된 집합으로 제한한다.
   값·표시·색띠 판독은 하지 않는다. 설계상 C라고 사진 몸체까지 C로 강제하지 않는다.
2. 후보를 못 정하면 `candidate_bodies:[]`와 미식별 사유를 허용한다.
   이는 사진·분할 결과에서 못 찾았다는 뜻이며 보드에 없다는 증거가 아니다.
3. `sam_body`가 있으면 후보 집합의 원소여야 한다. 후보 선정에 성공해도
   `mapping_status:ambiguous`와 `sam_body:null`이 가능해야 한다. 개별 대응을
   모른다는 이유로 후보 종류·ID를 버리지 않는다.
4. `chosen_by:muse_spark`, 모델 자식 실행 경로·head SHA, 원문, 파서 정규화,
   후보 ID·종류·이유를 `body_candidates_proposed`에 묶어 남긴다. 이는 관측으로
   검증된 종류가 아니라 모델의 제안이다. 후보 확인·작업자 수정은 별도 사건에
   남기며 수정된 ID를 Spark 선정으로 표시하지 않는다.
5. 지목 화면은 그 사건의 후보 ID만 강조한다. 전체 SAM 결과와 값 읽기 대상의
   차이를 분명히 한다. 복수 후보를 읽는 경우 예상 범위를 관측 전에 고정하고,
   모든 허용 대응을 평가한다. 이 단계도 출처를 모델·작업자·코드로 구분한다.
6. 원본 SAM 마스크 전체는 보존한다. 일반 `electronic component` 분할 입력은
   유지하고, 종류 선별은 뒤의 Spark 호출에서 수행한다. 03의 두 저항이나 05의
   W1도 강제로 하나를 고르게 하지 않는다. 도통 확인과 사진에서 보임은 별개다.
7. 새 어댑터·호출부·이벤트 감사·오프라인 검증을 함께 준비하여 다음 사례 실행
   전에 새 버전으로 고정·푸시한다. 동결된 과거 코드를 직접 고치거나 새 필드를
   과거 Spark 응답에 소급해서 채우지 않는다. 파서 단독 추가를 적용 완료라고
   부르지 않는다.

호출 수 목표는 기존 사진 단계와 같은 SAM 1회 + Spark 지목 1회다. 실제 적용 시
토큰 상한·예상 비용을 실행 전에 별도로 알린다. 이번 검토 자체는 0회·$0이다.
