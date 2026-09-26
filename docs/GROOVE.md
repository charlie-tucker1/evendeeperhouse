# GROOVE.md — the micro-timing layer (first-principles addendum to the v1 directive)

## 1. Why the beat grid is not enough

The v1 directive's coordinate system is the constant-tempo beat grid, and at the bar level
that is exactly right. But *groove* — the thing that separates a rolling deep-house record
from a stiff one, and a seamless blend from an obviously mixed one — lives **below** the grid,
in the 5–20 ms deviations that a DAW quantise grid does not remove:

| phenomenon | where it lives | typical magnitude | seam tell when mismatched |
|---|---|---|---|
| swing | off-16th hats/percs late of nominal | 0–25 ms (50–60 %) | two hat patterns *flam* into mush |
| bass placement | bass note onset vs kick onset | −10…+30 ms | groove lurches at the bass swap |
| kick attack | 10→90 % rise of the folded kick | 2–15 ms | kicks flam; low end goes hollow |
| sidechain pump | duck depth + release of pads/bass to the kick | 3–12 dB, 100–300 ms | B's pads pump to a kick the listener no longer hears |
| pattern | which 16ths carry hats / bass energy | binary-ish per position | both tracks hitting the same off-16ths = double density |

A DJ cannot address any row of that table from a mixer. There is no knob. Pros handle it by
(a) picking records that happen to share a feel, and (b) not overlapping long. The machine
can *measure* every row for every track once, *score* pairwise compatibility in the
zero-render L1 tier, and — the inhuman part — *warp* the incoming track so its micro-timing
lands on the outgoing track's (groove transfer), sidechain B to A's kick so the pump is
coherent, and choose the bass-swap bar where the two bass placements agree.

## 2. The groove profile (analysis artefact, P0.8)

Computed once per track from the fitted grid, over the middle 60 % of the track, with stems
when available (falls back to band-splits). All quantities are averages over hundreds of
bars, so they are stable and cheap. Stored in the sidecar under `groove`.

- **Micro-timing template** `delta_ms[16]`, `hit[16]`: for each 16th position *p* in the bar,
  fold a fine onset envelope at the *bar* period and look ±40 % of a 16th around the nominal
  position; `delta_ms[p]` = peak offset from nominal, `hit[p]` = normalised peak mass
  (how strongly *something* plays there). This is Ableton's "extract groove" done for the
  whole record. Computed for three bands — `low` (<150 Hz: kick+bass), `mid`, `high`
  (>5 kHz: hats) — because hats and bass do not swing by the same amount.
- **Swing** `swing_pct`: 0.5 + mean(delta of odd 16ths in the high band) / eighth-period.
  50 % = straight, 58 % = rolling, 66 % = triplet.
- **Kick transient** `kick_rise_ms`, `kick_decay_ms`, `kick_sub_ratio`: from the folded low-band
  beat profile (the same `_fold_energy` griddoctor draws); sub ratio = energy <80 Hz / 80–200 Hz.
- **Bass pattern** `bass_pattern[16]`, **hat pattern** `hat_pattern[16]`: mean band energy
  per 16th position, normalised to sum 1. Off-beat bass ("bounce") shows as mass at 2,6,10,14.
- **Pump** `pump_depth_db`, `pump_release_ms`: fold the mid/high-band envelope at the beat
  period; depth = peak-to-trough in dB inside the beat, release = time from trough to 90 %
  recovery. Sidechain compression is the heartbeat of the genre; measure it.

## 3. Groove compatibility (L1 features, zero render)

For a candidate (A, B) overlap, added to the directive §6 L1 vector:

- `flam_risk = Σ_p hitA_high[p] · hitB_high[p] · |deltaA_high[p] − deltaB_high[p]|` — both
  tracks hitting the same 16th with different micro-timing. Above ~8 ms per hit is audible.
- `swing_mismatch = |swingA − swingB|` (ms at the shared tempo).
- `bass_placement_step = |deltaA_low[0] − deltaB_low[0]|` at the swap bar — how far the groove
  lurches when the low end changes hands.
- `pattern_density = Σ_p hatA[p]·hatB[p]` — double-density hats during the overlap.
- `pump_mismatch = |depthA − depthB| + |releaseA − releaseB|/100`.
- `bass_pattern_continuity = cos(bass_patternA, bass_patternB)` — a reward, not a penalty.

All are 16-vectors ops → vectorise over thousands of candidates in numpy like the rest of L1.

## 4. Render ops that only a machine can do (P1.x / P7)

1. **Groove transfer.** Warp B so `deltaB[p] → deltaA[p]` for every 16th. Rubberband R3's
   `--timemap` takes (source sample, target sample) pairs — one pair per 16th boundary for the
   overlap region — and does it transient-preservingly. Cost: zero extra artefact beyond the
   stretch B already gets. Validation: recompute B's groove profile after warping; it must
   match A's within 2 ms.
2. **Kick phase alignment.** Two 50 Hz kicks a few ms apart partially cancel (hollow seam).
   Measure the kick fundamental's phase at the attack in both folded profiles; nudge B by the
   sub-ms residual so the fundamentals sum constructively during the overlap. Mastering
   engineers do this by hand for kick/bass; nobody can do it live.
3. **Coherent sidechain.** During the overlap, duck B's non-kick stems with an envelope derived
   from A's *actual* folded kick profile (not a generic compressor) so B pumps to the kick the
   listener hears. After the bass swap, cross-fade the envelope source to B's kick.
4. **Placement-aware bass swap.** Choose `bass_swap_frac` at the bar where
   `|deltaA_low − deltaB_low|` is smallest and both bass patterns carry a note on beat 1.
5. **Fill-aware entry.** Detect fills (last bar of an 8-bar phrase with high-band flux spike);
   land B's first full-energy bar right after A's fill so the fill *announces* the change.

## 5. Ground truth

`deephouse.synth.make_click_track` accepts `swing`, `pump_depth_db`, `hats`, `bass`. The
groove tests assert the profile recovers swing within 1.5 ms, pump depth within 1 dB, and the
hat/bass patterns' argmax positions. Real-record validation: run `deephouse groove <track>`
on a known straight track and a known swung one and compare `swing_pct`.

## 6. What this changes in the directive

- P0.8 (new): groove profile, after P0.5 features. Included in the G0 gate.
- §6 P2.2: L1 gains the six features of §3.
- §5 P1: `TransitionRecipe` gains `groove_transfer ∈ {off, on}` and `sidechain_source ∈ {none, A_kick}`
  (both off in the 16-recipe v1 grid; on in v1.1 once rubberband timemap is wired).
- NORTHSTAR §2 advantage (3) "micro-editing at scale" now has a concrete first instance.
