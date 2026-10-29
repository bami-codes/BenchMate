# Bounded Spark controller for a physical RC fixture

The adapter is implemented and tested; its first physical execution is pending.
It uses the existing Meta transport with at most eight requests, fixed serial
commands, boot continuity and raw REF/path/timing guards. The existing agent,
repair and discovery CLI commands retain their synthetic-only behavior.

Spark first inspects the declared nominal 10 kohm / 1 uF design and chooses a
new unloaded step. Only that trace fits a single tau, with gain fixed at one
and an origin from three separate stationary HOLD blocks. Nominal, R-changed
and C-changed point alternatives are then frozen. The model receives measured
summaries and these alternatives; fixture identity, assembly truth and prior
specimen results remain outside its input.

Spark may choose an OUT-to-REF 9.99 kohm load or an uninformative unloaded
repeat within the fixed budget. A load request pauses the process, saves exact
operator instructions and waits for a matching explicit USB-off wiring and
reconnection reply. No timeout is approval. The new boot receives one ARM;
an unexpected boot on an unchanged fixture stops the run without re-arming.

The loaded step compares the frozen point models. A unique supported model
still requires a new 0.15 V, 5 Hz sine check. Both its whole waveform and every
region must meet the unchanged 9 mV allowance. Its parameters never use loaded
or reserved OUT samples. Each waveform has a separately acquired HOLD origin;
the predicted curve is conditional on measured IN, not an absolute voltage
waveform known before acquisition. Failed or ambiguous checks require abstention.

The usual three-waveform path retains 7,680 frames: 1,536 waveform samples and
6,144 stationary guard/origin frames. Firmware sine warmup is separately counted
and is not stored as measurement data. Every capture attempt is counted; no
automatic retry, A4 servo, firmware update or physical repair is included.

## Invocation and manual pause

`scripts/physical_spark_rc.py` requires the frozen protocol path, an initial
operator-report JSON and the preceding boot ID. The initial report must identify
the unloaded fixture and explicitly confirm USB-off wiring and reconnection.
Run it only after the coordinating session has obtained those confirmations.

A live load request writes `operator-request.json` in the run directory. Its
response filename includes a unique request ID. The coordinating session relays
the physical instruction to the user and writes the actual reply with matching
`request_id`, `fixture`, `USB_off_wiring_confirmed`, `USB_connected` and `verbatim`.
No approval is generated automatically. The provider session stays in memory;
API credentials and encrypted reasoning are never saved in the run record.

## Validation and limits

113 relevant tests passed, including independent analytic R/C fake observations,
failed reserved checks, identical frozen models across phases, synthetic/replay
rejection, command-menu restrictions, real byte-protocol fake-device integration,
missing operator confirmation, changed boots, bad REF and transport timeouts.
These tests made no real serial or API calls. The end-to-end fake tool loop also
checked that an operator-only assembly marker never entered model tool results.

This first adapter targets known passive RC development fixtures and provisional
channel maps. It does not establish blinded diagnostic accuracy, calibrated
uncertainty, absolute-voltage accuracy, full D2 acceptance or physical repair.
