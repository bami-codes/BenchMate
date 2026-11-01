# 영상 플랜 A / B / C (11/2 02:00 KST 개정, Claude)

story-v3.1의 규칙을 그대로 따른다: 포럼 인용 1문장, "a fault I planted", B5는 "inspired by", ESP32 내부 주장 금지,
속도 비교 금지. `{중괄호}`는 실제 기록이 생기기 전까지 비워 두는 자리이며, 각 자리는 오른쪽에 적은 기록 필드에서만 채운다.
기록이 없으면 그 문장을 지운다.

**구성(모든 플랜 공통):** 포럼 사례(15초 이내) → D01 1막(알려진 설계의 진단과 수리) → B5 2막(초기 모델이 틀렸을 때 새 구조)
→ 다른 사람의 완수 → 숫자 → 해커톤 기간 중 제작.
**결정 시점:** B5 두 번째 시도가 끝난 직후(11/2 낮). 그 전에 셋 다 편집 가능한 상태로 둔다.
11/3 09:00까지 끝나지 않은 평가 결과는 넣지 않는다.

## 공통 도입 (0:00–0:27)

| 시간 | 화면 | 내레이션 |
| --- | --- | --- |
| 0:00 | 포럼 제목 + 1.8 V / 1.1 V, 실물 벤치 컷 2초 | On the Arduino forum, a voltage divider reads 1.1 V instead of 1.8. |
| 0:05 | 추측 라벨 테이프 | Replies guess: resistor tolerance, the meter, bad solder. |
| 0:09 | "Is the ESP32 even powered?" 테이프 | Early on, a reply points to the cause: the ESP32 has no power. A test confirms it. |
| 0:15 | 벤치 전경, 손, USB | BenchMate gives Muse Spark a bench to run those tests. |
| 0:19 | DAC/ADC 배선 클로즈업 | An Arduino and about $40 of parts drive the circuit and record it. Spark chooses each experiment; a person moves the wires. |

## 플랜 A — B5 실물 통과 (클라이맥스 = B5)

| 시간 | 장면 | 내레이션 | 채우는 기록 |
| --- | --- | --- | --- |
| 0:27 | D01 설계값, 21.4 ms | First, a fault I planted: a filter designed for 10 ms measures 21.4. | 10/30 실물 D01 |
| 0:33 | 도구 없는 답 5개(재측정 권고 포함) | Without measurements, Spark suggested a timing-definition error and advised re-measuring. | no-tool-spark |
| 0:37 | 두 용의자 곡선 | With it, Spark judged that one more step couldn't tell a bigger resistor from a bigger capacitor. | |
| 0:44 | 부하 연결 손 | So it asked for a known load. Both answers were locked first. Only one survived. | |
| 0:52 | 예약 사인 | It passed a waveform held in reserve. The capacitor is about twice its design value. | |
| 0:59 | GitHub 커밋 시각 → 손이 커패시터 제거 | Spark asks for one fix. Its forecast goes to GitHub before anyone touches the board. | 수리 run: `repair_publication` |
| 1:06 | 수리 후 곡선 | {The frozen repair model matches the measured response: X mV. Show the separate command-forecast result too.} | 수리 run: `repair_verification` |
| 1:12 | B5 미니 브레드보드 | Now a harder circuit, inspired by the forum problem. Spark isn't told the wiring. | |
| 1:19 | 진폭 스윕, 윗부분 평평 | Small signals pass. Big ones flatten on top. | B5 run: 학습 |
| 1:24 | 다섯 모델 실패 | None of its five starting models can do that. | B5 run: 초기 적합 |
| 1:29 | Spark 넷리스트 텍스트 | So Spark proposes one that isn't among them: a resistor and a diode. | B5 run: `propose_netlist` |
| 1:35 | ngspice → 커밋 해시와 시각 | Its netlist becomes a simulation, and the prediction goes to GitHub first. | B5 run: freeze 커밋 |
| 1:42 | 예약 입력 2개 | {Two inputs it never trained on. Both match.} | B5 run: `verification` |
| 1:49 | 처음 쓰는 사람의 손과 화면 | {Then someone new to BenchMate fixed a circuit whose fault value we hadn't used, following only Spark's requests.} | 비전문가 run, 밀봉 기록 |
| 2:02 | 숫자 장면 | 아래 "숫자 장면" | score.json, B5 변형 결과 |
| 2:35 | 공통 마무리 | | |

B5 개입(수리) 예측은 보류된 작업이라 넣지 않는다.

## 플랜 B — B5 실물 2회 모두 실패 (클라이맥스 = D01 수리 + 다른 사람의 완수)

D01 구간을 0:27–1:25로 늘린다. 수리 장면에는 실제 손 동작, 커밋 시각, 수리 전/후 곡선을 각각 2–3초 더 준다.
비전문가 완수를 별도 장면(약 15초)으로 둔다.

| 시간 | 장면 | 내레이션 |
| --- | --- | --- |
| 1:25 | 비전문가 완수 | {Someone new to BenchMate fixed a circuit whose fault value we hadn't used, following only Spark's requests.} |
| 1:40 | B5, 화면 전체에 **Simulated bench** 표시 | On a simulated bench, Spark goes further: a circuit it isn't told, with a diode none of its starting models include. |
| 1:48 | 넷리스트 → 예측 → 일치 | It proposes the missing structure, publishes the prediction, and both unseen inputs match. |
| 1:55 | 실물 시도 기록 | {On the real circuit, the run stopped at <기록의 실패 지점>. Both attempts are kept.} |
| 2:00 | 저항만 대조 | {In the resistor-only control, IN and OUT agreed.} |
| 2:02 | 숫자 장면 | |

실패 이유는 기록에 적힌 것만 말한다. 대조 검사는 "그 조건에서 IN/OUT 비교 통과"까지만 말하고, 계측 전체가 정상이라고 넓히지 않는다.

## 플랜 C — D01 실물 수리 예측이 빗나감

신뢰 장면으로 쓴다. 수리 성공 문장 대신:

- 수리 판정용 조건부 검증 자체가 실패한 경우: {The repaired response failed the frozen-model check. BenchMate did not verify the repair.}
- 명령 입력 예측만 어긋나고 조건부 검증은 통과한 경우: 두 결과를 각각 표시한다. 이 경우를 수리 판정 실패라고 바꾸지 않는다.
- 원인 확인 run이 있으면 그 결과만 짧게. 없으면 "That run is kept."로 끝낸다.

## 숫자 장면 (2:02–2:35, 모든 플랜 공통)

화면 라벨에는 **Simulated bench**와 회로 수를 쓴다. 완료된 평가만 넣고, 끝나지 않은 평가는 "not run"으로 표에 남긴다.
문장은 결과에 따라 아래에서 고른다. 우월 표현은 사전등록 규칙(완전한 과제, 양의 효과, Holm 보정)을 통과할 때만 쓴다.

1. **B5 변형(크게, 주인공).** b5-variants 결과가 있을 때만.
   - {On N hidden circuits none of its five starting models could explain, Spark proposed a structure that passed both unseen inputs and agreed with the circuit in X of 2N runs.}
   - 불필요한 다이오드: {On circuits without a diode, it proposed one m times.} 0이어도 말한다.
   - 격자 구조를 다 받은 엔진이 같거나 높으면: {An engine handed every answer structure reached Y. Spark had no list.}
   - 잘못된 확정이 하나라도 있으면 헤드라인 바로 옆에 둔다.
2. **과제 B(크게, 고정 절차 행 포함).**
   - 순위 숨김 Spark가 고정 절차와 같을 때: {Without the engine's ranking, Spark matched a hand-written plan: k of 16, with N simulated wiring changes on average.}
   - 낮을 때: 이 문장을 빼고 화면 표에는 그대로 남긴다.
   - "wiring changes"는 화면에 **simulated**를 붙인다.
3. **과제 A(작게, 측정 접근권 비교).** 측정하지 않는 Spark와 벤치를 쓰는 Spark의 비교라고 부른다. 같은 정보를 받은 비교라고 하지 않는다.
   - {Asked without measuring, Spark named the changed part in k of 24 circuits. With the bench, k of 24.}
4. 잘못된 부품 지목이 모든 행에서 0이면 한 줄로 강조한다: {No row named a wrong part.}
5. 빼는 행은 없다. Spark Open을 못 돌렸으면 "not run".

## 공통 마무리 (2:35–3:00)

| 화면 | 내레이션 |
| --- | --- |
| 이벤트 로그 해시 체인, 실패 run 폴더 | Models are locked before validation. Every attempt is kept, failures included. |
| 루프 다섯 단어 | Hypothesize. Choose the test. Lock the prediction. Measure. Verify. |
| 벤치 전경 | BenchMate turns a plausible explanation into a tested one. |
| 커밋 기록 첫 날짜, 끝 카드 | Built during the hackathon, from the first commit on October 27. |

## 촬영 목록 (11/2 23시 동결 전에 모두)

- 벤치 전경(정면·45°), USB 꽂기/빼기, 미니 브레드보드 위 부품 클로즈업 3컷
- D01: 부하 저항 연결 손, 추가 커패시터 제거 손(수리), 수리 후 화면
- B5: 시편 장착과 배선 클로즈업. 관객에게 보이는 배선과 모델에게 전달된 입력은 별개임을 명시한다, 진폭 스윕 동안의 화면
- 비전문가: 얼굴 없이 손과 화면만, 본인 동의
- 각 컷 앞뒤 2초 여유, 가능하면 60fps
