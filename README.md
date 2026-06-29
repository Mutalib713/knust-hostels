# KNUST Hostels Directory — 510+ hostels on & around campus

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
| **Total places** | **514** (on campus + within ~6 km) |
| **Types** | Hostel **403** · Guest house & Hotel **99** · Apartment/Self-contained **12** |
| On campus / Gaza pocket | 36 / 18 |
| **Confirmed manager contacts** (green tick) | **103** |
| With a phone number | 319 |
| With photos | 347 |
| With published price ranges | 31 |
| Map-pinned (lat/lng) | **514 (all)** |
| Average Google rating | 3.99★ |

## What's in the dashboard

- **Smart search & sort** — search-as-you-type suggestions, sort by **Most popular**
  (default), distance, rating, reviews, price, confirmed-first or name.
- **Filters** — by college, area, **type — 3 clean buckets (Hostel · Guest house & Hotel · Apartment) with counts**, amenities,
  confirmed-only and has-photo, with a one-tap **Reset all filters** and a live **"X found"** count.
- **Detail view** — photo gallery (tap to open a full-screen viewer with **swipe** + arrows),
  amenities, student review themes, **room-type price ranges**, and Call / Map / Directions buttons.
- **Interactive map** with colour-coded pins by area (gracefully degrades to a list-only
  view if offline).
- **"Ask Ama" AI assistant** — a chat helper that answers questions like *"cheapest confirmed
  hostel in Ayeduase under 3000"*, grounded **only** in the real directory data (Google Gemini
  via a serverless function; falls back to offline keyword search if the AI is unavailable).
- **Message us** — a "💬 Message us" button in the chat header to report a wrong number, a
  closed/missing hostel or suggest a change — either via **WhatsApp** or a quick **email** form.
- **Prices** for 31 hostels (room-type ranges, e.g. *2-in-1 GHS 3,400–5,200*), sourced from getrooms.co.
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
- **`hostels_tight.json`** — the mapped 501-hostel base set as JSON.
- **`mp_contacts.json`** — Campus-MP / SRC manager contact list.
- **`getrooms_prices.json`** — scraped room-type prices (exact-name matched).
- **`mp_geocode.json`** — coordinates for the contact-only hostels.
- **`enrich_build.py`** — builds `data.js` + the CSV from all of the above.
- **`reclassify_clean.py`** — final pass: de-dupes, merges building fragments, and sets the 3 clean **Type** buckets.

## CSV columns

`Name, Area, Type, Category, Distance_km, Rating, Reviews, Price_from_GHS, Price_source,
Phone, Confirmed_Contact, Amenities, Colleges_nearby, Website, Latitude, Longitude,
Google_Maps_URL, Image`

## Coverage by area

| Area | Count |  | Area | Count |
|------|------:|--|------|------:|
| Kotei | 137 | | Ayigya | 13 |
| Ayeduase | 138 | | Oduom | 12 |
| Boadi | 43 | | Anwomaso | 11 |
| **On Campus (KNUST)** | **36** | | Anloga Junction | 9 |
| Bomso | 22 | | Gyinyase | 8 |
| Deduako | 19 | | Emena | 7 |
| **Gaza** | **18** | | Appiadu | 6 |
| Kentinkrono | 15 | | Susuanso (campus edge) | 5 |
| Oforikrom | 15 | | | |

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

## Data-quality notes

- All 514 places are map-pinned; ~25 of the original set use a Google area-level fallback pin —
  use the Maps link to confirm the exact spot. Distances are straight-line from campus centre.
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

# Layer 3 (de-dupe, merge building fragments, set the 3 clean Type buckets):
python reclassify_clean.py
```

## Deploy

Hosted on **Vercel** (static site + one serverless function). Every push to `main` auto-deploys.

- **Static site** — `index.html` + `data.js`, no build step.
- **AI backend** — `api/chat.js`, a Vercel serverless function that proxies **Google Gemini**
  and keeps the API key server-side. Set one environment variable in Vercel: **`GEMINI_KEY`**
  (optional: `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `THINKING_LEVEL`, `GEMINI_TIMEOUT_MS`).
- `.vercelignore` keeps the build scripts and raw data out of the public deployment.

---

*Styled with a blue (#1E40AF) + amber (#F59E0B) palette, Fira Sans / Fira Code.*
