#!/usr/bin/env python3
"""Sound design + final mux: out/film.mp4 (video only) + out/sfx.json + narration clips → out/benchmate.mp4 (and .srt).

  python3 audio.py                      # full mix → out/benchmate.mp4; prints the ffprobe duration check and RMS/peak dBFS
  python3 audio.py --preview 20 40      # only seconds 20–40 of the mix → out/preview.wav (no mux)
  python3 audio.py --no-sfx             # bed + narration only
  python3 audio.py --check              # just re-measure an existing out/benchmate.mp4

Inputs: out/film.mp4 (duration read with ffprobe), out/sfx.json ([{"t": s, "kind": name}, ...] from the film stage),
out/scenes.json ([{"id": "s1", "start": s, "seconds": len}, ...]), optional voice/sN.mp3|wav|m4a placed at start + 0.4,
optional out/captions.json (→ out/benchmate.srt, as mux.py did). Everything is synthesized here with numpy at 48 kHz
stereo: a quiet chord bed (peak −26 dBFS, ducked 6 dB under narration), short effects per event kind (peak −18…−22 dBFS,
`seal` −12), narration levelled to about −16 dBFS, a soft limiter at −1 dBFS. The audio is cut to the video length.
"""
import argparse, json, pathlib, subprocess, sys, wave
import numpy as np

V = pathlib.Path(__file__).resolve().parent; OUT, VO = V / 'out', V / 'voice'
SR = 48000
KINDS = ('type', 'forecast', 'sweep', 'needle_red', 'crossout', 'pass', 'commit', 'seal', 'card', 'end')


def db(x): return 10 ** (x / 20)
def dbfs(x): return 20 * np.log10(max(float(x), 1e-12))
def probe(path, what='format=duration', sel=None):
    cmd = ['ffprobe', '-v', 'error'] + (['-select_streams', sel] if sel else []) + ['-show_entries', what, '-of', 'csv=p=0', str(path)]
    return float(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().split('\n')[0] or 'nan')


# ---------- small synthesis helpers (mono float arrays) ----------
def tt(ms): return np.arange(int(SR * ms / 1000)) / SR
def fade(y, ms=5):
    n = min(int(SR * ms / 1000), len(y) // 2); r = np.linspace(0, 1, n)
    if n: y[:n] *= r; y[-n:] *= r[::-1]
    return y
def expd(t, tau): return np.exp(-t / tau)
def peak_to(y, dbfs_peak):
    p = np.max(np.abs(y)) if len(y) else 0
    return y * (db(dbfs_peak) / p) if p > 0 else y
def bandpass(x, lo, hi, soft=0.5):
    """FFT band-pass with smooth (cosine) edges; `soft` is the edge width as a fraction of the edge frequency."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    def edge(f0, up):
        w = max(f0 * soft, 1.0); z = np.clip((f - f0) / w + 0.5, 0, 1); z = 0.5 - 0.5 * np.cos(np.pi * z)
        return z if up else 1 - z
    return np.fft.irfft(X * edge(lo, True) * edge(hi, False), len(x))
def tri(f, t): return 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))


def sfx(kind, rng):
    """One effect as (mono array, offset seconds before the event time at which the array starts)."""
    if kind == 'type':                      # 8 ms noise burst, band-passed by a decaying 3.4 kHz sine
        t = tt(8); y = rng.standard_normal(len(t)) * np.sin(2 * np.pi * 3400 * t) * expd(t, 0.0025)
        return peak_to(fade(y, 1.5), -24), 0
    if kind == 'forecast':                  # faint rising two-tone chime 660 → 990 Hz, 120 ms
        t = tt(120); e1 = np.clip(1 - t / 0.07, 0, 1) ** 1.5; e2 = np.clip((t - 0.045) / 0.015, 0, 1) * expd(np.clip(t - 0.045, 0, 1), 0.03)
        y = np.sin(2 * np.pi * 660 * t) * e1 + np.sin(2 * np.pi * 990 * t) * e2
        return peak_to(fade(y), -22), 0
    if kind == 'sweep':                     # low filtered-noise whoosh, 350 ms, centre rising a little as it passes
        t = tt(350); env = np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 1.6
        y = bandpass(rng.standard_normal(len(t)), 180, 900) * env + 0.35 * bandpass(rng.standard_normal(len(t)), 600, 1800) * env ** 2
        return peak_to(fade(y), -22), 0
    if kind == 'needle_red':                # dull 90 Hz thud with exponential decay, 180 ms, plus a quiet click
        t = tt(180); y = np.sin(2 * np.pi * 90 * t) * expd(t, 0.045) + 0.3 * np.sin(2 * np.pi * 180 * t) * expd(t, 0.02)
        c = tt(3); y[:len(c)] += 0.25 * rng.standard_normal(len(c)) * expd(c, 0.0007)
        return peak_to(fade(y, 2), -18), 0
    if kind == 'crossout':                  # paper-tear-like ragged noise burst, 60 ms
        t = tt(60); rag = np.interp(t, np.linspace(0, 0.06, 14), rng.uniform(0.2, 1, 14)) * np.sin(np.pi * np.clip(t / 0.06, 0, 1)) ** 0.5
        y = bandpass(rng.standard_normal(len(t)), 900, 6500) * rag
        return peak_to(fade(y, 2), -20), 0
    if kind == 'pass':                      # soft bright single tone 1320 Hz, 140 ms, quick decay
        t = tt(140); y = np.sin(2 * np.pi * 1320 * t) * np.clip(t / 0.004, 0, 1) * expd(t, 0.035)
        return peak_to(fade(y, 3), -20), 0
    if kind == 'commit':                    # single soft click + very short high ping
        t = tt(90); c = tt(2); y = np.sin(2 * np.pi * 2640 * t) * np.clip((t - 0.004) / 0.003, 0, 1) * expd(np.clip(t - 0.004, 0, 1), 0.02) * 0.6
        y[:len(c)] += rng.standard_normal(len(c)) * expd(c, 0.0005)
        return peak_to(fade(y, 2), -20), 0
    if kind == 'seal':                      # anticipation swell 300 ms, then a 55 Hz impact with a slow 700 ms decay
        pre, t = tt(300), tt(700); swell = bandpass(rng.standard_normal(len(pre)), 120, 1400) * (pre / 0.3) ** 2.2 * 0.25
        hit = np.sin(2 * np.pi * 55 * t) * expd(t, 0.22) + 0.3 * np.sin(2 * np.pi * 110 * t) * expd(t, 0.09) + 0.12 * np.sin(2 * np.pi * 220 * t) * expd(t, 0.04)
        c = tt(6); hit[:len(c)] += 0.5 * bandpass(rng.standard_normal(len(c)), 300, 4000) * expd(c, 0.0015)
        hit *= np.clip(t / 0.003, 0, 1); y = np.concatenate([swell, hit]); y[-int(SR * 0.25):] *= np.linspace(1, 0, int(SR * 0.25))
        return peak_to(fade(y, 4), -12), 0.3
    if kind == 'card':                      # very quiet woody tap, triangle 220 Hz, 50 ms
        t = tt(50); y = tri(220, t) * expd(t, 0.012) * np.clip(t / 0.001, 0, 1)
        return peak_to(fade(y, 2), -24), 0
    if kind == 'end':                       # gentle resolving chord in the bed's key (A minor → A with the 9th), 3 s
        t = tt(3000); env = np.clip(t / 0.35, 0, 1) ** 2 * np.clip((3 - t) / 1.6, 0, 1) ** 1.5; y = np.zeros_like(t)
        for f, g in ((110, 1), (164.81, 0.7), (220, 0.55), (246.94, 0.35), (329.63, 0.3)):
            y += g * (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env
        return peak_to(fade(y, 8), -22), 0
    return None, 0


# ---------- bed ----------
def bed(total_s):
    """Slow warm chords: 64 bpm feel, one chord per two bars (7.5 s), 1.2 s attack / 2.5 s release, A-minor-ish, slightly
    detuned left/right. Returns stereo (n, 2) with peak −26 dBFS, faded in over 2 s and out over the last 3 s."""
    n = int(round(total_s * SR)); y = np.zeros((n, 2)); beat = 60 / 64; bar = 8 * beat
    chords = [(110, 130.81, 164.81, 220), (87.31, 110, 130.81, 164.81), (73.42, 110, 146.83, 220), (82.41, 123.47, 164.81, 196)]
    k = 0; a = 0.0
    while a < total_s:
        ch = chords[k % len(chords)]; k += 1; b = a + bar; s0, s1 = int(a * SR), min(int((b + 2.5) * SR), n)
        if s1 <= s0: break
        t = np.arange(s0, s1) / SR; tl = t - a
        env = np.clip(tl / 1.2, 0, 1) ** 2 * np.clip((b + 2.5 - t) / 2.5, 0, 1) ** 1.5
        env *= 1 + 0.05 * np.cos(2 * np.pi * tl / beat)  # gentle tremolo on the beat, for the 64 bpm feel
        for ci, side in enumerate((1 - 0.0009, 1 + 0.0009)):
            seg = np.zeros_like(t)
            for vi, f in enumerate(ch):
                fv = f * side; g = (1.0, 0.8, 0.7, 0.45)[vi]
                seg += g * (np.sin(2 * np.pi * fv * t) + 0.33 * np.sin(2 * np.pi * 2 * fv * t) + 0.08 * np.sin(2 * np.pi * 3 * fv * t)) * (1 + 0.08 * np.sin(2 * np.pi * 0.11 * t + vi))
            y[s0:s1, ci] += seg * env
        a = b
    y = peak_to(y, -26); t = np.arange(n) / SR
    return y * (np.clip(t / 2, 0, 1) * np.clip((total_s - t) / 3, 0, 1))[:, None]


# ---------- narration ----------
def decode(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(sr), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<f4').reshape(-1, 2).astype(np.float64)
def level_voice(x, target=-16):
    """Gain so that the gated RMS of the clip sits at `target` dBFS: 400 ms blocks, keeping those within 25 dB of the
    loudest block and above −70 dBFS (so pauses do not count); clamped ±24 dB."""
    m = x.mean(axis=1); blk = int(0.4 * SR); nb = len(m) // blk
    if nb == 0: return x
    p = (m[:nb * blk].reshape(nb, blk) ** 2).mean(axis=1); loud = p[(p > p.max() * db(-25) ** 2) & (p > db(-70) ** 2)]
    if not len(loud): return x
    want = target - dbfs(np.sqrt(loud.mean())); g = float(np.clip(want, -24, 24))
    if g != want: print(f'warning: narration clip needs {want:+.0f} dB to reach {target} dBFS; gain clamped to {g:+.0f} dB (check the export level)', file=sys.stderr)
    return x * db(g)
def trim_to_speech(x, sid):
    """Cut a clip 0.15 s after its last aligned sentence (voice/timings.json) with a 60 ms fade, and fade the head over 20 ms:
    the providers' tails can carry a cut breath or fricative that the levelling then amplifies."""
    tf = VO / 'timings.json'
    if not tf.exists(): return x
    sc = json.loads(tf.read_text()).get('scenes', {}).get(sid)
    if not sc or not sc.get('sentences'): return x
    end = min(len(x), int(round((sc['sentences'][-1]['end'] + 0.15) * SR))); x = x[:end].copy()
    f = min(len(x), int(0.06 * SR)); x[-f:] *= np.linspace(1, 0, f)[:, None] if x.ndim == 2 else np.linspace(1, 0, f)
    h = min(len(x), int(0.02 * SR)); x[:h] *= np.linspace(0, 1, h)[:, None] if x.ndim == 2 else np.linspace(0, 1, h)
    return x
def narration(scenes, n):
    """Mix of the voice clips at each scene's voice_at (stereo (n, 2)) and the clip spans [(a, b), ...] in seconds."""
    y = np.zeros((n, 2)); spans = []
    for sc in scenes:
        f = next((p for p in [VO / f"{sc['id']}.mp3", VO / f"{sc['id']}.wav", VO / f"{sc['id']}.m4a"] if p.exists()), None)
        if not f: continue
        x = level_voice(trim_to_speech(decode(f), sc['id'])); s0 = int(round(sc.get('voice_at', sc['start'] + 0.4) * SR)); s1 = min(s0 + len(x), n)
        if s1 <= s0: continue
        y[s0:s1] += x[:s1 - s0]; spans.append((s0 / SR, s1 / SR)); print(f"voice {f.name} at {s0 / SR:.2f}s, {len(x) / SR:.2f}s")
    return y, spans
def duck(spans, n, depth_db=-6, attack=0.08, release=0.3):
    """Gain curve: 1 outside narration, depth under it; attack/release ramps, release held 0.3 s past each clip."""
    cr = 100; g = np.zeros(int(np.ceil(n / SR * cr)) + 1)
    for a, b in spans: g[int(a * cr):int((b + release) * cr) + 1] = 1
    k = np.ones(int(attack * cr)) / int(attack * cr); g = np.convolve(g, k, mode='same'); g = np.clip(g, 0, 1)
    return np.interp(np.arange(n) / SR, np.arange(len(g)) / cr, 1 + (db(depth_db) - 1) * g)


# ---------- mix ----------
def limiter(y, ceiling_db=-1, knee=0.5):
    """Soft clamp: linear below `knee`, tanh-shaped above, never exceeding the ceiling."""
    c = db(ceiling_db); a = np.abs(y); over = a > knee
    out = y.copy(); out[over] = np.sign(y[over]) * (knee + (c - knee) * np.tanh((a[over] - knee) / (c - knee)))
    return out
def write_wav(path, y):
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
def render(total, scenes, events, with_sfx=True, seed=7):
    n = int(round(total * SR)); rng = np.random.default_rng(seed)
    voice, spans = narration(scenes, n)
    mix = bed(total) * duck(spans, n)[:, None] + voice
    if with_sfx:
        cache, used, skipped = {}, {}, {}
        for ev in events:
            kind, t0 = ev.get('kind'), float(ev.get('t', 0))
            if kind not in KINDS: skipped[kind] = skipped.get(kind, 0) + 1; continue
            if kind not in cache or kind in ('type', 'crossout'): cache[kind] = sfx(kind, rng)   # noisy ones get fresh noise each time
            y, pre = cache[kind]; s0 = int(round((t0 - pre) * SR)); a, b = max(s0, 0), min(s0 + len(y), n)
            if b <= a: continue
            mix[a:b] += y[a - s0:b - s0, None]; used[kind] = used.get(kind, 0) + 1
        print('sfx:', ', '.join(f'{k} ×{v}' for k, v in sorted(used.items())) or 'none')
        if skipped: print('sfx skipped (unknown kind):', skipped, file=sys.stderr)
    return limiter(mix), spans


def check(path):
    """Print the container / video / audio durations and the RMS + peak of the audio track (decoded to PCM)."""
    fmt, vd, ad = probe(path), probe(path, 'stream=duration', 'v:0'), probe(path, 'stream=duration', 'a:0')
    ok = max(fmt, vd, ad) - min(fmt, vd, ad) <= 0.05
    print(f'durations  container {fmt:.3f}s  video {vd:.3f}s  audio {ad:.3f}s  →', 'OK (within 0.05 s)' if ok else 'MISMATCH > 0.05 s')
    x = decode(path).mean(axis=1); blk = 2 * SR; nb = max(len(x) // blk, 1)
    win = np.sqrt((x[:nb * blk].reshape(nb, -1) ** 2).mean(axis=1)) if len(x) >= blk else np.array([np.sqrt((x ** 2).mean())])
    print(f'audio      RMS {dbfs(np.sqrt((x ** 2).mean())):.1f} dBFS  peak {dbfs(np.abs(x).max()):.1f} dBFS  '
          f'loudest 2 s window RMS {dbfs(win.max()):.1f} dBFS (at {int(win.argmax()) * 2}s)  quietest {dbfs(win.min()):.1f} dBFS')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--preview', nargs=2, type=float, metavar=('FROM', 'TO'), help='render only this window to out/preview.wav')
    ap.add_argument('--no-sfx', action='store_true', help='bed and narration only'); ap.add_argument('--check', action='store_true', help='only measure out/benchmate.mp4')
    ap.add_argument('--seed', type=int, default=7); args = ap.parse_args()
    if args.check: sys.exit(0 if check(OUT / 'benchmate.mp4') else 1)
    total = probe(OUT / 'film.mp4', 'stream=duration', 'v:0')
    if not total == total: total = probe(OUT / 'film.mp4')
    scenes = json.loads((OUT / 'scenes.json').read_text()) if (OUT / 'scenes.json').exists() else []
    events = json.loads((OUT / 'sfx.json').read_text()) if (OUT / 'sfx.json').exists() else []
    if not events: print('no out/sfx.json events', file=sys.stderr)
    print(f'film {total:.3f}s, {len(scenes)} scenes, {len(events)} events')
    mix, spans = render(total, scenes, events, with_sfx=not args.no_sfx, seed=args.seed)
    print(f'mix peak {dbfs(np.abs(mix).max()):.1f} dBFS, narration {len(spans)} clips')
    if args.preview:
        a, b = sorted(args.preview); a, b = int(max(a, 0) * SR), int(min(b, total) * SR)
        write_wav(OUT / 'preview.wav', mix[a:b]); print('wrote', OUT / 'preview.wav', f'{(b - a) / SR:.1f}s'); return
    mixf = OUT / '_mix.wav'; write_wav(mixf, mix)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(OUT / 'film.mp4'), '-i', str(mixf), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-t', f'{total:.3f}', '-shortest', '-movflags', '+faststart', str(OUT / 'benchmate.mp4')], check=True)
    if (OUT / 'captions.json').exists():
        fmt = lambda s: f'{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int((s % 1) * 1000):03d}'
        caps = json.loads((OUT / 'captions.json').read_text())
        (OUT / 'benchmate.srt').write_text(''.join(f"{i + 1}\n{fmt(c['a'])} --> {fmt(c['b'])}\n{c['text']}\n\n" for i, c in enumerate(caps)))
    print('wrote', OUT / 'benchmate.mp4'); sys.exit(0 if check(OUT / 'benchmate.mp4') else 1)


if __name__ == '__main__': main()
