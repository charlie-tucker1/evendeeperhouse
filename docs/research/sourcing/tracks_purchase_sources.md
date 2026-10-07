# Where to legally acquire full-length deep / melodic / tech house tracks for a 1,000–5,000-track offline mixing library (as of October 2026)

Scope note: research conducted 2026-10-07 from the US. Several primary pages were blocked to automated fetching (Traxsource release pages returned HTTP 502/403, Bandcamp label pages returned a bot "Client Challenge", junodownload.com was unreachable through the proxy, bpmmusic.io is JavaScript-only). Where a primary page could not be read, the secondary source and its date are stated and the claim is marked accordingly. Anything dated 2023 or earlier is flagged "possibly outdated".

Two headline changes since 2025 that reshape the landscape:
1. **Juno Download shut down on 1 June 2026** (re-downloads of past purchases still work, no new sales) — [Digital DJ Tips, 8 Jun 2026](https://www.digitaldjtips.com/juno-download-shuts-down-after-20-years/).
2. **Beatsource was merged into Beatport starting 3 March 2026**; the open-format catalogue and "DJ Edits" now live in a new Beatport "Professional+" tier — [Beatportal, 2 Mar 2026](https://www.beatportal.com/articles/1291036-beatport-and-beatsource-to-unite-into-one-premium-dj-platform).

---

## Key Question 1 — Beatport (store): pricing, formats, filters, taxonomy, bulk workflow, Streaming/LINK DRM, API v4

### Takeaway
Beatport is the deepest single catalogue for deep/melodic/tech house; US per-track prices are $1.49 / $1.69 / $2.49 for MP3 with a flat +0.70 "local currency units" (so +$0.70 in the US) to get WAV or AIFF. Purchases are ordinary downloadable files; Beatport Streaming (ex-LINK) files are locked inside DJ software and are unusable in a custom DSP pipeline. There is no public "Extended Mix" filter that I could verify, and there is no sanctioned self-serve API v4 access path.

### Cited Findings
**Per-track prices and formats**
- Beatport's Deep House Top 100 (fetched 2026-10-07, US IP) shows every track at one of three prices: $1.49, $1.69 or $2.49; only a single (MP3) price is displayed per track — [Beatport Deep House Top 100](https://www.beatport.com/genre/deep-house/12/top-100).
- Lossless upgrade: "pay the difference (0.70 units of your local currency)" at checkout; lossless formats offered are WAV and AIFF (FLAC not mentioned for store purchases) — [Beatport Support, "Upgrading Purchased tracks from MP3 to Lossless (Beatport Store Only)", last updated 5 May 2026](https://support.beatport.com/hc/en-us/articles/8980748912020-Upgrading-Purchased-tracks-from-MP3-to-Lossless-Beatport-Store-Only).
- Secondary confirmation of the price ladder: "$1.49 catalogue, $1.69 new releases, $2.49 exclusives; lossless costs about $0.75 more per track" — [The DJ Diaries, Nov 2025, modified 5 Oct 2026](https://thedj-diaries.com/dive-deep-your-ultimate-guide-to-dj-music-downloads/). (The $0.75 figure conflicts with Beatport's own 0.70; trust the Beatport help centre.)
- Secondary: "$1.49–2.49 per MP3 track; $2.49–3.49 per WAV track" — [Digital DJ Pool blog, 7 Apr 2026](https://digitaldjpool.com/blog/where-do-djs-get-their-music/). (The WAV range is ~$0.30 higher than Beatport's own +0.70 math; treat Beatport's figure as authoritative.)
- Possibly outdated: in 2016 the lossless surcharge was a flat 75¢, and Beatport coupons typically took 10–15% off — [DJ TechTools, 14 Mar 2016](https://djtechtools.com/2016/03/14/what-digital-stores-have-the-best-prices-on-dj-music-320-wav).
- Beatport's own editorial says AIFF downloads from the store carry metadata and artwork whereas WAV lacks metadata; it recommends AIFF or FLAC for store downloads — [Beatportal, 21 Jan 2025](https://www.beatportal.com/articles/798615-what-is-the-best-audio-format-for-djs).
- File sizes for a 6-minute track (Beatport's figures): WAV/AIFF ~63 MB, FLAC ~35–40 MB, 320 kbps MP3 ~14.4 MB — [Beatportal, 21 Jan 2025](https://www.beatportal.com/articles/798615-what-is-the-best-audio-format-for-djs).

**"Extended Mix" filtering**
- The Deep House Top 100 page exposes column headers only ("Title/Artists", "Label/Remixers", "Subgenre/BPM & Key", "Released"); no Extended Mix or length filter was visible — [Beatport Deep House Top 100](https://www.beatport.com/genre/deep-house/12/top-100).
- Beatport's help centre documents a **Key** filter available "in any track list" (My Beatport, artist pages, genre pages via the Tracks tab) — [Beatport Support, "How do I filter by key", updated 5 May 2026](https://support.beatport.com/hc/en-us/articles/4412511051668-How-do-I-filter-by-key). No help article for a length/mix-name filter was found.
- Of the 100 Deep House chart entries, 12 titles end in "Extended Mix" and several more use "Extended" / "Extended Remix" — [Beatport Deep House Top 100](https://www.beatport.com/genre/deep-house/12/top-100).

**Genre taxonomy**
- Beatport has a dedicated Deep House genre page (genre id 12) — [Beatport Deep House Top 100](https://www.beatport.com/genre/deep-house/12/top-100). The /genres index page returned 404 to the fetcher, so the full taxonomy could not be read directly in this run (see Gaps).
- ZIPDJ's pricing page lists "House", "Deep House", "Tech House" and "Melodic House & Techno" as genre names — the last being Beatport's taxonomy string — [ZIPDJ pricing](https://www.zipdj.com/pricing).

**Bulk purchase workflow**
- Beatport supports multiple named carts: use the arrow beside any Buy button to create/choose a cart; manage at beatport.com/account/carts (create, rename, set default); "Main Cart" and "Hold Bin" are fixed; tracks can be moved between carts singly or in batches via MOVE TO — [Beatport Support, "How do I use multiple custom carts", updated 17 Sep 2026](https://support.beatport.com/hc/en-us/articles/4412527201556-How-do-I-use-use-multiple-custom-carts).
- DJ.Studio's "Legalize Mix" feature generates a Beatport cart of the tracks used in a mix for bulk purchase at export — [DJ.Studio Help, 4 May 2026](https://help.dj.studio/en/articles/12332505-beatport-beatsource-streaming-vs-shop-in-dj-studio).
- Beatport Streaming "Essential" lists "unlimited purchase re-downloads" as a plan feature, implying re-downloads are limited for non-subscribers — [stream.beatport.com](https://stream.beatport.com/). (The dedicated re-download help article returned 404.)

**Beatport Streaming (formerly LINK) — tiers, DRM, usability**
- Current tiers (fetched 2026-10-07, USD): Essential $10.99/mo or $109/yr (full-track playback, "high-quality" streaming, unlimited purchase re-downloads); Advanced $15.99/mo or $159/yr (DJ-software integrations, stem separation, Traktor Play licence); Professional $29.99/mo or $299/yr (1,000-track offline storage, lossless FLAC streaming); Professional+ $34.99/mo or $349/yr (adds open-format "DJ Edits"). Annual saves 17%. Up to five devices. DJ Edits "cannot be purchased or downloaded" — [stream.beatport.com](https://stream.beatport.com/).
- Offline locker is deleted on cancellation and "accessible only on the device it was originally created, within the DJ software it was originally created"; it cannot be moved between devices or DJ software — [Beatport Support, updated 5 May 2026](https://support.beatport.com/hc/en-us/articles/10922320713236-Will-my-offline-locker-be-deleted-if-I-cancel-my-subscription).
- Review (possibly outdated): Beatport music cannot be exported to USB for CDJs, metadata cannot be edited, tracks cannot be edited in a DAW, the DJ app's Record feature is disabled with Beatport music, offline files play only within the app while logged in, and the terms limit use to personal, non-public-performance — [Digital DJ Tips review, 2019, updated 20 Aug 2023](https://www.digitaldjtips.com/reviews/beatport-link-music-streaming-for-djs/).
- DJ.Studio: "You cannot publish DJ mixes with streaming files"; streaming requires Advanced or Professional; the shop gives 2-minute label-chosen previews, streaming gives full tracks — [DJ.Studio Help, 4 May 2026](https://help.dj.studio/en/articles/12332505-beatport-beatsource-streaming-vs-shop-in-dj-studio).
- Beatsource migration: Beatsource ($12.99) users move to Beatport Advanced ($15.99 after 3 months); Beatsource Pro+ ($34.99) maps to Beatport Professional+ at the same price; standalone Beatsource sunsets; purchase history transfers as playlists — [Beatportal, 2 Mar 2026](https://www.beatportal.com/articles/1291036-beatport-and-beatsource-to-unite-into-one-premium-dj-platform).

**API v4**
- The community `beets-beatport4` plugin states "it is also currently not possible to request API access the 'normal' way" (client credentials or Beatport-issued token); it works by scraping the public OAuth client ID from Beatport's own API docs site and logging in with a user's Beatport username/password (stored unencrypted) or a browser-copied token; token endpoint `https://api.beatport.com/v4/auth/o/token/` — [GitHub: Samik081/beets-beatport4](https://github.com/Samik081/beets-beatport4).
- `https://api.beatport.com/v4/docs/` returns HTTP 200 but is a JavaScript single-page app (only "API Docs" in the static HTML), so no access-policy text could be read without a browser — observed via curl on 2026-10-07 (no citable text).
- Third-party scrapers/wrappers exist (e.g., an Apify "beatport-scraper" actor, and MCP servers wrapping Beatport) — [Apify listing](https://apify.com/crawlerbros/beatport-scraper.md); these are not Beatport-sanctioned.

### Inferences
- A US buyer should model Beatport at **$1.49–$2.49 per MP3 and $2.19–$3.19 per WAV/AIFF**; with the Deep House chart mix of $1.49/$1.69/$2.49, a blended average of roughly $1.70 (MP3) / $2.40 (lossless) is realistic. Older catalogue tends to the $1.49 tier.
- Because the surcharge is a flat +0.70, lossless costs ~+41% at the $1.69 tier but only ~+28% at the $2.49 tier.
- Beatport Streaming/Professional (FLAC, 1,000-track locker) is the cheapest way to *listen* to 1,000 lossless tracks, but it is useless for a custom offline DSP pipeline: the files are software-locked, device-locked, non-exportable and deleted on cancel.
- No verified "Extended Mix" filter exists. Practical workaround: query by genre and sort/parse titles for "Extended" strings, or simply rely on the fact that underground deep/melodic/tech house "Original Mix" releases are already 6–8 minute DJ versions (the radio-edit/extended split is mostly a commercial-dance phenomenon). Track durations are shown on release pages, so a length threshold can be applied manually or via scraped metadata.
- Programmatic metadata access requires either the unofficial docs-client-ID login path or a scraper; both likely sit outside Beatport's ToS and may break without notice.

### Gaps
- Beatport's MP3 bitrate (believed 320 kbps) was not stated on any page fetched.
- Full Beatport genre/sub-genre list (Melodic House & Techno, Tech House, Minimal / Deep Tech, Afro House, Organic House, Progressive House, "DJ Tools" genre) could not be fetched directly (/genres returned 404); only Deep House was confirmed.
- No explicit "DRM-free" statement for store purchases was found; the plain MP3/WAV/AIFF download and re-download flows imply ordinary files, but this is inference.
- Re-download limits for non-subscribers (the help article returned 404).
- Cart size limits, "Buy whole release" button text, and any volume discount — none documented in the pages fetched.
- Official Beatport API v4 access policy (partner-only vs. closed) could not be read from Beatport itself.

---

## Key Question 2 — Traxsource: pricing, formats, house depth, acapellas/instrumentals/DJ tools

### Takeaway
Traxsource is the house specialist (Deep House, Soulful House, Afro House, Jackin, Tech House, Melodic/Progressive, Minimal/Deep Tech are all first-class genres) and sells in MP3, WAV and AIFF; visible US prices are $1.49 / $1.99 / $2.49 per track. It has dedicated Acapella, Efx/DJ Tools and STEMS categories. Whether lossless costs extra could not be confirmed from Traxsource itself in this run.

### Cited Findings
- Traxsource's Deep House Top 100 shows single prices of $1.49, $1.99 or $2.49 per track; each track has an "Add to Cart" button; some items are "Album Only"; no bulk "buy all" control was visible; no separate WAV/AIFF price or format toggle appeared in the chart view — [Traxsource Deep House Top 100](https://www.traxsource.com/genre/13/deep-house/top).
- Site meta description: "Download Real House and Electronic Music in AIFF, WAV and MP3 format" — [Traxsource Deep House Top 100](https://www.traxsource.com/genre/13/deep-house/top).
- Genre navigation (fetched 2026-10-07): House, Deep House, Soulful House, Garage, Afro House, Nu Disco / Indie Dance, Jackin House, Tech House, Techno, Classic House, Soul / Funk / Disco, Afro / Latin / Brazilian, Melodic / Progressive House, Minimal / Deep Tech, plus Lounge / Chill Out, Electronica, Broken Beat / Nu-Jazz, World, Drum & Bass, Pop / Dance, Electro House, Leftfield, R&B / Hip Hop, **Sounds Samples & Loops, Acapella, Beats, Efx / DJ Tools, and STEMS** — [Traxsource Acapella genre page](https://www.traxsource.com/genre/7/acapella).
- The Acapella genre page lists a Top 10 (nine tracks at $1.49, one at $1.99) and 48+ releases in its grid with a "SEE ALL" link; one acapella carried an "audio origin" flag ("Scanned, but not verifiable as Human Made or AI Assisted") — [Traxsource Acapella genre page](https://www.traxsource.com/genre/7/acapella).
- Deep House chart titles include many "Extended Mix"/"Extended Club Mix", "Original Mix" and dub versions, and zero "Instrumental" titles in the 73 visible entries — [Traxsource Deep House Top 100](https://www.traxsource.com/genre/13/deep-house/top).
- Secondary: Traxsource prices "start at around $1.99" (no format breakdown) — [The DJ Diaries, Nov 2025](https://thedj-diaries.com/dive-deep-your-ultimate-guide-to-dj-music-downloads/). (Conflicts with the $1.49 entries seen on Traxsource's own chart.)
- Secondary: Traxsource (since 2004) focuses on "underground house music" plus techno, progressive house and nu-disco; formats AIFF, WAV and MP3; "purely a download store" — [Digital DJ Tips, "11 Best Music Download Stores", updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- Possibly outdated: a March 2018 price restructure made "AIFF/WAV packages more affordable", cut exclusive promo tracks by $0.50 and introduced a "classic" (older-than-90-days) price tier — [5 Magazine, 6 Mar 2018](https://5mag.net/news/traxsource-mp3-price-2018/).
- Possibly outdated: in 2016 Traxsource stocked only ~55% of a test basket of tracks versus Beatport's 80% — [DJ TechTools, 14 Mar 2016](https://djtechtools.com/2016/03/14/what-digital-stores-have-the-best-prices-on-dj-music-320-wav).

### Inferences
- The three-tier $1.49/$1.99/$2.49 ladder likely corresponds to Traxsource's catalogue/new/exclusive-promo tiers (by analogy to Beatport and the 2018 restructure), with older releases at $1.49.
- The STEMS and Acapella categories make Traxsource the most useful store for *official* stem-like material in the house domain; combined with "Efx / DJ Tools" this is a real (if small) source of artefact-free vocal/instrumental separations.
- For deep/soulful/afro house, Traxsource is likely to have labels and releases absent from Beatport; for melodic house & techno and tech house, Beatport probably has deeper coverage.

### Gaps
- **Lossless pricing policy unverified**: release pages (which show per-format prices) returned HTTP 502/403 to both WebFetch and curl, and traxsource.com/help and /faq returned 404. I could not confirm whether WAV/AIFF cost the same as MP3 or carry a surcharge.
- MP3 bitrate not stated on any fetched page.
- Catalogue size, re-download policy, DRM statement, bulk-buy or cart limits — not found.
- Size of the STEMS category and whether items are label-supplied multitrack stems — the STEMS genre page URL I guessed returned 404.

---

## Key Question 3 — Bandcamp: FLAC, pay-what-you-want, label pages, discounts, tooling

### Takeaway
Bandcamp sells DRM-free downloads in eight formats (including FLAC, WAV, AIFF, ALAC, MP3-320, MP3-V0) chosen at download time for one price set by the artist/label; it is the only major source where lossless costs nothing extra by design. It is poorly suited to bulk purchasing (one release at a time) and its label pages are protected against automated access, but a purchased collection can be bulk-downloaded with the unofficial `bandcamp-dl` script.

### Cited Findings
- Buyers can take "any (or all)" of: MP3 V0, MP3 320, FLAC, AAC, Ogg Vorbis, ALAC, WAV, AIFF, selected from a dropdown next to the download link — [Bandcamp Help, "Download formats", dated 12 Jun 2026](https://get.bandcamp.help/hc/en-us/articles/23020648367255).
- Artists keep 82% of revenue and set their own prices; purchased music can also be streamed in the app — [Digital DJ Tips, updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- Bandcamp "is less suited to bulk buying" (said in the context of replacing Juno Download) — [Digital DJ Tips, 8 Jun 2026](https://www.digitaldjtips.com/juno-download-shuts-down-after-20-years/).
- Across ~6.7 million logged sales (Sep–Dec 2020), buyers paid on average ~1.24× list price, and paid more on $0 pay-what-you-want items on Bandcamp Fridays — [Components, Mar 2021 (possibly outdated)](https://components.news/bandcamp-the-chaos-bazaar/).
- US sales tax: Bandcamp collects sales tax on digital items in 31 states plus DC; **Florida is not on the list** (nor are CA, NY, OR), so a Miami buyer should see no sales tax on digital purchases — [Bandcamp Help, "What about taxes", 3 Jun 2026](https://get.bandcamp.help/en/articles/15263230-what-about-taxes).
- `bandcamp-dl` (iliana) downloads your **entire purchased collection**, albums as ZIPs and singles individually; auth via the bandcamp.com `identity` cookie (auto-read from Firefox/Chrome via browser-cookie3, or passed with `--identity`); default format FLAC, with `--format` options aac-hi, aiff-lossless, alac, flac, mp3-320, mp3-v0, vorbis, wav; "This script only downloads items you've purchased"; uses undocumented APIs and may break — [GitHub: iliana/bandcamp-dl](https://github.com/iliana/bandcamp-dl).
- Other PyPI tools (`bandcamp-downloader`, `bcamp-dl`) target public/free pages rather than owned collections — [PyPI: bandcamp-downloader](https://pypi.org/project/bandcamp-downloader/0.0.8.post11), [PyPI: bcamp-dl](https://pypi.org/project/bcamp-dl).
- Many artists on Bandcamp offer FLAC and WAV — [Internet Tattoo, 27 Dec 2024](https://www.internettattoo.com/blog/best-sites-to-download-dj-music-tracks).

### Inferences
- For a lossless library, Bandcamp is the cheapest *per lossless track* among the stores (no surcharge), but effective spend depends on label list prices; EP/album bundles typically price several tracks together, so per-track cost is often below Beatport's lossless price.
- The workflow is: buy release-by-release on the site (no multi-release cart across labels), then run `bandcamp-dl --format flac` once to pull everything. This is the only store in this survey with a working "download my whole purchased library" CLI.
- Because all formats are included, buying on Bandcamp lets the project A/B the same master as FLAC vs MP3-320 at no extra cost — useful for the lossy-vs-lossless DSP comparison.

### Gaps
- Label pages (Anjunadeep, All Day I Dream, Innervisions, Keinemusik, Life and Death, Crosstown Rebels, Hot Creations, Toolroom, Defected, Glasgow Underground, Sol Selectas): every `<label>.bandcamp.com/music` request returned HTTP 200 with a bot "Client Challenge" page, so I could not verify which labels actually maintain Bandcamp stores or what they charge. Treat label presence as unverified in this run.
- No current (2025–2026) statistics on typical per-track or per-EP prices for dance labels, or on the share of pay-what-you-want items.
- Bandcamp discount codes / bulk behaviour: no documentation fetched. Bandcamp Friday (fee-waiver days) is referenced only in the 2021 dataset; current schedule not verified.
- Whether Bandcamp caps re-downloads — not addressed in the help article fetched.

---

## Key Question 4 — Juno Download and other stores (7digital, Qobuz, HDtracks, Volumo, Boomkat)

### Takeaway
Juno Download no longer exists as a store (closed 1 June 2026). Among the remaining alternatives, Volumo (~€1.49/track, same price for MP3 or lossless, credit-top-up discounts of 5–30%) is the closest replacement for underground house; 7digital, Qobuz and HDtracks are album/hi-res oriented and weak for DJ-oriented house.

### Cited Findings
- Juno Download "stopped trading on Monday 1 June 2026 with no warning"; past purchases remain re-downloadable after login (older orders may need an email with the order number); the farewell page points users to Traxsource, Beatport, Mixupload and Volumo; Juno Records (vinyl) is a separate company and still trades — [Digital DJ Tips, 8 Jun 2026, updated 25 Jun 2026](https://www.digitaldjtips.com/juno-download-shuts-down-after-20-years/).
- Possibly outdated: Juno Download offered MP3, WAV, FLAC and AIFF — [Internet Tattoo, Dec 2024](https://www.internettattoo.com/blog/best-sites-to-download-dj-music-tracks); MP3 from ~$1.19 with lossless at a "modest additional charge" — [The DJ Diaries, Nov 2025](https://thedj-diaries.com/dive-deep-your-ultimate-guide-to-dj-music-downloads/).
- Volumo: tracks typically ~€1.49 (artist-set); formats MP3 and lossless WAV, AIFF, FLAC at the **same price**; a credit system where pre-loaded funds (spend within 30 days) earn 5–30% discount scaling with amount loaded; genres techno, house, d&b, breaks, electronica; "download it again whenever you need" — [Crossfader, 25 Sep 2025, modified 11 May 2026](https://wearecrossfader.co.uk/blog/volumo-review/). Digital DJ Tips calls Volumo "the closest in spirit to Juno, with format choice after purchase and no sales-based Top 100" — [Digital DJ Tips, Jun 2026](https://www.digitaldjtips.com/juno-download-shuts-down-after-20-years/).
- 7digital: "no MP3s; hi-res focus", "looking tired", not available in Europe — [Digital DJ Tips, updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- Qobuz: strongest in classical/jazz with electronic as one genre among several; "frequent streaming upsells" — [Digital DJ Tips, updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- HDtracks: pop/rock/jazz/classical, hi-res (e.g., 24/96), "expensive, album-focused rather than track-focused" — [Digital DJ Tips, updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- Boomkat: underground/alternative (dub techno, ambient, grime…), MP3/FLAC — [Digital DJ Tips, updated 11 Jan 2026](https://www.digitaldjtips.com/?p=2774639).
- Possibly outdated: Bleep charged ~$2.19 for 24-bit WAV above its standard WAV/FLAC price (2016) — [DJ TechTools, 2016](https://djtechtools.com/2016/03/14/what-digital-stores-have-the-best-prices-on-dj-music-320-wav).

### Inferences
- Volumo's credit-discount model (up to 30% off) makes it potentially the cheapest *lossless* per-track store for a 1,000+ track buy if its catalogue covers the needed labels — but its catalogue depth for melodic house/tech house is unverified.
- 7digital/Qobuz/HDtracks should be considered only for specific artist albums; they lack DJ-store features (BPM/key, mix-version taxonomy) and are priced per album.

### Gaps
- No per-track USD prices for 7digital, Qobuz or HDtracks were found in 2025–2026 sources.
- Volumo catalogue size, US pricing in USD, and MP3 bitrate — not found.
- Mixupload (named on Juno's farewell page) — not researched.

---

## Key Question 5 — DJ record pools (BPM Supreme, DJcity, ZIPDJ, Digital DJ Pool, Late Night, DMS, Promo Only, Club Killers)

### Takeaway
Record pools are the cheapest way to accumulate thousands of 320 kbps MP3s ($10–$50/month, often unlimited), but they are promotional services for working DJs with mainstream/open-format catalogues; only Digital DJ Pool (indie house/deep/tech/afro, $9.99/mo) and ZIPDJ (60+ genres incl. House, Deep House, Tech House, Melodic House & Techno; $25–$50/mo) materially cover the target genres, and WAV is essentially absent. Their terms are promotional-use licences, not purchase licences — a legal grey zone for research datasets.

### Cited Findings
**Prices and plans (vendor pages first, then comparisons)**
- ZIPDJ (vendor page): Pro Unlimited $50/mo ($35 first month), $45/mo billed quarterly, $35/mo billed yearly; Silver $25/mo (50 downloads/mo); Gold $30/mo (100 downloads/mo); "Highest Quality MP3s (320kbps)"; "60+ Genres" including House, Deep House, Tech House and Melodic House & Techno; no working-DJ verification mentioned; **WAV not mentioned** — [ZIPDJ pricing](https://www.zipdj.com/pricing).
- Digital DJ Pool (vendor blog, 28 Mar 2026, "pricing verified March 2026"): $9.99/mo or $89.99/yr, unlimited 320 kbps MP3 downloads, 200,000+ tracks all from independent labels, 75+ added daily, weekly 25-track "Friday Drop", genres "independent house, deep house, tech house, afro house, techno"; files "yours to keep after cancelling" (self-claim) — [Digital DJ Pool, "Record pool options 2026"](https://digitaldjpool.com/blog/record-pool-options-2026/).
- Same Digital DJ Pool comparison lists: BPM Supreme $24.99/$34.99/$69.99 (320 MP3; hip-hop/R&B/pop/Latin/EDM; no house category named); DJcity $19.99/$29.99 (320 MP3; urban/open-format); Club Killers $29.99 (320 MP3; open-format edits/mashups); **zipDJ $19.99/$29.99 "320kbps MP3 and lossless WAV"**; DMS $19.99/$29.99/$49.99 (320 MP3; mainstream/classics; tiers by download volume); Late Night and Headliner "varies" — [Digital DJ Pool, 28 Mar 2026](https://digitaldjpool.com/blog/record-pool-options-2026/). Note the publisher is itself a pool.
- DJcity (vendor help centre, 31 Mar 2026): $10 intro then $34.99/mo; 250+ genres; bulk downloads as native MP3 (no zip); regional catalogues (USA, Latino, UK, Germany, Japan, South Asia); claims ZipDJ is $35 intro then $50/mo with 60+ genres and zip-file bulk downloads — [DJcity vs ZipDJ 2026](https://support.djcity.com/hc/en-us/articles/32309678969236-DJcity-vs-ZipDJ-record-pool-comparison-2026). **Conflicts** with Digital DJ Pool's $19.99/$29.99 figure for DJcity; prefer DJcity's own page.
- Second Digital DJ Pool article (7 Apr 2026): BPM Supreme $22.99–$34.99 (Standard/Premium), DJcity ~$29.95, ZIPDJ $25–$50 (Intro/Pro/Unlimited), Beatport LINK $14.99–$39.99 — [Digital DJ Pool, "Where do DJs get their music"](https://digitaldjpool.com/blog/where-do-djs-get-their-music/). (Internal inconsistency with the same publisher's March table; and the Beatport LINK range is outdated versus stream.beatport.com's $10.99–$34.99.)
- BPM Supreme's pricing URL redirects to bpmmusic.io/supreme, a JavaScript-only page whose meta description lists "open format, Latin, hip-hop, dance, and more" — [bpmmusic.io/supreme](https://bpmmusic.io/supreme). Plans/prices could not be read.
- Late Night Record Pool: US$47/mo, unlimited 320 kbps MP3, chart hits plus 70s–2000s classics; reviewer says it "lacks disco and house" and does not cover underground dance; must rate each track before download — [Digital DJ Tips review, 2017, updated 30 Aug 2019 (possibly outdated)](https://www.digitaldjtips.com/reviews/late-night-record-pool/).
- ZIPDJ (2020 review, possibly outdated): from $25/mo, top unlimited plan $50 month-to-month; 320 kbps tagged MP3s with artwork; downloads queued and delivered as one .zip; genre labels come from the labels so miscategorisation occurs; "a record pool for working DJs… pools generally require members to be working DJs"; labels supply music in exchange for metrics/promotion — [DJ TechTools, 6–7 Oct 2020](https://djtechtools.com/2020/10/06/digital-record-pools-revisiting-zipdj).
- General: "most digital DJ pools cost roughly $15 to $50 per month"; no pool is described as house-focused — [Magnetic Magazine, 23 Dec 2025](https://magneticmag.com/2025/12/record-pools-for-djs/).
- Beatport's own subscription (Professional+) includes open-format "DJ Edits" that "cannot be purchased or downloaded" — effectively a streaming-only pool — [stream.beatport.com](https://stream.beatport.com/).

### Inferences
- For the target genres only two pools are plausible: Digital DJ Pool (cheapest, indie-house-centric, MP3 only) and ZIPDJ Pro Unlimited (broad, includes Beatport-style "Melodic House & Techno" bucket, MP3; WAV claim unconfirmed). Mainstream pools (BPM Supreme, DJcity, DMS, Late Night, Club Killers) are mostly hip-hop/pop/open-format and are poor fits.
- Pool catalogues are label-promo driven: they skew toward current promo releases rather than deep back-catalogue, and "deep house" tagging is by the uploading label, so genre purity will be lower than on Beatport/Traxsource.
- Licence risk: pools distribute promotional copies to working DJs; their terms (not retrievable here) generally forbid redistribution and are not "purchase" licences. Using pool files as a research dataset is at best unaddressed by the terms and at worst a breach — flag plainly to the user. Store purchases (Beatport/Traxsource/Bandcamp/Volumo) are cleaner.

### Gaps
- Primary terms-of-service text for ZIPDJ (/terms returned 404), BPM Supreme and DJcity could not be fetched; working-DJ eligibility and anti-redistribution clauses are therefore uncited.
- Promo Only "POOL" pricing and formats: no 2025–2026 source found.
- DMS pricing from its own site not fetched (only the competitor's table).
- Whether ZIPDJ actually offers WAV: ZIPDJ's own pricing page says only "320kbps MP3" while Digital DJ Pool's comparison says "320kbps MP3 and lossless WAV" — unresolved conflict.
- Any per-day download throttles behind "unlimited" plans — not documented.

---

## Key Question 6 — Free/promo sources (Bandcamp free, SoundCloud gates via Hypeddit/ToneDen, Beatport free downloads)

### Takeaway
Free download gates deliver whatever file the artist uploaded (typically MP3 of unknown bitrate) one track at a time behind follow/like/comment requirements; they are legal but low-volume and quality-inconsistent, so they are a supplement, not a library-building strategy.

### Cited Findings
- Hypeddit "fan gate": a Hypeddit page linked from a SoundCloud track's Download button; fans log into SoundCloud and click "Download & Like/Follow", with an optional comment-to-download; the artist uploads an MP3 which Hypeddit hosts (SoundCloud itself does not permit direct downloads); Pro plan US$5/mo or $49/yr for artists — [Digital DJ Tips Hypeddit review, 2015, updated 13 Oct 2021 (possibly outdated)](https://www.digitaldjtips.com/reviews/hypeddit/).
- SoundCloud: "free to browse… bitrates vary widely. Some artists enable free downloads" — [Digital DJ Pool, 7 Apr 2026](https://digitaldjpool.com/blog/where-do-djs-get-their-music/).
- Beatport Streaming plans explicitly exclude "free downloads of unpurchased tracks" — [stream.beatport.com](https://stream.beatport.com/). (This implies Beatport still runs occasional free-download promotions, but no current Beatport free-downloads page was found.)
- YouTube/SoundCloud rips are "typically 128 quality" and are exposed on premium systems (quoted from a 2012 DJ TechTools piece) — [Digital DJ Pool, 6 Jul 2026](https://digitaldjpool.com/blog/mp3-vs-wav-for-djs/).

### Inferences
- Free gates are fine for adding a few hundred edits/bootlegs, but the lack of bitrate control (and frequent 128–192 kbps uploads) makes them unsuitable as the backbone of a DSP-mixing dataset; every file should be spectrally audited (see KQ8).
- Free downloads are usually bootleg edits of copyrighted songs; the artist's permission to download does not necessarily clear the underlying rights — a consideration if the dataset will ever be published.

### Gaps
- ToneDen's current download-gate format/quality policy — not researched (no source fetched).
- Whether Beatport still runs a dedicated free-downloads section in 2026 — no page found.

---

## Key Question 7 — Store previews (Beatport/Traxsource 2-minute clips)

### Takeaway
Beatport previews are auto-generated 2-minute clips taken from the middle of the track by default (labels can reposition them); they are not full tracks and are suitable only for metadata/analysis, not for mixing.

### Cited Findings
- Beatport previews are 2-minute clips generated automatically, by default "the exact 2 minutes in the middle of the track"; labels distributing via Proton can set a custom preview start time; a Beatport subscription unlocks "needledrop" (play any part of the track); Bandcamp offers free needledrop previews — [Proton Help Center](https://intercom.help/proton-radio/en/articles/4474941-beatport-2-minute-previews-how-to-control-them-as-a-label-artist-or-dj).
- "Shop gives 2-minute preview clips selected by the record label"; streaming gives full-length tracks — [DJ.Studio Help, 4 May 2026](https://help.dj.studio/en/articles/12332505-beatport-beatsource-streaming-vs-shop-in-dj-studio).
- Beatport Streaming Essential describes "full-track playback replacing lo-fi previews" — [stream.beatport.com](https://stream.beatport.com/).

### Inferences
- Previews are explicitly "lo-fi" per Beatport's own marketing and are 2 minutes long, so they cannot provide intro/outro material for transition modelling; at most they are useful for BPM/key sanity checks or embedding-based similarity, not for audio training of transitions.

### Gaps
- Preview bitrate/codec was not stated by any source fetched (commonly reported as 128 kbps, but unverified here).
- Traxsource preview length/quality — not found.

---

## Key Question 8 — Budget math and the 320 MP3 vs lossless trade-off for DSP mixing

### Takeaway
A 1,000-track library costs roughly $1,500–$2,500 as Beatport MP3, $2,200–$3,200 as Beatport WAV/AIFF, ~$1,600 as Volumo lossless (~€1.49, less 5–30% credit discounts), highly variable but typically lower per lossless track on Bandcamp, and as little as $10–$50 total via a house-oriented record pool (MP3 only, promo licence). Measured evidence shows 320 kbps MP3 retains content to ~19–19.5 kHz and is indistinguishable to most listeners in blind tests, but lossy artefacts become more audible after tempo/pitch processing — relevant to a transition engine.

### Cited Findings
**Price inputs (all 2026 unless flagged)**
- Beatport MP3 $1.49 / $1.69 / $2.49; lossless +0.70 local-currency units — [Beatport Deep House Top 100](https://www.beatport.com/genre/deep-house/12/top-100); [Beatport Support, May 2026](https://support.beatport.com/hc/en-us/articles/8980748912020-Upgrading-Purchased-tracks-from-MP3-to-Lossless-Beatport-Store-Only).
- Independent estimate: upgrading 10,000 Beatport tracks to lossless ≈ $7,000 for a US buyer (0.70 × 10,000) — [Digital DJ Pool, 6 Jul 2026](https://digitaldjpool.com/blog/mp3-vs-wav-for-djs/).
- Traxsource $1.49 / $1.99 / $2.49 (format surcharge unknown) — [Traxsource Deep House Top 100](https://www.traxsource.com/genre/13/deep-house/top).
- Volumo ~€1.49, same price any format, 5–30% credit discount — [Crossfader, 2025/2026](https://wearecrossfader.co.uk/blog/volumo-review/).
- Digital DJ Pool $9.99/mo unlimited 320 MP3 — [Digital DJ Pool](https://digitaldjpool.com/blog/record-pool-options-2026/); ZIPDJ Pro Unlimited $50/mo ($35 first month; $35/mo yearly) — [ZIPDJ pricing](https://www.zipdj.com/pricing).
- Beatport Streaming Professional $29.99/mo for a 1,000-track locked offline locker with FLAC — [stream.beatport.com](https://stream.beatport.com/).

**Storage inputs**
- Per minute of stereo audio: 320 kbps MP3 2.4 MB; 16-bit FLAC 5.6 MB; 16-bit WAV 10.6 MB (DJ TechTools 2017 figures); 10,000 four-minute tracks ≈ 96 GB MP3 / 224 GB FLAC / 424 GB WAV — [Digital DJ Pool, 6 Jul 2026](https://digitaldjpool.com/blog/mp3-vs-wav-for-djs/).
- Six-minute track: MP3 ~14.4 MB, FLAC ~35–40 MB, WAV/AIFF ~63 MB — [Beatportal, 21 Jan 2025](https://www.beatportal.com/articles/798615-what-is-the-best-audio-format-for-djs).

**MP3 vs lossless: measured/technical evidence**
- Spectrogram cutoffs observed with Spek/Spectro: 320 kbps MP3 hard cutoff ~19–19.5 kHz; 256 kbps ~19 kHz; 128 kbps ~16 kHz. Auditing a 3,400-file DJ library found 214 transcoded "fake WAV/lossless" files (~6%), implicating record pools, promo packs and "some Beatport purchases where labels allegedly uploaded the wrong master" — [DJ TechTools forum, 30 Apr 2026 (promotional post by the Spectro app's author)](https://forum.djtechtools.com/t/i-stop-playing-fake-wavs-at-gigs-heres-how-to-audit-your-entire-library-in-minutes/154703).
- Possibly outdated: LAME 320 kbps encodes sometimes show a 16 kHz lowpass and sometimes ~20 kHz depending on encoder version/settings and content; pink-noise test at 320 kbps retained content to ~19.7 kHz — [Audacity forum, Sep 2018](https://forum.audacityteam.org/t/flac-wav-to-mp3-320-kbps-16-khz-cut-off/50352).
- Blind test: in NPR's 2015 quiz (6 songs × WAV/320/128), listeners picked the WAV 36.0% of the time vs a 33.3% chance baseline; 1.6% got all six right; most respondents used headphones — reported in [Digital DJ Pool, 6 Jul 2026](https://digitaldjpool.com/blog/mp3-vs-wav-for-djs/) (publisher sells MP3 subscriptions; possibly biased framing).
- Beatport's editorial: "changing tempo or pitch adds artifacts that are more noticeable in lossy files"; 320 MP3 can sound "thinner" on large systems; 128–192 kbps unsuitable for club systems (no measurements) — [Beatportal, 21 Jan 2025](https://www.beatportal.com/articles/798615-what-is-the-best-audio-format-for-djs).
- Keylock artefacts are attributed to the time-stretch algorithm (e.g., Traktor's Elastique Pro V3) rather than the file format; the CDJ-3000 converts all inputs to 96 kHz/32-bit float internally — [Digital DJ Pool, 6 Jul 2026](https://digitaldjpool.com/blog/mp3-vs-wav-for-djs/).
- Volume-gated DJ advice: don't DJ with files under 320 kbps — [Internet Tattoo, Dec 2024](https://www.internettattoo.com/blog/best-sites-to-download-dj-music-tracks); files below 256 kbps should not be played at a serious gig — [The DJ Diaries, Nov 2025](https://thedj-diaries.com/dive-deep-your-ultimate-guide-to-dj-music-downloads/).

### Inferences (budget table; derived from the cited prices, US buyer, no sales tax on Beatport/Traxsource assumed and none on Bandcamp digital in Florida)
| Route | Per track | 1,000 tracks | 3,000 tracks | 5,000 tracks | Format / licence |
|---|---|---|---|---|---|
| Beatport MP3 (all $1.49) | $1.49 | $1,490 | $4,470 | $7,450 | 320 MP3 (bitrate unverified), personal-use purchase |
| Beatport MP3 (blended ~$1.70) | ~$1.70 | ~$1,700 | ~$5,100 | ~$8,500 | as above |
| Beatport MP3 (all $2.49 new/exclusive) | $2.49 | $2,490 | $7,470 | $12,450 | as above |
| Beatport WAV/AIFF (= MP3 + $0.70) | $2.19–$3.19 (~$2.40 blended) | $2,190–$3,190 | $6,570–$9,570 | $10,950–$15,950 | 16-bit lossless, personal-use purchase |
| Traxsource (single price shown) | $1.49–$2.49 | $1,490–$2,490 | $4,470–$7,470 | $7,450–$12,450 | MP3/WAV/AIFF; lossless surcharge unknown |
| Volumo lossless (~€1.49 ≈ $1.6; 5–30% credit discount) | ~$1.15–$1.55 | ~$1,150–$1,550 | ~$3,450–$4,650 | ~$5,750–$7,750 | WAV/AIFF/FLAC at MP3 price; catalogue depth unverified |
| Bandcamp FLAC | artist-set (no reliable mean) | n/a | n/a | n/a | all formats incl. FLAC/WAV; EP bundles often cheaper per track |
| Digital DJ Pool (1–3 months) | ≈ $0.01–$0.03 | $10–$30 | $10–$30 | $10–$30 (if throughput allows) | 320 MP3 only; promotional licence, indie labels only |
| ZIPDJ Pro Unlimited (1–3 months) | ≈ $0.01–$0.15 | $35–$145 | $35–$145 | $35–$145 | 320 MP3; promotional licence |
| Beatport Streaming Professional | $29.99/mo | not ownable | not ownable | not ownable | FLAC inside DJ app only; unusable in own pipeline |

- Storage for 5,000 six-minute extended mixes: ~72 GB (320 MP3), ~175–200 GB (FLAC), ~315 GB (WAV) — derived from the Beatportal per-track sizes.
- Quality trade-off for the research use case: at 320 kbps the ~19 kHz lowpass removes little musically relevant content, and the NPR data suggests listeners cannot reliably tell; but the pipeline's time-stretch/pitch-shift and crossfade EQ will operate on decoded audio where lossy pre-echo and high-band quantisation are amplified (Beatport's editorial makes this qualitative claim; no measured pre-echo study was found). For *analysis* features (beat tracking, key, structure) 320 MP3 is sufficient; for *rendered* transitions destined for listening tests, lossless masters are preferable, and Bandcamp/Volumo provide them at no premium.
- Audit every acquisition regardless of claimed format: ~6% of one DJ's "lossless" library was transcoded, including some store purchases.

### Gaps
- No peer-reviewed or instrumented study of MP3 pre-echo on kick transients in a DJ-mixing context was found; the "artefacts after tempo change" claim is qualitative (Beatport editorial).
- Beatport's MP3 encoder settings/bitrate are not published on any fetched page.
- Bandcamp per-track price distribution for deep/melodic house labels is unknown, so its column in the table is left blank rather than estimated.
- Record pool "unlimited" plans may rate-limit; the time to pull 5,000 files is undocumented, so the 1-month cost assumption is optimistic.
- Sales tax on Beatport/Traxsource digital purchases for a Florida buyer was not verified (Bandcamp's own page indicates Florida is not taxed for digital items).
