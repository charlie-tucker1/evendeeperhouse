# deephouse

Search-based DJ transition engine for deep / melodic / tech house. Stockfish first
(hand-crafted eval + deep search), AlphaGo later (learned critic on mined pro
transitions, expert iteration).

Read in order:

1. `NORTHSTAR.md` — mission, theory, invariants, roadmap. *How* to build.
2. `deephouse_ultracode_directive_v1.md` — phases, gates, schemas, algorithms. *What* to build next.

## Status

**Session 1 (Phase 0, P0.1–P0.3) — complete.**

- `ingest` — decode anything → canonical 44.1 kHz/16-bit FLAC, SHA-1 identity, registry.
- `analyze` — constant-tempo grid fit: tracker → RANSAC-lite linear fit → band folding →
  low-band phase check (the kick is the beat) → time-domain sub-hop phase refinement →
  downbeat vote. Synthetic tests: BPM within 0.004, beat0 within 1.3 ms, downbeat exact.
- `griddoctor` — click-overlay WAV + 3-panel diagnostic PNG + human override into the sidecar.
- `selftest` — end-to-end on synthetic house tracks with known ground truth.

**Session 1b (P0.5, P0.6, P0.8) — complete.**

- `features` — beat-synchronous `.npz` cache (log-mel, RMS, onset, chroma; per stem when cached).
  Chroma is stem-aware / HPSS-hardened so kicks don't vote on key.
- `groove` — the micro-timing layer (`docs/GROOVE.md`): per-16th micro-timing template and hit
  strength in low/mid/high bands, swing %, kick transient, bass and hat patterns, sidechain pump
  depth/release; plus pairwise `groove_compat` features for L1. Synthetic: swing within 0.05 ms,
  pump within ~1 dB.
- `key` — Krumhansl–Schmuckler on cached chroma → Camelot (essentia `edma` preferred on the box).

**Session 1c (P0.7, Phase 1, Phase 2 v0) — complete.**

- `structure` — sections (SSM + Foote novelty + low-band change), phrase phase, labels, cue points.
- grid hardening — real RANSAC (breakdown-proof), kick-ness confidence (tracker-independent).
- `render` — the pure-function simulator (`render/engine.py`): sample-exact alignment on A's
  master clock, stems path (bass swap, vocal duck, HPF entry sweep) or LR4 bands path, program-gain
  match, master. Determinism + golden hash, bit-exact null test, B's kicks on A's grid within 1 ms.
- `next` — search v0: enumerate (B, cues, recipe) → L0 gates → vectorised beat-domain L1 with the
  groove-compat features → ranked report; `--render` renders the top-k different transitions.
- `listen` — ratings to `ratings.jsonl` (the future critic's labels).

Measured on synthetic material: analyze ≈ 8–11 s per 2-min track (CPU, librosa tracker), render ≈ 5 s per
80-bar transition, L1 ≈ 3.5–5k triples/s.

Next on the box: P0.4 stems (demucs), real-track griddoctor pass, G1/G2 by ear, then P2.3 L2 render features
and P2.4 one-ply look-ahead.

## Setup (Fedora / RTX 5070 box)

```bash
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev,render]"
# GPU / heavy analysis extras (beat_this, essentia, demucs, CLAP):
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130
uv pip install -e ".[analysis]"
sudo dnf install ffmpeg rubberband
```

## Use

```bash
deephouse selftest                       # synthetic end-to-end; must print "selftest OK"
deephouse ingest ~/music/house --kind track
deephouse ingest ~/music/sets  --kind set
deephouse analyze                        # grid + features + groove + key for every track
deephouse analyze --stages grid          # or a subset; every stage is idempotent
deephouse groove <id>                    # micro-timing table, swing, pump, patterns
deephouse list
deephouse griddoctor <sha1-prefix|filename>       # writes griddoctor_out/<id>/click.wav + grid.png
deephouse griddoctor <id> --downbeat-shift 2      # fix a downbeat by ear
deephouse griddoctor <id> --accept                # mark reviewed
deephouse structure <id>                 # sections + cue points
deephouse render A B --cue-out 48 --cue-in 8 --recipe all     # 16 recipes → renders/<run>/
deephouse next A --k 5 --render          # search the library from seed A, render the top 5
deephouse listen renders/<run>           # rate them 1–5 (+tags) → ratings.jsonl
```

Listen to `click.wav`: clicks (1 kHz) must sit on the kicks, accents (1.5 kHz) on the 1.
Look at `grid.png`: red fold curve rises sharply at 0 ms; residual panel is flat (no drift).

## Tests

```bash
pytest          # synthetic click-track grid recovery, exhaustive Camelot wheel
ruff check .
```

## Layout

```
deephouse.yaml              config (paths, genre band, grid params, camelot policy)
src/deephouse/
  config.py  ingest.py  audio.py  synth.py  cli.py
  analysis/  grid.py trackers.py griddoctor.py store.py analyze.py camelot.py
             features.py groove.py key.py sections.py
  render/    recipe.py dsp.py engine.py io.py
  search/    engine.py
  critic/ mine/                      (later phases)
docs/GROOVE.md              the micro-timing layer: why, what is measured, what it enables
cache/analysis/{sha1}.json  per-track sidecar (grid, key, sections, cues; human overrides)
library/canonical/{sha1}.flac
bench/BENCH.md
```
