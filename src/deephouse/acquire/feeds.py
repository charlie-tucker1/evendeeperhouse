"""Podcast-RSS acquisition (docs/SOURCING.md §3b, the ToS-clean route).

Publishers of DJ radio shows expose their *original* MP3s as RSS enclosures — measured
192–320 kbps for most shows below (2026-10-07), vs 160 kbps AAC from the SoundCloud player.
Nothing here circumvents a platform mechanism: enclosures are files the publisher chose to
serve. Each download gets a provenance sidecar (feed, GUID, title, pubDate, link, description —
which usually carries the tracklist — enclosure URL, bytes, ffprobe codec/bitrate).

Registry entries carry the bitrate the researcher measured; re-measure with `deephouse feeds probe`.
"""

from __future__ import annotations

import email.utils
import hashlib
import html
import json
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import Config

USER_AGENT = "deephouse-research/0.1 (personal non-commercial research; contact via repo)"


@dataclass(frozen=True)
class Feed:
    key: str
    name: str
    url: str
    median_kbps: int
    genres: tuple[str, ...]
    host: str
    note: str = ""
    items: int | None = None
    typical_minutes: int | None = None


# Verified 2026-10-07 by parsing the live XML (see docs/research/sourcing/dj_set_sources.md).
FEEDS: tuple[Feed, ...] = (
    Feed("cattaneo", "Hernán Cattáneo – Resident", "https://podcast.hernancattaneo.com/feed.xml", 320,
         ("progressive", "melodic"), "Podbean", "809 items since 2011; 60 min", 809, 60),
    Feed("dha", "Deep House Amsterdam (DHA FM)", "https://feeds.soundcloud.com/users/soundcloud:users:15904471/sounds.rss", 320,
         ("deep", "melodic", "tech"), "SoundCloud RSS", "feed capped at 500 items; original MP3 via 302", 500, 64),
    Feed("crosstown", "The Crosstown Mix Show", "https://feed.podbean.com/thecrosstownmixshow/feed.xml", 320,
         ("deep", "tech"), "Podbean", "100 items; 90 min", 100, 90),
    Feed("yotto", "Yotto – Odd One Out Radio", "https://feed.podtoo.com/distro/jFBUMUI_", 320,
         ("melodic", "deep"), "Podtoo", "", 104, 61),
    Feed("atish", "Atish", "https://feeds.feedburner.com/atishmusic", 320, ("deep", "melodic"), "Feedburner", "", 113, 60),
    Feed("tml_friendship", "Tomorrowland Friendship Mix", "https://feeds.soundcloud.com/users/soundcloud:users:243635960/sounds.rss", 320,
         ("mixed", "melodic", "tech"), "SoundCloud RSS", "genre varies per guest", 271, 60),
    Feed("clapcast", "Claptone – Clapcast", "https://portal-api.thisisdistorted.com/xml/clapcast", 320,
         ("deep", "tech"), "This Is Distorted", "", 585, 61),
    Feed("ra", "RA Podcast", "https://ra.co/xml/podcast.xml", 195,
         ("mixed",), "SoundCloud RSS", "VBR, uploader-dependent (RA.1059 ≈ 195 kbps); genre varies", 500, 75),
    Feed("toolroom", "Toolroom Radio", "https://portal-api.thisisdistorted.com/xml/toolroom-radio", 191,
         ("tech", "house"), "This Is Distorted", "2 h episodes; some items 320", 238, 120),
    Feed("defected", "Defected Radio (incl. Glitterbox)", "https://portal-api.thisisdistorted.com/xml/defected-in-the-house", 192,
         ("house", "deep"), "This Is Distorted", "1,062 items since 2015", 1062, 60),
    Feed("purified", "Nora En Pure – Purified Radio", "http://portal-api.thisisdistorted.com/xml/nora-en-pure-purified-radio", 192,
         ("deep", "melodic"), "This Is Distorted", "", 527, 60),
    Feed("glasgow_underground", "Glasgow Underground Radio", "https://portal-api.thisisdistorted.com/xml/glasgow-underground-radio", 191,
         ("deep", "house"), "This Is Distorted", "", 178, 60),
    Feed("spectrum", "Joris Voorn – Spectrum Radio", "https://jorisvoornspectrum.libsyn.com/rss", 209,
         ("melodic", "tech"), "Libsyn", "feed capped at 100 items", 100, 61),
    Feed("miss_monique", "Miss Monique", "https://feeds.soundcloud.com/users/soundcloud:users:17716472/sounds.rss", 128,
         ("melodic",), "SoundCloud RSS", "128 kbps uploads — below the QA floor for listening", 169, 60),
    Feed("dialekt", "Sultan + Shepard – Dialekt Radio", "https://feeds.simplecast.com/3dnPjov_", 128,
         ("melodic",), "Simplecast", "Simplecast transcodes to 128 — features only", 351, 60),
)


def feed_by_key(key: str) -> Feed:
    for f in FEEDS:
        if f.key == key:
            return f
    raise KeyError(f"unknown feed {key!r}; known: {[f.key for f in FEEDS]}")


@dataclass
class Episode:
    feed_key: str
    guid: str
    title: str
    pub_date: str | None
    link: str | None
    description: str
    enclosure_url: str
    enclosure_type: str | None
    enclosure_length: int | None
    duration_s: int | None = None

    @property
    def id(self) -> str:
        return hashlib.sha1((self.feed_key + "|" + self.guid).encode()).hexdigest()[:16]


def _text(el, tag: str, ns: dict | None = None) -> str | None:
    x = el.find(tag, ns or {})
    return (x.text or "").strip() if x is not None and x.text else None


def _parse_duration(s: str | None) -> int | None:
    if not s:
        return None
    parts = s.strip().split(":")
    try:
        if len(parts) == 1:
            return int(float(parts[0]))
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except ValueError:
        return None


def fetch_feed(feed: Feed, timeout: int = 60) -> list[Episode]:
    req = urllib.request.Request(feed.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        xml = r.read()
    root = ET.fromstring(xml)
    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    out: list[Episode] = []
    for item in root.iter("item"):
        enc = item.find("enclosure")
        if enc is None or not enc.get("url"):
            continue
        guid = _text(item, "guid") or enc.get("url")
        length = enc.get("length")
        out.append(Episode(
            feed_key=feed.key, guid=guid, title=_text(item, "title") or "", pub_date=_text(item, "pubDate"),
            link=_text(item, "link"), description=html.unescape(re.sub(r"<[^>]+>", " ", _text(item, "description") or "")).replace("\xa0", " "),
            enclosure_url=enc.get("url"), enclosure_type=enc.get("type"),
            enclosure_length=int(length) if length and length.isdigit() else None,
            duration_s=_parse_duration(_text(item, "itunes:duration", ns)),
        ))
    return out


def ffprobe_audio(path: Path) -> dict:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=codec_name,bit_rate,sample_rate,channels:format=duration,bit_rate", "-of", "json", str(path)],
            capture_output=True, text=True, check=True).stdout
        d = json.loads(out)
        st = (d.get("streams") or [{}])[0]
        fmt = d.get("format") or {}
        br = st.get("bit_rate") or fmt.get("bit_rate")
        return {"codec": st.get("codec_name"), "declared_kbps": int(int(br) / 1000) if br else None,
                "sample_rate": int(st["sample_rate"]) if st.get("sample_rate") else None,
                "channels": st.get("channels"), "duration_s": float(fmt["duration"]) if fmt.get("duration") else None}
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, ValueError):
        return {}


def _slug(s: str, n: int = 60) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:n] or "episode"


def pull(cfg: Config, feed: Feed, out_root: Path | None = None, max_items: int | None = None,
         min_minutes: int = 40, sleep_s: float = 2.0, dry_run: bool = False, log=print) -> list[Path]:
    """Download enclosures newest-first into ``sets/feeds/<feed>/``, skipping ones already present
    (by episode id), with a JSON provenance sidecar per file. Polite: one at a time, ``sleep_s`` apart."""
    out_dir = (out_root or (cfg.path("sets") / "feeds")) / feed.key
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "_archive.json"
    have: dict[str, str] = json.loads(archive.read_text()) if archive.exists() else {}
    episodes = fetch_feed(feed)
    log(f"[feeds] {feed.name}: {len(episodes)} items in feed, {len(have)} already pulled")
    got: list[Path] = []
    n = 0
    for ep in episodes:
        if max_items is not None and n >= max_items:
            break
        if ep.id in have:
            continue
        if ep.duration_s is not None and ep.duration_s < min_minutes * 60:
            continue
        date = ""
        if ep.pub_date:
            try:
                date = email.utils.parsedate_to_datetime(ep.pub_date).strftime("%Y%m%d") + "_"
            except (TypeError, ValueError):
                date = ""
        ext = ".mp3" if (ep.enclosure_type or "").endswith("mpeg") or ep.enclosure_url.lower().split("?")[0].endswith(".mp3") else ".audio"
        dst = out_dir / f"{date}{_slug(ep.title)}_{ep.id}{ext}"
        if dry_run:
            log(f"  would pull {dst.name}  ({(ep.enclosure_length or 0) / 1e6:.0f} MB, {ep.duration_s or '?'} s)")
            n += 1
            continue
        t0 = time.time()
        req = urllib.request.Request(ep.enclosure_url, headers={"User-Agent": USER_AGENT})
        tmp = dst.with_suffix(dst.suffix + ".part")
        with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
            final_url = r.geturl()
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        tmp.replace(dst)
        meta = {**asdict(ep), "id": ep.id, "feed": asdict(feed), "final_url": final_url, "bytes": dst.stat().st_size,
                "fetched_at": time.time(), "probe": ffprobe_audio(dst), "route": "podcast_rss_enclosure"}
        dst.with_suffix(dst.suffix + ".provenance.json").write_text(json.dumps(meta, indent=1, default=str))
        have[ep.id] = dst.name
        archive.write_text(json.dumps(have, indent=1, sort_keys=True))
        kb = meta["probe"].get("declared_kbps")
        log(f"  pulled {dst.name}  {meta['bytes'] / 1e6:.0f} MB  {kb or '?'} kbps  ({time.time() - t0:.0f}s)")
        got.append(dst)
        n += 1
        time.sleep(sleep_s)
    return got


@dataclass
class FeedStatus:
    feed: Feed
    items: int
    pulled: int
    hours_in_feed: float
    sample_kbps: int | None = None
    error: str | None = None
    extra: dict = field(default_factory=dict)


def status(cfg: Config, feed: Feed, out_root: Path | None = None) -> FeedStatus:
    out_dir = (out_root or (cfg.path("sets") / "feeds")) / feed.key
    archive = out_dir / "_archive.json"
    pulled = len(json.loads(archive.read_text())) if archive.exists() else 0
    try:
        eps = fetch_feed(feed)
    except Exception as e:  # noqa: BLE001
        return FeedStatus(feed, 0, pulled, 0.0, error=str(e)[:80])
    hours = sum((e.duration_s or (feed.typical_minutes or 60) * 60) for e in eps) / 3600
    return FeedStatus(feed, len(eps), pulled, hours)
