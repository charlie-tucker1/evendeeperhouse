# deephouse bench

Source of truth for throughput and quality numbers. One row per measurement; no gate passes without its row.

| date | commit | phase | analyze_s_per_track | demucs_s_per_track | L1_triples_per_s | render_s_per_transition | search_wall_min | critic_auc | human_top5_hits | blind_ab_pass_rate | notes |
|------|--------|-------|---------------------|--------------------|------------------|-------------------------|-----------------|------------|-----------------|--------------------|-------|
| 2026-09-26 | 8f3146f | 0–2 (synthetic, CPU, librosa tracker) | 8–11 (2-min tracks, all stages) | — | 3,600–5,200 | ~5.0 (80-bar, bands path) | <0.1 (5-track lib) | — | — | — | cloud container, no GPU; real-track numbers pending the box |
