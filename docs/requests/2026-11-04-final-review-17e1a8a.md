# 최종 제출 전 검토 — main 17e1a8a

검토 대상은 Claude가 보고한 `17e1a8a`와 현재 공개 Pages 빌드 `f16165a`다.
모델·SAM 호출과 하드웨어 동작은 0회다. 사이트·README·영상 소스는 직접 수정하지 않았다.

## P1: 사례03·05 재생 데이터 4개가 main과 gh-pages에 없음

`site/data/runs/index.json`은 아래 네 ID를 참조하지만 해당 JSON은 두 브랜치 모두에 없다.
공개 URL도 실제 HTTP 404였다. 03 재생은 빈 플레이어, 05 보고서는 Loading…에 머문다.

- `site/data/runs/20261104T021333-c80ef3617e.json`
- `site/data/runs/20261104T034748-10ab5af750.json`
- `site/data/runs/20261104T041918-d1084cbeb4.json`
- `site/data/runs/20261104T051005-fac3d07c86.json`

원인: 루트 `.gitignore:16`의 `runs/`가 `site/data/runs/`까지 무시한다.
기존 파일은 추적 중이라 남아 있지만 신규 네 파일은 빠졌다. 작업 트리가 clean이어도 탐지되지 않는다.
이미 생성한 네 파일을 명시적으로 추적하거나 재추출하고, 사이트 데이터 디렉터리에 대한 좁은 ignore 예외를 둔다.
공개 데이터 4개를 강제로 추가하는 경우에도 `git add -f` 대상은 위 네 파일로 한정한다.
전체 `runs/`, DNG, `.private/`를 공개하면 안 된다.
그 후 gh-pages를 다시 배포하고 네 URL이200이며 실제 재생/보고서가 열리는지 확인한다.
`index.json`의 모든 ID에 대응하는 추적 파일이 존재하는 검사도 배포 전에 넣는 것이 좋다.

## P1: 최신 Tests는 진행 중이 아니라 실패

main `17e1a8a`의 [실제 Actions 결과](https://github.com/bami-codes/BenchMate/actions/runs/41823720153):
**13 failed, 834 passed, 1 skipped, 30 errors**, pytest 단계에서 실패했다.
직전 main 커밋들도 같은 Tests 실패가 있다. Pages 빌드 성공과 테스트 성공을 구분해야 한다.

주요 원인은 두 가지다.

1. `benchmate/__init__.py:8`은 `__path__`만 src로 돌린다.
   `importlib.resources.files('benchmate')`는 여전히 루트 shim 디렉터리를 반환한다.
   `src/benchmate/viewer.py:51`의 리소스 로드가 존재하지 않는 `benchmate/viewer.css`를 찾아
   다수 HTTP/뷰어/리뷰 테스트가 실패한다. 실제 CSS는 `src/benchmate/viewer.css`에 있다.
   이 증상은 로컬에서도 그대로 재현했다. 단순히 테스트를 숨기지 말고 shim의 패키지 리소스 해석을 고쳐야 한다.
2. `tests/test_photo_v2_images.py:20`은 OpenCV를 사용하는데 `pyproject.toml`의 dev 의존성에 없다.
   CI의 `pip install -e '.[dev]'` 이후 `ModuleNotFoundError: cv2`가 난다.

107개 원래 동결 소스는 현재도 일치한다. 동결 실행기/수치/기록을 고치는 문제로 확대하지 않는다.

## P1: 봉인과 채점 설명이 아직 여러 곳에서 과장됨

일부 문장을 고쳤지만 아래에는 여전히 코드가 verdict와 sealed answer를 자동 대조해 정답 채점한다는 뜻이 남아 있다.

- `README.md:5`: “every verdict is scored by code against a sealed answer”
- `site/index.html:22`, `site/assets/landing.js:67`: 같은 주장
- `site/index.html:186`: hidden fault가 result와 code로 비교된다는 설명
- `docs/submission.md:23`: “scored by code against a truth”
- `docs/submission.md:15`: “impossible to cheat”는 검증기가 입증하는 범위를 넘는다.

실제 코드는 파형/읽기를 고정 모델·범위와 채점한다. 봉인은 공개된 구성의 digest가 사전 commitment와 같은지 검사한다.
Spark 결과와 심은 고장은 나란히 제시되며, 포괄적인 자동 정답 판정은 아니다.
권장 문장: **“Code checks predictions against measurements. The sealed assembly is revealed afterward, and its digest is checked against the prior commitment.”**
영상 자막과 About에도 같은 구분을 유지한다.

## P1: 측정 전 forecast와 측정 후 measured-IN 검증을 분리해 설명

`README.md:52`, `docs/submission.md:17`은 아직 측정하지 않은 IN을 이미 사용해 예측한 것처럼 읽힌다.

실제 순서는 `src/benchmate/channel_timing_session_v4.py:41` 및 `:85`에 명확하다.

1. 측정 전 모델·파라미터와 **명령 입력 기반 예측**을 고정한다. `future_measured_IN_used:false`다.
2. 측정 뒤 고정 모델에 **실측 IN**을 넣어 조건부 OUT을 계산·채점한다. 예약 OUT 재피팅은 없다.
3. command score와 conditional score는 별개다. 05 복원 attempt2의 command-step 최악 구간은12.666mV로 실패했고,
   conditional-step 최악 구간은4.344mV로 통과했다. 03 복원도 command-step9.762mV 실패를 보존한다.

권장 설명: **“Before capture, the model and command-input forecast are frozen. After capture, the frozen model is driven by measured IN for conditional validation; both scores are retained separately.”**
측정 전 예측 전체가9mV를 통과한 것처럼 읽히지 않게 한다. 실험이나 기준 변경을 요청하는 것이 아니다.

## P2: 입력 범위·검증 예시·개수 문구 보완

- `README.md:73`, `docs/submission.md:27`의 “never told … hole positions”는 너무 넓다.
  사례03 사진 대응은 operator-confirmed IN=A3·OUT=A13·REF=A17 포트 정보를 실제로 받았다.
  숨은 고장/부품값을 주지 않았다는 사실과, 확인된 연결 포트 맥락을 준 사실을 구분해 쓴다.
  근거: 원래 pair의 `operator-photo-ports.json`, v5 사진 요청 코드92–96행, 원문 요청 plan.
- README의 사례05 검증 예시는 첫 pair의484 events만 확인한다. 사이트에서 보여주는 consistent 복원 attempt2에는
  아래 명령도 추가해야 한다. 실제로 통과했다.
  `PYTHONPATH=src python3 -S -m benchmate.channel_timing_audit_v4 examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750`
  결과:238 events + prior484 events + preflight4 events, PASS.
- 사례03 verifier는 실제로 `{"passed":true,...}` JSON을 출력한다. README의 출력 설명을 실제 stdout과 맞춘다.
- `README.md:160`의 “Five small passive circuits plus a diode case”는 여섯처럼 읽힌다. 다섯 중 하나가 diode 사례다.
- `README.md:62`의 모든 캡처가0.5ms인 듯한 표현은 step0.5ms/sine2ms로 구분한다.
- “10 official runs”는 현재 사이트에 선택한 fault/restored 재생10개다. 전체 장부의 모든 시도 수와 혼동하지 않도록
  “10 displayed/replayed runs; all attempts retained”로 단위를 명시하는 편이 정확하다.
- `site/assets/landing.js:75`의 모든 원인이 포럼에서 확정됐다는 문장은 원래 EEVblog 사례의 부분 확인과 맞지 않는다.
  “forum-inspired cases rebuilt on our bench”처럼 현재 재현의 범위를 표현한다.

## 확인된 정상 항목

- README 로컬 상대 링크를 다시 검사했고 누락은 없었다.
- README의 오프라인 검증5개는 모두 exit0/통과했다. 05 복원 후속 검증도 별도로 통과했다.
- `web/`, 루트 `PRODUCT.md`, `DESIGN.md`는 실제 삭제되어 있다. 기존 기록과107개 원래 동결 소스는 유지된다.
- 사이트 사례 목록은5개이고 LED는 제외되어 있다. 101 Spark·6 SAM·약$1.01 집계는 현재 자료와 일치한다.
- 최신 비디오 문서 상단은 새 제출 영상이 아직 없고 이전 컷은 초안이라는 점을 명시한다.
- 공개 Pages 빌드는 성공했지만 데이터404 검사는 하지 못한 상태다. 성공한 build가 앱 동작을 보증하지 않는다.

영상 URL은 `docs/submission.md:9`에 아직 placeholder다. 누락 데이터·CI·문구 수정과 병행해 현재 사례로 영상을 만들고
실제 업로드 URL을 넣어야 한다. 이전 mock 포함 백업 영상을 이번 다섯 사례의 최종 영상으로 표기하지 않는다.

## 이번 검토에서 완료한 저장소 About 설정

홈페이지를 `https://bami-codes.github.io/BenchMate/`로 설정했고 토픽은
`hackathon`, `meta`, `muse-spark`, `sam`, `arduino`, `ngspice`, `electronics`다.
설명은 위 과장 표현을 피해서 다음과 같이 설정했다.

> Muse Spark chooses experiments on a real Arduino circuit. Frozen models are checked against measurements; sealed records and offline verification expose each step.
