# BenchMate 영상 이야기 v3.1 (확정안)

11/1 19:40 KST. Codex 검토(`docs/final-sprint.md`의 "Codex 검토")를 반영한 확정안이다. 개인 과목 자료는 쓰지 않는다.

## 구조

포럼 문제 → D01 실물 진단과 수리 → B5 구조 발견과 검증.

- **포럼 문제(약 20초):** [Arduino 포럼, 2021년 7월](https://forum.arduino.cc/t/voltage-divider-is-not-giving-correct-voltage/884099).
  ESP32에 연결한 분압기가 1.8 V 대신 1.1 V를 낸다. 저항 오차, 멀티미터, 납땜 같은 추측이 나오는 가운데
  전원과 입력 클램프 설명도 일찍(7/12, 12·20번 글) 나왔다. 질문자는 7/17(46번 글) 직접 시험해서
  전원이 없으면 틀리고 전원이 있으면 맞다는 것을 확인했다. 7/25(57번 글)에 "Real life testing was the correct
  way to find the issue."라고 썼다. 메시지는 **"설명은 있었지만, 시험으로 확인해야 했다"**이다.
- **D01(실물):** "a fault I planted"라고 밝힌다. 도구 없는 Spark 답변 5개(재측정 권고까지 같이 보여준다) →
  부하 실험 → 고정 → 하나만 살아남음 → 예약 사인 → 판정(명목 R 가정 표시)과 아직 모르는 것.
  수리는 오늘 밤 실행 결과가 나온 뒤 문장을 확정한다. 그 전까지는 자리표시자다.
- **B5:** "a simplified input-clamp test circuit inspired by the forum problem · not an ESP32"로 소개한다.
  "아무 힌트도 없다"가 아니라 "실제 배선을 알려주지 않았다"고 말한다. 다이오드는 "처음 다섯 선형 후보에는
  없던 구조"라고 하고, ESP32 내부 부품을 찾았다고 하지 않는다. 실물이 안 되면 Simulated bench로 표시한다.
- **빼는 것:** 칩 전원 켜기 단계, "엿새 vs 몇 분" 비교, "Now the forum circuit, rebuilt", "It's the ESP32's input protection".
- **마무리:** "BenchMate turns a plausible explanation into a tested one."

## 내레이션 (가편집 v2 기준)

**1. 포럼 문제**

1. On the Arduino forum, a voltage divider reads 1.1 V instead of 1.8.
2. Replies guess: resistor tolerance, the meter, bad solder.
3. Early on, a reply points to the cause: the ESP32 has no power.
4. Days later, a test confirms it.

**2. BenchMate**

5. BenchMate gives Muse Spark a bench to run those tests.
6. An Arduino drives the circuit and measures it. About $40 of parts.
7. Spark chooses each experiment. I only move the wires.

**3. D01: 일부러 넣은 결함 (실물)**

8. First, a fault I planted, in a circuit designed for 10 ms.
9. The intended design is 10 kΩ and 1 µF.
10. It measures 21.4 ms. Twice as slow.
11. Without measurements, Spark suggested a timing mix-up and asked us to check.
12. With one, it sees two suspects: a bigger resistor, or a bigger capacitor.
13. Another step test can't separate them.
14. So Spark asks for a known load.
15. Both answers are locked first.
16. Only one survives.
17. Then it passes a waveform it never saw.
18. Verdict: the capacitor is about twice its design value.
19. And it says what it still doesn't know.

**4. 앱**

20. In the app, every step links back to its raw data.

**5. D01 수리 (오늘 밤 실물, 결과 나오기 전까지 자리표시자)**

21. Spark asks for one fix: restore the designed capacitance.
22. Its prediction goes to GitHub before I touch anything.
23. I pull the extra capacitor, and the bench measures again.

**6. B5: 포럼 문제에서 영감을 받은 시험 회로**

24. Next, a test circuit inspired by that forum problem.
25. It hides a clamp diode. Spark isn't told the wiring.
26. Small signals pass. Big ones get flattened on top.
27. None of the five starting models can do that.
28. So Spark proposes a new structure: a resistor and a diode.
29. Its netlist becomes a simulation, then a locked prediction.
30. Two inputs it never trained on. Both match.

**7. 믿을 수 있는 이유**

31. Models are locked before validation measurements.
32. Every attempt is kept. Failures included.

**8. 마무리**

33. Hypothesize. Choose the test. Lock the prediction. Measure. Verify.
34. BenchMate turns a plausible explanation into a tested one.

## 인용 규칙

포럼 화면 캡처와 사용자 이름은 쓰지 않는다. 요약하고 출처를 단다. 그대로 인용하는 문장은 57번 글의 한 문장뿐이다.
