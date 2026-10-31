# SAM 3.1 feasibility — October 31, 2026

Current scheduling update (October 31 evening): the user authorized a bounded
one-photo API feasibility trial while physical work is unavailable. This overrides
the earlier after-B5 timing for the **trial**, not a claim of integration or quality.
No breadboard photo was found among project image files (private holdouts were
excluded); an operator-supplied path is pending. **Zero SAM calls so far.**
Do not substitute a synthetic schematic and call it a breadboard-photo test.
Do not install a local GPU stack for this one-hour-limited probe.

| Question | Observed answer |
| --- | --- |
| Official API? | Yes. `sam-3.1` uses `POST https://api.meta.ai/v1/responses`, with an image and a short noun-phrase prompt. Streaming to completion is documented. |
| Official Mac local path? | The official repository requires Python 3.12+, PyTorch and CUDA. This workspace is arm64 macOS, Python 3.11.9, with no torch installed. No documented native Mac path was validated. This does not prove that a third-party port is impossible. |
| Can “capacitor” find exactly the desired part? | **Unknown.** The API returns all matching instances, possibly none. No breadboard image was supplied or sent in this check. A box prompt can target a reviewed location; a text match alone does not identify a circuit node. |
| Measured latency / mask quality? | **Not measured.** API availability is not an account-access, latency or quality result. |
| Integration effort? | Planning estimate: a bounded one-image probe should fit a 30-minute session once the image and authorization are ready. A production overlay requires additional mask parsing, coordinate checks and UI work; no time guarantee. |

Prospective probe, not yet executed: sanitize one approved breadboard photo,
retain its hash and the exact prompt, send one `capacitor` request, retain every
returned mask and zero-match/failure result, time the complete request and
visually inspect whether the intended component is correctly separated. Do not
select only a favorable mask and describe the whole request as correct.

If Spark supplies a box, convert its normalized coordinates to the actual
sanitized image's pixels before a later SAM box-prompt request. The returned
overlay is a visual pointer only. It cannot validate continuity, component
value, fault causation or the safety of a repair.

Sources checked October 31:
- [Meta: segmenting with prompts](https://dev.meta.ai/docs/sam/segmenting)
- [Official installation prerequisites](https://github.com/facebookresearch/sam3#installation)
- [SAM 3.1 model card](https://huggingface.co/facebook/sam3.1)

## Follow-up evidence from Spark vision (still zero SAM calls)

The [three actual schematic reads](../examples/vision-spark/2026-10-31/20261031T060049-13a656638d/README.md)
matched visible values/connections but returned imprecise component boxes. In
image 03 the C1 box excludes the lower capacitor plate. A Spark-generated box
must therefore be reviewed before any SAM targeting; this synthetic-schematic
observation does not establish SAM quality or real-breadboard localization.
