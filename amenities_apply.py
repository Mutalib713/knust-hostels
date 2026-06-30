# -*- coding: utf-8 -*-
"""Enrich hostel amenities (runs AFTER korley_apply.py).
Sources: getrooms.co Facilities (scraped via Apify website-content-crawler) +
user-confirmed Wi-Fi (all on-campus hostels, plus Frontline/Wagyingo/Georgia).
Reads + rewrites data.js and knust_hostels.csv. Idempotent (amenities are a set union)."""
import json, re, os, csv
from collections import Counter
OUT = r'C:\Users\mutal\skills\knust-hostels'

# getrooms.co Facilities -> our canonical amenity vocabulary, keyed by the DB hostel name
GETROOMS = {
 'Thy Kingdom Come Hostel': ['Water', 'Kitchen', 'Study room'],
 'Adwoa Akyaa Hostel': ['Water', 'Kitchen', 'Study room'],
 'F Plaza Hostel': ['Water', 'Kitchen', 'Study room'],
 'Outlook Hostel': ['Water', 'Kitchen'],
 'URBAN PLATINUM HOSTEL': ['Security'],
 'Thy Will Be Done Hostel': ['Water', 'Kitchen', 'Study room'],
 'Anglican Hostel': ['Security', 'Backup power'],
 "Caesar's Palace Hostel": ['Water', 'Kitchen', 'Study room'],
 'Blue Ark Hostel': ['Security', 'TV'],
 'DAKENS International Hostel': ['Security', 'Water', 'Kitchen', 'Study room', 'TV'],
 'Destiny View Hostel': ['Water', 'Kitchen', 'Study room'],
 'Divine Kama Hostel': ['Water', 'Kitchen', 'Study room'],
 'Georgia hostel': ['Water', 'Kitchen', 'Study room', 'Wi-Fi', 'Air-conditioned'],
 'Honesty Student Hostel': ['Security'],
 'Millennium Light Hostel': ['Security', 'TV'],
 'Anarosa Hostel': ['Backup power', 'Self-contained', 'Parking', 'TV', 'Kitchen', 'Security'],
 'Enin Hostel': ['Water', 'Kitchen', 'Study room'],
 'Evandy Hostel KNUST': ['Security', 'TV', 'Backup power'],
 'By His Grace Hostel': ['Water', 'Kitchen', 'Study room'],
 'High Achievers Hostel': ['Security', 'TV'],
 'Amen Main Hostel': ['Kitchen', 'Study room', 'Backup power', 'Water', 'Security'],
 'Frontline INN hostel': ['Backup power', 'Self-contained', 'Parking', 'TV', 'Kitchen', 'Security', 'Air-conditioned'],
 'Frontline Premium Tower': ['Security', 'Wi-Fi', 'TV', 'Backup power', 'Water', 'Study room'],
}
# off-campus hostels confirmed to have Wi-Fi (user + getrooms); on-campus all get it by area
WIFI_NAMES = {
 'Frontline INN hostel', 'Frontline Apartment', 'Frontline Court', 'Frontline Premium Tower',
 'Wagyingo Opal Hostel', 'Wagyingo Main Hostel', 'Wagyingo Onyx Hostel', 'Georgia hostel',
}

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
GR = {norm(k): v for k, v in GETROOMS.items()}
WIFI = {norm(x) for x in WIFI_NAMES}

META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '): META = json.loads(line[14:].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '): HOSTELS = json.loads(line[17:].rstrip().rstrip(';'))

gr_hits = wifi_oncampus = wifi_named = 0
for h in HOSTELS:
    am = set(h.get('amenities') or [])
    nn = norm(h['name'])
    if nn in GR: am.update(GR[nn]); gr_hits += 1
    if h['area'] == 'On Campus (KNUST)': am.add('Wi-Fi'); wifi_oncampus += 1
    if nn in WIFI: am.add('Wi-Fi'); wifi_named += 1
    h['amenities'] = sorted(am)

amen = Counter(a for h in HOSTELS for a in h.get('amenities', []))
META['amenities'] = [a for a, _ in amen.most_common()]
META['with_amenities'] = sum(1 for h in HOSTELS if h.get('amenities'))

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

print(f"getrooms merged: {gr_hits}   on-campus Wi-Fi: {wifi_oncampus}   named Wi-Fi: {wifi_named}")
print(f"hostels with amenities now: {META['with_amenities']}")
print("amenity vocabulary:", dict(amen))
