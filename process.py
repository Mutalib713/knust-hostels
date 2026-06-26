# -*- coding: utf-8 -*-
"""Clean the Apify Google Maps scrape of KNUST-area hostels."""
import json, re, csv, os, sys
sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:\Users\mutal\.claude\projects\C--Users-mutal-skills\35adc9b3-602b-448c-83ac-f38b924f1253\tool-results\mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782456802279.txt'
OUT = r'C:\Users\mutal\skills\knust-hostels'

items = json.load(open(SRC, encoding='utf-8'))['items']

ACCOMM_CATS = {
    'Hostel', 'Hotel', 'Guest house', 'Lodging', 'Bed & breakfast',
    'Student dormitory', 'Group accommodation', 'Housing complex',
}
NAME_KW = ['hostel', 'hall', 'lodge', 'lodging', 'residenc', 'residency',
           'guest house', 'guesthouse', 'suites', 'court', 'apartment',
           'annex', ' inn', 'inn ', 'hostels']

# exact titles that slip through but are NOT accommodation
EXCLUDE_TITLES = {
    'nhyiaeso', 'dakodwom', 'odeneho kwadaso', 'angola junction',
    'bakana plaza', 'notice boardgh', 'ipmc kumasi', 'chokmarh',
    'christian service university', 'kessben university college',
    'daybreak house',
}

import math
KLAT, KLNG = 6.6745, -1.5716  # KNUST main campus centre

# Locality centroids (lat, lng). KNUST belt first, then wider Kumasi.
LOCALITIES = {
    'Ayeduase': (6.6800, -1.5570), 'Bomso': (6.6800, -1.5690),
    'Ayigya': (6.6920, -1.5640), 'Kotei': (6.6880, -1.5380),
    'Kentinkrono': (6.7060, -1.5690), 'Boadi': (6.6720, -1.5240),
    'Deduako': (6.6640, -1.5360), 'Anloga Junction': (6.6930, -1.5770),
    'Oforikrom': (6.6840, -1.5870), 'Emena': (6.7180, -1.5520),
    'Maxima': (6.7000, -1.5550), 'Susanso': (6.6550, -1.5150),
    'Daban': (6.6650, -1.5050),
    # wider Kumasi (so distant places are labelled honestly, not as KNUST area)
    'Nhyiaeso': (6.6830, -1.6290), 'Kwadaso': (6.6890, -1.6460),
    'Tafo': (6.7350, -1.6060), 'Asuoyeboa': (6.6920, -1.6680),
    'Ampabame': (6.6080, -1.6320), 'Bantama': (6.7050, -1.6280),
    'Suntreso': (6.6950, -1.6420), 'Santasi': (6.6620, -1.6420),
    'Atonsu': (6.6480, -1.5680), 'Ahinsan': (6.6560, -1.5950),
    'Asokore Mampong': (6.7200, -1.5350),
}

def hav(la1, lo1, la2, lo2):
    R = 6371.0
    dla = math.radians(la2 - la1); dlo = math.radians(lo2 - lo1)
    a = math.sin(dla/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlo/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def derive_area(it):
    lat, lng = it.get('location.lat'), it.get('location.lng')
    if lat and lng:
        best = min(LOCALITIES.items(), key=lambda kv: hav(lat, lng, kv[1][0], kv[1][1]))
        return best[0]
    nb = (it.get('neighborhood') or '').strip()
    return nb or 'Kumasi'

def dist_knust(it):
    lat, lng = it.get('location.lat'), it.get('location.lng')
    if lat and lng:
        return round(hav(lat, lng, KLAT, KLNG), 2)
    return None

def zone_of(km):
    if km is None: return 'Unknown'
    if km <= 3: return 'Core (≤3km – walkable)'
    if km <= 6: return 'Near (3–6km)'
    if km <= 10: return 'Outer (6–10km)'
    return 'Far (>10km – elsewhere in Kumasi)'

def is_accom(it):
    cat = (it.get('categoryName') or '').strip()
    title = (it.get('title') or '').strip().lower()
    if title in EXCLUDE_TITLES:
        return False
    if cat in ACCOMM_CATS:
        return True
    if any(k in title for k in NAME_KW):
        return True
    return False

kept = [it for it in items if is_accom(it)]
dropped = [it for it in items if not is_accom(it)]

# de-duplicate by normalized title + rounded coords
def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

seen = {}
unique = []
for it in kept:
    lat = it.get('location.lat'); lng = it.get('location.lng')
    key = (norm(it.get('title')), round(lat, 4) if lat else None, round(lng, 4) if lng else None)
    # also collapse exact-name duplicates regardless of tiny coord diffs
    namekey = norm(it.get('title'))
    if key in seen or namekey in {norm(u.get('title')) for u in unique}:
        continue
    seen[key] = True
    unique.append(it)

# build clean records
clean = []
for it in unique:
    km = dist_knust(it)
    clean.append({
        'name': (it.get('title') or '').strip(),
        'category': (it.get('categoryName') or '').strip() or 'Accommodation',
        'area': derive_area(it),
        'km_from_knust': km,
        'zone': zone_of(km),
        'address': (it.get('address') or '').strip(),
        'lat': it.get('location.lat'),
        'lng': it.get('location.lng'),
        'maps_url': it.get('url') or '',
        'phone': (it.get('phone') or '').strip(),
        'website': (it.get('website') or '').strip(),
        'rating': it.get('totalScore'),
        'reviews': it.get('reviewsCount') or 0,
        'source': 'Google Maps (GPS-verified)',
    })

# sort by distance then name
clean.sort(key=lambda r: (r['km_from_knust'] if r['km_from_knust'] is not None else 999, r['name'].lower()))

json.dump(clean, open(os.path.join(OUT, 'hostels_tierA.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

print('RAW items:', len(items))
print('KEPT accommodation:', len(kept))
print('UNIQUE after dedup:', len(clean))
print()
from collections import Counter
print('--- by ZONE ---')
for z in ['Core (≤3km – walkable)', 'Near (3–6km)', 'Outer (6–10km)', 'Far (>10km – elsewhere in Kumasi)', 'Unknown']:
    n = sum(1 for r in clean if r['zone'] == z)
    print(f'{n:3d}  {z}')
print()
print('--- by AREA (nearest locality) ---')
for a, n in Counter(r['area'] for r in clean).most_common():
    print(f'{n:3d}  {a}')
