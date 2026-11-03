# Operator-requested photo follow-up: two calls, fifteen minutes

The operator explicitly amended the attempt-1 processing policy after its
unreadable results: one final OpenCV attempt, then restoration and 01-R01
regardless of the photo outcome. The first masks, false positive and null
readings stay intact. This is a follow-up, not a replacement or a claim that
these transformations preceded the first result.

Time box: 2026-11-03 20:22:08–20:37:08 KST. New script
`scripts/photo_cv_followup.py` uses pinned OpenCV 4.12.0, numpy 2.2.6 and the
already stripped, fixed-conversion PNG. It makes no hardware call.

The settings and two resulting inputs are committed/pushed before any new
vision request:

- Reference region: observer-defined whole-board ROI [0.14,0.30,0.89,0.72] in
  full-image normalized coordinates. Within it, saturation <60 and brightness
  at/above its 60th percentile select bright neutral plastic. Channel means are
  scaled to their common mean; measured means/gains and reference mask remain.
- Blue mask: OpenCV HSV [90,70,30] through [135,255,255], restricted to that
  board ROI, closing 7x7 and opening 3x3. Keep every contour's selection data.
  Choose the largest contour with area >=2000 px, aspect 0.6–1.8, fill >=0.45.
  It selects the visible box body in this image, without consulting values.
  This crop is OpenCV-derived, not a SAM success.
- Other crop: existing first SAM resistor box mapped to the full image, no
  padding. The selected blue crop has 5% padding.
- Per crop: CLAHE only on Lab L, clip limit 2, tile grid 8x8; cubic enlargement
  exactly 3x. The actual inputs are 1371x342 and 1218x972. No additional detail
  or color calibration is claimed by enlargement/neutralization.

Both inputs have only RGB PNG pixel chunks. Each gets one fresh-context Spark
request, image only plus the unchanged generic assembly-photo prompt, with no
component type hint, nominal value, diagnosis, SAM label or selection record.
Raw tool arguments, nulls and ambiguities remain unchanged. No retry. Estimated
combined new cost $0.01–0.08; actual usage is recorded afterward. Read-start
marker prevents accidentally replaying the stage; the deadline is checked before
each request. There is no third request to improve a disappointing result.

After the two readings, or an exhausted time box, finish photo work and ask the
operator to restore the series path with USB off. Register 01-R01 only after its
restoration confirmation and a fresh unarmed PING. Same A3 guard, unchanged
numerical rules and a fresh Spark diagnosis context; photos and prior outcomes
are excluded.
