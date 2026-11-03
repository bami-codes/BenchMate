# One board photograph, deterministic RAW conversion and independent crop reads

The operator chose one board photograph per assembly instead of separate close-up
photographs. Case 01's supplied ProRAW image was visually reviewed at full pixel
resolution before any model call. Both component bodies and their visible
markings are present without occlusion. It is dark; this is sufficient to attempt
reading, not a guarantee that a model will read every band or printed character.

Keep the same framing method, camera/lens, support, lighting and capture settings
for later cases. Keep the component markings facing the camera. A failed or
unreadable result remains failed/unreadable; do not tune processing after seeing
that result. No separate close-up is required by this version of the workflow.

`scripts/photo_raw.py` fixes rawpy 0.27.1 / LibRaw 0.22.1 / Pillow 12.3.0:

- As-shot camera white balance; automatic WB and automatic brightening disabled.
- Brightness multiplier 1.0; adaptive maximum adjustment disabled.
- sRGB output primaries, eight bits per channel, fixed gamma pair 2.222/4.5.
- Stored orientation applied by LibRaw; no perspective/white-plastic color fit.
- Full-resolution unsharpened derivative retained. Mild sharpening is fixed at
  UnsharpMask radius 0.8 px, amount 50%, threshold 3; no local/manual adjustment.

This records decoder settings, not an assertion that computational ProRAW is
unprocessed sensor data or that the colors have been calibrated. In this file
LibRaw reports an RGB stack and camera coefficients [1,1,1,0]; these are retained
as reported. No independent neutral-target color calibration is claimed.

Both RGB PNG derivatives are created from new pixel buffers with only IHDR,
IDAT and IEND chunks. EXIF/GPS, file names and other source metadata are not
copied. The original DNG stays in ignored `pictures/`; only its SHA-256 is in
the conversion record. `conversion.json` records settings, library versions,
converter digest and derivative hashes; `photo-binding.json` binds them to the
completed physical run. Neither record is an input to a model.

SAM gets the entire metadata-free image at at most 1600 px on its long edge.
It receives only the image and concept, first `resistor`, then `capacitor`.
The exact returned masks and all failures/misses are retained. Crop coordinates
are mapped back to the full 3024x4032 converted image with fixed 15% padding;
Spark reads those full-resolution crops in separate fresh contexts, each at
most 1600 px. The first eight returned crop records are eligible; no quality
selection. The original photograph is never replaced by the manual quality
preview used to assess whether the capture method was usable.

Before each stage report the call count. This photograph permits two SAM calls
and at most eight crop-vision calls; the actual crop-read count is disclosed
after segmentation. Actual usage is retained. Diagnosis, nominal values,
operator truth, case mapping, filenames and capture metadata are excluded.
R/C null readings remain `unreadable`; original markings and ambiguities remain
unchanged. Visual IDs do not automatically identify schematic IDs or wiring.

After independent photo results are preserved, the operator restores the
assembly and 01-R01 uses the same intended schematic and a fresh Spark context.
No photographic or prior diagnostic result is supplied to the restored run.
