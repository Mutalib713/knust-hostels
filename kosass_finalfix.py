# -*- coding: utf-8 -*-
"""Tiny targeted cleanup after kosass_dedupe.py, from the deep duplicate audit.

Three fixes the audit confirmed against the raw KOSASS source:
  1) Rename the Bomso "Morning Star Hostel" -> "Morning Star Palace" (its real KOSASS
     name) so it no longer collides with the distinct Ayeduase "Morning Star Hostel".
  2) Drop "Moses Osei Homestel" — empty stub (rooms 0, no digital addr) sharing the
     manager phone of the real "Mr Moses Homestel".
  3) Drop "Mojo Homestel" — empty stub (rooms 0, no manager) sharing Oso Homestel's
     digital address.
Idempotent. Recomputes META + rewrites data.js + knust_hostels.csv.
"""
import json, re, os, csv, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.dirname(os.path.abspath(__file__))

js = ('global.window={};require(%r);process.stdout.write(JSON.stringify({M:window.META,H:window.HOSTELS}));'
      % os.path.join(OUT, 'data.js').replace('\\', '/'))
r = subprocess.run(['node', '-e', js], capture_output=True, text=True, encoding='utf-8')
if r.returncode: raise SystemExit(r.stderr)
d = json.loads(r.stdout); META, H = d['M'], d['H']
before = len(H)

# 1) rename Bomso Morning Star
ren = 0
for x in H:
    if x['name'].strip().lower() == 'morning star hostel' and x['area'] == 'Bomso':
        x['name'] = 'Morning Star Palace'; ren += 1

# 2+3) drop the two confirmed empty-stub duplicates
DROP = {('moses osei homestel', 'Ayeduase'), ('mojo homestel', 'Ayeduase')}
kept = [x for x in H if (x['name'].strip().lower(), x['area']) not in DROP]
dropped = [x for x in H if (x['name'].strip().lower(), x['area']) in DROP]
H = kept

print('renamed Morning Star (Bomso):', ren)
print('dropped stubs:', [x['name'] for x in dropped])

from collections import Counter
type_order = ['Hostel', 'Guest house & Hotel', 'Apartment / Self-contained', 'Homestel (family home)']
tc = Counter(x.get('type', 'Hostel') for x in H); ac = Counter(x['area'] for x in H)
amen = Counter()
for x in H:
    for a in x.get('amenities', []): amen[a] += 1
META.update({
    'total': len(H), 'areas': [a for a, _ in ac.most_common()], 'area_counts': dict(ac.most_common()),
    'types': [t for t in type_order if tc.get(t)] + [t for t in tc if t not in type_order],
    'type_counts': {**{t: tc[t] for t in type_order if tc.get(t)}, **{t: tc[t] for t in tc if t not in type_order}},
    'amenities': [a for a, _ in amen.most_common()],
    'confirmed': sum(1 for x in H if x.get('confirmed')), 'with_images': sum(1 for x in H if x.get('images')),
    'with_amenities': sum(1 for x in H if x.get('amenities')), 'with_phone': sum(1 for x in H if x.get('phone')),
    'with_price': sum(1 for x in H if x.get('price_from')),
    'registered_count': sum(1 for x in H if x.get('registered')),
    'with_digital': sum(1 for x in H if x.get('digital_address')),
})
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(META, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(H, ensure_ascii=False) + ';\n')
with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name','Area','Type','Category','Distance_km','Rating','Reviews','Price_from_GHS','Price_source',
                'Phone','Confirmed_Contact','KNUST_Registered','Reg_No','Digital_Address','Rooms_Total','Male_Cap',
                'Female_Cap','Amenities','Colleges_nearby','Website','Latitude','Longitude','Google_Maps_URL','Image'])
    for x in H:
        w.writerow([x['name'],x['area'],x.get('type',''),x.get('category',''),x.get('km_from_knust'),
                    x.get('rating') or '',x.get('reviews'),x.get('price_from') or '',x.get('price_src') or '',
                    x.get('phone'),'yes' if x.get('confirmed') else '','yes' if x.get('registered') else '',
                    x.get('reg_no',''),x.get('digital_address',''),x.get('rooms_total',''),x.get('male_cap',''),
                    x.get('female_cap',''),' | '.join(x.get('amenities',[])),' | '.join(x.get('colleges',[])),
                    x.get('website',''),x.get('lat'),x.get('lng'),x.get('maps_url'),(x.get('images') or [''])[0]])
print('total: %d -> %d' % (before, len(H)))
