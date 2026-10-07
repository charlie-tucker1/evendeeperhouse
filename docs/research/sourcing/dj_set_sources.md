# DJ-set corpus sourcing (deep / melodic / tech house) — sources, volumes, crowd-audio, RSS route, tooling, rules

Scope note: the coordinator already verified codec/bitrate facts for SoundCloud (AAC 96k/160k free, 256k Go+ with oauth cookie, `download` format only when uploader enables it), Mixcloud (64 kbps AAC+ standard) and YouTube (itag 251 Opus ~130–160k / 140 AAC 128k). Those are taken as given below and not re-derived. Everything marked **[measured 2026-10-07]** is a primary measurement I made during this research with `yt-dlp --flat-playlist` (YouTube channel tabs, SoundCloud user pages) or by parsing live RSS XML; the "source" link for those is the page that was measured. Measurements exclude Shorts tabs, members-only and unlisted videos.

---

## KQ1. Live-stream / video series: recording chain (desk vs crowd), volume, hosting, length

### Takeaway
Ten YouTube channels alone hold roughly **30,000 hours of ≥45-minute DJ-set video** (HÖR ~9,200 h, Boiler Room ~6,400 h, Beatport ~3,500 h, Defected ~2,550 h, Mixmag ~2,550 h, DJ Mag ~2,100 h, Tomorrowland ~2,000 h, Anjunadeep ~1,200 h, RA ~350 h, Cercle ~270 h), so volume is not the constraint — genre filtering, YouTube's 128–160 kbps audio, and anti-bot limits are. Published evidence on the capture chain is thin: Boiler Room is documented as producing "a separate dedicated audio mix" plus a multitrack recording; Ultra's broadcaster "relies heavily on ambience microphones"; Cercle credits a per-show sound engineer; HÖR's chain is undocumented. Crowd-presence therefore has to be validated empirically per series (method proposed under Gaps).

### Cited Findings

**Measured channel volumes (YouTube, ≥45 min entries counted as "sets") [measured 2026-10-07]**

| Channel (tab) | Entries | Total h | ≥45-min entries | ≥45-min hours | Median length |
|---|---|---|---|---|---|
| HÖR Berlin `/streams` — [channel UCmfF7JZv26UUKyRedViGIlw](https://www.youtube.com/channel/UCmfF7JZv26UUKyRedViGIlw/streams) | 8,808 | 8,192 | 8,743 | 8,155 | 55 min |
| HÖR Berlin `/videos` — [same channel](https://www.youtube.com/channel/UCmfF7JZv26UUKyRedViGIlw/videos) | 1,087 | 1,073 | 1,021 | 1,055 | 59 min |
| Boiler Room `/videos` — [@boilerroom](https://www.youtube.com/@boilerroom/videos) | 8,027 | 6,135 | 4,610 | 4,878 | 49 min |
| Boiler Room `/streams` — [@boilerroom](https://www.youtube.com/@boilerroom/streams) | 1,860 | 1,734 | 1,373 | 1,486 | 58 min |
| Beatport `/streams` — [@beatport](https://www.youtube.com/@beatport/streams) | 1,265 | 2,424 | 1,207 | 2,395 | 63 min |
| Beatport `/videos` — [@beatport](https://www.youtube.com/@beatport/videos) | 1,232 | 1,136 | 859 | 1,067 | 60 min |
| Defected Records `/videos` — [channel UCnOxaDXBiBXg9Nn9hKWu6aw](https://www.youtube.com/channel/UCnOxaDXBiBXg9Nn9hKWu6aw/videos) | 4,707 | 2,640 | 1,489 | 2,326 | 7 min (many clips/music videos) |
| Defected Records `/streams` — [same](https://www.youtube.com/channel/UCnOxaDXBiBXg9Nn9hKWu6aw/streams) | 59 | 224 | 56 | 224 | 135 min |
| Mixmag `/videos` — [@Mixmag](https://www.youtube.com/@Mixmag/videos) | 2,815 | 2,204 | 1,583 | 2,056 | 58 min |
| Mixmag `/streams` — [@Mixmag](https://www.youtube.com/@Mixmag/streams) | 290 | 494 | 283 | 492 | 96 min |
| DJ Mag `/streams` — [@DJMag](https://www.youtube.com/@DJMag/streams) | 924 | 1,468 | 876 | 1,440 | 64 min |
| DJ Mag `/videos` — [@DJMag](https://www.youtube.com/@DJMag/videos) | 1,227 | 788 | 514 | 674 | 20 min |
| Tomorrowland `/videos` — [user/TomorrowlandChannel](https://www.youtube.com/user/TomorrowlandChannel/videos) | 2,722 | 2,068 | 1,649 | 1,942 | 58 min |
| Tomorrowland `/streams` — [same](https://www.youtube.com/user/TomorrowlandChannel/streams) | 17 | 63 | 13 | 62 | 244 min |
| Anjunadeep `/videos` — [@Anjunadeep](https://www.youtube.com/@Anjunadeep/videos) | 3,785 | 994 | 427 | 662 | 6 min (mostly track uploads) |
| Anjunadeep `/streams` — [@Anjunadeep](https://www.youtube.com/@Anjunadeep/streams) | 427 | 521 | 424 | 519 | 61 min |
| Resident Advisor `/videos` — [@ResidentAdvisor](https://www.youtube.com/@ResidentAdvisor/videos) | 679 | 388 | 229 | 298 | 16 min |
| Resident Advisor `/streams` — [@ResidentAdvisor](https://www.youtube.com/@ResidentAdvisor/streams) | 19 | 57 | 19 | 57 | 95 min |
| Cercle `/videos` — [@Cercle](https://www.youtube.com/@Cercle/videos) | 200 | 271 | 174 | 267 | 88 min |
| Cercle `/streams` — [@Cercle](https://www.youtube.com/@Cercle/streams) | 3 | 4 | 3 | 4 | 75 min |
| UMF TV `/videos` — [@UMFTV](https://www.youtube.com/@UMFTV/videos) | 532 | 31 | 3 | 3 | 2 min (clips only; no streams tab) |

- Sum of ≥45-min hours across the ten channels above ≈ 30,100 h (HÖR 9,210; Boiler Room 6,364; Beatport 3,462; Defected 2,550; Mixmag 2,548; DJ Mag 2,114; Tomorrowland 2,004; Anjunadeep 1,181; RA 355; Cercle 271) — arithmetic on the measured table above.
- Title-keyword scans are a poor genre proxy: only 177 of ~9,900 Boiler Room titles and 40 of ~9,900 HÖR titles contain "house/deep/melodic/tech"; 962 Mixmag titles contain "Lab"; 1,017 DJ Mag titles contain "live from / sessions / DJ set"; Defected has 656 long-form titles matching "Live from…/@…" venue patterns — [measured from the channel listings above].

**Boiler Room**
- "Each broadcast has a separate dedicated audio mix, and a multi-track recording is also made"; after a show the recording loops for 72 hours; 875,000 YouTube subscribers at the time — [Broadcast Now, "Beats international: live streaming music"](https://www.broadcastnow.co.uk/beats-international-live-streaming-music/5101198.article) (undated in extract; context ≈2015–16, so treat as older information).
- Boiler Room archives both video and audio unless a guest objects; recordings are edited after the event, "audio is sometimes remastered"; master video+audio exist for 4,000+ recordings since 2011; archive described as "10,000s of hours"; final versions posted to YouTube, SoundCloud, boilerroom.tv and the app, typically a few weeks after broadcast; some 2010–12 shows are lost — [RE:VIVE, "Do you even archive? Boiler Room" (12 Feb 2018)](https://revivethis.org/do-you-even-archive-boiler-room/) (2018 — older information).
- Boiler Room says it has organised 8,000+ performances since 2010 (5,000 in 200+ cities); first session March 2010; DICE bought it in 2021 and sold it to Superstruct (KKR) in January 2025 — [Wikipedia: Boiler Room (music broadcaster)](https://en.wikipedia.org/wiki/Boiler_Room_(music_broadcaster)).
- Current (Oct 2026) Boiler Room YouTube descriptions carry the line "Listen to Boiler Room's archive on Apple Music: https://apple.co/BoilerRoom", i.e. the official audio archive is pointed at Apple Music — [measured from @boilerroom video descriptions via yt-dlp, 2026-10-07](https://www.youtube.com/@boilerroom/videos).
- Boiler Room uploaded 200 sets spanning ten years to Apple Music in Aug 2020, each split into individual tracks so "100% of royalties from the streams" go to rights holders — [RA News, 18 Aug 2020](https://ra.co/news/73300) (2020 — older).
- Boiler Room's SoundCloud account `platform` still lists 8,696 tracks; of the 40 most recent, 35 are ≥45 min — [measured 2026-10-07](https://soundcloud.com/platform/tracks).

**Cercle**
- 240+ "Cercle Shows" across 31 countries; founded 2016 (first show Eiffel Tower, Oct 2016); Cercle Festival capacity 24,000 (2022, 2024); Cercle Odyssey (2025 tour) uses rented local sound — [Wikipedia: Cercle (company)](https://en.wikipedia.org/wiki/Cercle_(company)).
- Cercle YouTube descriptions include "This artistic performance has been recorded live" on festival/location sets and name a sound engineer on some shows (e.g. "Agata Dankowska, Sound Engineer" on the Hania Rani Odyssey show) — [measured from @Cercle descriptions, 2026-10-07](https://www.youtube.com/@Cercle/videos).
- Cercle's recent uploads skew to live acts/Odyssey (Max Richter, Hania Rani, Bonobo, Monolink) with DJ sets from Cercle Festival (Dixon, Ann Clue, Disclosure b2b Mochakk, 5,300–8,800 s each) — [same listing](https://www.youtube.com/@Cercle/videos).
- Cercle SoundCloud `cerclelive`: 239 tracks; 16 of the 40 most recent are ≥45 min — [measured 2026-10-07](https://soundcloud.com/cerclelive/tracks).

**HÖR Berlin**
- First stream August 2019; founders moved from Tel Aviv; by Dec 2021 "over 2.5k videos on YouTube", 300k subscribers; room has absorbers above the desk and at the back and is "certainly not the best room for critical listening"; monitoring on ADAM AX-series; article does not describe the capture chain or an audience — [ADAM Audio blog, Dec 2021](https://www.adam-audio.com/blog/hoer-berlin/) (2021 — older).
- hoer.live states "more than 4000 shows in our archive", "broadcasting six days a week", "our content remains freely accessible to everyone", and "Our website cannot be used without the integration of streaming content from YouTube" (i.e. the archive is YouTube-hosted/embedded); paid tiers are Xtra €3.99/month and Max €39.99/year for Track ID, favourites, calendar, shop discount — [hoer.live/members](https://hoer.live/members/).
- The Oct 2022 subscription launch listed "an archive of all broadcasts" among subscriber features while keeping free access for "one million monthly viewers" — [Mixmag Asia, 2022](https://mixmag.asia/read/berlin-streaming-platform-hoer-launches-new-site-subscription-international); the current members page (above) says content remains free.
- Independent index watchthedj.com tags recent HÖR sets as House, Deep House, Tech House, Progressive House, Minimal House, Techno, Deep Techno, hip-hop etc. (Doc Martin, Move D, Traumer, Fritz Kalkbrenner, DJ Hell in May–Aug 2026) — [watchthedj.com/channels/hoer-berlin](https://watchthedj.com/channels/hoer-berlin).
- HÖR publishes an artist performance agreement online — [hoer.live/artist-performance-agreement](https://hoer.live/artist-performance-agreement/) (not fetched; relevant if rights language is needed).

**Mixmag The Lab**
- Mixmag describes The Lab as "our weekly party" celebrating 10 years (≈2011 start), with "hundreds of sets" in the Lab video section on mixmag.net and YouTube — [Mixmag, "10 years of The Lab"](https://mixmag.net/feature/the-lab-10-back-to-back).
- Lab sets are typically ~1 h (e.g. Tom Misch "live 1 hour-set for Lab LDN") — [playingwithsound.net](http://www.playingwithsound.net/news.asp?id=548); Lab LDN has a permanent projection-mapped stage design — [HeavyM blog](https://www.heavym.net/mapping-permanent-stage-design-at-mixmag-lab-london/).

**Ultra / Tomorrowland / festivals**
- Ultra's broadcaster Nomobo runs audio over Dante with Yamaha CL consoles, a large audio crew and an "audio director with EDM experience"; the team "relies heavily on ambience microphones", the promoter supplies a split so every channel is separate, and Orban processing is applied to live and VoD versions to make them louder — [Broadcast Now](https://www.broadcastnow.co.uk/beats-international-live-streaming-music/5101198.article) (older, ≈2015).
- Tomorrowland's official channel holds 1,649 sets ≥45 min (1,942 h), median 58 min — [measured 2026-10-07](https://www.youtube.com/user/TomorrowlandChannel/videos). Tomorrowland also publishes the "Tomorrowland Friendship Mix" as a SoundCloud-backed podcast (271 episodes, see KQ3).
- UMF TV's YouTube `/videos` tab is clips (532 entries, 31 h total, 3 ≥45 min) and has no `/streams` tab — [measured 2026-10-07](https://www.youtube.com/@UMFTV/videos).

**Defected / Anjunadeep / Beatport / DJ Mag / RA**
- Defected's weekly "Defected Radio Show" is uploaded to YouTube at 7,201 s (2 h) (e.g. "Hosted By Monki 02.10.26"), alongside venue sets ("Nic Fanciulli | Live from the Ditch at Defected Malta | Rolling Tech House Mix", 3,756 s) and studio sets ("Leyo | Live from Defected HQ") — [measured 2026-10-07](https://www.youtube.com/channel/UCnOxaDXBiBXg9Nn9hKWu6aw/videos).
- Anjunadeep's `/streams` tab is almost entirely long-form (424 of 427 entries ≥45 min; 519 h) and includes "The Anjunadeep Edition 613 with Eric Luttrell (Live at Explorations)" (7,014 s) — i.e. the Edition series had reached episode ~613 by Oct 2026; 97 `/videos` titles and 2 `/streams` titles contain "Open Air" — [measured 2026-10-07](https://www.youtube.com/@Anjunadeep/streams).
- Beatport's `/streams` tab (1,207 sets ≥45 min, 2,395 h, median 63 min) contains festival stage streams such as "Solomun B2B Patrick Topping Live | Rockstar Energy presents @creamfields 2024 | @beatport Live" (6,839 s) — [measured 2026-10-07](https://www.youtube.com/@beatport/streams).
- DJ Mag `/streams` (876 sets ≥45 min, 1,440 h) includes HQ sessions such as "Dr Dubplate Live From DJ Mag HQ" (3,725 s) — [measured 2026-10-07](https://www.youtube.com/@DJMag/streams).
- The general two-source technique behind crowd-audible DJ recordings (mixer REC OUT + room mics, aligned and blended in a DAW with low-end rolled off on the crowd track) is documented by DJ TechTools — [DJ TechTools, Dec 2017](https://djtechtools.com/2017/12/11/record-mix-dj-set-live-crowd-noise/).

### Inferences
- "Separate dedicated audio mix" + "multi-track recording" (Boiler Room) and "relies heavily on ambience microphones" (Ultra) both imply mixed desk+ambience feeds, so these series should carry crowd signal; HÖR (small closed studio) and studio-type series (Mixmag Lab, DJ Mag HQ, Defected HQ) are the ones most likely to be close to a clean desk feed — but no source states this explicitly, so it must be checked by listening (see Gaps).
- The two HÖR tabs together (~9,900 entries, ~9,260 h, almost all 45–75 min) exceed the ">4000 shows" figure on hoer.live; the members-page number is probably stale. HÖR is the single largest free long-form archive found, but it is techno-heavy; the deep/melodic/tech-house fraction is unknown (watchthedj tags suggest it is material).
- Boiler Room's YouTube `/videos` tab (8,027) plus `/streams` (1,860) ≈ 9,900 entries is consistent with "8,000+ performances" and the 2018 "4,000+ masters" figure, suggesting near-complete public availability of the archive on YouTube.
- Cercle's 200 public videos vs "240+ shows" implies a few dozen removed/private; Cercle's recent output is mostly live acts, so its DJ-set share for these genres is on the order of 100–150 sets (~150–200 h).
- Genre filtering will remove most of the 30k hours. If 20–35% of HÖR/Boiler Room/Beatport/DJ Mag and most of Anjunadeep/Defected/Mixmag Lab long-form content fits deep/melodic/tech house, the order of magnitude is ~8,000–12,000 h of in-genre set video before dedup — enough for a 10k-hour pretraining target only if YouTube's 128–160 kbps audio is acceptable.

### Gaps
- No interview or technical article found that states Boiler Room's, Cercle's or HÖR's microphone configuration (room/crowd mics vs desk-only). The ProSoundNetwork piece "Boiler Room: Where streams can come true" exists but now redirects to a Mix Online category page and could not be read.
- An empirical crowd-presence test (download the last ~90 s of one set per series and measure post-music level/variance; desk feed → near-silence, room mics → applause/chatter) was attempted but could not run here: YouTube media extraction from this datacenter IP returned "Sign in to confirm you're not a bot" and HTTP 429 (see KQ6). The user can run the same test locally with browser cookies; it is cheap (~1 MB per set).
- Per-genre counts per channel are unmeasurable from titles; a tag/description-based or audio-classifier filter is needed.
- Printworks: no official channel found (the `@PrintworksLondon` handle holds 31 short videos). Printworks-recorded sets exist inside Boiler Room/Mixmag/Defected/others' channels but were not enumerated.
- Ibiza venue streams (Hï, Ushuaïa, Pacha, DC-10) were not researched.

---

## KQ2. SoundCloud accounts/series dense in the genres: volume and real obtainable quality

### Takeaway
Label and artist accounts hold thousands of tracks, but most label accounts are dominated by track premieres; the set-dense accounts are Boiler Room (`platform`), Keinemusik, Solomun, Anjunadeep (recent uploads), Toolroom and Cercle. In a 40-track sample of 11 accounts not a single upload exposed an original-file `download` format, so the realistic SoundCloud quality for these accounts is the 160 kbps AAC HLS transcode — unless the show is also distributed as a podcast RSS (KQ3), which serves the original MP3.

### Cited Findings
**Account sizes [measured 2026-10-07 via `yt-dlp --flat-playlist <user>/tracks`]**
- Boiler Room `platform`: 8,696 tracks; 35/40 most recent ≥45 min; 0/40 with `download` format — [soundcloud.com/platform](https://soundcloud.com/platform/tracks)
- Mixmag `mixmag-1`: 7,028 tracks; 6/40 recent ≥45 min (mostly premieres); 0/40 download — [soundcloud.com/mixmag-1](https://soundcloud.com/mixmag-1/tracks)
- Toolroom Records: 2,752 tracks; 22/40 recent ≥45 min (Toolroom Radio episodes + releases); 0/40 download — [soundcloud.com/toolroomrecords](https://soundcloud.com/toolroomrecords/tracks)
- Anjunadeep: 2,740 tracks; 38/40 recent ≥45 min (Edition episodes/sets; 54 h in the 40-track sample); 0/40 download — [soundcloud.com/anjunadeep](https://soundcloud.com/anjunadeep/tracks)
- Glasgow Underground: 2,015 tracks (duration not sampled) — [soundcloud.com/glasgowunderground](https://soundcloud.com/glasgowunderground/tracks)
- Crosstown Rebels: 1,762 tracks; 6/40 recent ≥45 min; 0/40 download — [soundcloud.com/crosstownrebels](https://soundcloud.com/crosstownrebels/tracks)
- All Day I Dream: 761 tracks; 0/40 recent ≥45 min (recent uploads are releases) — [soundcloud.com/alldayidream](https://soundcloud.com/alldayidream/tracks)
- Sol Selectas: 758 tracks (not sampled) — [soundcloud.com/solselectas](https://soundcloud.com/solselectas/tracks)
- Innervisions: 532 tracks; 4/40 recent ≥45 min — [soundcloud.com/innervisions](https://soundcloud.com/innervisions/tracks)
- Afterlife `afterlifeofc`: 491 tracks; 0/40 recent ≥45 min — [soundcloud.com/afterlifeofc](https://soundcloud.com/afterlifeofc/tracks)
- Keinemusik: 433 tracks; 38/40 recent ≥45 min (39.7 h in sample); 0/40 download — [soundcloud.com/keinemusik](https://soundcloud.com/keinemusik/tracks)
- Cercle `cerclelive`: 239 tracks; 16/40 ≥45 min — [soundcloud.com/cerclelive](https://soundcloud.com/cerclelive/tracks)
- Solomun: 117 tracks; 29/40 ≥45 min (36.9 h in sample) — [soundcloud.com/solomun](https://soundcloud.com/solomun/tracks)
- The slugs `hotcreations`, `bedrock-records` and `lane8music` returned HTTP 404 (wrong slugs, not absence of accounts) — [measured].
- SoundCloud's own RSS podcast export is capped at 500 items: the RA Podcast feed holds exactly 500 items (RA.584, Aug 2017 → RA.1059, Oct 2026) while Apple lists 523 episodes; DHA FM holds 500 while Apple lists 598 — [RA feed](https://ra.co/xml/podcast.xml), [DHA feed](https://feeds.soundcloud.com/users/soundcloud:users:15904471/sounds.rss); corroborated by hearthis.at's FAQ noting SoundCloud RSS import is "limited to 500 tracks" — [hearthis.at/faq](https://hearthis.at/faq/).
- Apple Podcasts indexes several SoundCloud-backed DJ feeds that are rich in these genres: DHA FM (Deep House Amsterdam) 598 eps, Miss Monique 169 eps, Atish 113 eps (incl. "Atish 100 — all night live in SF, 5 hours"), Tomorrowland Friendship Mix 271 eps — [iTunes Search API results, 2026-10-07](https://itunes.apple.com/search?media=podcast&term=Deep%20House%20Amsterdam).

### Inferences
- Where a SoundCloud show also has an RSS feed, fetch the RSS enclosure rather than the SoundCloud stream: the enclosure 302-redirects to `cf-media.sndcdn.com` and serves the uploader's original MP3 (verified 82.7 MB / 56 min ≈ 195 kbps VBR for RA.1059; 320 kbps for many others), vs 160 kbps AAC via the player.
- Artist podcast-series accounts (Solomun, Keinemusik, Anjunadeep Edition, Toolroom Radio) are the efficient SoundCloud targets; big label accounts (Crosstown, Innervisions, Afterlife, ADID) are mostly 5–8-minute premieres and should be filtered by duration (`--match-filter "duration>2700"`).
- Roughly: Keinemusik ≈ 400 sets (~400 h), Solomun ≈ 80–100 sets, Anjunadeep ≈ 600+ Edition episodes plus Open Air sets (~700–900 h), Toolroom Radio ≈ 850+ episodes (TR862 in Oct 2026) × 1–2 h, Boiler Room SC up to several thousand sets — but SoundCloud quality is 160k AAC without RSS.

### Gaps
- Durations were sampled only for the 40 most recent uploads per account; full per-account hour counts were not computed (SoundCloud flat listings omit duration; full extraction costs one API call per track).
- Defected, Diynamic and Hot Since 82 SoundCloud pages returned zero entries with an impersonation warning (yt-dlp needs `curl_cffi` for SoundCloud impersonation) and were not re-run.
- Dixon, Âme, Jamie Jones/Paradise, Hot Since 82, Lane 8/This Never Happened, Ben Böhmer, Tinlicker, Lee Burridge, Bedrock/Digweed Transitions, Hot Creations accounts were not measured (wrong/unknown slugs or time).

---

## KQ3. Podcast RSS feeds: which exist, enclosure bitrates, legality of fetching

### Takeaway
A dozen major shows have public RSS feeds with direct MP3 enclosures, and the measured bitrates are far better than streaming: the This Is Distorted network (Defected Radio, Toolroom Radio, Purified, Glasgow Underground Radio) serves ~192 kbps CBR (Clapcast 320), while Podbean/Podtoo/SoundCloud-backed feeds (Hernán Cattáneo Resident, Crosstown Mix Show, Yotto, RA Podcast, DHA, Tomorrowland Friendship Mix, Atish) serve 320 kbps or the original VBR file; Simplecast-hosted feeds are transcoded down to 128 kbps. Together these feeds expose roughly 5,500 episodes ≈ 6,000+ hours of 1–2 h mixes with tracklists in the item descriptions.

### Cited Findings
**Verified feeds (XML fetched and parsed 2026-10-07; bitrate = enclosure `length` × 8 ÷ `itunes:duration`, median over items >10 min)**
- Defected Radio (combined "Defected In The House" feed incl. Glitterbox Radio Show): 1,062 items since Apr 2015, median 60 min, median **192 kbps** (min 128), host audio.thisisdistorted.com — [feed](https://portal-api.thisisdistorted.com/xml/defected-in-the-house); verified by HEAD: Toolroom episode TR862 (2 h) = 288,002,126 bytes `audio/mpeg` → 320 kbps for that item — [enclosure](https://audio.thisisdistorted.com/repository/audio/episodes/TR862_-_TWOHOURSHOW-1790857702281662969-NDMxNzEtMjg4MDAyMTI2.mp3)
- Toolroom Radio: 238 items, median **120 min**, median 191 kbps (152–329) — [feed](https://portal-api.thisisdistorted.com/xml/toolroom-radio)
- Nora En Pure – Purified Radio: 527 items, 60 min, median 192 kbps — [feed](http://portal-api.thisisdistorted.com/xml/nora-en-pure-purified-radio)
- Clapcast (Claptone): 585 items, 61 min, median **323 kbps** — [feed](https://portal-api.thisisdistorted.com/xml/clapcast)
- Glasgow Underground Radio: 178 items, 60 min, median 191 kbps — [feed](https://portal-api.thisisdistorted.com/xml/glasgow-underground-radio)
- MDLBEAST Radio Selects: 203 episodes on the same This Is Distorted platform — [iTunes lookup](https://itunes.apple.com/search?media=podcast&term=Solomun%20%2B1) → [feed](https://portal-api.thisisdistorted.com/xml/mdlbeast-radio)
- RA Podcast: 500 items in feed (Apple lists 523), median 75 min, median computed 320 kbps but variable — RA.1059 is 82,743,239 bytes for 56 min ≈ 195 kbps and ffprobe reports a 195 kb/s VBR MP3 at 48 kHz; enclosure 302-redirects feeds.soundcloud.com → cf-media.sndcdn.com (signed CloudFront URL, `audio/mpeg`) — [feed](https://ra.co/xml/podcast.xml)
- DHA FM (Deep House Amsterdam): 500 items in feed (Apple: 598), median 64 min, median 320 kbps, SoundCloud-backed — [feed](https://feeds.soundcloud.com/users/soundcloud:users:15904471/sounds.rss)
- Hernán Cattáneo – Resident: 809 items since May 2011, 60 min, median **320 kbps** (Podbean; verified 151,081,248 bytes for ep. 804) — [feed](https://podcast.hernancattaneo.com/feed.xml)
- The Crosstown Mix Show (Crosstown Rebels): 100 items, median 90 min, 320 kbps (Podbean) — [feed](https://feed.podbean.com/thecrosstownmixshow/feed.xml)
- Yotto – Odd One Out Radio: 104 items, 61 min, 320 kbps (Podtoo) — [feed](https://feed.podtoo.com/distro/jFBUMUI_)
- Joris Voorn – Spectrum Radio: 100 items (feed-capped; episode 492 is current), 61 min, median 209 kbps (Libsyn) — [feed](https://jorisvoornspectrum.libsyn.com/rss)
- Tomorrowland Friendship Mix: 271 items, 60 min, median 320 kbps (SoundCloud-backed; verified 135,078,593 bytes for a 1 h episode ≈ 300 kbps) — [feed](https://feeds.soundcloud.com/users/soundcloud:users:243635960/sounds.rss)
- Miss Monique: 169 items, 60 min, median 128 kbps (SoundCloud-backed; uploader-dependent) — [feed](https://feeds.soundcloud.com/users/soundcloud:users:17716472/sounds.rss)
- Atish: 113 items, 60 min, median 320 kbps — [feed](https://feeds.feedburner.com/atishmusic)
- Sultan + Shepard – Dialekt Radio: 351 items, 60 min, **128 kbps** (Simplecast `128_default_tc.mp3` transcode) — [feed](https://feeds.simplecast.com/3dnPjov_)
- Beatport's own podcast feeds are stubs (House & Techno: 2 episodes) — [iTunes lookup](https://itunes.apple.com/search?media=podcast&term=Beatport); "Echo System by Cercle" is a 13-episode Acast talk show, not sets — [iTunes lookup](https://itunes.apple.com/search?media=podcast&term=Cercle).
- Shows **not** found in Apple Podcasts: Anjunadeep Edition, Solomun +1, Jamie Jones Paradise, Bedrock/Digweed Transitions, Lane 8 This Never Happened, Dixon/Innervisions, Keinemusik, Afterlife, Mixmag mixes, XLR8R, Pete Tong (BBC feeds are talk/mini-mix only) — [iTunes Search API queries, 2026-10-07](https://itunes.apple.com/search?media=podcast&term=Anjunadeep%20Edition).
- Feed URL discovery needs no API key: `https://itunes.apple.com/search?media=podcast&term=<show>` returns `feedUrl` and `trackCount` — [Apple iTunes Search API](https://itunes.apple.com/search?media=podcast&limit=4&term=Defected%20Radio) (used throughout).
- hearthis.at exposes per-user podcast feeds (`https://hearthis.at/<user>/podcast.xml`, e.g. trackwolves 500 eps, belgradio 140 eps, horatioofficial 500 eps) — [iTunes lookups](https://itunes.apple.com/search?media=podcast&term=Tinlicker).
- `podcast-dl` (Node CLI for bulk-downloading podcast feeds) is maintained: latest 12.1.4, last modified 2026-08-17 — [npm registry](https://registry.npmjs.org/podcast-dl).

### Inferences
- Feed hours (items × median length): Defected/Glitterbox ≈ 1,060 h; Toolroom ≈ 480 h; Purified ≈ 530 h; Clapcast ≈ 590 h; Glasgow Underground ≈ 180 h; RA ≈ 625 h; DHA ≈ 530 h; Cattáneo ≈ 810 h; Crosstown ≈ 150 h; Yotto ≈ 105 h; Spectrum ≈ 100 h; Friendship Mix ≈ 270 h; Miss Monique ≈ 170 h; Atish ≈ 110 h; Dialekt ≈ 350 h → ≈ 6,000 h total, of which ≈ 3,500 h are squarely deep/melodic/tech house (Defected, Toolroom, Purified, Glasgow Underground, DHA, Cattáneo, Yotto, Crosstown, Atish, Friendship Mix partly). These are radio shows/studio mixes: clean desk feeds with no crowd, and often with voice-over IDs/intros that must be trimmed.
- Podcast enclosures are files the publisher deliberately exposes for download by any podcast client; fetching them with a feed downloader does not circumvent a streaming mechanism or platform ToS in the way SoundCloud/YouTube ripping does. Copyright in the recordings (and in the underlying tracks) is unaffected by the delivery mechanism, so the research-use/fair-use question remains the same as for any corpus — this is an inference, not legal advice, and no legal source was consulted.
- Feed item caps (SoundCloud 500, Libsyn 100 in Spectrum's case) mean the oldest episodes of long-running shows are not in the feed; Podbean and This Is Distorted feeds appear uncapped (809 and 1,062 items).

### Gaps
- Mixcloud-only shows (many "Defected Radio"/"Glitterbox" and label shows also on Mixcloud) were not enumerated; coordinator established 64 kbps standard quality, so they are a last resort.
- Anjunadeep Edition has no RSS; it lives on SoundCloud (160k AAC) and YouTube streams (Opus ~130–160k).
- No legal source (case law / counsel) on bulk-downloading public podcast enclosures for research was consulted; the statement above is reasoning from how RSS works.

---

## KQ4. Other hosts: hearthis.at, Audiomack, Twitch, Bandcamp, Beatport, Apple Music DJ Mixes

### Takeaway
hearthis.at is a usable secondary source (192 kbps CBR transcodes, per-user RSS feeds, "Live DJ Sets" group), Twitch is effectively unusable for VOD harvesting (DJ Program VODs/clips containing licensed music are muted or removed; VODs expire), and Apple Music DJ Mixes are a DRM-protected streaming catalogue that now hosts Boiler Room's official audio archive — relevant as a listening reference, not as a corpus source. Audiomack, Bandcamp and Beatport's in-app mixes were not verified.

### Cited Findings
- hearthis.at transcodes uploads to "192 kbit/s constant bitrate, joint stereo"; Premium members can set their own bitrate; accepted formats MP3/WAV/FLAC/OGG; free accounts have a 400 MB/week quota, 5 GB storage, 30-track cap; it can import a SoundCloud RSS (max 500 tracks) — [hearthis.at FAQ](https://hearthis.at/faq/). hearthis.at has a "Live DJ Sets" section and a "DJ Mixes" group — [hearthis.at/livedjsets](https://hearthis.at/livedjsets/), [DJ Mixes group](https://hearthis.at/group/46550/dj-mixes/). Per-user `podcast.xml` feeds exist (see KQ3).
- Twitch DJ Program (this secondary source gives a 5 Oct 2025 launch date, which conflicts with widely reported 2024 program announcements — treat the date as unverified; deals with UMG, WMG, Sony and independents): "The licenses exclusively cover live performances" and "VODs (past broadcasts) and Clips that contain copyrighted music from the program will continue to be muted or removed" — [aidjsets.com, 12 Oct 2025](https://aidjsets.com/blog/twitch-s-dj-program-how-to-legally-stream-music-in-october-2025) (secondary source; Twitch's help pages render via JS and could not be fetched).
- Twitch introduced a 100-hour storage limit for Highlights and Uploads from 19 April 2025 — [Hacker News thread quoting Twitch's infographic](https://news.ycombinator.com/item?id=43139026), [ResetEra](https://www.resetera.com/threads/twitch-is-implementing-a-100-hour-storage-limit-for-highlights-and-uploads-starting-april-19-2025-and-deleting-the-rest.1113855/); past-broadcast retention is widely reported as 7/14/60 days by account tier — [vodfetch.com](https://vodfetch.com/blog/how-long-do-twitch-vods-last) (page returned HTTP 445 on fetch; tiers not independently verified here).
- Boiler Room's audio archive is on Apple Music (200 sets uploaded Aug 2020, split into tracks for royalty payment, with more promised) — [RA News](https://ra.co/news/73300); current Boiler Room YouTube descriptions link "Listen to Boiler Room's archive on Apple Music" — [@boilerroom descriptions, measured 2026-10-07](https://www.youtube.com/@boilerroom/videos).
- Search results for Apple Music DJ Mixes are dominated by DRM-removal marketing pages (e.g. [noteburner](https://www.noteburner.com/apple-music-tips/apple-music-and-drm.html), [dj.studio](https://dj.studio/blog/dj-with-apple-music)), consistent with the catalogue being FairPlay-protected — but no Apple document was fetched to confirm.
- Beatport's YouTube channel is a large set source (≈3,460 h ≥45 min across both tabs) — [measured, KQ1](https://www.youtube.com/@beatport/streams); its podcast feeds are stubs — [KQ3].

### Inferences
- Apple Music DJ Mixes are unusable as a bulk corpus (DRM + per-track splitting that would also break transition continuity for mining) — consistent with the coordinator's assumption; treat as confirmed-by-absence rather than by Apple documentation.
- Twitch's DJ Program makes the live stream the only licensed artefact; any VOD corpus would have to be captured live (e.g. `streamlink`), which is operationally heavy and legally no better than ripping.
- hearthis.at at 192 kbps CBR is better than SoundCloud's 160k AAC for whatever sets exist there, but its catalogue for these genres is small and uncurated (no volume data found).

### Gaps
- Audiomack: not researched (no bitrate/volume facts found within budget).
- Bandcamp: not researched; DJ mixes on Bandcamp are uncommon in these genres and typically paid — unverified.
- Beatport in-app DJ mixes / Beatport Streaming mixes: not researched.
- Twitch VOD retention tiers and Twitch's own DJ Program text not fetched from Twitch (JS-rendered help portal).

---

## KQ5. Volume & storage: hours obtainable per source, storage at target bitrates, dedup

### Takeaway
Across the sources measured, long-form set audio is available on the order of 30,000 h (YouTube, mixed genres) + ~6,000 h (podcast RSS, mostly in-genre radio mixes) + several thousand hours on SoundCloud artist/label accounts; a 10,000-hour corpus is ~0.7 TB at 160 kbps, 1.4 TB at 320 kbps, and ~1.15 TB if resampled to 16 kHz mono PCM for pretraining. Cross-platform duplication (same set on YouTube, SoundCloud, RSS, Apple Music) is pervasive and must be handled by fingerprinting, not metadata.

### Cited Findings
- Storage arithmetic (hours × 3600 × kbps × 1000 / 8): 10,000 h = 0.29 TB @64k, 0.43 TB @96k, 0.58 TB @128k, **0.72 TB @160k**, 0.86 TB @192k, 1.15 TB @256k, **1.44 TB @320k**; 16-bit/44.1 kHz stereo WAV 6.35 TB; FLAC (~60%) ≈ 3.8 TB; 16 kHz mono 16-bit PCM 1.15 TB — computed for this note.
- Measured per-source long-form hours (≥45 min): HÖR 9,210; Boiler Room 6,364; Beatport 3,462; Defected 2,550; Mixmag 2,548; DJ Mag 2,114; Tomorrowland 2,004; Anjunadeep 1,181; RA 355; Cercle 271 — [KQ1 table, measured 2026-10-07].
- Podcast RSS hours ≈ 6,000 (KQ3 inference from verified item counts × median durations).
- Boiler Room publishes each set to YouTube, SoundCloud, its own site and (since 2020) Apple Music — [RE:VIVE 2018](https://revivethis.org/do-you-even-archive-boiler-room/), [RA 2020](https://ra.co/news/73300); Anjunadeep Edition appears both as YouTube streams and SoundCloud uploads — [measured, KQ1/KQ2]; Defected Radio Show appears as a 2 h YouTube video and as a 1 h-median RSS episode (different edits) — [measured, KQ1/KQ3].

### Inferences
- Realistic in-genre yield before dedup: YouTube ~8–12k h (after genre filtering of 30k h), RSS ~3.5k h in-genre, SoundCloud artist/label series ~2–4k h (largely overlapping with YouTube/RSS). Dedup should assume 20–40% overlap between SoundCloud and YouTube for the same series, and that RSS vs YouTube versions of radio shows may be different edits (1 h vs 2 h), so audio fingerprinting (e.g. chromaprint/segment hashing) rather than title matching is required.
- For a 10k-hour self-supervised set at 16 kHz mono the on-disk size (~1.2 TB) is similar to the compressed-source size; keep the compressed originals (~0.7–1.4 TB) and derive.
- Crowd-reaction mining wants the video-series subset (Boiler Room, Cercle festival shows, Beatport/DJ Mag festival streams, Tomorrowland, Defected venue sets); self-supervised pretraining can use everything; transition mining benefits most from the clean radio-show podcasts (no crowd masking) plus HÖR.

### Gaps
- No per-genre hour counts; no measurement of how many SoundCloud sets duplicate YouTube uploads.

---

## KQ6. Tooling: yt-dlp / scdl / RSS fetchers / discovery; rate limits and ban risk

### Takeaway
yt-dlp is the single tool for YouTube and SoundCloud (scdl v3 is now just a yt-dlp wrapper and is not actively developed); `--download-archive` + `--write-info-json` + duration filters give idempotent bulk fetches with tracklist-bearing descriptions. Observed in this session: YouTube returned HTTP 429 after ~30k flat-playlist entries in ~15 minutes from a datacenter IP and refused media extraction with "Sign in to confirm you're not a bot"; yt-dlp 2026.08 also requires a JavaScript runtime for YouTube and `curl_cffi` impersonation for SoundCloud user pages.

### Cited Findings
- yt-dlp option semantics (README): `--download-archive FILE` "Download only videos not listed in the archive file. Record the IDs of all downloaded videos in it"; `--write-info-json` "Write video metadata to a .info.json file"; `--write-description`; `--sleep-requests SECONDS` "sleep between requests during data extraction"; `--sleep-interval/--max-sleep-interval` before each download; `--limit-rate`; `--cookies-from-browser BROWSER[+KEYRING][:PROFILE][::CONTAINER]`; `--match-filters` with `&`-joined comparisons; `-x --audio-format {best,aac,alac,flac,m4a,mp3,opus,vorbis,wav}`; `--embed-metadata`; `--parse-metadata`; `--flat-playlist` ("some entry metadata may be missing"); `--dateafter`; `-N` concurrent fragments; `--impersonate` for TLS fingerprinting — [yt-dlp README](https://github.com/yt-dlp/yt-dlp/blob/master/README.md).
- Observed 2026-10-07 with yt-dlp 2026.08.19 on YouTube watch pages from a cloud IP: `HTTP Error 429: Too Many Requests`, then `ERROR: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies`, plus `WARNING: No supported JavaScript runtime could be found. Only deno is enabled by default; to use another runtime add --js-runtimes RUNTIME[:PATH] ... YouTube extraction without a JS runtime has been deprecated` — [yt-dlp EJS wiki referenced by the warning](https://github.com/yt-dlp/yt-dlp/wiki/EJS), [cookies FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp). Flat channel listings (no media URLs) of ~10k-entry channels completed without error before the 429 appeared.
- Observed on SoundCloud user pages: `WARNING: [soundcloud:user] The extractor is attempting impersonation, but no impersonate target is available` (install `curl_cffi`); listings still returned track counts, but three accounts returned zero entries — [measured].
- scdl: "As of version 3, scdl is a wrapper around yt-dlp with some defaults and patches"; development "is not active"; flags `-l URL`, `-a` (all tracks incl. reposts), `-t` (uploads only), `-f` (likes), `-r` (reposts), `-p` (playlists), `--download-archive`, `--sync`, `--only-original`, `--no-original`, `--opus`, `--flac` (only if original is lossless), `--auth-token`, `--client-id`, `--yt-dlp-args` — [scdl README](https://github.com/scdl-org/scdl/blob/master/README.md).
- SoundCloud's licence to download applies only "where the appropriate functionality has been enabled by the user who uploaded the relevant Content" — [SoundCloud Terms of Use, last amended 17 Aug 2026](https://soundcloud.com/terms-of-use). In my 11-account sample no set exposed that `download` format (KQ2).
- Podcast feed discovery: Apple's iTunes Search API returns `feedUrl`/`trackCount` without a key — [example query](https://itunes.apple.com/search?media=podcast&limit=4&term=Toolroom%20Radio); `podcast-dl` 12.1.4 (2026-08-17) bulk-downloads feeds — [npm](https://registry.npmjs.org/podcast-dl).
- Discovery indexes: watchthedj.com indexes DJ-set videos by channel with genre tags (HÖR page shows 16 pagination pages) — [watchthedj.com](https://watchthedj.com/channels/hoer-berlin).

### Inferences
- Recommended invocations (built from the documented flags above; verify locally):
  - YouTube channel/playlist audio with metadata, idempotent, duration-filtered, gentle:
    `yt-dlp -f "bestaudio[ext=m4a]/bestaudio" --match-filters "duration>=2700 & duration<=12600" --download-archive br.archive --write-info-json --write-description -o "%(channel)s/%(upload_date)s - %(title).120s [%(id)s].%(ext)s" --sleep-requests 1.5 --min-sleep-interval 5 --max-sleep-interval 20 --limit-rate 4M --cookies-from-browser firefox --js-runtimes node https://www.youtube.com/@boilerroom/streams`
    (use `/streams` and `/videos` separately; keep Opus 251 or m4a 140 as delivered — do not transcode; `--dateafter` for incremental runs; `--flat-playlist --print "%(id)s|%(duration)s|%(title)s"` first to plan).
  - SoundCloud user/series: `yt-dlp -f "download/hls_aac_160k/bestaudio" --match-filters "duration>=2700" --download-archive sc.archive --write-info-json --sleep-requests 1 --min-sleep-interval 3 --max-sleep-interval 10 https://soundcloud.com/keinemusik/tracks` (with `pip install "yt-dlp[default,curl-cffi]"`; Go+ 256k only with an oauth_token cookie per coordinator; likes/reposts via `.../likes` and `.../reposts` URLs or scdl `-f/-r` for discovery).
  - RSS: resolve feed via iTunes Search API, then `podcast-dl --url <feed> --include-meta --archive archive.json --threads 2` (or a 30-line Python feedparser loop) — enclosures are plain MP3 URLs, so no format logic is needed.
- The `.info.json` `description` field is where Boiler Room/Mixmag/Anjunadeep/Defected put tracklists and "Live from …" venue strings; RSS `<description>`/`<content:encoded>` do the same for radio shows — both can seed transition timestamps.
- Ban-risk ordering (from what was observed and documented): YouTube media extraction is the most aggressive (IP-level bot checks; cookie use ties activity to an account that can be flagged); SoundCloud tolerated ~15 parallel user-page listings and 40-track extractions per account without errors; RSS/CDN enclosures (CloudFront, Podbean, This Is Distorted) are designed for client download. Run YouTube from a residential IP, single-threaded with sleeps, in daily batches of a few hundred videos; expect to need cookies.
- 1001Tracklists' per-source pages (e.g. Boiler Room, Cercle, HÖR source indexes with tracklists and timestamps) are the obvious discovery/alignment index, but the site returned no response to automated fetches here (HTTP 000) — expect bot protection; use manually or via a browser session.

### Gaps
- 1001Tracklists pages could not be fetched (connection refused/blocked); their coverage counts are unverified.
- `castero` was not evaluated (it is an interactive TUI client, not a bulk fetcher — unverified).
- No documentation found on exact YouTube/SoundCloud request-rate thresholds; the 429/bot-check observation above is a single datapoint from a datacenter IP.

---

## KQ7. Platform rules: ToS text on downloading/scraping, and practical enforcement

### Takeaway
All three platforms prohibit ripping/scraping in their current terms: SoundCloud (amended 17 Aug 2026) bars "copy, rip or capture" and "scraping"; YouTube (effective 15 Dec 2023) bars "access, reproduce, download" except as authorised and "automated means (such as robots, botnets or scrapers)"; Mixcloud bars "downloading, side-loading" and "any robot, spider, scraper". Podcast RSS enclosures are the only route where the publisher itself offers the file for download. Enforcement observed is technical (bot checks, 429s) rather than legal, but the user should treat all YouTube/SoundCloud bulk fetching as ToS-violating regardless of research intent.

### Cited Findings
- SoundCloud Terms of Use (Last Amended August 17, 2026), "Your use of the Platform": "You must not copy, rip or capture, or attempt to copy, rip or capture, any Content from the Platform"; "You must not employ scraping or similar techniques to aggregate, repurpose, republish or otherwise make use of any Content"; automated means "by the use of bots, botnets, scripts, apps, plugins, extensions or other automated means" are prohibited; "circumvent or attempt to circumvent or copy any copy protection mechanism or territorial restrictions"; downloads are licensed only "where the appropriate functionality has been enabled by the user who uploaded the relevant Content" — [SoundCloud Terms of Use](https://soundcloud.com/terms-of-use).
- YouTube Terms of Service (Effective as of December 15, 2023), "Permissions and Restrictions": "You may view or listen to Content for your personal, non-commercial use"; you are not allowed to "access, reproduce, download, distribute, transmit, broadcast, display, sell, license, alter, modify or otherwise use any part of the Service or any Content except: (a) as expressly authorized by the Service; or (b) with prior written permission from YouTube and, if applicable, the respective rights holders"; nor to "access the Service using any automated means (such as robots, botnets or scrapers) except (a) in the case of public search engines, in accordance with YouTube's robots.txt file; or (b) with YouTube's prior written permission" — [YouTube Terms](https://www.youtube.com/t/terms) (fetched directly; the page is robots-disallowed to fetchers).
- Mixcloud Terms: Content "downloading, side-loading, exchanging, creating of derivative works, uploading" is "strictly prohibited" except as expressly permitted; the licence is to "listen to audio streamed from the Website"; clause 5.1.7 "not to obtain or attempt to obtain any Content through any means not intentionally made available"; 5.1.8 "not to use any robot, spider, scraper, or other automated means to access the Platform for any purpose"; 8.2.2 "you will not interfere with the streaming mechanism of the Platform"; offline listening is a Premium feature ("Download shows and listen on the go") — [Mixcloud Terms](https://www.mixcloud.com/terms/) (no last-updated date visible).
- HÖR states its content "remains freely accessible to everyone" and that its site depends on YouTube embeds — [hoer.live/members](https://hoer.live/members/); HÖR also publishes an artist performance agreement — [hoer.live](https://hoer.live/artist-performance-agreement/) (not read).
- Practical enforcement observed: YouTube HTTP 429 and "Sign in to confirm you're not a bot" on media extraction from a cloud IP (KQ6); no SoundCloud blocking observed at the scale tested — [measured 2026-10-07].

### Inferences
- The ToS texts are contractual restrictions between the user and the platform; they do not themselves speak to fair use of the resulting corpus, and this note does not assess copyright or fair-use questions (no legal source consulted). The lowest-friction route that avoids any ToS-circumvention argument is the podcast RSS tier (publisher-offered files) — ~6,000 h, clean desk feeds, 192–320 kbps.
- For YouTube and SoundCloud, the practical risks are account/IP flagging rather than litigation for personal, non-redistributed research; using a personal account's cookies (needed for YouTube reliability and for SoundCloud Go+ 256k) concentrates that risk on that account.

### Gaps
- No source found describing actual enforcement actions (account bans) against research-scale downloading on any of the three platforms.
- Legality of fetching public RSS enclosures for research was not confirmed against a legal source; see KQ3 inference.
