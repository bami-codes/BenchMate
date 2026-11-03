# Case02 restored diagnosis after QA: consistent, restored photo still pending

Parent: `examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/`.
Completed diagnostic child: `diagnosis-restored/20261103T182908-a2c37df9e3/`.
The parent awaits its new restored photograph and is not a completed repair pair.
The original failures, preceding restored failure and completed standalone QA
remain unchanged; no first-attempt selection is replaced.

Native Spark verdict: **consistent**. Display caption:
**No mismatch in the tests Spark chose**. Nominal and all four families that
change one R/C value at a time remain compatible with the accepted checks. This is bounded
terminal consistency, not unique parameters, proof every component is correct,
or a confirmed cause/repair of the earlier REF instability. Native
`physical_repair_demonstrated:false` is preserved. Operator restoration is retained
separately and an actual restored-state photo/group record remains outstanding.

Fresh-context Spark selected the exact native actions below. No prior result,
isolated values or QA waveform was passed to this diagnostic model.

| Training action | Nominal whole RMS mV | Worst region mV | Passed |
|---|---:|---:|---|
| unloaded_step_large,+/-0.5V | 4.848551 | 7.280184 | yes |
| loaded_step_small,+/-0.2V | 2.232476 | 3.620328 | yes |
| loaded_sine_5hz_small,0.15V | 0.780195 | 1.128241 | yes |

Terminal prediction SHA-256
`faf45cef89ec6cca3e71d8939dd858eb568252a7c3b171fe7423dd111d8a8b7d`
was remotely published before either reserved capture in
`5f55271d65ea0d235b4040416e60198cbd64ebd8`. No holdout refit:

| Reserved input | Nominal whole RMS mV | Worst region mV | Passed |
|---|---:|---:|---|
| unloaded +/-0.35V step | 3.420886 | 5.912490 | yes |
| unloaded5Hz,0.65V sine | 2.675686 | 3.748481 | yes |

All25 original guard blocks passed, retaining12,800 raw frames. A3 raw3mV,
auxiliary A4 role, independent origins,9mV whole/regional limits and all107
frozen engine/firmware sources remain. The final output was confirmed parked at
REF; the serial controller is closed. Last boot:
`0b9429bc77088ec5da04aae4d4511cfb`. No new photo/SAM/binding stage has run.

Actual diagnostic usage: **6 Spark,0SAM,estimated$0.05312755**, not the$6 SDK
reservation. Case02 including failed attempts/reading/photo history:
**28 Spark,1SAM,estimated$0.32065000**. Whole reading cohort:
**64 Spark,2SAM,estimated$0.63100110**.

Next stage: USB off, preserve the restored105/104 specimen and unloaded wiring,
capture one new whole-board photo. Existing fixed RAW conversion and metadata
removal are reused. Planned calls **1 SAM +1 Spark binding**, estimated$0.016–0.03
depending on tokens. No separate close-up, vision value reader or repeated DMM
reading is required. The replaced105 means the earlier474 photograph cannot be
labelled a new restored-state capture. Nullable-v2 and honest unresolved parallel
candidate-group semantics remain. Standing necessary-call approval applies.

Native diagnostic standard-library audit:

```text
PASS events=235 forecasts=4 measurements=5 order_checks=19 prediction_files=1 run_status=run_completed head_sha256=74f64eef2be804bdaa0ab1ed8e2df7bcb6154fc95ff22e7f7779574a98260de6 scope=internal_integrity+recorded_order creation_time=unproven
```

Pending-photo parent core audit (includes original fault/photo pair and completed
unordered reading; additional preceding-failure/QA references are separately
audited and retained in the context, not counted as new scored measurements):

```text
PASS events=558 forecasts=10 measurements=12 order_checks=43 prediction_files=4 run_status=cohort_state head_sha256=bc7d4b8f1e74b8baee12fa4c86c6c4f3c345a8733bb29dbcfcdc162da61f86f6 scope=internal_integrity+recorded_order creation_time=unproven
```

These checks concern retained integrity/recorded order, not original creation
time, physical truth, operator authenticity or stable behavior on future boots.
