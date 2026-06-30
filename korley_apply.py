# -*- coding: utf-8 -*-
"""Apply the verified corrections from the Korley Boye poster cross-check
(runs AFTER reclassify_clean.py). Fixes one typo'd number and merges two
duplicate pairs that existed because Bruce-poster typo names didn't match the
Google names. Reads + rewrites data.js and knust_hostels.csv. Idempotent."""
import json, re, os, csv, math, random, urllib.parse
from collections import Counter
OUT = r'C:\Users\mutal\skills\knust-hostels'

META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '): META = json.loads(line[14:].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '): HOSTELS = json.loads(line[17:].rstrip().rstrip(';'))

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
log = []

def first(pred): return next((h for h in HOSTELS if pred(h)), None)

COLLEGE_AREAS = {
 'Engineering': {'Ayeduase','On Campus (KNUST)','Gaza','Bomso','Oforikrom'},
 'Science': {'On Campus (KNUST)','Ayeduase','Bomso','Ayigya','Susuanso (campus edge)','Gaza'},
 'Art & Built Environment': {'Ayeduase','On Campus (KNUST)','Gaza','Bomso'},
 'Humanities & Social Sciences (KSB)': {'Bomso','Ayigya','Ayeduase','On Campus (KNUST)','Anloga Junction','Oforikrom','Susuanso (campus edge)'},
 'Health Sciences': {'Ayigya','Kentinkrono','Bomso','Emena','Anloga Junction','On Campus (KNUST)'},
 'Agriculture & Natural Resources': {'Kotei','Oduom','Boadi','Deduako','Anwomaso','Appiadu','Gyinyase'},
}
def colleges_for(area):
    cs = [c for c, areas in COLLEGE_AREAS.items() if area in areas]
    return cs or list(COLLEGE_AREAS.keys())

def km_to_knust(lat, lng):
    if lat is None or lng is None: return None
    klat, klng = 6.6745, -1.5716
    dlat, dlng = math.radians(lat - klat), math.radians(lng - klng)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(klat))*math.cos(math.radians(lat))*math.sin(dlng/2)**2
    return round(2 * 6371 * math.asin(math.sqrt(a)), 2)

def area_centroid(area):
    pts = [(h['lat'], h['lng']) for h in HOSTELS if h['area'] == area and h.get('lat') and h.get('lng')]
    if not pts: return (6.6745, -1.5716)
    return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))

def add_hostel(name, area, phone, note=''):
    if any(norm(h['name']) == norm(name) and h['area'] == area for h in HOSTELS):
        return  # already present -> idempotent
    clat, clng = area_centroid(area)
    lat = round(clat + random.uniform(-0.0015, 0.0015), 6); lng = round(clng + random.uniform(-0.0015, 0.0015), 6)
    HOSTELS.append({'name': name, 'area': area, 'category': 'Hostel', 'type': 'Hostel',
        'km_from_knust': km_to_knust(lat, lng), 'lat': lat, 'lng': lng,
        'maps_url': 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(name + ' hostel KNUST Kumasi'),
        'website': '', 'rating': None, 'reviews': 0, 'coord_reliable': False, 'closed': False,
        'phone': phone, 'manager_phone': phone, 'confirmed': True, 'images': [], 'amenities': [],
        'review_tags': [], 'colleges': colleges_for(area), 'price_from': None, 'rooms': [], 'price_src': '',
        'added_from': 'korley_poster'})
    log.append(f"Added '{name}' [{area}] {phone} {note}")

# 1) Liberty: our data has the Bruce typo 0240993470; correct (Korley) = 0240983470
lib = first(lambda h: norm(h['name']) == 'libertyhostel')
if lib and re.sub(r'\D', '', lib.get('phone', '')) != '0240983470':
    log.append(f"Liberty phone {lib.get('phone')} -> 0240983470")
    lib['phone'] = '0240983470'; lib['manager_phone'] = '0240983470'; lib['confirmed'] = True

# 2) Merge 'Anclan' (Bruce typo name) into 'Anglican Hostel' (correct Google entry, real coords)
anclan = first(lambda h: norm(h['name']) == 'anclan')
angli = first(lambda h: norm(h['name']) == 'anglicanhostel')
if anclan and angli:
    angli['phone'] = '0249481310'; angli['manager_phone'] = '0249481310'; angli['confirmed'] = True
    HOSTELS.remove(anclan)
    log.append("Merged 'Anclan' -> 'Anglican Hostel' (confirmed mobile 0249481310; kept Google map pin)")
elif anclan:
    anclan['name'] = 'Anglican Hostel'; log.append("Renamed 'Anclan' -> 'Anglican Hostel'")

# 3) Rename 'R B & D' -> 'P B & D' (Korley spelling is the correct one)
rbd = first(lambda h: norm(h['name']) == 'rbd')
if rbd: rbd['name'] = 'P B & D'; log.append("Renamed 'R B & D' -> 'P B & D'")

# 4) Premier Tower: drop 'Palace', merge the PTP duplicate -> 'Premier Tower'
palace = first(lambda h: norm(h['name']) == 'premiertowerpalace')
ptp = first(lambda h: 'ptp' in norm(h['name']) or 'premieretowerpalace' in norm(h['name']))
cands = [x for x in (ptp, palace) if x]
if cands:
    # keep the richer record (real photos / rating / reviews) so we don't lose the map pin
    keep = max(cands, key=lambda h: (len(h.get('images', [])), 1 if h.get('rating') else 0, h.get('reviews', 0)))
    keep['name'] = 'Premier Tower'; keep['phone'] = '0244025917'; keep['manager_phone'] = '0244025917'; keep['confirmed'] = True
    for d in cands:
        if d is not keep: HOSTELS.remove(d); log.append(f"Dropped duplicate '{d['name']}'")
    log.append("Set canonical 'Premier Tower' (confirmed 0244025917)")

# 14) Adom Bi -> area is Ayeduase (both posters agree), not Kotei
adom = first(lambda h: norm(h['name']) == 'adombiheights')
if adom and adom['area'] != 'Ayeduase':
    adom['area'] = 'Ayeduase'; adom['colleges'] = colleges_for('Ayeduase')
    log.append("Adom Bi Heights area Kotei -> Ayeduase")

# 15) Morning Star: our single entry (phone 0244928138) is the AYEDUASE one (mislabelled Bomso);
#     fix its area, then add the missing Bomso one (0245247533)
ms = first(lambda h: norm(h['name']) == 'morningstarhostel' and re.sub(r'\D', '', h.get('phone', '')) == '0244928138')
if ms and ms['area'] != 'Ayeduase':
    ms['area'] = 'Ayeduase'; ms['colleges'] = colleges_for('Ayeduase')
    log.append("Morning Star (0244928138) area Bomso -> Ayeduase")
add_hostel('Morning Star Hostel', 'Bomso', '0245247533', '(Bomso branch, was missing)')

# 16) Casa Maria (Ayeduase) is a separate place from La Casa Maria (Emena) -> add it
add_hostel('Casa Maria', 'Ayeduase', '0208185998', '(number shared w/ La Casa Maria - verify)')

# 17) obvious display-name typos
NAME_FIX = {'paradiseregainedhostleknust': 'Paradise Regained Hostel', 'bluearkhostel': 'Blue Ark Hostel'}
for h in HOSTELS:
    nf = NAME_FIX.get(norm(h['name']))
    if nf and h['name'] != nf:
        log.append(f"Name fix: '{h['name']}' -> '{nf}'"); h['name'] = nf

# ---- recompute META + write ----
amen = Counter(a for r in HOSTELS for a in r.get('amenities', []))
tc = Counter(r.get('type') for r in HOSTELS)
order = ['Hostel', 'Guest house & Hotel', 'Apartment / Self-contained']
META.update({
    'total': len(HOSTELS),
    'areas': [a for a, _ in Counter(r['area'] for r in HOSTELS).most_common()],
    'area_counts': dict(Counter(r['area'] for r in HOSTELS).most_common()),
    'amenities': [a for a, _ in amen.most_common()],
    'confirmed': sum(1 for r in HOSTELS if r.get('confirmed')),
    'with_images': sum(1 for r in HOSTELS if r.get('images')),
    'with_amenities': sum(1 for r in HOSTELS if r.get('amenities')),
    'with_phone': sum(1 for r in HOSTELS if r.get('phone')),
    'with_price': sum(1 for r in HOSTELS if r.get('price_from')),
    'types': [t for t in order if tc.get(t)],
    'type_counts': {t: tc[t] for t in order if tc.get(t)},
})

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

print(f"total now: {META['total']}   confirmed: {META['confirmed']}")
print("changes:")
for l in log: print("  -", l)
