# BenchMate 3분 영상 대본

확정 구조와 내레이션은 `docs/story-v3.md`(v3.1)에 있다. 영상은 `video/narration.json`에서 생성한다.


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
