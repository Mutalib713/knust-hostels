# -*- coding: utf-8 -*-
"""Produce the CSV + data.js used by the dashboard from the cleaned datasets."""
import json, csv, os, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'

near = json.load(open(os.path.join(OUT, 'hostels_final.json'), encoding='utf-8'))
far  = json.load(open(os.path.join(OUT, 'hostels_far_kumasi.json'), encoding='utf-8'))

# sort: by area, then rating desc, then reviews desc
def sortkey(r):
    return (r['area'], -(r['rating'] or 0), -(r['reviews'] or 0))
near.sort(key=sortkey)

# ---- CSV (full, for Excel/Sheets) ----
cols = ['name','area','category','km_from_knust','rating','reviews','phone','website',
        'address','lat','lng','maps_url','coord_reliable','closed']
with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name','Area','Category','Distance_km_from_KNUST','Rating','Reviews','Phone',
                'Website','Address','Latitude','Longitude','Google_Maps_URL','Location_Reliable','Closed'])
    for r in near:
        w.writerow([r['name'], r['area'], r['category'], r['km_from_knust'], r['rating'] or '',
                    r['reviews'] or 0, r['phone'], r['website'], r['address'], r['lat'], r['lng'],
                    r['maps_url'], 'yes' if r['coord_reliable'] else 'approx', 'yes' if r['closed'] else 'no'])

# ---- data.js (for the dashboard) ----
meta = {
    'generated': '2026-06-26',
    'total': len(near),
    'areas': [a for a, _ in Counter(r['area'] for r in near).most_common()],
    'area_counts': dict(Counter(r['area'] for r in near).most_common()),
    'with_phone': sum(1 for r in near if r['phone']),
    'with_rating': sum(1 for r in near if r['rating']),
    'gps_verified': sum(1 for r in near if r['coord_reliable']),
    'categories': [c for c, _ in Counter(r['category'] for r in near).most_common()],
    'knust': {'lat': 6.6745, 'lng': -1.5716},
}
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(meta, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(near, ensure_ascii=False) + ';\n')

print('CSV rows:', len(near))
print('data.js written. total=', meta['total'])
print('areas:', meta['area_counts'])
print('with_phone:', meta['with_phone'], 'with_rating:', meta['with_rating'], 'gps_verified:', meta['gps_verified'])
print('far (appendix):', len(far))
