# NORTHSTAR.md — deephouse goal directive

## 0. Document contract

This is the **orientation document**: mission, theory of the domain, invariants to preserve, roadmap beyond v1, and decision tiebreakers. `deephouse_ultracode_directive_v1.md` (same directory) is the **execution document**: current phases, gates, schemas, algorithms.

**Precedence.** For *what to build next*, the execution directive wins — always. For *how to build it* wherever the directive is silent (API shape, generality vs. shortcut, what to log, what to make pluggable), this document wins. If a v1 instruction appears to conflict with a §5 invariant, execute the v1 instruction and flag the conflict in the commit message. This document changes only by explicit human edit; agents may propose changes, never silently rewrite.

## 1. Mission

Build a transition/search system for deep/melodic/tech house that reaches **Move 37 performance**: transitions and set arcs that are simultaneously high-surprisal under the human prior and high-value under grounded reward — blends pros wouldn't attempt, validated by human and crowd response.

The ladder of end-state bars:

1. **Indistinguishability** (v1 bar): blind A/B vs. real pro seams, ≥50% pass rate.
2. **Preference**: deephouse seam preferred over the pro seam on ≥25% of matched pairs.
3. **Move-37 events**: human-confirmed hits in the bottom-decile-prior × top-decile-value quadrant, at a measurable and growing rate.
4. **Flow-state set**: a full 60–90 min generated set that house-head listeners rate as a good *set* — arc, placement, detonation timing — not merely a chain of good seams.

## 2. Theory of the domain

Move 37 was not "the AI got creative." It decomposes into three mechanisms: a **prior** over expert play (imitation policy — it assigned the move ~1/10,000), a **value function grounded in real outcomes** (self-play win/loss), and **search that can override the prior** when value pulls a low-probability action upward. Surprise comes from the prior; quality comes from the value function; search is the bridge. Every design decision in this repo should be traceable to one of those three.

Mapping to DJing, with three deliberate divergences from Go:

- **No intrinsic reward exists.** Taste has no win/loss. Therefore **reward-model engineering is the load-bearing wall** of the entire project; everything else is downstream. The reward stack (§3) is the answer.
- **The action space is not fixed.** In Go, brilliance is pure selection. A DJ in flow state making "impossible" songs blend is not selecting a compatible track — they are *manufacturing compatibility* by transforming the material. Brilliance here lives in **transformation space** (§4).
- **The reward *is* human response.** Unlike Go, staying anchored to human-validated taste is not a limitation to engineer around; it is the win condition. Move 37 was alien play validated by the game's reward. Ours is an alien blend validated by the crowd going off. Same structure, different oracle.

The machine's four structural advantages over a human at the decks, in descending order of expected contribution to perceived quality: (1) **offline search breadth** — render and score thousands of cue/recipe/program candidates per seam where a human auditions a handful; (2) **spectral surgery** — per-time-frequency-cell collision ducking no hardware EQ can do; (3) **micro-editing at scale** — DAW-tier bespoke edits (custom outros, groove transfer, note nudges) generated per seam instead of hand-made for special occasions; (4) **generative tissue** — audio that exists on neither record. Most quality will come from search; the research flag is generative. Budget effort accordingly.

## 3. Reward stack (in order of groundedness)

**R1 — Crowd-reaction mining (the closest available analog to win/loss).** Recorded sets contain not just transitions but *outcomes*: audible crowd eruptions in live/festival/Boiler-Room-style recordings (broadband 2–8 kHz bursts, off-grid, in the non-music residual — detectable with a small classifier); SoundCloud timestamped comments (a crowd-labeled map of "this moment landed"); YouTube timestamp comments; 1001Tracklists transition timestamps with track IDs (which additionally converts the Phase-3 miner from blind fingerprint search into guided alignment — a ~10× speedup). Nobody has assembled reactions-paired-with-transitions for this genre. **This corpus is the data moat and the reward grounding.**

**R2 — Pro imitation.** Mined pro transitions define the prior — the distribution against which surprisal is measured — and supply hard negatives via corruption. Already specified in v1 Phases 3–4.

**R3 — Curated frontier labels.** Human ears (owner + trusted listeners), spent surgically via active learning: the system requests ratings only where the critic ensemble disagrees or where the optimizer is probing. Hundreds of labels doing the work of tens of thousands of random ones.

**Reward model v2 doctrine.** An ensemble of critics scored pessimistically (lower confidence bound); ensemble disagreement as the active-learning acquisition function; continuous human labeling on the optimization frontier so the reward model moves with the optimizer. **Goodhart is the main boss:** optimizing hard against any learned critic will discover adversarial garbage that scores high. Treat reward hacking as an expected, instrumented event class (§6), not a surprise.

## 4. Action-space doctrine

- **v1:** a 16-combination recipe grid. Selection-dominant, deliberately tiny.
- **Endgame:** search over **transformation programs** — compositional sequences of operations applied to both sides of the seam: loops and rolls of phrase sections, stem-matrix mutes/swaps, key nudges (±2 semitones), free-form automation curves (EQ/filter/gain as curves, not presets), tempo ramps, double-drop alignment, and generated elements (risers/fills — the only codec-touched audio, blended band-limited over DSP-clean lows). "Seemingly random songs" become great transitions because the system searches transformation space until a path exists, at a breadth no human auditions.
- **Implication binding on v1 today:** the renderer must be able to evolve into an interpreter of a *serialized program*, not remain a consumer of one fixed dataclass. Keep `TransitionRecipe` versioned and forward-compatible (a list-of-ops representation is acceptable early). This costs almost nothing now and is brutal to retrofit.
- **First showcase deliverable from the existing enumerator:** double-drop search — align two tracks' drop bars as a new cue type, L1-score spectral compatibility over the aligned bars, render survivors. Pros treat landed double drops as trophies; for the machine it is a filter over a cross product.

## 5. Invariants v1 must preserve for the endgame

Each entry: the invariant, then why the endgame dies without it.

1. **The renderer is a pure, deterministic function.** It is the *simulator*. Search, expert iteration, and reproducible evaluation all collapse if rendering grows hidden state, ambient config, or nondeterminism.
2. **Beat-domain coordinates + per-beat feature cache.** This is what makes million-candidate search affordable (stretch invariance ⇒ zero-render scoring). Never admit a feature that breaks per-beat aggregation or grid alignment.
3. **Log everything.** Every candidate's feature vector, program, and scores; every human label; every optimizer run's provenance. This is flywheel fuel — disk is cheaper than re-labeling, and thrown-away rollouts are thrown-away training data.
4. **Hard filters must be demotable to soft priors.** Implement L0 gates (Camelot/BPM/energy) as pluggable scorers behind config, so they can become prior features with a UCB-style exploration budget (10–20% of every render budget on low-prior/high-uncertainty candidates) without surgery. A hard-coded gate is a Move-37 veto: it is precisely the mechanism that would have pruned the 1/10,000 move.
5. **Clean-sample-domain DSP; neural codecs touch only generated elements.** Trained ears are the evaluation instrument; codec smear on sustained pads fails silently and poisons listening tests.
6. **Label tier separation.** Gold (fingerprint-aligned), silver (boundary-mined), reaction-derived, and human ratings never mix in evaluation sets. Noisy labels may pretrain; they may never grade.
7. **Human-in-the-loop is permanent architecture, not scaffolding.** Expert iteration with a learned reward is only sound while fresh human labels keep anchoring the reward model. The `ratings.jsonl` pipeline is a first-class system component forever.

## 6. Metrics beyond the v1 bench table

- **Surprisal**: −log p(candidate) under the imitation prior. (Requires a proposal/prior model — distilled from search acceptances during expert iteration, P8.)
- **Value**: reward-model score; report ensemble mean and lower confidence bound.
- **Move-37 quadrant**: bottom-decile prior probability × top-decile value. Instrument it, fast-track members to human ears, and track the **human-confirmed hit rate** over time — this is the headline research metric of the whole project. "It's not a human move, but it worked" becomes a measurable event class.
- **Reward-hacking audit**: the top-k of every optimizer run gets an ear audit; confirmed hacks are logged with their exploit mechanism; hack rate must trend down as RM v2 hardens.
- **Calibration**: Spearman correlation of reward model vs. human ratings on the active-learning frontier, tracked per RM version.

## 7. Roadmap beyond v1 (P5–P8)

Sequenced after G4. Each phase has a gate; v1 gates are never blocked by endgame work.

- **P5 — Reaction miner + tracklist alignment.** 1001Tracklists-guided set alignment; crowd-burst detector on the non-music residual; timestamped-comment scrapers. **Gate G5:** ≥1,000 reaction-labeled transition moments; burst-detector precision ≥80% on spot-check.
- **P6 — Representation + reward model v2.** MERT-style self-supervised masked-audio pretraining on the full set hoard (~10k hours); critic ensemble on the pretrained encoder; active-learning loop live. **Gate G6:** RM v2 beats the G4 critic on held-out human ratings, and disagreement-based acquisition demonstrably beats random labeling on the label-efficiency curve.
- **P7 — Transformation-program search.** Program-interpreting renderer, operation library, soft-prior UCB scoring with exploration budget; double-drop searcher as first showcase. **Gate G7:** a blend between two L0-*incompatible* tracks (fails the hard Camelot/BPM gates) that humans rate ≥4/5 — the first manufactured-compatibility trophy — plus a curated double-drop bank.
- **P8 — Expert iteration + set-level search.** Distill a proposal network from search-accepted candidates (the policy-improvement operator); beam/MCTS over the pairwise value graph with an energy-arc prior for full-set planning. **Gate G8:** flow-state set listening test (bar 4 of §1) plus first reported Move-37 hit rate.

## 8. Data and compute posture

- **Hoard sets as audio, not video.** Strip to opus/mp3 (~96–128 kbps is fine for mining and SSL; keep a lossless subset for evaluation listening). 10,000 hours ≈ 1–2 TB: one large drive plus a cloud object-storage mirror. Video is kept only if crowd *vision* ever becomes necessary; crowd audio makes it mostly redundant.
- **Compute envelope.** One-time GPU batches (source separation over the hoard ~1,000 GPU-h; SSL pretrain a few hundred to ~1k A100/H100 spot hours); the search render farm is CPU-bound and embarrassingly parallel. Maximal build comfortably under ~$2k plus storage. **The binding constraints are data curation and label quality, never compute — spend money and attention accordingly.**
- **Provenance.** Keep source URLs/IDs for every file; this is a personal research corpus — no redistribution of audio.

## 9. Non-goals (anti-scope)

- Not a real-time performance tool. Offline search *is* the advantage; real-time is a later product decision, not a research goal.
- Not full-track music generation, not a streaming product, no UI beyond CLI + reports until G8.
- No monolithic end-to-end audio model replacing the factorized system (analysis → search → render → critic). Revisit only if P5–P8 evidence demands it.
- Never round-trip the full mix through a neural codec (restates invariant 5 because it will be tempting).
- v1 (Stockfish) ships first, always: it is also the candidate generator the AlphaGo needs.

## 10. How agents use this document

At session start, read this file, then the execution directive. Tiebreaker rules, in order:

1. When two implementations are near-equal cost, choose the one that preserves §5 invariants and §4 forward-compatibility.
2. Never add a hard filter without a config path to soften it into a scored prior.
3. When uncertain whether to persist something, persist it (invariant 3).
4. Scope questions resolve against §9; if still ambiguous, ask the owner rather than expand scope.
5. On apparent conflict between the execution directive and this document: execute the directive, flag the conflict in the commit message, propose the reconciliation.
