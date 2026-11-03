# Primary REF guard A3, prospective version 1

The operator selected this route before another QA or official attempt. F01
and F02 remain failed/countable, with their original A4 guards and records.
No old result is reclassified. A4's later sine mean changes while A3 remains
comparatively steady. A3 was deliberately wired to REF via A23–A45 earlier;
it is not the old DRIVE channel in this hardware revision.

For this version, A3 is the primary REF channel. Preserve the original 3 mV
raw block-mean span limit, 0.15 V REF sample envelope, A1/A2/A3 raw-rail limits,
HOLD mean/sample/spread limits and HOLD stationarity. A1/A2 signal protection,
byte protocol validation, ADC readback, timing checks and REF park checks are
unchanged. A4 is excluded from stopping predicates, retained in every raw
frame, and explicitly reported as auxiliary with its former rail/envelope/span
flags and A4−A3 mean difference. Do not call all four channels qualified.

There is no regression, fitted k, reference subtraction, offset adaptation,
sample deletion, threshold relaxation, firmware upload or wiring change.
The original 80 engine/adapter sources and the 82-source F02 orchestration
remain byte-for-byte preserved. A new guard mixin is used by new adapters.
Model fitting, experiment menu, scoring and independent prospective prediction
requirements are unaffected. All future captures retain the new named guard.

The actual compatible board previously measured 5.19–5.20 kohm from A4 to 5V
in both probe polarities, with its external A4 lead removed and USB off.
An earlier DMM observation of a roughly 0.53 V drop across the old A4 0.994 kohm
series resistor supports a pull-up-like path. A roughly 0.63 mA current and
several ohms of changing contact resistance can explain a few mV of sense
error. This is a supported mechanism, not proof of a particular board resistor,
constant powered current, or the dynamic cause. The official Minima schematic
marks I2C R1/R2 pullups **not mounted**; actual compatible-board assembly was
not identified: https://docs.arduino.cc/resources/schematics/ABX00080-schematics.pdf

Before F03: offline guard-only replay must still reject F01's A3 excursion;
synthetic REF/IN/OUT fault injections must reject actual primary faults. F02's
new A3 replay is a diagnostic check of the proposed rule, never a retrospective
diagnosis pass. Then run one new unloaded waveform QA on the present, already
armed boot: 3 HOLDs plus 7 fixed waveforms and their return HOLDs, 17 blocks /
8704 frames, at most 37 serial commands, no ARM or retry. Spark 0 calls, $0.
Observe the expected REF state, wait 10 s, then recheck it before capture.
The waveforms are the preserved original-guard QA set, independent of Spark.

QA OUT is not fitted or supplied to a later diagnosis. This QA qualifies the
new primary-channel guards only in its observed configuration; it does not
identify the cause or prove absolute voltage accuracy. After PASS, preregister
F03 and its effective guard protocol before a fresh Spark context. Any QA
failure stops immediately, with choices presented before another measurement.
