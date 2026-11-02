# Local photo reconstruction environment

This environment prepares the crowded-board photo workflow without changing the
physical bench environment. It does not open serial ports or call a paid API.
The product's next step is per-photo board registration and terminal candidates;
photo reconstruction and electrical fault diagnosis are not implemented yet.

## Install separately

Run from the repository root. `requirements-macos.lock` records the installed
Python 3.11 / Apple Silicon environment, rather than changing `pyproject.toml`
runtime dependencies or the existing `.venv`.

```sh
uv venv --python .venv/bin/python .tools/photo-reconstruction/venv
uv pip install --python .tools/photo-reconstruction/venv/bin/python -r experiments/photo_reconstruction/requirements-macos.lock
```

CoTracker source and weights are ignored local downloads, not vendored code:

```sh
git clone https://github.com/facebookresearch/co-tracker.git .tools/photo-reconstruction/co-tracker
git -C .tools/photo-reconstruction/co-tracker checkout 82e02e8029753ad4ef13cf06be7f4fc5facdda4d
```

Official checkpoint: [scaled_offline.pth](https://huggingface.co/facebook/cotracker3/resolve/main/scaled_offline.pth).
Downloaded SHA-256: `2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834`
(101,890,938 bytes). Save it as
`.tools/photo-reconstruction/checkpoints/scaled_offline.pth` and verify the hash
before loading. The probe uses `torch.load(..., weights_only=True)`.

## Prepare and inspect existing photos

```sh
PYTHONPATH=src .tools/photo-reconstruction/venv/bin/python -m benchmate.photo_bench prepare --source pictures --output .private/photo-bench/library-new
PYTHONPATH=src .tools/photo-reconstruction/venv/bin/python -m benchmate.photo_bench serve --library .private/photo-bench/library-new --port 8768
```

Open `http://127.0.0.1:8768`. The library already prepared on 2026-11-02 is
`.private/photo-bench/library-20261102`. Reuse it with `serve`; do not overwrite
the first import. The viewer supports filename filtering, full-resolution pixel
inspection, zoom and download of manually selected point coordinates. These
points are not automatically labelled holes, terminals or electrical evidence.

The CLI only writes image outputs under `.private/photo-bench/`, which is ignored
by Git. Original photos remain untouched. The server binds to loopback, serves
cleaned images only, rejects foreign Host headers and has no mutation/API/USB
endpoints. Do not expose it with a public tunnel.

Each photo has an independent source hash, an oriented RGB master, a <=1600px
overview, and a record. The PNG validator rejects metadata chunks, profiles,
EXIF, text, animation, bad CRCs and trailing bytes. Input/master limits are 64MB
and 24 megapixels; the master PNG limit is 80MB. The HEIC path uses native macOS
`sips`, applies remaining EXIF orientation and saves fresh RGB pixels.

Crop from the full-resolution master, not its overview:

```sh
PYTHONPATH=src .tools/photo-reconstruction/venv/bin/python -m benchmate.photo_bench crop --master .private/photo-bench/library-new/PHOTO_ID/master.png --box 1000 1600 2600 2800 --output .private/photo-bench/board-crop.png
```

Bounds use **oriented-master pixel edges**, with exclusive right/bottom edges.
The sidecar records independent x/y scaling after integer output sizing and the
master hash. There is no upsampling. Raw HEIC axes, Spark coordinates and SAM
inclusive boxes must not be substituted for these coordinates.

Every imported photo starts with `state_id: null` and
`same_state_verified: false`. Similar-looking photos, filenames and capture
times do not establish unchanged wiring. Do not turn these historical images
into a synthetic "real video" for tracking evaluation.

## Local model probes

```sh
.tools/photo-reconstruction/venv/bin/python experiments/photo_reconstruction/probe_local.py environment --output .private/photo-bench/environment-new.json
PYTORCH_ENABLE_MPS_FALLBACK=0 .tools/photo-reconstruction/venv/bin/python experiments/photo_reconstruction/probe_local.py cotracker --device cpu --source .tools/photo-reconstruction/co-tracker --checkpoint .tools/photo-reconstruction/checkpoints/scaled_offline.pth --output .private/photo-bench/cotracker-cpu-new.json
PYTORCH_ENABLE_MPS_FALLBACK=0 .tools/photo-reconstruction/venv/bin/python experiments/photo_reconstruction/probe_local.py cotracker --device mps --source .tools/photo-reconstruction/co-tracker --checkpoint .tools/photo-reconstruction/checkpoints/scaled_offline.pth --output .private/photo-bench/cotracker-mps-new.json
```

The probe uses **eight synthetic translated-texture frames**, four query points,
the real pretrained offline model and its default internal resolution. Shape,
finite output, time, memory and failures are recorded. This tests execution,
not breadboard tracking accuracy. Each device gets one first attempt; results
are never overwritten. A caller should enforce a six-minute process timeout.
If native MPS fails, the CPU result remains a distinct run; no hidden fallback.

VGGT-Omega's official reproduction checkpoint returned HTTP 401 to an anonymous
HEAD request on 2026-11-02. No VGGT inference has run. Approved checkpoint
access is needed before testing CPU/MPS; this is not evidence that Mac cannot
run the model. No photos were sent to Hugging Face or the public demo.

## First results — 2026-11-02

- All **33** existing HEIC images imported; **0** failures. Original hashes
  unchanged, stripped master and overview validation passed, no same-state
  groups inferred and no user images uploaded or committed.
- Python **3.11.9**, PyTorch **2.15.0**, OpenCV **4.11.0**; CPU and MPS tensor
  checks passed. Existing physical-bench `.venv` package list is unchanged.
- **CoTracker3 pretrained inference passed on both CPU and native MPS**, with
  automatic CPU fallback disabled. Eight synthetic 192×256 frames, four queried
  points, default internal 384×512 resolution. CPU inference: **2.032s**; MPS:
  **3.171s**. These are first-run microtests, not speed or real-video accuracy
  benchmarks. No conclusion about crowded-wire performance yet.
- VGGT-Omega reproduction weights: anonymous access **401**; no inference run.
- **416 tests passed across runs, 1 skipped**. Three loopback-server tests first
  hit sandbox socket restrictions and passed when rerun with loopback permission.
  All seven new media tests also passed in the isolated photo environment.
- Local gallery initial Chrome rendering and HTTP access checks passed. Full
  interaction/mobile testing remains for the subsequent product interface.

[Machine-readable results](../../examples/photo-environment/2026-11-02/summary.json),
[CPU raw output](../../examples/photo-environment/2026-11-02/cotracker-cpu.json),
[MPS raw output](../../examples/photo-environment/2026-11-02/cotracker-mps.json).

The D01 frozen sources match the existing protocol. An older B5 protocol already
had two presentation-file hash differences at the start of this task
(`design_replay.py`, `viewer.py`); this work changed neither. Resolve the active
protocol choice before a future physical B5 run, rather than silently updating
frozen evidence. See the preservation report in the results directory.

## Next work

1. Register the 830-hole board in individual full-resolution photos. Use held-out
   visible holes to measure projection error before assigning terminals.
2. Add Spark endpoint candidates and SAM location prompts with a concrete,
   reviewed image-input/call budget. No paid requests were made in this step.
3. Evaluate CoTracker on a real, continuous video of **unchanged wiring**, when
   available. Existing stills remain useful for geometry and occlusion work.
4. Connect supported measurements to revisions of visual hypotheses, then the
   existing D01 repair flow. A mask alone does not establish a repair target.

Official references: [CoTracker](https://github.com/facebookresearch/co-tracker),
[VGGT-Omega](https://github.com/facebookresearch/vggt-omega),
[PyTorch MPS](https://docs.pytorch.org/docs/stable/notes/mps.html).
