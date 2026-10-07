# HANDOFF.md — state of deephouse as of 2026-10-07

For the Claude Code session that picks this up. Read in this order: this file → `NORTHSTAR.md` →
`deephouse_ultracode_directive_v1.md` → `README.md` → `docs/GROOVE.md` → `docs/SOURCING.md` (§1, §6, §7).

## 1. What exists and works

Seven commits on `main` (github.com/charlie-tucker1/evendeeperhouse). 81 tests pass; ruff clean.
All of it was built and tested on **synthetic** house material with known ground truth — it has
not yet touched a real record. That is the first job (§3).

| Stage | Module | Status |
|---|---|---|
| Ingest (P0.1) | `ingest.py` | done — ffmpeg → canonical 44.1k/16-bit FLAC, SHA-1 identity, registry |
| Constant-tempo grid (P0.2) | `analysis/grid.py`, `trackers.py` | done — proper RANSAC (breakdown-proof), kick-ness phase check + confidence, sub-ms time-domain phase refinement, rectified-flux downbeat vote. Synthetic: BPM < 0.004, beat0 < 1.3 ms |
| griddoctor (P0.3) | `analysis/griddoctor.py` | done — click overlay WAV + 3-panel PNG + sidecar overrides |
| Stems (P0.4) | — | **not done** (needs the GPU; demucs batch into `cache/stems/{sha1}/`) |
| Beat features (P0.5) | `analysis/features.py` | done — npz contract; stem-aware/HPSS chroma from C2 |
| Key (P0.6) | `analysis/key.py` | done — Krumhansl/Temperley on chroma → Camelot; essentia `edma` path written, untested |
| Sections + cues (P0.7) | `analysis/sections.py` | done — SSM + Foote + low-band change; exact on arranged synth |
| Groove profile (P0.8, new) | `analysis/groove.py` | done — per-16th micro-timing, swing, pump, patterns; `groove_compat` features. See `docs/GROOVE.md` |
| Renderer (P1) | `render/engine.py`, `dsp.py`, `recipe.py` | done — pure function, stems or LR4 path, equal-power bass handover, LUFS match, limiter; rubberband backend written, **untested** (varispeed fallback tested) |
| Search L0/L1 (P2.1–2.2) | `search/engine.py` | done — `deephouse next A --render`; ~4k triples/s |
| L2 render features, look-ahead (P2.3–2.4) | — | **not done** |
| Miner (P3), critic (P4) | — | not started |
| Ratings loop | `cli.py listen` | done — `ratings.jsonl` |

Conventions that everything depends on: `beat0_s` = first grid beat ≥ 0; `downbeat_offset` ∈ 0..3;
`GridFit.effective()` applies human overrides everywhere; per-beat features make L1 stretch-invariant;
the renderer is deterministic (golden-hash test in `tests/fixtures/render_golden.json` — set
`DEEPHOUSE_UPDATE_GOLDEN=1` only for intentional output changes).

## 2. Environment on the Fedora / RTX 5070 box

```bash
git clone https://github.com/charlie-tucker1/evendeeperhouse deephouse && cd deephouse
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev,render]"
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130   # cu128 if cu130 fails
uv pip install -e ".[analysis]"        # beat_this, essentia, demucs, laion-clap
sudo dnf install ffmpeg rubberband
pytest && deephouse selftest           # both must pass before anything else
deephouse version                      # should list beat_this among trackers
```

Known risks on first install: `essentia` wheel availability on Fedora/py3.11 (fallback key backend is
automatic); `beat_this` checkpoint download on first run; `pyrubberband` needs the `rubberband` CLI
on PATH (the renderer falls back to varispeed, which pitch-shifts — fine for ±6 %, but say so in meta).

## 3. Next session, in order (this is Session 2 in the directive's §12)

1. **First contact with real records.** Ingest ~20 tracks you own (`deephouse ingest <dir>`),
   `deephouse analyze`, then `deephouse griddoctor <id>` on every one and *listen* to `click.wav`.
   Expect surprises: off-beat locks, wrong downbeats, swung tracks. Record the hit rate — that is the
   G0 ear-check. If beat_this is available, compare `--stages grid` with `grid.tracker: librosa` vs
   `beat_this` on the same 20 and keep the better default. Also run `deephouse groove <id>` on one
   known-straight and one known-swung track and sanity-check `swing_pct`.
2. **Stems.** Write `analysis/stems.py` (P0.4): `demucs -n htdemucs_ft`, FLAC into
   `cache/stems/{sha1}/{bass,drums,vocals,other}.flac`, flag-gated, batch, idempotent. Kick it off
   overnight. Then `deephouse analyze --force --stages features,groove,key,structure` so stems feed
   chroma/groove/vocal cues.
3. **G1 by ear.** Two compatible tracks: `deephouse render A B --cue-out N --cue-in M --recipe all`,
   listen to all 16, note which recipe sounds like a human mix. Record `render_s_per_transition`.
4. **G2 by ear.** `deephouse next <seed> --k 5 --render`, then `deephouse listen renders/<run>`.
   Record `search_wall_min`, `L1_triples_per_s` in `bench/BENCH.md`.
5. **P2.3 L2 + P2.4 look-ahead** in `search/` (short-term LUFS std over the seam, spectral-flux
   continuity, low-end crest, chroma dissonance; one-ply `value(B)` from the pairwise L1 matrix).
6. **Ingest QA (from `docs/SOURCING.md` §4):** add an effective-bandwidth / declared-bitrate check at
   ingest (spectral rolloff vs the LAME lowpass table; Opus always shelves at 20 kHz, so don't
   misclassify it) and store `codec`, `declared_kbps`, `measured_bandwidth_hz` in the sidecar — the
   critic must never learn bitrate instead of quality (codec-matching rule, Decision 5).

## 4. Data acquisition — the plan is in `docs/SOURCING.md`

One-paragraph version: **buy the gold, pull the feeds, skip the rips.** Mixed compilations that ship
unmixed lossless sources + the continuous mix in one purchase (fabric presents via artists'
Bandcamps, Global Underground GU43–49/Select/Afterhours, Balance 031, Toolroom Ibiza, DJ-Kicks Honey
Dijon) give ~1,250 professional transitions with exact source audio *and* ~1,300 lossless in-genre
tracks — the mixing library and the miner's gold corpus in one ~$600–1,500 purchase. Podcast RSS
enclosures (Cattáneo, DHA, Crosstown, Yotto at 320 kbps; Toolroom/Defected ~192 kbps; ~3,500 in-genre
hours) beat SoundCloud rips (160 kbps AAC max for free accounts) on both quality and terms. Free
ground truth: Faraldo's Zenodo key sets (audio included), UnmixDB, mixotic, Raveform (TISMIR 2026),
EDM-CUE; MixesDB is live again with a MediaWiki API. Juno Download closed (Jun 2026); Beatsource
folded into Beatport (Mar 2026); record pools' terms forbid building databases.

**Decisions Charlie still needs to make** (§7 of the report, defaults in parentheses): lossless vs
320 for the library (lossless for anything rendered); whether to use yt-dlp at all (bounded, logged
subsets only); Digital DJ Pool (skip); SoundCloud Go+ (no); codec-match the critic (yes); gold series
order (fabric → GU → Balance → DJ-Kicks → Toolroom → Anjunadeep last); MixesDB crawl vs Raveform
(Raveform first); crowd-reaction mining (gold-as-reward first, pilot later); YouTube Data API vs
heatmap (don't build on the API's 30-day retention rules); store mix for breadth; publishing renders
(private only).

## 5. Things that will bite

- Real tracks are not constant-tempo only if they were played live or vinyl-ripped; the grid flags
  `residual` drift in griddoctor's third panel — a slope there means the track is not DAW-quantised.
- `lowband_flip: auto` only flips for the librosa tracker; with beat_this the check just flags
  (`lowband_suggests_flip`). Watch that flag on real tracks and decide the policy.
- The downbeat vote without a downbeat tracker is a heuristic (~70–80 % expected on real house);
  beat_this gives real downbeats — prefer it.
- `render` currently loads whole tracks into memory; fine for 10-minute tracks, not for 2-hour sets.
  The miner will need a windowed loader.
- The limiter is a Python loop (~2–3 s per 2-min render). Vectorise or numba it when it matters.
- Bench rows so far are synthetic-only (`bench/BENCH.md`); the first real-track rows are the gate.

## 6. Kickoff prompt for the next session

"Read HANDOFF.md, NORTHSTAR.md, deephouse_ultracode_directive_v1.md, README.md, docs/GROOVE.md,
and docs/SOURCING.md §1/§6/§7. Run `pytest` and `deephouse selftest`. Then execute HANDOFF §3 in
order: real-track griddoctor pass on ~20 owned tracks (report the ear-check hit rate and any grid
failure modes with griddoctor PNGs), `analysis/stems.py` (P0.4) with tests, G1 and G2 by ear with
bench rows, then P2.3/P2.4. Ask Charlie for the §4 decisions before any purchase or any yt-dlp use."
