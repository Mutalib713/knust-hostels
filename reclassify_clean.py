# -*- coding: utf-8 -*-
"""Post-process step (runs AFTER enrich_build.py): de-duplicate, merge building
fragments, drop non-hostel junk, and collapse Google's 22 messy place-types into
3 clean buckets. Reads the current data.js and rewrites data.js + knust_hostels.csv.
Idempotent: safe to run more than once."""
import json, re, os, csv
from collections import Counter
OUT = r'C:\Users\mutal\skills\knust-hostels'

# ---- load current data.js ----
META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '):
        META = json.loads(line[len('window.META = '):].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '):
        HOSTELS = json.loads(line[len('window.HOSTELS = '):].rstrip().rstrip(';'))
assert META and HOSTELS, 'could not parse data.js'
before = len(HOSTELS)

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

# ---- 1) DROP: true duplicates, empty ghosts, non-hostel junk, nameless fragments ----
DROP_NORM_AREA = {                                   # drop only this copy (keep the other)
    (norm('blue ark hostel'), 'On Campus (KNUST)'),  # dup of Bomso (same phone)
    (norm('johannes Hostel [knust]'), 'On Campus (KNUST)'),  # dup of Johannes [Kotei]
}
DROP_NORM = {norm(x) for x in [
    'Meghan Hostel', "Samantha's Franco", 'Franko new',   # empty ghosts beside a real hostel
    'Yoflo Tech',                                         # a tech business, not a hostel
    'Block B', 'Block C', 'Room 1C1',                     # nameless fragments / a single room
    'Queens Hall Annex', 'Queens Hall East Wing',         # on-campus hall wings -> parent hall
    'Republic Hall Annex', 'Unity Hall Block B', '3A Katanga Hall',
    'BMS Lodge - One-Bedroom Superior Apartment',         # BMS Lodge room-type splits -> one entry
    'BMS Lodge - Deluxe One-Bedroom Apartment',
    'BMS Lodge - Two-Bedroom Townhouse', 'BMS Lodge - Vacation Home',
]}

# ---- 2) RENAME: disambiguate genuine same-name pairs; collapse BMS to one name ----
RENAME = {                                            # (norm(name), area) -> new name
    (norm('Peace Hostel'), 'Kotei'): 'Peace Hostel (Kotei)',
    (norm('Peace Hostel'), 'Oforikrom'): 'Peace Hostel (Oforikrom)',
    (norm('PINK HOSTEL'), 'On Campus (KNUST)'): 'Pink Hostel (On Campus)',
    (norm('PINK HOSTEL'), 'Susuanso (campus edge)'): 'Pink Hostel (Susuanso)',
    (norm('BMS Lodge - Casa Maria'), 'Boadi'): 'BMS Lodge',
}

# ---- 3) TYPE: 22 Google place-types -> 3 clean buckets (name first, then category) ----
HOSTEL = 'Hostel'
HOTEL = 'Guest house & Hotel'
APART = 'Apartment / Self-contained'
def classify(name, category):
    n = (name or '').lower(); c = (category or '').lower()
    if re.search(r'\bapartment|apartments|\bflat\b|flats\b|self[- ]?contain', n): return APART
    if re.search(r'hostel|\bhall\b|dormitor', n): return HOSTEL
    if re.search(r'hotel|guest ?house|\blodge\b|lodging|\binn\b|motel|b&b|bed and breakfast', n): return HOTEL
    if c in ('apartment', 'apartment building', 'apartment complex', 'holiday apartment rental'): return APART
    if c in ('hotel', 'guest house', 'bed & breakfast', 'motel', 'lodging', 'lodge', 'indoor lodging'): return HOTEL
    return HOSTEL  # hostel directory default (covers dormitory/student-housing/mislabelled types)

kept, dropped, renamed = [], [], 0
for r in HOSTELS:
    nm, ar, nnm = r['name'], r.get('area', ''), norm(r['name'])
    if (nnm, ar) in DROP_NORM_AREA or nnm in DROP_NORM:
        dropped.append(f"{nm} [{ar}]"); continue
    if (nnm, ar) in RENAME:
        r['name'] = RENAME[(nnm, ar)]; renamed += 1
    r['type'] = classify(r['name'], r.get('category'))
    kept.append(r)

# ---- recompute META ----
amen = Counter(a for r in kept for a in r.get('amenities', []))
tc = Counter(r['type'] for r in kept)
type_order = [HOSTEL, HOTEL, APART]
META.update({
    'total': len(kept),
    'areas': [a for a, _ in Counter(r['area'] for r in kept).most_common()],
    'area_counts': dict(Counter(r['area'] for r in kept).most_common()),
    'amenities': [a for a, _ in amen.most_common()],
    'confirmed': sum(1 for r in kept if r.get('confirmed')),
    'with_images': sum(1 for r in kept if r.get('images')),
    'with_amenities': sum(1 for r in kept if r.get('amenities')),
    'with_phone': sum(1 for r in kept if r.get('phone')),
    'with_price': sum(1 for r in kept if r.get('price_from')),
    'types': [t for t in type_order if tc.get(t)],
    'type_counts': {t: tc[t] for t in type_order if tc.get(t)},
    'generated': '2026-06-29',
})

with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(META, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(kept, ensure_ascii=False) + ';\n')

with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Area', 'Type', 'Category', 'Distance_km', 'Rating', 'Reviews', 'Price_from_GHS',
                'Price_source', 'Phone', 'Confirmed_Contact', 'Amenities', 'Colleges_nearby', 'Website',
                'Latitude', 'Longitude', 'Google_Maps_URL', 'Image'])
    for r in kept:
        w.writerow([r['name'], r['area'], r.get('type', ''), r.get('category', ''), r.get('km_from_knust'),
                    r.get('rating') or '', r.get('reviews'), r.get('price_from') or '', r.get('price_src') or '',
                    r.get('phone'), 'yes' if r.get('confirmed') else '', ' | '.join(r.get('amenities', [])),
                    ' | '.join(r.get('colleges', [])), r.get('website'), r.get('lat'), r.get('lng'),
                    r.get('maps_url'), r['images'][0] if r.get('images') else ''])

print(f"before: {before}   dropped: {len(dropped)}   renamed: {renamed}   after: {len(kept)}")
print("type buckets:", dict(META['type_counts']))
print("dropped entries:")
for d in dropped: print("   -", d)
