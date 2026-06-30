# -*- coding: utf-8 -*-
"""Amenity enrichment (runs AFTER korley_apply.py). Focus: Wi-Fi, where we have a
defensible source — owner-confirmed (all on-campus hostels), the getrooms.co listings
we already hold, and specific chains the user verified (Frontline, Wagyingo).
Idempotent; rewrites data.js + knust_hostels.csv. Does NOT invent amenities."""
import json, re, os, csv
from collections import Counter
OUT = r'C:\Users\mutal\skills\knust-hostels'

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '): META = json.loads(line[14:].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '): HOSTELS = json.loads(line[17:].rstrip().rstrip(';'))

# getrooms.co listings we scraped earlier (real booking listings -> have Wi-Fi)
try:
    GR = {norm(g['name']) for g in json.load(open(os.path.join(OUT, 'getrooms_prices.json'), encoding='utf-8'))}
except FileNotFoundError:
    GR = set()

# chains the user verified as having Wi-Fi (matched by substring so all buildings are covered)
WIFI_SUBSTR = re.compile(r'frontline|wagyingo', re.I)

added = []
for h in HOSTELS:
    am = set(h.get('amenities') or [])
    if 'Wi-Fi' in am:
        continue
    reason = None
    if h['area'] == 'On Campus (KNUST)':
        reason = 'on-campus'
    elif norm(h['name']) in GR:
        reason = 'getrooms'
    elif WIFI_SUBSTR.search(h['name']):
        reason = 'verified chain'
    if reason:
        am.add('Wi-Fi'); h['amenities'] = sorted(am); added.append(f"{h['name']} [{h['area']}] ({reason})")

# recompute amenity-related META
amen = Counter(a for r in HOSTELS for a in (r.get('amenities') or []))
META['amenities'] = [a for a, _ in amen.most_common()]
META['with_amenities'] = sum(1 for r in HOSTELS if r.get('amenities'))

with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(META, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(HOSTELS, ensure_ascii=False) + ';\n')

with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Area', 'Type', 'Category', 'Distance_km', 'Rating', 'Reviews', 'Price_from_GHS',
                'Price_source', 'Phone', 'Confirmed_Contact', 'Amenities', 'Colleges_nearby', 'Website',
                'Latitude', 'Longitude', 'Google_Maps_URL', 'Image'])
    for r in HOSTELS:
        w.writerow([r['name'], r['area'], r.get('type', ''), r.get('category', ''), r.get('km_from_knust'),
                    r.get('rating') or '', r.get('reviews'), r.get('price_from') or '', r.get('price_src') or '',
                    r.get('phone'), 'yes' if r.get('confirmed') else '', ' | '.join(r.get('amenities', [])),
                    ' | '.join(r.get('colleges', [])), r.get('website'), r.get('lat'), r.get('lng'),
                    r.get('maps_url'), r['images'][0] if r.get('images') else ''])

wifi_total = sum(1 for r in HOSTELS if 'Wi-Fi' in (r.get('amenities') or []))
print(f"Wi-Fi added to {len(added)} hostels.  Total with Wi-Fi now: {wifi_total}")
by = Counter(a.split('(')[-1].rstrip(')') for a in added)
print("by source:", dict(by))
