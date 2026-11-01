# B5 variant design — reviewed v1.1

Design: [design.json](../examples/b5-variants/2026-11-02/design.json).
Frozen before any physical B5 run or final variant evaluation. The grid is the
original D1–D8, L1–L2 and G1–G3; later V1–V4 remain separate. Three selection
noise repetitions, fifteen alternative families, three generic fitting starts.
The true circuit gets no true starting values. Training only fits parameters.

## Review changes before any results

- Any failed alternative fit makes distinguishability unresolved. It never
  counts as a rejected alternative. This fixes an exclusion loophole in v1.
- Check the actual unchanged single-start session gate as well as multistart
  fits; a selector must not assume a gate the agent cannot open.
- D8 is antiparallel, not anti-series: the original circuit connections stay.
- Wider-response scoring uses the same noiseless measured input and delays as
  the generated output. Command forecasts remain separately labelled.
- The widest sine is 0.85 V, inside the existing envelope even after the allowed
  80 mV reference shift. Three extra inputs are unseen in the session, not two.
- Random streams are keyed by condition, so action order cannot change another
  arm's observations. Selection and evaluation streams stay separate.
- New implementation lives outside src/benchmate. It may be built overnight;
  final variant evaluation still waits until physical B5 has been attempted.
- Empty primary sets, incomplete selection and all fit failures are reported.
  No criterion is relaxed to create a headline success rate.

## Interpretation

Report performance on the circuits selected by the registered rule, under the
specified alternatives, noise and budget. No unique topology/parts claim.
All thirteen variants remain visible, including exclusions. Two Spark runs per
non-control variant are not independent circuits. The three gate controls each
have one Spark run: 23 runs, at most 184 HTTP requests including recovery.

The engine-only arm is a restricted starting point. The oracle library receives
all ten answer structures and is a disclosed strong comparator. No LLM advantage
is assumed. Actual hypothesis-gate behaviour and unneeded diode proposals are
reported separately from predictive validity. The video cutoff is November 3,
09:00 KST; physical success is never assumed by a fallback script.
