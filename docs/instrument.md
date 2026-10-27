# D2 계측 준비

보드 도착 전 작성·컴파일한 펌웨어다. 실제 출력·속도·정착·채널 시간차는 아직 검증하지 않았다. 하드웨어 원시값은 진단 엔진에 넣지 않는다.

## 첫 연결

외부 회로 없이 `firmware/bringup`으로 보드 인식과 원시 ADC를 확인한다. LM358 픽스처를 조립하고 전원·REF를 실측한 다음 `firmware/instrument`를 사용한다.

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

출력을 확인한 뒤 DUT를 연결하고 취득한다. 보드가 리셋됐거나 설정이 다르면 취득은 재무장하지 않고 실패한다. 다시 DUT를 빼고 REF부터 설정한다.

```sh
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --kind hold --hold-v 1.6
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --kind step --amplitude-v 0.5 --samples 512 --period-us 500
uv run benchmate instrument --port 실제포트 --vref-v 4.7 --ref-v 1.6 --kind sine --amplitude-v 0.2 --frequency-hz 1 --samples 512 --period-us 4000
```

명령 전압은 입력한 공급값으로 환산한 DAC 설정값이다. 보정된 실측 전압이 아니므로 A3·A4의 실제 파형을 확인해야 한다.

## 구현된 경계와 남은 확인

- REF±1 V 코드 범위, 한 번에 1 V 이하 변화. 양방향 계단은 ±0.5 V 이하이며 코드 반올림으로 제한을 넘지 않게 진폭을 내림 처리한다.
- 최소 1,200 ms 대기(현재 최대 RC 사전범위의 5τ 이상) 후 A2의 원시값 안정 구간과 클리핑을 확인한다. 기본 안정 범위 20 counts는 D2에서 정할 임시값이다.
- 사인 정착 구간을 먼저 실행하고 주파수당 최소 20샘플을 요구한다. 형식 검사가 실제 속도 달성을 뜻하지는 않는다.
- A1–A4의 14비트 원시값, 12비트 DAC 코드, 프레임 및 채널별 읽기 완료 시각을 RAM에 저장한 뒤 전송한다. 읽기 완료 시각은 보정된 샘플 aperture가 아니다.
- ADC sampling-state 255를 요청하고 레지스터 읽기 결과를 패킷에 남긴다. 설정이 유지되지 않으면 호스트가 거절한다. 간섭 개선 효과는 실측해야 한다.
- 기한 초과·부분 블록·잘못된 시각을 거절하고 원본을 실패 기록에 남긴다. 완료 후 REF로 복귀한다. 취득 중 새 직렬 입력은 취득을 취소하고 REF로 복귀시킨다.

## 512샘플 제한

D2에서는 지터·채널 시각을 가정하지 않고 전부 기록한다. 1,000샘플은 코어 예약 힙/스택까지 포함하면 링크에 실패해 512샘플로 제한했다. 실측 후 압축 시각 표현과 긴 블록을 별도로 검토한다.

컴파일 결과: WiFi flash 64,420 B / static RAM 18,192 B; Minima flash 51,888 B / static RAM 15,392 B. 업로드·실측은 하지 않았다. 현재 코어의 `analogRead`와 긴 샘플 시간을 포함한 실제 속도는 D2에서 확인한다. 5 kHz 취득이나 500 Hz 신호 대역을 달성했다고 주장하지 않는다.

D2에서 전원·REF, DAC/A3 범위·왜곡, 풀다운, A1–A5 오프셋·기울기, aperture·지터, 채널별 σ·ρ·모델 오차, 전류 검출 한계, 정착 기준, 주파수 상한·여섯 주파수와 검증 조건을 고정한다. 보정된 픽스처 모델이 연결되기 전까지 하드웨어 추론은 차단한다.

## 검증 조건의 구분력 확인

현재 개발 조건(무부하 ±0.35 V 계단, 10 kΩ 부하의 1 Hz/±1 V 사인)은 유지한다. 학습에서 고정한 RC와 제안 구조의 예측 차이(RMS·최댓값), 각각의 출력 잔차와 지역별 잡음 정규화 검사를 함께 기록한다. 한 조건에서 둘 다 통과하면 그 조건의 구분력이 약하다고 표시한다. 지금의 합성 성공은 실물 조건의 구분력을 보장하지 않는다.

D2에서는 실측 잡음·픽스처 오차와 가능한 자극 범위로 예측 차이를 평가하고, 최종 평가 전에 조건과 판단 기준을 고정한다. 검증 결과를 보고 조건을 바꾸거나 재적합한 경우에는 그 관측을 개발 데이터로 분류하고 변경 이유를 남긴다. X2는 사용하지 않는다.

상향 0.7 V 계단을 검토한다면 **REF → REF+0.7 V**처럼 시작·끝 전압을 명시해야 한다. 현재 `--amplitude-v 0.7`은 양방향 ±0.7 V, 즉 1.4 V 변화이므로 허용되지 않는다. 한쪽 방향 계단은 현재 인터페이스에 구현되지 않았으며, 추가 시 파형 표현·정착·보정과 최대 1 V 변화 규칙을 먼저 검증해야 한다.
