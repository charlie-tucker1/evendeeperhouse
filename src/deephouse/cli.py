"""deephouse command-line interface (typer)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import load

app = typer.Typer(help="deephouse — search-based DJ transition engine.", no_args_is_help=True, add_completion=False)
console = Console()


def _cfg(config: Path | None):
    return load(config)


@app.callback()
def _main(ctx: typer.Context, config: Path | None = typer.Option(None, "--config", "-c", help="Path to deephouse.yaml")):
    ctx.obj = _cfg(config)


@app.command()
def version() -> None:
    """Print version and available tracker backends."""
    from .analysis import trackers

    console.print(f"deephouse {__version__}  trackers: {', '.join(trackers.available_backends())}")


@app.command()
def ingest(
    ctx: typer.Context,
    path: Path = typer.Argument(..., exists=True, help="File or directory of audio"),
    kind: str = typer.Option("track", "--kind", "-k", help="track | set"),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Free-form tag(s) to attach"),
    force: bool = typer.Option(False, "--force", help="Re-canonicalise even if present"),
) -> None:
    """Decode audio → canonical FLAC (tracks) and register by SHA-1."""
    from .ingest import ingest_path

    entries = ingest_path(ctx.obj, path, kind=kind, tags=tag, force=force, log=console.print)
    console.print(f"[green]done[/] — {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} in registry")


@app.command()
def analyze(
    ctx: typer.Context,
    track: list[str] = typer.Argument(None, help="sha1 / prefix / filename; default = all tracks"),
    force: bool = typer.Option(False, "--force", help="Recompute even if cached"),
    stages: str = typer.Option("grid,features,groove,key,structure", "--stages", help="Comma-separated subset of: grid,features,groove,key,structure"),
) -> None:
    """Per-track analysis: grid (P0.2), beat features (P0.5), groove (P0.8), key (P0.6), sections + cues (P0.7)."""
    from .analysis.analyze import ALL_STAGES, analyze_all

    st = tuple(x.strip() for x in stages.split(",") if x.strip())
    bad = [x for x in st if x not in ALL_STAGES]
    if bad:
        raise typer.BadParameter(f"unknown stage(s) {bad}; choose from {ALL_STAGES}")
    results = analyze_all(ctx.obj, force=force, only=track or None, stages=st, log=console.print)
    flagged = [r for r in results if "needs_griddoctor" in r.flags or "phase_flipped_lowband" in r.flags or "downbeat_uncertain" in r.flags]
    done = [r for r in results if not r.skipped]
    if done:
        mean_s = sum(r.seconds for r in done) / len(done)
        console.print(f"\n[bold]{len(done)} analysed[/] (mean {mean_s:.1f} s/track), {len(results) - len(done)} cached, "
                      f"[yellow]{len(flagged)} flagged for griddoctor[/]")
    for r in flagged:
        console.print(f"  [yellow]⚠[/] {r.sha1[:10]}  {r.name}  {' '.join(r.flags)}")


@app.command()
def griddoctor(
    ctx: typer.Context,
    track: list[str] = typer.Argument(..., help="sha1 / prefix / filename (one or more)"),
    out: Path | None = typer.Option(None, "--out", help="Output root (default: ./griddoctor_out)"),
    bpm: float | None = typer.Option(None, "--bpm", help="Override BPM"),
    beat0: float | None = typer.Option(None, "--beat0", help="Override beat0 (s)"),
    downbeat_offset: int | None = typer.Option(None, "--downbeat-offset", help="Override downbeat offset 0..3"),
    downbeat_shift: int | None = typer.Option(None, "--downbeat-shift", help="Shift downbeat by N beats (±)"),
    accept: bool = typer.Option(False, "--accept", help="Mark the (effective) grid as human-reviewed"),
    clear_override: bool = typer.Option(False, "--clear-override", help="Remove any override"),
    no_render: bool = typer.Option(False, "--no-render", help="Only apply override/accept; skip click/PNG"),
) -> None:
    """Render click-overlay + diagnostic PNG for a grid, or apply a human override."""
    from .analysis.griddoctor import apply_override, resolve_entry, run_griddoctor

    for key in track:
        e = resolve_entry(ctx.obj, key)
        if any(v is not None for v in (bpm, beat0, downbeat_offset, downbeat_shift)) or accept or clear_override:
            g = apply_override(ctx.obj, e, bpm=bpm, beat0_s=beat0, downbeat_offset=downbeat_offset,
                               downbeat_shift=downbeat_shift, accept=accept, clear=clear_override)
            console.print(f"[green]override applied[/] {e.sha1[:10]}: {g.bpm:.3f} bpm  beat0 {g.beat0_s:.3f}  down {g.downbeat_offset}  reviewed={g.reviewed}")
        if not no_render:
            o = run_griddoctor(ctx.obj, e, out_root=out)
            console.print(f"[bold]{e.sha1[:10]}[/] {Path(e.source_path).name}")
            console.print(f"  {o.grid.bpm:.3f} bpm  beat0 {o.grid.beat0_s:.3f}s  down {o.grid.downbeat_offset}  conf {o.grid.confidence:.2f}  flags {o.grid.flags or '—'}")
            console.print(f"  click: {o.click_wav}\n  png:   {o.png}")


@app.command()
def groove(ctx: typer.Context, track: list[str] = typer.Argument(..., help="sha1 / prefix / filename")) -> None:
    """Print a track's groove profile (docs/GROOVE.md)."""
    from .analysis import store
    from .analysis.griddoctor import resolve_entry
    from .analysis.groove import GrooveProfile

    for key in track:
        e = resolve_entry(ctx.obj, key)
        doc = store.load_analysis(ctx.obj, e.sha1)
        if not doc or not doc.get("groove"):
            console.print(f"[yellow]{e.sha1[:10]}: no groove profile — run `deephouse analyze --stages groove`[/]")
            continue
        p = GrooveProfile.from_dict(doc["groove"])
        console.print(f"[bold]{e.sha1[:10]}[/] {Path(e.source_path).name}   ({p.source}, {p.bars_used} bars)")
        console.print(f"  swing {p.swing_pct * 100:.1f}%  (conf {p.swing_confidence:.2f})   pump {p.pump_depth_db:.1f} dB / {p.pump_release_ms:.0f} ms   "
                      f"kick rise {p.kick_rise_ms:.1f} ms  decay {p.kick_decay_ms:.0f} ms  sub {p.kick_sub_ratio:.2f}")
        t = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        t.add_column("16th")
        for i in range(16):
            t.add_column(str(i), justify="right")
        for band in ("low", "mid", "high"):
            t.add_row(f"Δ {band} ms", *[f"{d:+.0f}" if h > 0.3 else "·" for d, h in zip(p.delta_ms[band], p.hit[band], strict=True)])
        t.add_row("hat pat", *[f"{v * 16:.1f}" for v in p.hat_pattern])
        t.add_row("bass pat", *[f"{v * 16:.1f}" for v in p.bass_pattern])
        console.print(t)


@app.command()
def render(
    ctx: typer.Context,
    a: str = typer.Argument(..., help="outgoing track (sha1 / prefix / filename)"),
    b: str = typer.Argument(..., help="incoming track"),
    cue_out: int = typer.Option(..., "--cue-out", help="A's bar where the overlap starts"),
    cue_in: int = typer.Option(0, "--cue-in", help="B's bar that lands on A's cue-out downbeat"),
    recipe: str = typer.Option("ov16_eqp_bs50_hpf0", "--recipe", help="recipe key from `deephouse recipes`, or 'all'"),
    lead_in: int | None = typer.Option(None, "--lead-in", help="bars of A before the overlap"),
    tail: int | None = typer.Option(None, "--tail", help="bars of B after the overlap"),
    no_stems: bool = typer.Option(False, "--no-stems", help="force the band-split path"),
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """Render one transition (or all 16 recipes) to renders/<run_id>/ (Phase 1)."""
    from .analysis.griddoctor import resolve_entry
    from .render.engine import render as _render
    from .render.io import load_track, render_config_from, save_render
    from .render.recipe import default_grid

    ea, eb = resolve_entry(ctx.obj, a), resolve_entry(ctx.obj, b)
    ta, tb = load_track(ctx.obj, ea, with_stems=not no_stems), load_track(ctx.obj, eb, with_stems=not no_stems)
    rc = render_config_from(ctx.obj, lead_in_bars=lead_in, tail_bars=tail)
    grid = default_grid()
    recipes = grid if recipe == "all" else [r for r in grid if r.key == recipe]
    if not recipes:
        raise typer.BadParameter(f"unknown recipe {recipe!r}; see `deephouse recipes`")
    console.print(f"A {ea.sha1[:10]} {ta.grid.bpm:.3f} bpm ({ta.n_bars} bars, stems={ta.stems is not None})   "
                  f"B {eb.sha1[:10]} {tb.grid.bpm:.3f} bpm ({tb.n_bars} bars, stems={tb.stems is not None})   rate {ta.grid.bpm / tb.grid.bpm:.4f}")
    for r in recipes:
        res = _render(ta, cue_out, tb, cue_in, r, rc)
        p = save_render(ctx.obj, res, run_id=run_id)
        m = res.meta
        console.print(f"  {r.key:22s} {m['wall_s']:5.1f}s  path={m['path']}  B trim {m['b_trim_db']:+.1f} dB  master {m['master_trim_db']:+.1f} dB  → {p}")


@app.command("next")
def next_cmd(
    ctx: typer.Context,
    a: str = typer.Argument(..., help="seed track (sha1 / prefix / filename)"),
    k: int = typer.Option(5, "--k", help="how many to show / render"),
    m: int = typer.Option(100, "--m", help="how many L1 candidates to keep"),
    render_top: bool = typer.Option(False, "--render", help="render the top-k to renders/<run_id>/"),
    run_id: str | None = typer.Option(None, "--run-id"),
    report: bool = typer.Option(True, "--report/--no-report", help="write search_report.md + candidates.jsonl"),
) -> None:
    """Search v0: enumerate (B, cues, recipe) triples, L0 filter, L1 beat-domain score, rank."""
    import json
    import time

    from .analysis.griddoctor import resolve_entry
    from .search.engine import load_library, search_next

    ea = resolve_entry(ctx.obj, a)
    lib = load_library(ctx.obj)
    seed = next((t for t in lib if t.sha1 == ea.sha1), None)
    if seed is None:
        raise SystemExit(f"{ea.sha1[:10]} is not fully analysed (needs grid, features, structure)")
    rep = search_next(ctx.obj, seed, lib, top=m)
    console.print(rep.table(k))
    run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
    out_dir = ctx.obj.path("renders") / run_id
    if report:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "search_report.md").write_text("```\n" + rep.table(min(m, 100)) + "\n```\n")
        with (out_dir / "candidates.jsonl").open("w") as f:
            for c in rep.ranked:
                f.write(json.dumps(c.to_dict()) + "\n")
        console.print(f"[dim]report → {out_dir / 'search_report.md'}[/]")
    if render_top:
        from .render.engine import render as _render
        from .render.io import load_track, render_config_from, save_render

        rc = render_config_from(ctx.obj)
        ta = load_track(ctx.obj, ea)
        cache = {}
        for i, c in enumerate(rep.collapsed()[:k], 1):
            if c.b.sha1 not in cache:
                cache[c.b.sha1] = load_track(ctx.obj, resolve_entry(ctx.obj, c.b.sha1))
            res = _render(ta, c.cue_out, cache[c.b.sha1], c.cue_in, c.recipe, rc)
            res.meta["l1"] = c.l1
            res.meta["l1_features"] = c.l1_features
            p = save_render(ctx.obj, res, run_id=run_id, name=f"{i:02d}_{c.b.name[:24]}_{c.recipe.key}")
            console.print(f"  [{i}] {res.meta['wall_s']:4.1f}s → {p.name}")


@app.command()
def listen(
    ctx: typer.Context,
    renders_dir: Path = typer.Argument(..., exists=True, help="renders/<run_id>/ directory"),
    start_at: float = typer.Option(0.0, "--start-at", help="seconds into each render to start playback (e.g. just before the overlap)"),
    no_play: bool = typer.Option(False, "--no-play", help="don't play audio (rate from another player)"),
) -> None:
    """Audition renders and record 1–5 ratings (+ tags) to ratings.jsonl — the critic's training data."""
    import json
    import time

    import soundfile as sf

    wavs = sorted(renders_dir.glob("*.wav"))
    if not wavs:
        raise SystemExit(f"no .wav files in {renders_dir}")
    sd = None
    if not no_play:
        try:
            import sounddevice as sd  # type: ignore
        except Exception:  # noqa: BLE001
            console.print("[yellow]sounddevice unavailable — rating without playback (open the wav in any player)[/]")
    ratings_path = ctx.obj.path("ratings")
    console.print(f"{len(wavs)} render(s). Keys: 1–5 rate, s skip, r replay, q quit. Tags after the rating, e.g. '4 mud, late-swap'.")
    for w in wavs:
        meta_p = w.with_name(w.name.replace(".wav", ".render_meta.json"))
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        console.print(f"\n[bold]{w.name}[/]  {meta.get('recipe_key', '')}  L1 {meta.get('l1', float('nan')):.2f}" if meta else f"\n[bold]{w.name}[/]")
        y, sr = sf.read(str(w), dtype="float32")
        if sd is not None:
            ov = meta.get("overlap_start_sample")
            s0 = int(start_at * sr) if start_at else (max(ov - 4 * meta.get("samples_per_bar", 0), 0) if ov else 0)
            sd.play(y[s0:], sr)
        while True:
            ans = console.input("  rating> ").strip()
            if ans == "q":
                if sd is not None:
                    sd.stop()
                return
            if ans == "s":
                break
            if ans == "r" and sd is not None:
                sd.play(y, sr)
                continue
            parts = ans.split(maxsplit=1)
            if parts and parts[0] in ("1", "2", "3", "4", "5"):
                tags = [t.strip() for t in parts[1].split(",")] if len(parts) > 1 else []
                rec = {"render_id": w.stem, "run": renders_dir.name, "rating": int(parts[0]), "tags": tags, "ts": time.time(),
                       "a": meta.get("a"), "b": meta.get("b"), "recipe": meta.get("recipe_key"), "l1": meta.get("l1")}
                with ratings_path.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                console.print(f"  [green]saved[/] {rec['rating']} {tags}")
                break
            console.print("  1–5 [tags], s, r, q")
        if sd is not None:
            sd.stop()
    console.print(f"\nratings → {ratings_path}")


@app.command()
def recipes() -> None:
    """List the v1 recipe grid."""
    from .render.recipe import default_grid

    for r in default_grid():
        console.print(f"  {r.key:22s} overlap {r.overlap_bars:2d} bars  entry {r.entry_curve:11s} bass swap @ {r.bass_swap_frac:.2f}  hpf sweep {r.entry_hpf_sweep}")


@app.command()
def structure(ctx: typer.Context, track: list[str] = typer.Argument(..., help="sha1 / prefix / filename")) -> None:
    """Print a track's sections and cue points."""
    from .analysis import store
    from .analysis.griddoctor import resolve_entry

    for key in track:
        e = resolve_entry(ctx.obj, key)
        doc = store.load_analysis(ctx.obj, e.sha1)
        st = (doc or {}).get("structure")
        if not st or "error" in st:
            console.print(f"[yellow]{e.sha1[:10]}: no structure — run `deephouse analyze --stages structure`[/]")
            continue
        console.print(f"[bold]{e.sha1[:10]}[/] {Path(e.source_path).name}   {st['n_bars']} bars, phrase0 {st['phrase0_bar']}")
        t = Table(box=None, padding=(0, 1), header_style="bold")
        for col in ("bars", "label", "energy", "vocal", "bass", "harm"):
            t.add_column(col)
        for s_ in st["sections"]:
            t.add_row(f"{s_['start_bar']:>3}–{s_['end_bar']:<3}", s_["label"], f"{s_['energy']:.2f}", "v" if s_["vocal"] else "", "b" if s_["bass_active"] else "", f"{s_['harm_density']:.2f}")
        console.print(t)
        console.print("  cues in : " + "  ".join(f"bar {c['bar']} ({c['score']:.2f})" for c in st["cues_in"]))
        console.print("  cues out: " + "  ".join(f"bar {c['bar']} ({c['score']:.2f})" for c in st["cues_out"]))


@app.command("list")
def list_cmd(ctx: typer.Context, kind: str = typer.Option("track", "--kind", "-k")) -> None:
    """List registry entries with their grid status."""
    from .analysis import store
    from .ingest import Registry

    reg = Registry(ctx.obj.path("registry"))
    t = Table(title=f"registry — {kind}s")
    for col in ("sha1", "name", "dur", "bpm", "beat0", "down", "conf", "key", "swing", "pump", "rev", "flags"):
        t.add_column(col)
    for e in reg.by_kind(kind):
        doc = store.load_analysis(ctx.obj, e.sha1)
        g = store.get_grid(doc) if doc else None
        dur = f"{e.duration_s / 60:.1f}m" if e.duration_s else "?"
        if g:
            k = (doc.get("key") or {})
            gr = (doc.get("groove") or {})
            t.add_row(e.sha1[:10], Path(e.source_path).name[:40], dur, f"{g.bpm:.3f}", f"{g.beat0_s:.3f}", str(g.downbeat_offset),
                      f"{g.confidence:.2f}", k.get("override") or k.get("camelot") or "—",
                      f"{gr['swing_pct'] * 100:.0f}%" if gr else "—", f"{gr['pump_depth_db']:.1f}" if gr else "—",
                      "✓" if g.reviewed else "", " ".join(g.flags))
        else:
            t.add_row(e.sha1[:10], Path(e.source_path).name[:40], dur, "—", "—", "—", "—", "—", "—", "—", "", "not analysed")
    console.print(t)


@app.command()
def selftest(
    ctx: typer.Context,
    out: Path = typer.Option(Path("selftest_out"), "--out", help="Where to write synthetic tracks"),
    n: int = typer.Option(3, "--n", help="Number of synthetic tracks"),
) -> None:
    """Generate synthetic house tracks with known grids and run ingest→analyze→griddoctor on them."""
    import numpy as np
    import soundfile as sf

    from .analysis.analyze import analyze_all
    from .analysis.griddoctor import resolve_entry, run_griddoctor
    from .ingest import ingest_path
    from .synth import make_click_track

    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    truths = {}
    for i in range(n):
        bpm = float(rng.uniform(118, 128))
        beat0 = float(rng.uniform(0, 60 / bpm))
        down = int(rng.integers(0, 4))
        y, tr = make_click_track(bpm=bpm, beat0_s=beat0, downbeat_offset=down, duration_s=90.0, snr_db=18.0, style="house", seed=i)
        p = out / f"synth_{i:02d}_{bpm:.2f}bpm.wav"
        sf.write(str(p), y, tr.sr, subtype="PCM_16")
        truths[p.name] = tr
    entries = ingest_path(ctx.obj, out, kind="track", tags=["synthetic"], log=console.print)
    results = analyze_all(ctx.obj, only=[e.sha1 for e in entries], force=True, log=console.print)
    console.print()
    ok = True
    for e, r in zip(entries, results, strict=True):
        tr = truths[Path(e.source_path).name]
        P = tr.period_s
        d = (r.beat0_s - tr.beat0_s) % P
        d = min(d, P - d)
        bar = 4 * P
        dd = ((r.beat0_s + r.downbeat_offset * P) - (tr.beat0_s + tr.downbeat_offset * P)) % bar
        dd = min(dd, bar - dd)
        good = abs(r.bpm - tr.bpm) <= 0.01 and d <= 0.005 and dd <= 0.005
        ok &= good
        console.print(f"  {'[green]PASS[/]' if good else '[red]FAIL[/]'} {r.name}: bpm err {r.bpm - tr.bpm:+.4f}  beat0 err {d * 1000:.2f} ms  downbeat err {dd * 1000:.1f} ms")
        o = run_griddoctor(ctx.obj, resolve_entry(ctx.obj, e.sha1), out_root=out / "griddoctor")
        console.print(f"       griddoctor → {o.png}")
    console.print("\n[bold green]selftest OK[/]" if ok else "\n[bold red]selftest FAILED[/]")
    raise typer.Exit(0 if ok else 1)


if __name__ == "__main__":  # pragma: no cover
    app()
