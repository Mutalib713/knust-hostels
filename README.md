# KNUST Hostels Directory — 501 hostels on & around campus

A comprehensive, up-to-date dataset of hostels, halls, guest houses and student
accommodation **on the KNUST campus and across the close student areas** of Kumasi —
each grouped by its **real location** and pinned to its **exact Google Maps spot**.

**Generated:** 2026-06-26 · **Total:** 501 places (on campus + within ~6 km) · **46 on campus + 16 in Gaza**.

## What's in the dashboard

Photos for ~352 hostels, **confirmed manager contacts** (green tick) from the SRC list,
a getrooms-style **detail view** (photo gallery, amenities, student review themes, call/map/directions),
filters by **college / area / type / amenities / confirmed-only / has-photo**, search-as-you-type
**suggestions**, an interactive **map**, a **sticky search bar**, **mobile-responsive** layout,
a **back-to-top** button, a safety **disclaimer**, and a "how freshers book" guide.

> Prices aren't shown for most hostels because they aren't published online — call the manager for current fees.

## How to use

- **`index.html`** — open in any browser. Interactive dashboard with search, area/type
  filters, sort, a live map (colour-coded pins), and per-hostel Google Maps + Directions +
  Call buttons. Includes a "Download CSV" button. (Map tiles need internet; the list works offline.)
- **`knust_hostels.csv`** — the full dataset for Excel / Google Sheets (UTF-8 BOM).
- **`data.js` / `hostels_tight.json`** — the same data as JSON (used by the dashboard).

## Columns

`Name, Area, Category, Distance_km_from_KNUST, Rating, Reviews, Phone, Website,
Address, Latitude, Longitude, Google_Maps_URL, Location_Reliable, Closed`

## Coverage by area

| Area | Count |  | Area | Count |
|------|------:|--|------|------:|
| **On Campus (KNUST)** | **46** | | Oforikrom | 15 |
| **Gaza** | **16** | | Ayigya | 13 |
| Kotei | 134 | | Oduom | 12 |
| Ayeduase | 117 | | Anwomaso | 11 |
| Boadi | 47 | | Anloga Junction | 9 |
| Bomso | 21 | | Gyinyase | 8 |
| Deduako | 19 | | Emena | 7 |
| Kentinkrono | 15 | | Appiadu / Susuanso | 11 |

**On-campus group (46)** = traditional halls (University/Katanga, Unity, Republic, Queens,
Africa, Independence, Chancellor's/Hall 7 "Brunei") **and** private hostels built on KNUST land —
e.g. Spring, Shaba, Steven Paris, Transport, R-TEP, TEK Credit, GUSSS, Graduate Students' Hostel,
plus on-campus guest houses.

**Gaza group (16)** = the dense, slightly-off-campus hostel pocket NE of campus — Gaza Hostel,
ADEPA, Anglican, the African-capital "Courts" (Libreville, Kinshasa, N'Djamena), Georgia, Crystal
Rose, Sun City, Viable, JF, Banivillas, Wilkado, etc.

## Methodology

1. **Apify Google Maps Scraper** (`compass/crawler-google-places`), two runs — the decisive one
   used a **coordinate-bounded polygon** around the KNUST belt (datasets `TUDHF1zrlFPYtrahU`, `2R7egZ1ofFv9s7bWv`).
2. **Merge & dedupe** by Google place ID + name/proximity (677 raw → 581 accommodation).
3. **Accurate area grouping (two signals):**
   - **On-campus** is decided by **point-in-polygon against the real KNUST campus boundary**
     fetched from OpenStreetMap (Overpass) — see `campus_boundary.py` → `campus_rings_kumasi.json`.
   - **Off-campus** areas come from **reverse-geocoding each coordinate** to its OSM suburb
     (`reverse_geocode.py` → `geo_cache.json`).
4. **Tightened for students** — kept only on-campus + recognised close suburbs (Kotei, Ayeduase,
   Bomso, Boadi, Kentinkrono, Ayigya, Deduako, Oduom, Appiadu, Gyinyase, Anwomaso, Emena, Anloga,
   Oforikrom, Susuanso) within ~6 km. **80 central/outer-Kumasi places were dropped** (Adum, Bantama,
   Asokwa, Asafo, Nhyiaeso, Adiebeba, …).
5. **Cross-checked** against KNUST directories / web (KOSASS, GetRooms, HostelGig, Knustnoticeboard, TikTok).

## Data-quality notes

- ~25 places had a Google area-level fallback pin (flagged `Location_Reliable = approx`) —
  use the Maps link to confirm the exact spot. Distances are straight-line from campus centre.
- ~270 have a phone number; ~485 are GPS-verified; avg rating 3.99★.
- Reference data — verify current room availability and prices directly with each hostel.

## Reproduce / refresh

```bash
python merge_clean.py        # rebuild from raw Apify pulls (581 accommodation)
python reverse_geocode.py    # reverse-geocode coords -> geo_cache.json (~11 min, rate-limited)
python campus_boundary.py    # fetch KNUST boundary; then: python analyze_campus.py  (-> campus_rings_kumasi.json)
python classify_and_build.py # campus point-in-polygon + suburb areas + tighten -> CSV + data.js
```
