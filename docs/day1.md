# 1일차 실행 안내

현재 단계는 합성 데이터로 핵심 실험 흐름을 검증하고 실제 보드를 연결할 준비를 한 상태다. 하드웨어 진단 성능, B5 구조 제안, 홀드아웃 성공은 아직 주장하지 않는다.

## 실행

프로젝트 폴더에서 실행한다. `uv`는 프로젝트 전용 `.venv`를 사용한다.

```sh
uv sync --extra dev
uv run benchmate doctor
uv run pytest -q
uv run benchmate simulate --case b1
uv run benchmate simulate --case b6
uv run benchmate simulate --case d01-r
uv run benchmate simulate --case d01-c
```

출력의 `run` 경로를 그대로 재생한다. 재생은 저장된 결과와 해시 연결을 확인하며 API를 다시 호출하지 않는다.

```sh
uv run benchmate replay runs/실행폴더
```

키는 `.env`의 `MODEL_API_KEY`, `BASETEN_API_KEY`에서 읽는다. `.env`, `.private`, `runs`는 Git에서 제외되어 있다. 공개용 실행 기록은 검토 후 별도 디렉터리로 선별한다. Baseten은 `meta-models/muse-spark-open-1026`만 사용한다.

```sh
uv run benchmate api-smoke --provider meta
uv run benchmate api-smoke --provider meta --effort max
uv run benchmate api-smoke --provider baseten
```

각 API 검사는 실제 API 요청 최대 2회다. 합성 관측을 반환하는 도구를 모델이 호출하고, 결과를 받은 뒤 보고하는지 확인한다. 이는 연결과 도구 프로토콜 검사다.

실제 Spark가 합성 계측기의 다음 측정을 선택하고 검증까지 요청하는 통합도 사용할 수 있다. `simulate`는 LLM 없이, `agent`는 Meta API를 호출해서 실행한다. 둘 다 실제 보드 측정은 아니다.

```sh
uv run benchmate agent --case b6
uv run benchmate agent --case d01-r
```

에이전트는 관측 확인 → 추가 측정 선택 → 독립 검증 요청 → 세 칸 보고를 수행한다. 확인 전 확정과 예산 초과 요청은 코드가 막는다. 한 실행의 상한은 공통 탐색 1회 + 판정 측정 3회 + 확인 1회, API 요청 8회다. 션트 DC 두 수준은 판정 측정 2회로 센다. 자세한 경계와 실행 기록은 [에이전트 안내](agent.md)에 있다.

비용 기록의 `reserved_allowance_usd`는 청구 금액이 아니다. 요청마다 보수적인 로컬 허용액을 예약한다. Meta의 실제 토큰 비용은 공식 요금으로 추정할 수 있으나 Baseten 해커톤 요금은 별도 확인이 필요하다. 대시보드 청구액과 다를 수 있고, 다른 프로그램이 사용하는 비용은 여기서 차단할 수 없다.

## 보드가 도착하면

먼저 외부 회로 없이 보드를 USB로 연결하고 다음 명령으로 포트와 보드를 확인한다.

```sh
sh scripts/arduino.sh board list
```

WiFi 보드의 컴파일과 업로드 예시다. 포트는 위 명령에서 확인한 실제 값으로 바꾼다. Minima는 FQBN 끝의 `unor4wifi`를 `minima`로 바꾼다.

```sh
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/bringup
sh scripts/arduino.sh upload --fqbn arduino:renesas_uno:unor4wifi --port /dev/cu.usbmodem실제포트 firmware/bringup
uv run benchmate capture --port /dev/cu.usbmodem실제포트
```

초기 펌웨어는 `PING`, `READ`, `CAPTURE`를 지원한다. DAC 자극을 내보내지 않는다. A1~A4의 14비트 원시값 64개와 채널별 읽기 완료 시각을 RAM에 저장한 뒤 전송한다. 시각은 ADC의 실제 샘플 시각으로 보정된 값이 아니며, 떠 있는 입력의 값은 의미 있는 회로 측정이 아니다.

LM358과 커패시터까지 도착하면 고정 장치를 조립하고 D2에 전원, 버퍼, 오프셋, 채널 시간차, 지터, 검출 한계를 검증한다. 지금 원시값을 전압으로 환산하거나 하드웨어 확률 판정에 넣지 않는다.

## 다음 구현 순서

보드를 기다리는 동안에도 개발을 계속한다. Spark의 합성 실험 제어 루프를 먼저 연결했다. 다음으로 보드 없이 할 수 있는 일은 다음과 같다.

1. 현재 판단·남은 불확실성·다음 측정을 보여주는 실행 화면과 결선 지시. 실제 기록을 읽고 합성/실측/재생을 구분한다.
2. 생성 넷리스트의 소자·노드·수치 제한 검사와 B5 시뮬레이션. Spark가 만든 연결이 그대로 ngspice에 들어가게 하고, 미사용 조건의 예측을 먼저 기록한다.
3. D01의 수리 전 예측 → 부품 교체 → 재측정 흐름을 합성 데이터로 완결한다.

보드가 도착하면 원시 ADC 확인과 픽스처 보정을 우선한다. 자극·취득 펌웨어, 실제 채널 시각, B1/B6 션트 판별과 D01 부하 측정을 확인한 뒤 같은 제어 루프에 하드웨어를 연결한다. 실측 결과 없이 잡음·검출 한계·배선 성능을 확정하지 않는다. X2 측정은 최종 파이프라인 고정 뒤에 한다.
