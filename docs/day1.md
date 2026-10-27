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

각 API 검사는 실제 API 요청 최대 2회다. 합성 관측을 반환하는 도구를 모델이 호출하고, 결과를 받은 뒤 보고하는지 확인한다. 이는 연결과 도구 프로토콜 검사다. 현재 엔진 시뮬레이션은 LLM 없이 동작하며, Spark가 실험 전체를 지휘하는 통합은 다음 작업이다.

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

1. 준비된 계측 픽스처의 자극·취득 펌웨어와 호스트 연결, 실제 채널 시각 보정.
2. B1/B6 실제 관측과 션트 판별, D01 부하 측정. 개입 횟수 기록.
3. Spark 제어 루프 통합, 생성 넷리스트 검증기, B5의 미사용 조건 예측.
4. 대표 수리 장면과 재연결 반복 실행. X2 측정은 최종 파이프라인 고정 뒤에 한다.

