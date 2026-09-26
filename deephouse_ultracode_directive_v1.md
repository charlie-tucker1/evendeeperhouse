# deephouse — Ultracode Research Directive v1.0

**Mission.** Build the Stockfish-then-AlphaGo of DJing for deep/melodic/tech house: given a currently playing track and a large local library, enumerate candidate (next-track, cue-pair, recipe) triples, cheaply score thousands, render the top ~100, rank with a critic, and surface the top-k transitions as listenable audio. End-state bar: blind A/B seams against real recorded-set transitions with house-head listeners; pass indistinguishability on ≥50% of seams.

**Strategy.** Imitation + search + human-in-the-loop (AlphaGo, not AlphaZero — no intrinsic reward exists; the mined pro-transition corpus is the reward model). Ship the hand-crafted-eval engine first (Stockfish-classical), then replace the eval with a learned critic trained on mined transitions and accumulated listener ratings (the NNUE moment).

**Read `NORTHSTAR.md` first.** It holds the invariants and the endgame this directive must stay compatible with; on *how* to build wherever this document is silent, it wins.

---

## 1. System doctrine (invariants — violate none)

1. **Beat domain is the coordinate system.** Every track gets a constant-tempo grid (house is DAW-quantized). All analysis features are cached per beat. Because stretching B to A's BPM aligns beat indices 1:1, all cheap scoring happens in beat coordinates with zero resampling and zero rendering. This invariance is the engine's core trick — protect it.
2. **Evaluation cascade.** L0 static filters (key/BPM/energy, no audio) → L1 beat-domain collision/mashability score (cached features, no render; target ≥2,000 triples/sec) → L2 render + DSP-feature heuristic critic (~100 renders) → L3 learned critic (Phase 4) → L4 ears. Never spend render compute on a candidate L1 hasn't shortlisted.
3. **Determinism.** Same inputs → bit-identical render. All randomness seeded; renderer is a pure function of (A, B, cues, recipe, config). Golden-file hash tests enforce this.
4. **Clean sample domain for DSP.** The full mix never round-trips a neural codec. Stems and mixes stay float32 PCM through all DSP tiers. (Neural codec tokens enter only in the Phase-6 infiller horizon, band-limited and blended.)
5. **Data flywheel.** Every rendered candidate persists its feature vector and render metadata. Every listening session records ratings to `ratings.jsonl`. Labels are never thrown away — they are the future critic's training set.
6. **Benchmark table is source of truth.** `bench/BENCH.md` tracks throughput and quality numbers per phase. No gate passes without its row.
7. **Manual override beats clever inference.** Every analysis artifact (grid, key, cues) has a human-editable override field in its sidecar JSON. `griddoctor` exists so bad grids get caught by ear, not discovered three phases later.

---

## 2. Environment

**Host:** the Fedora / RTX 5070 (sm_120) box. All phases run here (demucs, CLAP, and later the critic need the GPU; audio deps are cleanest on Linux). Remote dev via JetBrains Gateway per the deepC pattern.

**Runtime:** Python 3.11 (essentia/madmom wheel safety), managed with `uv`. Repo tooling: `ruff`, `pytest`.

```bash
# env bootstrap
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev,render]"
# torch with Blackwell (sm_120) support — cu130 wheels; fall back to cu128 if needed
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130
# heavy analysis extras: beat_this (primary tracker), essentia (key), demucs (stems), CLAP
uv pip install -e ".[analysis]"
# fallback tracker only if beat_this fails on this box
uv pip install cython && uv pip install git+https://github.com/CPJKU/madmom
# system deps
sudo dnf install ffmpeg rubberband  # rubberband 3.x → R3 engine via '-3'
```

**Disk budget:** plan ≥250 GB free (canonical FLACs ~40 GB / 1,000 tracks; 4-stem FLACs ~150 GB / 1,000 tracks; renders and caches on top). If tight, stems are the thing to prune to a working subset.

**Repo layout:**

```
deephouse/
  deephouse.yaml            # single config: paths, genre band, camelot policy, recipe grid, critic weights
  src/deephouse/
    config.py ingest.py audio.py synth.py cli.py
    analysis/               # grid.py, trackers.py, griddoctor.py, store.py, analyze.py, camelot.py,
                            # then key.py, sections.py, features.py, cues.py
    render/                 # engine.py, automation.py, filters.py, loudness.py
    search/                 # enumerate.py, l1.py, ranker.py, lookahead.py
    critic/                 # l2_features.py, heuristic.py, learned.py (Phase 4)
    mine/                   # boundaries.py, align.py (audfprint), dataset.py
  cache/analysis/{sha1}.json + {sha1}.npz
  cache/stems/{sha1}/{bass,drums,vocals,other}.flac
  library/canonical/{sha1}.flac      # 44.1 kHz stereo 16-bit, TPDF-dithered
  sets/                     # recorded sets corpus (mining input)
  renders/{run_id}/         # wavs + render_meta.json + search_report.md
  ratings.jsonl
  bench/BENCH.md
  tests/
```

**CLI surface (typer):**

```
deephouse ingest <dir> [--kind track|set]     # decode → canonical flac + hash registry
deephouse analyze [--stems] [--clap]         # grid, key, sections, beat features, cues
deephouse griddoctor <track>                 # click-overlay wav + diagnostic png; accepts overrides
deephouse render <A> <B> --cue-out N --cue-in M --recipe R
deephouse next <A> [--k 5] [--m 100] [--lookahead]
deephouse mine <sets_dir>
deephouse listen <renders_dir>               # plays, records 1–5 rating + tags → ratings.jsonl
deephouse bench
deephouse selftest                           # synthetic end-to-end with known ground truth
```

---

## 3. Data contracts

**Track identity:** `sha1` of raw file bytes. Re-encoded file ⇒ new identity; registry maps paths→hashes.

**`cache/analysis/{sha1}.json`** (human-readable, override-able):

```json
{
  "sha1": "…", "source_path": "…", "duration_s": 372.4,
  "grid": {"bpm": 123.984, "beat0_s": 0.312, "downbeat_offset": 2,
            "confidence": 0.97, "override": null, "reviewed": false, "flags": []},
  "key":  {"camelot": "8A", "name": "A minor", "confidence": 0.81, "override": null},
  "bars": {"bar0_beat": 2, "phrase0_bar": 0},
  "sections": [{"start_bar": 0, "end_bar": 16, "label": "intro", "energy": 0.31,
                 "vocal": false}, …],
  "cues_in":  [{"bar": 0, "energy": 0.31, "vocal": false, "bass_active": false,
                 "harm_density": 0.22}, …],
  "cues_out": [{"bar": 176, …}, …]
}
```

Grid conventions: `beat0_s` is the time of grid beat index 0, the first beat at or after t=0 (0 ≤ beat0 < period); `downbeat_offset` ∈ 0..3 is the index of the first downbeat; beat k is a downbeat iff `(k − downbeat_offset) % 4 == 0`; `bars.bar0_beat == downbeat_offset`. Overrides are applied by `GridFit.effective()` — every consumer goes through it.

**`cache/analysis/{sha1}.npz`** (beat-synchronous, float32):
`mel_mix [n_beats, 64]` (log-mel dB, mean per beat), `mel_bass / mel_drums / mel_vocals / mel_other` (same shape, present iff stems), `chroma [n_beats, 12]` (median CQT chroma per beat), `rms_{stem} [n_beats]`, `onset_env_beat [n_beats]`.

**`TransitionRecipe` (dataclass, fully serializable, versioned):** `overlap_bars ∈ {16, 32}` (8 later), `entry_curve ∈ {equal_power, stepped}` (stepped = B at −9 dB for first half, then equal-power to unity), `bass_swap_frac ∈ {0.5, 0.75}` (bar within overlap where A's lows are killed and B's opened), `entry_hpf_sweep ∈ {on, off}` (B enters HPF 250 Hz → 20 Hz over first half), `vocal_rule = duck_A` (if both vocal stems active in the same bars, mute A's vocal stem for those bars), `tempo_policy = stretch_B_to_A` (v1; post-overlap ramp-back is v1.1). Default grid = 2×2×2×2 = **16 recipes**. Per NORTHSTAR §4, keep the representation evolvable into a list-of-ops program.

**`render_meta.json`** per render: full recipe + cues + config hash + L1 score + L2 feature vector + wall time. **`ratings.jsonl`**: `{render_id, rating: 1–5, tags: [...], ts}`.

---

## 4. Phase 0 — Corpus + analysis substrate

**P0.1 Ingest.** *(done, session 1)* `ffmpeg -vn` decode everything (`.mp3 .m4a .mp4 .wav .aiff .flac`) → 44.1 kHz stereo float → TPDF dither → 16-bit FLAC in `library/canonical/`. Registry `library/registry.json` (path, sha1, kind: `track` vs `set`). Recorded sets are registered, not canonicalised.

**P0.2 Constant-tempo grid fit.** *(done, session 1)* Per track: (a) run beat_this (fallback madmom, then librosa) for beat + downbeat estimates; (b) robust-fit a constant grid — linear regression of beat index → beat time with outlier rejection (RANSAC-lite: incremental index assignment, iterate fit → drop residuals >30 ms → refit), yielding `bpm` (float64) and `beat0_s`; (c) fold BPM into the genre band `[116, 130]` (half/double disambiguation); (d) low-band phase check — four-on-the-floor means the kick *is* the beat: if the anti-beat carries decisively more <150 Hz attack energy, flip by half a period and flag `phase_flipped_lowband`; (e) sub-hop phase refinement by folding the signal energy at sample resolution around the consensus beat and placing the beat on the steepest rise, confined to ±30 ms; (f) `downbeat_offset` by majority vote of tracker downbeats against the grid, else a rectified magnitude-flux + accent vote; (g) `confidence` = inlier fraction × grid coverage. If confidence < 0.9 → flag `needs_griddoctor`. Measured on synthetic material: BPM within 0.004, beat0 within 1.3 ms, downbeat exact.

**P0.3 griddoctor.** *(done, session 1)* Renders a 30 s excerpt (starting on a downbeat, 25% into the track) with click overlay (1 kHz clicks at fitted beats, 1.5 kHz accents at downbeats) + a 3-panel PNG (onset envelope with grid lines; time-domain fold on-beat vs anti-beat; tracker residuals vs fitted grid). Overrides (`--bpm`, `--beat0`, `--downbeat-offset`, `--downbeat-shift`, `--accept`, `--clear-override`) write into the sidecar. Non-negotiable tooling: a wrong grid silently poisons every downstream phase.

**P0.4 Stems.** `demucs -n htdemucs_ft` → 4 stems → FLAC in `cache/stems/{sha1}/`. GPU batch, overnight job (~6–11 GPU-h / 1,000 tracks on the 5070). Flag-gated; the dev subset (20 tracks) gets stems immediately.

**P0.5 Beat features.** Compute the `.npz` contract: STFT → 64-band log-mel → mean per beat (per stem + mix); CQT chroma → median per beat; per-stem RMS per beat. All computed at native tempo — beat aggregation is what buys stretch invariance.

**P0.6 Key.** essentia `KeyExtractor` with the `edma` profile (electronic-music-tuned); map to Camelot (`analysis/camelot.py`, exhaustively tested); store confidence. Fallback: Krumhansl–Schmuckler templates on the cached chroma.

**P0.7 Sections + cues.** Foote checkerboard novelty on beat-sync [MFCC ⊕ chroma] self-similarity → boundary candidates → snap to nearest downbeat → segments labeled by heuristics: `energy` = normalized full-mix RMS; `vocal` = vocal-stem RMS above threshold; `bass_active` = bass-stem RMS above threshold; `harm_density` = chroma entropy. `cues_out` = phrase boundaries in the final 40% of the track, preferring low-vocal falling-energy sections; `cues_in` = phrase starts in the first 30%, preferring pre-first-drop low-density sections. Cap ~6 cues per side.

**Gate G0.** On a 20-track dev subset: full pipeline runs unattended; `griddoctor` ear-check passes ≥18/20 grids without override; keys sane on spot-check; bench rows recorded (`analyze_s_per_track`, `demucs_s_per_track`). Unit tests: synthetic click-track fixtures (known BPM/phase + noise) recover BPM within ±0.01 and beat0 within ±5 ms *(passing)*; Camelot table exhaustive test *(passing)*.

---

## 5. Phase 1 — Renderer (the move executor)

A pure function: `render(A, cue_out, B, cue_in, recipe, cfg) → wav + render_meta.json`. Output = `lead_in_bars` of A pre-overlap (default 16) + overlap + `tail_bars` of B (default 32), 44.1 kHz stereo float32 → 24-bit WAV.

**P1.1 Alignment math.** Stretch ratio `r = bpm_A / bpm_B` (reject candidates with `|log2 r| > log2(1.06)` upstream). B's samples pass through rubberband R3 (`pyrubberband`, `rbargs={'-3': ''}`), pitch preserved. Place B's `cue_in` downbeat sample-exactly on A's `cue_out` downbeat. All automation breakpoints land on beat times from the fitted grids. Decode only the segments needed (± padding for filters/stretch edge effects), not whole tracks.

**P1.2 Automation engine.** Per-sample float32 gain arrays built from beat-time breakpoints (linear in dB between breakpoints; equal-power crossfade = cos/sin law over θ∈[0, π/2] — correct for uncorrelated program material). Stems path: each stem gets its own gain array; bass swap = A-bass gain → −inf at `bass_swap_frac`, B-bass 0 → unity at the same bar (1-beat ramp). No-stems fallback: Linkwitz–Riley 4th-order split at 120 Hz (two cascaded 2nd-order Butterworth SOS per side; LR4 sums allpass-flat) and swap the low bands.

**P1.3 Time-varying filters.** HPF/LPF sweeps rendered block-wise: 1-beat blocks, filter cutoff interpolated per block (pedalboard `HighpassFilter`/`LowpassFilter`), 10 ms equal-power crossfades between adjacent block outputs to kill zipper noise.

**P1.4 Loudness chain.** Match B program gain so short-term LUFS (pyloudnorm, BS.1770) is continuous across the seam; master bus: integrated-LUFS trim to target (config, default −9 LUFS) → pedalboard `Limiter` at −1 dBTP.

**P1.5 Determinism + null tests.** Golden-file sha256 test on a fixed fixture render (use `deephouse.synth` tracks). Null test: identity recipe (overlap 0, no automation) reproduces A's segment bit-exactly pre-limiter.

**Gate G1.** Hand-pick two compatible dev tracks; render all 16 recipes; click-overlay verification shows zero drift across the overlap (constant-grid alignment is exact by construction — verify anyway); ≥1 recipe sounds like a competent human mix on ears; `render_s_per_transition` benched (target ≤8 s single-core; parallelize with `multiprocessing` at M=100).

---

## 6. Phase 2 — Search v0 (Stockfish-classical)

**P2.1 L0 static filters.** Candidate B's must satisfy: Camelot ∈ {same, ±1, relative} (config set; must stay demotable to a soft prior per NORTHSTAR §5.4), `|log2(bpm_A/bpm_B)| ≤ log2(1.06)`, entry-cue energy within a window of A's exit-cue energy (config slope for arc direction). Emit (B, cue_out, cue_in, recipe) triples; cap via config (~10–50k typical).

**P2.2 L1 beat-domain score.** For overlap of K beats, with B's per-beat features indexed 1:1 against A's (stretch invariance) and recipe gain masks applied to the *feature* domain (e.g., before `bass_swap_frac`, B's bass features are masked off — L1 is recipe-conditioned):
- `bass_clash = Σ_b min(rms_bass_A[b], rms_bass_B[b])` over beats where both unmasked (should be ~0 by construction; penalizes recipes that leave both open),
- `masking = Σ_{b,f} min(mel_A[b,f], mel_B[b,f])` weighted toward 20–300 Hz bands,
- `vocal_overlap_bars` (both vocal RMS above threshold, post-vocal-rule),
- `harmonic = mean_b cos(chroma_A[b], chroma_B[b])`,
- `energy_step = |energy_A_exit − energy_B_entry − target_arc_slope|`,
- `stretch_penalty = |log2 r|`,
- `clap_sim` (optional Phase-0 flag): cosine of chunk CLAP embeddings.
`L1 = w · features`, weights in `deephouse.yaml`. Vectorize with numpy over all triples; target ≥2,000 triples/sec.

**P2.3 Render + L2.** Top `M=100` by L1 → parallel render → L2 features on rendered audio: short-term LUFS trajectory std over the seam (flag jumps >1.5 LU), spectral-flux continuity at overlap entry/exit, post-mix 20–150 Hz energy crest ("mud"), measured vocal simultaneity, overlap-chroma dissonance vs consonance templates, plus L1 carry-overs. `L2 = w' · features` (hand weights v1). Persist every feature vector.

**P2.4 One-ply look-ahead.** `value(B) = max over B's cues_out of best L1 against the library` (lazily computed, cached pairwise). Final rank = `L2 + λ·value(B)` — never transition into a dead end. This is the "look forward over 50–100 possibles" behavior, literally.

**P2.5 Report + listener.** `search_report.md`: ranked table (B, cues, recipe, L1, L2 features, path). `deephouse listen` plays top-k via sounddevice, prompts 1–5 + tags, appends to `ratings.jsonl`.

**Gate G2.** From a seed track against the full analyzed library: ≥500 triples enumerated, L1-scored, top-100 rendered, ranked, top-5 emitted; wall time ≤10 min; blind listen: ≥1/5 verdict "would play this out." Bench: `L1_triples_per_s`, `search_wall_min`.

---

## 7. Phase 3 — Miner (the human-games database)

**P3.1 Fingerprint-aligned gold (primary).** Build an audfprint landmark DB over the track library. Query each recorded set against it — and because landmark hashing tolerates only ~1–2% speed change, query the *set* resampled over a ratio grid `0.94–1.06 step 0.005` (13 coarse ratios then local refine); sets are few, library DB is built once, so this direction is cheap. Matches yield (track_id, set_offset, ratio, confidence). Consecutive matched tracks A→B define a transition window: [A-match-end − 64 bars, B-match-start + 64 bars], with the doubly-matched region = the actual overlap. Store audio slice + alignment metadata. These are gold: exact boundaries, known source tracks, recoverable stretch ratios.

**P3.2 Boundary-only silver (fallback).** For sets whose tracks aren't in the library: beat-sync self-similarity novelty over long windows; sustained novelty + tempo continuity ⇒ candidate transition regions; slice ±64 bars. Noisier labels — usable for critic pretraining, never for gold eval.

**P3.3 Dataset.** `mine/dataset.py` emits `transitions/{id}/`: audio, beat grid of the mix slice, source IDs where known, tier ∈ {gold, silver}.

**Gate G3.** ≥100 transition windows extracted from the sets corpus; spot-check 20: boundary error ≤4 bars on gold, "plausibly a transition" on ≥80% of silver.

---

## 8. Phase 4 — Learned critic (the NNUE moment)

**P4.1 Inputs.** 32–64-bar windows as beat-sync tensors: mel_mix ⊕ stem-RMS tracks ⊕ chroma → `[n_beats, ~80]`.

**P4.2 Negatives (the design's crux).** Two families: (a) *execution negatives* — our own renderer run with deliberately bad params (off-phrase entry by 2/4/8 beats, no bass swap, clashing Camelot, no LUFS match); (b) *hard negatives* — corruptions of real mined transitions: circular-shift one side's beats by 0.5–2 beats in feature space, detune chroma ±1 semitone, re-inject bass where the pro killed it. (b) forces the model to learn execution quality, not track identity.

**P4.3 Model + training.** Small conv front-end → transformer encoder, 5–15 M params, BCE (real vs negative) + margin ranking on (real, corruption-of-same-real) pairs. Fits the 5070 trivially. Data: gold + silver positives, generated negatives, and `ratings.jsonl` as a fine-tune head (ratings 4–5 positive, 1–2 negative) once ≥300 ratings exist.

**P4.4 Integration.** L3 replaces the L2 weighted sum in ranking (L2 features remain as diagnostics). Re-run G2 protocol.

**Gate G4.** Held-out AUC (real vs corruption) ≥0.9; Spearman vs human ratings on held-out renders beats the L2 heuristic; blind top-5 hit rate strictly improves over G2.

---

## 9. Bench + eval protocol

`bench/BENCH.md` columns: date, commit, `analyze_s_per_track`, `demucs_s_per_track`, `L1_triples_per_s`, `render_s_per_transition`, `search_wall_min`, `critic_auc`, `human_top5_hits`, `blind_ab_pass_rate`. Blind A/B protocol (the end-state bar): pairs of (real set seam, deephouse seam) matched for energy/genre, randomized order, ≥2 house-head listeners, "which was the pro?" — report pass rate = fraction indistinguishable-or-preferred.

## 10. Risk register

- **Grid errors poison everything** → griddoctor + confidence gating + manual override; constant-tempo assumption is itself the strongest prior.
- **Rubberband artifacts** → hard cap stretch at ±6%; R3 engine; prefer BPM-close candidates in L0.
- **Demucs bleed** → conservative stem recipes v1 (bass swap + vocal duck only); no melodic-stem recombination yet.
- **Key detection errors** → store confidence; Camelot filter is config-off-able; chroma features still reach the critic regardless.
- **Silver-mine label noise** → tier separation; gold-only for eval; silver only pretrains.
- **Disk** → stems flag-gated; working subsets; FLAC everywhere.

## 11. Horizon (explicitly out of v1 scope)

Set-level planner (beam search over the L1/L3 pairwise graph with an energy-arc prior — the pairwise matrix from P2.4 is already its substrate); automation-curve recovery from gold alignments (NNLS on stem spectrograms → imitation-learn real fader/EQ moves); VampNet-style masked-token seam infiller trained on mined transitions (band-limited blend over DSP-clean lows); tempo-ramp master clock (v1.1). NORTHSTAR §7 sequences these as P5–P8.

## 12. Build order + session log

Order: **P0 → G0 → P1 → G1 → P2 → G2 → P3 → G3 → P4 → G4.** Each phase's output is the next phase's input; every gate ships something listenable or measurable.

- **Session 1 — done.** Repo scaffold, `deephouse.yaml`, ingest, constant-tempo grid fit with RANSAC-lite + low-band phase check + time-domain refinement, griddoctor, Camelot module, synthetic fixtures, 51 passing tests, `deephouse selftest` end-to-end.
- **Session 2 (on the 5070 box):** install `[analysis]` extras; `deephouse selftest`; ingest a 20-track dev subset; `analyze` with `beat_this`; griddoctor all 20 by ear; kick off overnight demucs (P0.4); then features/key/sections/cues (P0.5–P0.7) → close G0 with a bench row.
- **Session 3–4:** renderer → G1. **Session 5–6:** search v0 → G2 — at which point the thing described in the mission exists: seed a track, get five ranked, rendered, phrase-locked transitions to audition.

**Kickoff prompt for the coding agent (next session):** "Read NORTHSTAR.md, then deephouse_ultracode_directive_v1.md in full, then README.md. Session 1 (P0.1–P0.3) is complete and tested — run `pytest` and `deephouse selftest` to confirm the environment before touching anything. Execute P0.4–P0.7 exactly as specified: stems (flag-gated demucs batch), beat-synchronous features to the `.npz` contract in §3, key detection with Camelot mapping, sections + cues. Each step is a new module under `analysis/` wired into `analysis/analyze.py` as an idempotent stage. Write the tests first for anything with a checkable contract (npz shapes/dtypes, beat aggregation against synthetic material, key detection on synthetic chord stabs). Record the G0 bench row."
