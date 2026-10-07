"""Ingest QA (effective bandwidth vs declared bitrate) and podcast feed parsing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deephouse.audio import load_audio
from deephouse.audio_qa import assess, effective_bandwidth
from deephouse.synth import make_click_track

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


@pytest.fixture(scope="module")
def encoded(tmp_path_factory, sr):
    d = tmp_path_factory.mktemp("enc")
    y, _ = make_click_track(bpm=124, duration_s=40, style="house", hats="16ths", snr_db=40, seed=9, sr=sr)
    src = d / "src.wav"
    sf.write(str(src), y, sr, subtype="PCM_16")

    def enc(name, *args, inp=src):
        out = d / name
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(inp), *args, str(out)], check=True)
        return out

    files = {
        "real_flac": enc("real.flac", "-c:a", "flac"),
        "mp3_320": enc("mp3_320.mp3", "-c:a", "libmp3lame", "-b:a", "320k"),
        "mp3_128": enc("mp3_128.mp3", "-c:a", "libmp3lame", "-b:a", "128k"),
        "opus": enc("o.opus", "-c:a", "libopus", "-b:a", "128k"),
    }
    files["fake_320"] = enc("fake_320.mp3", "-c:a", "libmp3lame", "-b:a", "320k", inp=files["mp3_128"])
    files["fake_flac"] = enc("fake.flac", "-c:a", "flac", inp=files["mp3_128"])
    return files


def _probe(p: Path):
    from deephouse.acquire.feeds import ffprobe_audio

    return ffprobe_audio(p)


@pytest.mark.parametrize("key,flag,bw_lo,bw_hi", [
    ("real_flac", "ok", 20000, 23000),
    ("mp3_320", "ok", 19000, 21500),
    ("mp3_128", "ok", 15500, 17800),
    ("opus", "opus_normal", 19000, 21000),
    ("fake_320", "transcode_suspect", 15500, 17800),
    ("fake_flac", "transcode_suspect", 15500, 17800),
])
def test_qa_flags_transcodes(encoded, key, flag, bw_lo, bw_hi):
    p = encoded[key]
    pr = _probe(p)
    y, sr = load_audio(p)
    q = assess(y, sr, pr.get("codec"), pr.get("declared_kbps"))
    assert bw_lo <= q.bandwidth_hz <= bw_hi, (key, q.bandwidth_hz)
    assert q.flag == flag, (key, q)
    if flag == "transcode_suspect":
        assert q.cliff_db >= 18 and 15500 <= q.cliff_hz <= 17500          # the encoder's brick wall
    if key == "real_flac":
        assert q.cliff_db < 18                                             # no brick wall in a real master


def test_gradual_rolloff_is_dark_master_not_transcode(sr):
    """A genuine but dark master (smooth −7 dB/kHz slope, no cliff) must not be flagged as a transcode."""
    from scipy.signal import butter, sosfiltfilt

    rng = np.random.default_rng(1)
    n = rng.standard_normal(sr * 30).astype(np.float32) * 0.1
    y = sosfiltfilt(butter(1, 9000, btype="low", fs=sr, output="sos"), n).astype(np.float32)   # 6 dB/oct, gentle
    q = assess(y, sr, "mp3", 320)
    assert q.cliff_db < 18 or q.cliff_hz >= 19000        # no brick wall below the encoder's lowpass
    assert q.flag in ("dark_master", "ok")


def test_effective_bandwidth_on_bandlimited_noise(sr):
    from scipy.signal import butter, sosfiltfilt

    rng = np.random.default_rng(0)
    n = rng.standard_normal(sr * 20).astype(np.float32) * 0.1
    lp = sosfiltfilt(butter(8, 16000, btype="low", fs=sr, output="sos"), n).astype(np.float32)
    bw, plateau, floor = effective_bandwidth(lp, sr)
    assert 15000 <= bw <= 17000
    assert plateau > floor


RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<title>T</title>
<item><title>EP 2</title><guid>g2</guid><pubDate>Wed, 07 Oct 2026 17:00:00 GMT</pubDate><link>https://x/2</link>
<description>&lt;p&gt;Tracks&amp;nbsp;from&amp;nbsp;A &amp;amp; B&lt;/p&gt;</description>
<enclosure url="https://h/2.mp3?x=1" type="audio/mpeg" length="146653650"/><itunes:duration>01:01:06</itunes:duration></item>
<item><title>Short</title><guid>g1</guid><enclosure url="https://h/1.mp3" type="audio/mpeg" length="5"/><itunes:duration>10:00</itunes:duration></item>
<item><title>No enclosure</title><guid>g0</guid></item>
</channel></rss>"""


def test_feed_parsing(monkeypatch):
    from deephouse.acquire import feeds

    class R:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(feeds.urllib.request, "urlopen", lambda req, timeout=60: R(RSS.encode()))
    eps = feeds.fetch_feed(feeds.feed_by_key("yotto"))
    assert [e.guid for e in eps] == ["g2", "g1"]
    e = eps[0]
    assert e.duration_s == 3666 and e.enclosure_length == 146653650 and e.enclosure_url.endswith("?x=1")
    assert "Tracks from A & B" in e.description
    assert len({x.id for x in eps}) == 2
    assert all(f.median_kbps >= 128 for f in feeds.FEEDS) and len({f.key for f in feeds.FEEDS}) == len(feeds.FEEDS)
