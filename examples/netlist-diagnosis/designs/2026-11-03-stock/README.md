# Intended schematics, stock revision (2026-11-03)

The 1% resistor kit on hand has these 30 values and **no 22 kΩ**:
10, 22, 47, 100, 150, 200, 220, 270, 330, 470, 510, 680 Ω;
1, 2, 2.2, 3.3, 4.7, 5.1, 6.8, 10, 20, 47, 51, 68, 100, 220, 300, 470, 680 kΩ; 1 MΩ.

`design-02` and `design-04` therefore use **R2 = 20 kΩ** instead of 22 kΩ.
Nothing else changed. Rendered with `make_design.py` in this folder (Playwright
Chromium, DejaVu Sans). The same renderer reproduced the 2026-11-02 PNGs
pixel-identically before the edit. Against those originals, the only pixel
difference is the R2 digit region (`2` → `0`).

The 2026-11-02 files in `../2026-11-02/` are unchanged and stay bound to the
records that already hash them.
