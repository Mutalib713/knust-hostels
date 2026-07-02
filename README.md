# KNUST Hostels Directory — 670+ hostels on & around campus

A comprehensive, searchable directory of hostels, halls, guest houses and student
accommodation **on the KNUST campus and across the close student areas** of Kumasi —
each grouped by its **real location**, pinned to its **exact map spot**, and (where
available) tagged with **photos, amenities, confirmed manager contacts and prices**.

### 🌐 Live: **https://knust-hostels.vercel.app/**

> Independent student project — **not affiliated with KNUST**. Always **visit and verify**
> a room (and its current price) before paying.

---

## At a glance

| | |
|---|---:|
| **Total places** | **669** (on campus + within ~6 km, deduped) |
| **Types** | Hostel **493** · Guest house & Hotel **98** · Homestel (family home) **66** · Apartment/Self-contained **12** |
| On campus / Gaza pocket | 37 / 17 |
| **Confirmed manager contacts** (green tick) | **252** |
| **KNUST-registered** (official KOSASS badge) | **16** |
| With a phone number | 480 |
| With photos | 400 |
| With Ghana Post digital address | 224 |
| With published price ranges | 193 |
| With room count / capacity | 236 / 369 |
| Map-pinned (lat/lng) | 548 |
| Average Google rating | 3.99★ |

## What's in the dashboard

- **Smart search & sort** — search-as-you-type suggestions, sort by **Most popular**
  (default), distance, rating, reviews, price, confirmed-first or name.
- **Filters** — by college, area, **type — 4 buckets (Hostel · Guest house & Hotel · Homestel · Apartment) with counts**, amenities,
  **KNUST-registered-only**, confirmed-only and has-photo, with a one-tap **Reset all filters** and a live **"X found"** count.
- **KNUST-registered badge** — hostels the official **KOSASS** portal lists as registered/approved get a green badge
  (with registration number), plus a Ghana Post **digital address**, **room count / capacity** and official **zone** in the detail view.
- **Detail view** — photo gallery (tap to open a full-screen viewer with **swipe** + arrows),
  amenities, student review themes, **room-type price ranges**, and Call / Map / Directions buttons.
- **Interactive map** with colour-coded pins by area (gracefully degrades to a list-only
  view if offline).
- **"Ask Ama" AI assistant** — a chat helper that answers questions like *"cheapest confirmed
  hostel in Ayeduase under 3000"*, grounded **only** in the real directory data (Google Gemini
  via a serverless function; falls back to offline keyword search if the AI is unavailable).
  Understands campus nicknames (**Hall 7**, Conti, Katanga, Brunei, GUSSS, SRC…), tolerates
  typos ("adeppa" → *did you mean ADEPA?*), and always tells Gemini the true directory totals
  so it never wrongly claims a hostel "isn't in the directory".
- **Message us** — a "💬 Message us" button in the chat header to report a wrong number, a
  closed/missing hostel or suggest a change — either via **WhatsApp** or a quick **email** form.
- **Prices** for 193 hostels (room-type ranges, e.g. *2-in-1 GHS 3,400–5,200*), from the official KOSASS portal + getrooms.co.
- **HostelHubb app promo** — for room **videos** and direct booking (Play Store / App Store).
- **Mobile-first**, dark mode, sticky search, back-to-top, **CSV export**, and a safety disclaimer.

## How to book a hostel (in the app)

Works for both **freshers** and **continuing students**:

1. **Official KNUST portals** — [KOSASS](https://kosass.knust.edu.gh/hostels) ·
   [KOHS](https://kohs.knust.edu.gh/) · [GUSSS](https://gusss.knust.edu.gh/) (halls & approved hostels).
2. **Search & shortlist** here by area, price, distance and college.
3. **Call the manager** (green tick = contact we've confirmed).
4. **Visit before paying** — inspect the room; avoid agents who add fees.
5. **Book online** — [StudentRoomBook](https://studentroombook.com/) ·
   [GH Hostels](https://ghhostels.com/) · [HostelGig](https://hostelgig.com/) · the **HostelHubb** app.

## Files

- **`index.html`** — the dashboard. Open in any browser (no build step). Map tiles need
  internet; everything else works offline.
- **`knust_hostels.csv`** — full dataset for Excel / Google Sheets (UTF-8 BOM).
- **`data.js`** — the data the dashboard reads (`window.HOSTELS` + `window.META`).
- **`ama-brain.js`** — the Ask-Ama matching/answer engine (nicknames, typo tolerance, filters).
  Reads `data.js` live, so **every data update reaches the bot automatically** — the pipeline
  scripts rewrite `data.js` wholesale, which is why the brain lives in its own file.
- **`test_ama.js`** — the bot's QA suite (`node test_ama.js`): checks **every hostel is findable
  by its own name**, every area is parseable, plus ~50 real student phrasings. Run it after any
  data refresh; it exits non-zero on failure.
- **`hostels_tight.json`** — the mapped 501-hostel base set as JSON.
- **`mp_contacts.json`** — Campus-MP / SRC manager contact list.
- **`getrooms_prices.json`** — scraped room-type prices (exact-name matched).
- **`mp_geocode.json`** — coordinates for the contact-only hostels.
- **`enrich_build.py`** — builds `data.js` + the CSV from all of the above.
- **`reclassify_clean.py`** — de-dupes, merges building fragments, and sets the clean **Type** buckets.
- **`kosass_merge.py`** — layers the official KOSASS portal data onto `data.js` (registration, digital
  address, prices, capacity, new residences). Re-runnable; reads `kosass_residences.json`.
- **`kosass_dedupe.py`** — final integrity pass: drops nameless junk + merges duplicate records
  (`--dry` to preview). Re-runnable.
- **`kosass_residences.json`** — raw snapshot of the KOSASS `/api/v1/residences` API (owner/porter PII
  stripped). Not deployed to the live site.

## CSV columns

`Name, Area, Type, Category, Distance_km, Rating, Reviews, Price_from_GHS, Price_source,
Phone, Confirmed_Contact, KNUST_Registered, Reg_No, Digital_Address, Rooms_Total, Male_Cap,
Female_Cap, Amenities, Colleges_nearby, Website, Latitude, Longitude, Google_Maps_URL, Image`

## Coverage by area

| Area | Count |  | Area | Count |
|------|------:|--|------|------:|
| Ayeduase | 247 | | Ayigya | 14 |
| Kotei | 159 | | Gyinyase | 12 |
| Boadi | 48 | | Oduom | 12 |
| **On Campus (KNUST)** | **37** | | Anwomaso | 11 |
| Bomso | 30 | | Anloga Junction | 9 |
| Deduako | 19 | | Emena | 9 |
| Kentinkrono | 18 | | Appiadu | 6 |
| **Gaza** | **17** | | Susuanso (campus edge) | 5 |
| Oforikrom | 15 | | Ahinsan | 3 |

**On-campus group (36)** = traditional halls (University/Katanga, Unity, Republic, Queen's,
Africa, Independence, Chancellor's/Hall 7) **and** private hostels on KNUST land (Spring, Shaba,
Steven Paris, Transport, R-TEP, TEK Credit, GUSSS, Graduate Students' Hostel, on-campus guest houses).

**Gaza group (18)** = the dense, slightly-off-campus hostel pocket NE of campus — Gaza/Ghana
Hostels, ADEPA, Anglican, the African-capital "Courts" (Libreville, Kinshasa, N'Djamena),
Georgia, Crystal Rose, Sun City, Banivillas, etc.

## How it's built

**Layer 1 — the mapped base (501).** Built from an **Apify Google Maps** scrape
(`compass/crawler-google-places`) using a **coordinate-bounded polygon** around the KNUST
belt, then merged/deduped by place ID. Area grouping uses **two signals**: on-campus by
**point-in-polygon** against the real KNUST boundary (OpenStreetMap/Overpass), and off-campus
by **reverse-geocoding** each coordinate to its OSM suburb. Tightened to on-campus + close
student suburbs within ~6 km. (`merge_clean.py` → `reverse_geocode.py` → `campus_boundary.py`
→ `analyze_campus.py` → `classify_and_build.py`.)

**Layer 2 — enrichment (`enrich_build.py`).**
- **Photos & amenities** from a fuller Apify detail run.
- **Confirmed contacts** matched from the SRC list and the **Campus-MP poster** (`mp_contacts.json`).
  **31 hostels on those lists weren't in the Google-Maps set** (Amen Annex/Inn, Frontline
  Apartment/Court, Jita 1 & 2, JNS, Pii, Ceros, …) and are appended as **contact-only entries**,
  then **forward-geocoded** (Nominatim by name, area-centroid fallback → `mp_geocode.json`) so they
  also get map pins. This brings the total to **532** and confirmed contacts to **105**.
- **Prices** scraped from **getrooms.co** (browser crawl; only ~23 of its KNUST listings publish
  real figures) plus a few from studentroombook.com — exact-name matched, written to `getrooms_prices.json`.

**Layer 3 — cleanup & types (`reclassify_clean.py`).** Collapses Google's 22 raw place-types into
**3 buckets** (Hostel · Guest house & Hotel · Apartment/Self-contained) by name then category, drops
true duplicates (same phone) and nameless fragments, and merges split listings — on-campus hall wings
(Queen's/Republic/Unity/Katanga) and BMS Lodge's per-room-type entries — into one. Takes the set from 532 → **514**.

**Layer 4 — the official KOSASS overlay (`kosass_merge.py`).** Layers in the **official KNUST
KOSASS accommodation portal** (`kosass.knust.edu.gh`), whose public `/api/v1/residences` JSON carries
authoritative data we can't get from Google: **KNUST-registration status + registration numbers**, a
**Ghana Post digital address**, **per-room-type price ranges**, **room count + male/female capacity**,
and official location zones. It's a high-precision merge — records match by identical name-token set,
≥2 shared tokens, string similarity, or GPS within 180 m, so a shared surname alone never merges two
hostels. On a match it **cross-checks contacts**: if our number already equals the portal's manager
number the entry becomes *confirmed* (that's how confirmed contacts jumped 105 → **283**); if we have
none we fill the portal's; if they differ we keep ours. Every KOSASS residence not already listed —
mostly small family **"homestels"** — is added. Broken portal image links are dropped via a validated
allowlist. Takes the set from 514 → **745**. (Only manager contacts are surfaced; owner/porter numbers
are dropped for privacy. `kosass_residences.json` is a raw snapshot, kept out of the deployed site.)

**Layer 5 — deep de-dup (`kosass_dedupe.py`).** A final integrity pass. Drops **44 nameless junk
entries** KOSASS carries ("No Name", "Homestel (No Name) N", "Unnamed Hostel"), then merges
**30 duplicate records** — usually a KOSASS spelling variant of a place already listed by Google
(*Denad* = De Nad, *R & B* = R and B, *Buadi* = Boadi Executive, *Fredmak* = Fred Mark, *Maxi* = Maxie…).
Matching is deliberately cautious: it compares **core names** (after stripping "Hostel"/"and"), needs
a shared phone, near-identical name, or GPS < 18 m, and a `separate_buildings()` guard keeps genuine
chains apart (Amen Main/Annex/Inn, Celia Royale Main/Annex, Wagyingo Opal/Onyx…). The richer
Google-mapped record is kept and the other's unique fields folded in. Takes the set from 745 → **671**.

**Layer 6 — final audit (`kosass_finalfix.py`).** A last targeted pass from a deep duplicate audit:
renames the Bomso *Morning Star Hostel* → *Morning Star Palace* (its real KOSASS name, so it no longer
collides with the distinct Ayeduase one) and drops two confirmed empty-stub duplicates (*Moses Osei
Homestel*, *Mojo Homestel* — rooms 0, sharing a sibling's phone/address). Takes the set to **669**.

## Data-quality notes

- **515 of 669 places are map-pinned** with reliable coordinates; the rest (mostly small KOSASS
  homestels and ~25 older entries) use an area-level fallback pin — use the Maps link to confirm the
  exact spot. Distances are straight-line from campus centre.
- Contact-only entries (the 31 added from the MP/SRC lists) have a confirmed phone but no rating,
  photos or website yet, and their pin is an area-level estimate.
- **Prices and availability change** — confirm directly with each hostel before paying.

## Reproduce / refresh

```bash
# Layer 1 (only when re-scraping Google Maps):
python merge_clean.py && python reverse_geocode.py && python campus_boundary.py \
  && python analyze_campus.py && python classify_and_build.py

# Layer 2 (rebuild data.js + CSV from the enrichment sources):
python enrich_build.py

# Layer 3 (de-dupe, merge building fragments, set the clean Type buckets):
python reclassify_clean.py

# Layer 4 (overlay the official KOSASS portal: registration, digital address, prices, new homestels):
#   refresh the snapshot first (router may hijack DNS — force the real IP):
#   curl --resolve kosass.knust.edu.gh:443:129.122.17.238 --ssl-no-revoke \
#     "https://kosass.knust.edu.gh/api/v1/residences?page=1&limit=3000"  ->  kosass_residences.json
python kosass_merge.py

# Layer 5 (drop nameless junk + merge duplicate records; use --dry to preview):
python kosass_dedupe.py

# ALWAYS after any data update — verify the Ask-Ama bot still recognises everything
# (all names, all areas, nicknames, typos, filters). Exits non-zero on failure:
node test_ama.js
```

## Deploy

Hosted on **Vercel** (static site + one serverless function). Every push to `main` auto-deploys.

- **Static site** — `index.html` + `data.js` + `ama-brain.js`, no build step.
- **AI backend** — `api/chat.js`, a Vercel serverless function that proxies **Google Gemini**
  and keeps the API key server-side. Set one environment variable in Vercel: **`GEMINI_KEY`**
  (optional: `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `THINKING_LEVEL`, `GEMINI_TIMEOUT_MS`).
- `.vercelignore` keeps the build scripts and raw data out of the public deployment.

---

*Styled with a blue (#1E40AF) + amber (#F59E0B) palette, Fira Sans / Fira Code.*
