# VGGT-Ω on this Mac — executed, not inferred from CUDA examples

Machine: **Apple M4, 32 GiB**, macOS arm64, Python 3.11.9, PyTorch 2.15.0.
Official source commit: `48b23c8ce72c9a8fcf987f0d7f43d8e4870759f6`.
All runs use the complete **1,143,814,185-parameter** architecture, FP32 and
`VGGTOmega(autocast=False)`. Automatic MPS→CPU fallback was disabled.
No upstream source changes, reduced model, paid API or hardware commands.

| Weights | Device | Input | Forward time | Execution |
| --- | --- | --- | ---: | --- |
| Random initialization, not trained | CPU | 2 synthetic 416×416 frames | 3.334s | Pass |
| Random initialization, not trained | MPS | 2 synthetic 416×416 frames | 3.036s | Pass |
| Random initialization, not trained | MPS | 6 synthetic 512×512 frames | 7.527s | Pass |
| Official trained 416 reproduction | MPS | 1 cleaned local photo, 416×320 | 1.760s | Pass |
| Official trained 416 reproduction | CPU | 1 cleaned local photo, 416×320 | 1.014s | Pass |

These are first-run compatibility checks, **not** speed benchmarks or estimates
of breadboard reconstruction accuracy. The six-frame test establishes capacity
for that synthetic workload; it is not a test of six real views of a circuit.
The MPS driver reported 6,619,414,528 bytes allocated after the six-frame forward
pass; that is **not peak GPU memory** and should not be added to process RSS on
unified memory hardware.

## Official weights and access

Anonymous access first returned 401, then the existing authenticated account
returned 403. The user applied for access directly. A subsequent authenticated
HEAD returned an approved signed download (302). No access gate was bypassed.
The official Xet transport stalled without receiving checkpoint bytes. Official
HTTP transfer worked; bounded byte ranges were used, with the assembled SHA-256
checked against the official linked ETag. Partial transport attempts remain in
the private local logs; no signed URLs or credentials are published.

Checkpoint: `vggt_omega_1b_416_reproduce.pt`, **4,576,703,488 bytes**.
Hugging Face revision: `1041e80fc0e911235d3426b0a3d9a81075111a53`.
SHA-256: `e900833330eb0e570e10543e6108d0dd704fa7c8dbc32738a645987875298896`.
[Download verification](checkpoint.json). Model weights are not redistributed.

Strict state-dict loading succeeded, all predicted camera/depth/confidence
tensors were finite, and pose-to-camera conversion succeeded. The actual tensor
devices are recorded in each trained result. The input was the cleaned, local
IMG_8887 development photo. Neither the photo nor the private depth arrays were
sent to a model service or committed. Other historical photos were **not** fused:
their wiring states have not been shown to match.

CPU/MPS depth outputs agreed to a relative RMS difference of `8.63e-7` on this
same image; every depth value was positive and both inferred focal lengths were
positive. [Full device comparison](device-comparison.json). This checks device
consistency, not agreement with physical ground truth.

[CPU trained record](cpu-pretrained-photo-first.json) ·
[MPS trained record](mps-pretrained-photo-first.json) ·
[Six-frame untrained capacity record](mps-six-512-untrained-first.json) ·
[Software and preservation checks](verification.json).

## What this establishes

The tested VGGT-Ω camera/depth model **runs on this M4 Mac with trained weights**.
CUDA-only example code does not establish a CUDA-only model. The official
constructor permits disabling CUDA autocast; CPU and MPS execute the tested
forward path in FP32. The optional text-alignment branch, training and demo
stack were not evaluated.

What remains to test is whether multiple real views of the **same wiring state**
improve camera alignment or endpoint matching over the high-resolution planar
grid. Finite depth is not ground truth, millimetre accuracy, a visible hidden pin,
or an electrical connection. The 416 reproduction checkpoint is the official
comparison reference; the recommended 512 application checkpoint is a distinct
weight release and was not tested here.

## Reproduce

Get official model access directly from [Meta's model page](https://huggingface.co/facebook/VGGT-Omega).
Clone [the official repository](https://github.com/facebookresearch/vggt-omega)
into `.tools/photo-reconstruction/vggt-omega` and check out the source commit above.
Download the pinned checkpoint through your own approved Hugging Face account,
verify the SHA-256 above, and keep it under `.tools/`. Install the separate
[locked environment](../../../experiments/photo_reconstruction/requirements-macos.lock).
From the BenchMate root, use a **new** result path:

```sh
PYTHONPATH=src PYTORCH_ENABLE_MPS_FALLBACK=0 .tools/photo-reconstruction/venv/bin/python experiments/photo_reconstruction/vggt_probe.py --source .tools/photo-reconstruction/vggt-omega --device mps --resolution 416 --checkpoint .tools/photo-reconstruction/checkpoints/vggt-reproduction/vggt_omega_1b_416_reproduce.pt --image .private/photo-bench/library-20261102/photo-1dfbb3d87b87add3/master.png --prediction-dir .private/photo-bench/vggt-new-arrays --output .private/photo-bench/vggt-new.json
```

The public repository deliberately does not contain that private input. For an
execution-only synthetic probe, omit `--image` and `--prediction-dir` and choose
`--frames 2`. Use `--device cpu` for a separate CPU run. Preserve failures and
earlier records rather than overwriting them.
