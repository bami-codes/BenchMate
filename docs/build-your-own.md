# Build a BenchMate development bench

Start with the recorded demo, then assemble the low-voltage RC fixture below.
This is the build used for one physical D01 diagnosis, not a finished general
purpose instrument. The software runs locally; paid Meta calls are optional and
separate from replay. New builders still need to characterize their own channels.
The author's calibration and USB identity are not portable settings.

## 1. Run the complete example first — no board or API key

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/),
then from a terminal:

```sh
git clone https://github.com/bami-codes/BenchMate.git
cd BenchMate
uv sync --extra vision
uv run python scripts/known_design.py serve --demo
```

Open **http://127.0.0.1:8766**. Choose **Load recorded example**, inspect the
schematic and Spark's retained reading, enter your review note, save, then
continue to D01 replay. Select the four scenes through the final verification.
No API key, Arduino or ngspice is needed for this path. Ctrl-C stops the server.

The schematic is synthetic and its October 31 Spark reading is real. The D01
measurements are from a **separate circuit on October 30** with the same nominal
10 kΩ / 1 µF design. The replay does not measure or diagnose the selected image.
The C estimate is conditional on nominal resistance, not a direct capacitance
measurement. [Full evidence](physical-demo.md).

## 2. Parts and cost

Amounts below are **October 2026 project procurement records in KRW**, not live
store quotes or a lowest-price estimate. Bundles contain substantial spares;
shipping and the multimeter battery are excluded. Prices came from the project's
original purchase list; no receipt audit or current availability check is claimed.
The measured development run used the **R4 Minima-compatible** spare board, not
the originally purchased R4 WiFi-compatible board.

| Item | Quantity needed for RC / D01 fixture | Recorded purchase bundle | Bundle price |
| --- | --- | --- | ---: |
| UNO R4 Minima-compatible RA4M1 board | 1 | 1 board, Coupang | ₩10,310 |
| Large breadboard and jumper wires | 1 × 830-hole board, roughly 40 suitable jumpers | 830 + 400-hole boards, male jumpers, 126-piece U jumper set | ₩15,990 |
| Mini breadboard | 1 × 170-hole | 12 boards | ₩7,650 |
| 1% resistors | 10 kΩ × 7; 1 kΩ × 5; 100 kΩ × 1; optional extra 1 kΩ shunt | 30 values × 20, 10 Ω–1 MΩ | ₩7,300 |
| Nonpolar film capacitors | 0.1 µF × 2, 1 µF × 1; second 1 µF for D01 fault | 1 µF × 10, 0.1 µF × 20, 0.47 µF × 10 | ₩6,400 |
| LM358N DIP-8 | 2 | 5, DeviceMart | ₩1,500 |
| 1N4148 (B5 option) | 1 | 10, DeviceMart | ₩200 |
| USB-C **data** cable | 1 | 2 cables | ₩6,630 |
| **Parts basket, including surplus parts** | | | **₩55,980** |
| Multimeter, continuity / diode / DC modes | 1 | ANENG DM950 | ₩19,990 |
| **Basket plus multimeter** | | | **₩75,970** |

A laptop, cutters and a suitable meter battery are also needed. Cases, labels,
lighting, camera support and spare WiFi board are not required for this build.
This is a bundle-based budget, **not** a measured unit manufacturing cost.

The [official UNO R4 Minima documentation](https://docs.arduino.cc/hardware/uno-r4-minima/)
describes the 5 V RA4M1 board and its DAC/ADC. A compatible board may differ in
USB or peripheral circuitry. Do not substitute an R3, ESP32 or arbitrary 3.3 V
board and reuse this wiring or the saved calibration.

## 3. Electrical layout

Use USB power only for this recorded configuration. Disconnect it and wait for
the power LED to go out before wiring or changing parts. Keep external powered
circuits disconnected. This fixture is for the stated passive RC experiments.

```mermaid
flowchart LR
    DAC[Arduino A0 DAC] --> DRIVE[U1B voltage follower]
    DRIVE --> SHUNT[Bypass jumper or measured shunt]
    SHUNT --> IN[IN / A1]
    IN --> R[10 kΩ DUT resistor]
    R --> OUT[OUT]
    OUT --> C[1 µF DUT capacitor]
    C --> REF[Buffered REF ≈ supply / 3]
    OUT --> U2[U2A follower → A2]
    DRIVE --> A3[A3: before shunt]
    REF --> A4[A4: REF monitor]
    OUT -. optional 9.99 kΩ load .-> REF
```

**REF / RET is not GND.** GND is the blue supply rail; REF is a buffered divider
near 1.6 V. The mini-board capacitor and optional load return to REF.

### Coordinate convention

Use the same layout as [the fixture wiring table](fixture-wiring-table.md):
A–E connect within each numbered column, F–J connect on the other side of the
center trench; E and F are **not** connected across it. Numbers refer to terminal
columns, not power rails. The red/blue rail references below mean their **upper
left segment**, with rail holes counted from its left. Check the actual board's
connectivity; some rails split in the middle. Do not copy coordinates onto a
board with a different geometry.

Place both LM358N chips across the trench with markings up and the semicircular
notch to the **left**. U1 spans E10–E13 / F10–F13; U2 spans E20–E23 / F20–F23.
On each, the upper row from left to right is pins 8, 7, 6, 5; lower row 1, 2, 3, 4.
Confirm against the [manufacturer pinout, page 4](https://www.st.com/resource/en/datasheet/lm358.pdf).

### U1: supply, REF and DAC driver

| Part / wire | Endpoints | Purpose |
| --- | --- | --- |
| Arduino 5V / GND leads | Upper-left red / blue rail, separate free holes | USB supply; no free exposed 5V probe post |
| 10 kΩ × 3 | A3–A6; B6–B9; C9–C16 | Divider; node 9 is supply / 3 |
| Jumpers | B3–red rail hole 3; A10–red rail hole 5 | Divider and U1 positive supply |
| Jumpers | A16–blue rail hole 3; J13–blue rail hole 5 | Divider and U1 ground |
| Jumper | D9–H12 | Divider to U1 pin 3 |
| Jumper | G10–G11 | U1 REF follower, pins 1–2 |
| 1 kΩ + jumper | I10–I16; H16–H13 | REF output pull-down to GND |
| 0.1 µF film | D10–G13 | U1 supply decoupling |
| Jumper | B11–B12 | U1 driver follower, pins 7–6 |
| Arduino A0 lead | A0–A13 | DAC to U1 driver input, pin 5 |
| 1 kΩ | D11–D16 | Driver output pull-down |
| 100 kΩ | B13–E16 | DAC input pull-down |

The old temporary **A9–A13** jumper must be absent when A0 is connected. Do not
add the historical free probe posts at A11/B13. They are not needed for wiring.

### U2: measurement buffer and Arduino inputs

| Part / wire | Endpoints | Purpose |
| --- | --- | --- |
| Jumpers | C10–A20; B16–A27; C27–J23 | U2 supply and ground |
| 0.1 µF film | D20–G23 | U2 supply decoupling |
| Jumpers | G20–G21; B21–B22 | U2 follower feedback, pins 1–2 and 7–6 |
| 10 kΩ + jumper | I20–I27; H27–H23 | OUT buffer pull-down |
| 10 kΩ | D21–D27 | Auxiliary buffer pull-down |
| Jumper | C11–A28 | Driver output to pre-shunt node |
| **Jumper 11** | **B28–B35** | Shunt bypass for ordinary RC work |
| Jumper | A30–H22 | OUT to U2 pin 3 |
| Jumper | H10–A50 | Buffered REF distribution |
| **Jumper 14** | **B50–B23** | Auxiliary input fixed at REF; also supplies optional load return |
| 1 kΩ; Arduino lead | D35–G35; H35–A1 | IN channel |
| Jumper; 1 kΩ; Arduino lead | J20–A40; D40–G40; H40–A2 | Buffered OUT channel |
| Jumper; 1 kΩ; Arduino lead | C28–A45; D45–G45; H45–A3 | Pre-shunt drive channel |
| **Short jumper**; Arduino lead | **D50–G50**; H50–A4 | REF channel on this documented Minima fixture |
| 10 kΩ (measured 9.99 kΩ in original build); jumper | D55–D60; C23–A60 | Optional load, disconnected at D55 until requested |

A4 is directly connected only to the internal buffered REF. A1–A3 retain their
1 kΩ resistors. This A4 change was made after a measured board-specific loading
problem; it is not advice to remove ADC protection for arbitrary external signals.
A4 is used as a drift guard, not a trusted absolute REF estimate.

**C35–C30 calibration jumper 15 must be absent with a DUT installed.** Do not
connect either A55–C35 (IN branch) or E30–A55 (OUT load) during ordinary unloaded
RC setup. Never install both branch jumpers together. Keep jumper 14 while the
load's C23–A60 return depends on it.

### Mini-board: start with the ordinary RC circuit

| Part / wire | Endpoints |
| --- | --- |
| Large-board IN to mini-board | Large A35 → mini A3 |
| Large-board OUT to mini-board | Large D30 → mini A8 |
| Large-board REF to mini-board | Large C50 → mini A13 |
| DUT resistor, 10 kΩ | Mini B3–B8 |
| DUT capacitor, 1 µF nonpolar | Mini D8–D13 |
| Extension bridges | Mini E8–F8; E13–F13 |

For the D01 development fault, a second 1 µF capacitor was added at mini I8–I13
in parallel with the first. For B5, **both capacitors are removed**, and a diode
is used only under the separate [B5 operator sequence](b5-operator.md). These are
different configurations, not components to install together.

## 4. Check the unpowered assembly

Verify chip direction and that exposed leads do not touch adjacent nodes.
With USB disconnected, check continuity: 5V rail to U1/U2 pin 8; GND rail to
pin 4; each follower's output to its inverting input; A28↔A35 bypass; mini
A3↔large A35, mini A8↔large E30, mini A13↔large D50. With the extension bridges,
mini D8↔I8 and D13↔I13 should connect. The supply rails must not be shorted.
A buzzer check confirms connection, not correct resistance or calibration.
Measure resistors outside the circuit before installation; parallel paths make
in-circuit resistance readings ambiguous.

## 5. Install the instrument firmware

Install [Arduino CLI](https://docs.arduino.cc/arduino-cli/installation/). The
wrapper keeps the toolchain inside the project. The current firmware was built
against **Arduino Renesas UNO core 1.6.0**; use that revision for reproduction.
Keep fixture/DUT signal leads disconnected from the Arduino for the first upload.
The commands below describe a future operator action; the replay never runs them.

```sh
sh scripts/arduino.sh core update-index
sh scripts/arduino.sh core install arduino:renesas_uno@1.6.0
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4minima firmware/instrument
sh scripts/arduino.sh board list
```

Copy the **actual listed Minima port**, then upload:

```sh
BENCHMATE_PORT=/dev/cu.usbmodem_REPLACE_WITH_YOUR_PORT
sh scripts/arduino.sh upload --fqbn arduino:renesas_uno:unor4minima --port "$BENCHMATE_PORT" firmware/instrument
```

Use `unor4minima`, not `unor4wifi`, for Minima. Uploading replaces the sketch on
the selected board. The first software check needs no DAC command:

```sh
uv run python -m serial.tools.miniterm "$BENCHMATE_PORT" 115200 --eol LF
```

Type `PING` and Enter once. A valid response identifies
`benchmate-instrument-v2`, `type: pong`, a ready boot ID and ADC settings. Exit
with Ctrl-]. This is only a communication check. If there is no response, record
that failure, close the terminal and inspect the selected port/cable before a
new operator-confirmed attempt. Do not silently retry or treat an old boot ID as
current. Close all serial monitors before any capture runner opens the port.

## 6. First measurements and honest stopping point

Reconnect the checked fixture with USB off; keep the DUT disconnected for initial
REF/driver bring-up. Establish actual supply and REF and characterize channel gain,
offset, timing and noise using the [instrument procedure](instrument.md) and
[measured-input policy](measured-input.md). A small number of initial voltage
checks is still needed for a newly built bench; repeatedly centering every
waveform by hand is not the intended workflow.

The current physical runners carry **this project's device identity and
provisional calibration**. They deliberately reject mismatches. Do not bypass
those checks or paste the original supply, REF and boot ID into a different bench.
There is not yet a validated one-command commissioning wizard for a new build.
For a new builder, successful replay + assembled fixture + PING is the reproducible
first milestone; a scored physical diagnosis follows only after local commissioning.

The original bench's physical D01 run acquired 7,680 ADC frames across 15 blocks,
with five Spark requests and one manual load attachment. It is one development
run. Physical B5 and Spark-directed physical repair remain pending as of October 31.
This guide itself has **not yet been completed by an independent builder**.
