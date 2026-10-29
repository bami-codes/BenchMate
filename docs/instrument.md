# D2 계측 준비

2026-10-29, Minima에서 instrument v2 업로드·RESET·이전 ID 명령 거절·새 ID ARM을 확인했다. 첫 512프레임 블록은 수신됐지만 ADC 레지스터 검사 실패로 거절했으며 승인 샘플은 0이다. 이 검사에서 미사용 슬롯까지 읽던 오류를 수정해 컴파일·소프트웨어 테스트를 마쳤다. 수정본 업로드와 실제 사용 채널 레지스터 확인은 아직 하지 않았다. 별도로 A4의 1kΩ 저항 양쪽에서 REF 1.62V / ADC 쪽 2.15V가 보고돼 물리적 전압 차이를 조사 중이다. 보정 완료나 하드웨어 진단으로 취급하지 않는다. [원본 기록](../examples/hardware-fixture-bringup/2026-10-29-followup/README.md).

## 첫 연결

외부 회로 없이 `firmware/bringup`으로 보드 인식과 원시 ADC를 확인한다. LM358 도착 전에는 [부하 저항 없는 DC 루프백](dac-loopback.md)으로 A0 출력과 ADC의 기본 응답을 확인할 수 있다. 이후 LM358 픽스처를 조립하고 전원·REF를 실측한 다음 `firmware/instrument`를 사용한다.

```sh
sh scripts/arduino.sh board list
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/instrument
sh scripts/arduino.sh upload --fqbn arduino:renesas_uno:unor4wifi --port 실제포트 firmware/instrument
```

Minima에서는 FQBN 끝을 `minima`로 바꾼다.

## REF 설정과 측정

부팅 시 DAC는 꺼져 있다. **DUT를 뺀 상태에서** `--arm-only`로 REF를 먼저 만든다. 아래 4.7 V와 1.6 V는 예시이며 실제 측정값으로 바꾼다.

```sh
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --arm-only
```

결과의 `boot_id`를 보관한다. 출력을 확인한 뒤 DUT를 연결하고, 그 ID를 `--boot-id`로 전달해 취득한다. 보드가 리셋됐거나 설정이 다르면 취득은 재무장하지 않고 실패한다. 다시 DUT를 빼고 REF부터 설정한다. 아래 `실제부팅ID`는 `--arm-only`가 반환한 32자리 소문자 16진수로 바꾼다.

```sh
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --boot-id 실제부팅ID --kind hold --hold-v 1.6
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --boot-id 실제부팅ID --kind step --amplitude-v 0.5 --samples 512 --period-us 500
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --boot-id 실제부팅ID --kind sine --amplitude-v 0.2 --frequency-hz 1 --samples 512 --period-us 4000
```

명령 전압은 입력한 공급값으로 환산한 DAC 설정값이다. 보정된 실측 전압이 아니므로 A3·A4의 실제 파형을 확인해야 한다.

## 재시작·통신 단절 시 데이터 처리

- 프로토콜은 `benchmate-instrument-v2`다. PING·ARM·CAPTURE·STOP·오류 응답에 모두 `boot_id`, `boot_id_ready`, `uptime_ms`를 넣는다. 기존 v1 응답은 부팅 연속성을 검증할 수 없어 거절한다. 이전 DC 루프백 기록과 펌웨어는 그대로 유지한다.
- 부팅 ID는 RA4M1 하드웨어 난수 128비트로 생성한다. [Renesas 코어 1.6.0에서 사용하는 초기화·난수 함수](https://github.com/arduino/ArduinoCore-renesas/blob/1.6.0/cores/arduino/WMath.cpp)를 쓰되 두 반환 상태를 모두 확인한다. 실패하면 ID는 `null`이고 출력 명령을 허용하지 않는다. 장치 일련번호·`millis()`·고정 시드 난수를 ID로 대신 쓰지 않는다. 난수 ID의 충돌 확률은 0이 아니며 인증 수단도 아니다.
- ARM·CAPTURE·STOP에는 대상 부팅 ID를 넣는다. 보드가 PING 직후 재시작되어도 이전 ID의 명령을 출력 변경 전에 거절한다. 호스트는 ARM 때 받은 ID를 별도 CAPTURE 호출에도 요구한다.
- 응답마다 같은 ID와 정상 진행하는 uptime인지 확인한다. 짧은 취득 구간에서 uint32 `millis()`의 정상 순환은 허용하고 역행은 거절한다. 취득 응답을 받은 뒤 마지막 PING까지 같은 부팅이어야 `run_completed`를 기록한다.
- ID 변경·누락, 잘린 응답, 타임아웃, 연결 끊김, 잘못된 블록은 `instrument_run_invalidated`와 `run_failed`로 남긴다. 승인 샘플은 0이고 자동 재무장·재시도는 하지 않는다. 받은 원시 블록이나 잘린 응답은 보존한다. 부팅 변화가 확인되지 않은 단절을 임의로 '재시작'이라고 진단하지 않는다.

소프트웨어에서는 재시작 전·중·후와 부분 응답을 주입했고, 실제 스케치의 파서를 가짜 IO 환경에서도 실행해 이전 ID 명령이 출력을 바꾸지 않는 것을 확인했다. Minima에서 하드웨어 난수 생성 성공·ID 유지와 작업자 RESET 한 번 뒤 ID 변경, 이전 ID 명령 거절을 확인했다. 취득 중 RESET·USB 분리 검사는 **D2에 DUT를 뺀 상태에서** 별도로 해야 한다. 같은 케이블과 마지막 측정에 성공한 맥 포트를 유지하고, 바꾸면 기록한다.

D2 확인 순서: PING ID 확인 → RESET 한 번 → 새 ID 확인 → 이전 ID ARM/CAPTURE가 거절되는지 확인 → 새 ID로 다시 명시적 ARM. 이후 취득 중 RESET/USB 분리를 시험해 성공 결과가 생기지 않고 실패 기록이 남는지 확인한다. 2026-10-29 Minima에서 단일 RESET·이전 ID 거절·새 ID ARM까지 확인했다. 취득 중 RESET/USB 분리는 아직 시험하지 않았다.

## 구현된 경계와 남은 확인

- REF±1 V 코드 범위, 한 번에 1 V 이하 변화. 양방향 계단은 ±0.5 V 이하이며 코드 반올림으로 제한을 넘지 않게 진폭을 내림 처리한다.
- 최소 1,200 ms 대기(현재 최대 RC 사전범위의 5τ 이상) 후 A2의 원시값 안정 구간과 클리핑을 확인한다. 기본 안정 범위 20 counts는 D2에서 정할 임시값이다.
- 사인 정착 구간을 먼저 실행하고 주파수당 최소 20샘플을 요구한다. 형식 검사가 실제 속도 달성을 뜻하지는 않는다.
- A1–A4의 14비트 원시값, 12비트 DAC 코드, 프레임 및 채널별 읽기 완료 시각을 RAM에 저장한 뒤 전송한다. 읽기 완료 시각은 보정된 샘플 aperture가 아니다.
- ADC sampling-state 255를 실제 사용하는 A1/A2/A3의 AN000/001/002와 A4의 AN021 공유 레지스터에 요청한다. PING에 현재 값, CAPTURE에 사용 채널 번호와 취득 전후의 네 값을 남긴다. 호스트는 모두 255인지 확인한다. 미사용·예약 슬롯은 쓰거나 검사하지 않는다. 간섭 개선 효과는 실측해야 한다.
- 기한 초과·부분 블록·잘못된 시각을 거절하고 원본을 실패 기록에 남긴다. 완료 후 REF로 복귀한다. 취득 중 새 직렬 입력은 취득을 취소하고 REF로 복귀시킨다.

## 512샘플 제한

D2에서는 지터·채널 시각을 가정하지 않고 전부 기록한다. 1,000샘플은 코어 예약 힙/스택까지 포함하면 링크에 실패해 512샘플로 제한했다. 실측 후 압축 시각 표현과 긴 블록을 별도로 검토한다.

사용 채널 레지스터 수정본 컴파일 결과: WiFi flash 69,620 B / static RAM 18,356 B; Minima flash 66,164 B / static RAM 15,920 B. 관련 호스트·실제 스케치 파서 테스트 46개 통과. 현재 보드에는 이전 v2가 있으며 수정본 업로드는 대기 중이다. 사용 채널의 취득 전후 readback이 실제로 255인지 확인해야 한다. 첫 거절 블록은 소급해서 통과시키지 않는다. 5 kHz 취득이나 500 Hz 신호 대역을 달성했다고 주장하지 않는다.

D2에서 전원·REF, DAC/A3 범위·왜곡, 풀다운, A1–A5 오프셋·기울기, aperture·지터, 채널별 σ·ρ·모델 오차, 전류 검출 한계, 정착 기준, 주파수 상한·여섯 주파수와 검증 조건을 고정한다. 보정된 픽스처 모델이 연결되기 전까지 하드웨어 추론은 차단한다.

## 검증 조건의 구분력 확인

현재 개발 조건(무부하 ±0.35 V 계단, 10 kΩ 부하의 1 Hz/±1 V 사인)은 유지한다. 학습에서 고정한 RC와 제안 구조의 예측 차이(RMS·최댓값), 각각의 출력 잔차와 지역별 잡음 정규화 검사를 함께 기록한다. 한 조건에서 둘 다 통과하면 그 조건의 구분력이 약하다고 표시한다. 지금의 합성 성공은 실물 조건의 구분력을 보장하지 않는다.

D2에서는 실측 잡음·픽스처 오차와 가능한 자극 범위로 예측 차이를 평가하고, 최종 평가 전에 조건과 판단 기준을 고정한다. 검증 결과를 보고 조건을 바꾸거나 재적합한 경우에는 그 관측을 개발 데이터로 분류하고 변경 이유를 남긴다. X2는 사용하지 않는다.

상향 0.7 V 계단을 검토한다면 **REF → REF+0.7 V**처럼 시작·끝 전압을 명시해야 한다. 현재 `--amplitude-v 0.7`은 양방향 ±0.7 V, 즉 1.4 V 변화이므로 허용되지 않는다. 한쪽 방향 계단은 현재 인터페이스에 구현되지 않았으며, 추가 시 파형 표현·정착·보정과 최대 1 V 변화 규칙을 먼저 검증해야 한다.
