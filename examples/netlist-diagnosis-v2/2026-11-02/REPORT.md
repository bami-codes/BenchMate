# Six-circuit diagnosis v2: offline development record

All six planned forum-inspired circuits are in one software runner, including
the operator-reported JCET BC547B and red 5 mm diffused LED. No paid model,
actual serial port, wiring operation or firmware upload was used.

| Circuit | Faulted mock after reserved checks | Restored mock in a new session |
| --- | --- | --- |
| Pin output impedance | Effective series resistance increased; location unresolved | Consistent |
| Sensor-filter segment | Filter-C hypothesis under the declared single-fault/positive-value prior | Consistent |
| Two-resistor timing chain | RA/RB indistinguishable | Consistent |
| Unpowered-input divider | Proposed diode structure predictively supported | Consistent |
| Parallel decoupled load | Proposed series resistance predictively supported | Consistent |
| BC547B/red LED | Q1 gain and Rbase indistinguishable | Consistent |

Twelve outcomes match the development expectations. These are scripted,
shared-ngspice software checks, **not Spark decision accuracy or physical
accuracy**. All six use the same menu and reserved settings. The runtime allows
the agent to choose the order; only the explicitly labelled development
controller chooses the same three training actions here.

The active layout is four parts: Rbase 4.7k, Rled 1k, BC547B and a red LED.
The development fault uses Rbase 1M. A declared 47k/10k measurement divider to
REF is outside the DUT and is simulated with its loading, including the known
output load when selected. Collector COL is distinct from measured OUT.
GND and REF are distinct. The original forum's five-LED load and resistor values
are not copied literally; see the Changed explanation in the catalogue.

BC547B gain and LED forward voltage are development nuisances, not measured
device parameters. In the active region, a large base resistance and a very low
transistor gain can be electrically confounded. A fixed counterexample pair
was run through all eight menu and two reserved conditions; maximum output
difference was approximately 0.0001263 mV. The component list therefore retains
both Q1 and Rbase. A resistance point estimate from one fit is not unique.

The [retained numerical certificate](equivalence-envelope.json) also checks 16
normal/fault, gain-bound, red-forward-voltage-bound and load conditions. For
those conditions the measured output was 1.3632–1.9441 V and peak simulated
supply current was about 3.196 mA. This supports the proposed attenuation
within the existing voltage window; it does not qualify the actual hardware.
No optical brightness or physical LED current was measured.

Fifteen new tests passed. Four parameterized checks solve Ebers–Moll and LED
equations independently of SPICE. Additional tests cover current/voltage bounds,
ambiguity, prospective publication, no reserved refit, retained absolute DC,
disabled unqualified hardware and preservation of the complete 66-file v1
runtime. An incomplete numerical candidate assessment cannot produce a unique
diagnosis in v2. Optimizer failure is recorded as fit_error, not circuit failure.

The active physical path is deliberately disabled pending actual supply/REF,
absolute-DC calibration, attenuation and wiring checks. Subtracting an output
HOLD origin would discard the useful DC fault information, so the passive
HOLD-origin path is not silently reused for this case. No firmware range
expansion or upload is requested by the attenuated design.

- [Final twelve-session summary](summary.json)
- [Validation receipt and source hashes](validation.json)
- [Original development records](development-records.tar.gz): initial active
  run, first six-case batch and final six-case batch; all 25 event chains and
  terminal results verified. The final batch contains the conservative
  incomplete-fit gate; earlier versions and their source copies are retained.
- [Archive member hashes](archive-manifest.json)
- [Envelope/equivalence producer](../../../experiments/led_diagnosis_evidence.py)
- [Design and implementation handoff](../../../docs/netlist-diagnosis-v2-led.md)

Device-family reference: [JCET-authored BC546/BC547/BC548 datasheet, mirror](https://aitendo3.sakura.ne.jp/aitendo_data/product_img/transisitor/JCET/BC548_JCET.pdf).
The active model is a bounded development model, not a characterized
manufacturer SPICE model of the actual parts.
