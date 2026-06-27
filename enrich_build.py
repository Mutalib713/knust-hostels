# -*- coding: utf-8 -*-
"""Enrich the 501 hostels with images, amenities, confirmed contacts, college tags;
emit data.js + knust_hostels.csv for the dashboard."""
import json, re, os, sys, csv, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'
TR  = r'C:\Users\mutal\.claude\projects\C--Users-mutal-skills\35adc9b3-602b-448c-83ac-f38b924f1253\tool-results'

tight = json.load(open(os.path.join(OUT,'hostels_tight.json'), encoding='utf-8'))
r2 = json.load(open(os.path.join(TR,'mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782509230263.txt'), encoding='utf-8'))['items']
sy = json.load(open(os.path.join(TR,'mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782509233568.txt'), encoding='utf-8'))['items']
full = json.load(open(os.path.join(TR,'mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782511669631.txt'), encoding='utf-8'))['items']
managers = json.load(open(os.path.join(OUT,'managers.json'), encoding='utf-8'))
# Campus-MP (Bruce Clement '26) KNUST hostel contact list — newer, takes precedence over managers.json
try:
    MP = json.load(open(os.path.join(OUT,'mp_contacts.json'), encoding='utf-8'))
except FileNotFoundError:
    MP = []
PRICES = json.load(open(os.path.join(OUT,'prices.json'), encoding='utf-8'))
# getrooms.co scraped prices, keyed by EXACT hostel name (takes precedence over substring prices.json)
try:
    GETROOMS = {g['name']: g for g in json.load(open(os.path.join(OUT,'getrooms_prices.json'), encoding='utf-8'))}
except FileNotFoundError:
    GETROOMS = {}

R2 = {it['placeId']: it for it in r2 if it.get('placeId')}
SY = {it['placeId']: it for it in sy if it.get('placeId')}
FULL = {it['placeId']: it for it in full if it.get('placeId')}  # complete 501 run (galleries + amenities)

def pid(r):
    q = urllib.parse.urlparse(r['maps_url']).query
    return urllib.parse.parse_qs(q).get('query_place_id',[None])[0]

def amenities(it):
    ai = (it or {}).get('additionalInfo') or {}
    keep = {'Free Wi-Fi','Wi-Fi','Air-conditioned','Free parking','Parking','Laundry service',
            'Restaurant','Free breakfast','Breakfast','Bar','Fitness center','Pool','Outdoor pool',
            'Indoor pool','Kitchen in all rooms','Kitchens in some rooms','Room service','Pet-friendly',
            'Airport shuttle','Smoke-free','Accessible','Wheelchair accessible entrance','Spa','Business center'}
    out = set()
    for cat, d in ai.items():
        entries = d if isinstance(d, list) else [d]
        for e in entries:
            if isinstance(e, dict):
                for k, v in e.items():
                    if v is True and k in keep:
                        out.add('Wi-Fi' if k in ('Free Wi-Fi','Wi-Fi') else
                                ('Parking' if k in ('Free parking','Parking') else
                                ('Pool' if k in ('Pool','Outdoor pool','Indoor pool') else
                                ('Kitchen' if 'Kitchen' in k else
                                ('Wheelchair access' if 'Wheelchair' in k or k=='Accessible' else k)))))
    return sorted(out)

def images(p):
    for src in (FULL.get(p), SY.get(p)):
        urls = [u for u in ((src or {}).get('imageUrls') or []) if 'googleusercontent' in u][:4]
        if urls: return urls
    for src in (FULL.get(p), R2.get(p)):
        iu = (src or {}).get('imageUrl')
        if iu and 'googleusercontent' in iu: return [iu]
    return []

def review_tags(p):
    src = (FULL.get(p) or {}).get('reviewsTags') or (SY.get(p) or {}).get('reviewsTags') or (R2.get(p) or {}).get('reviewsTags') or []
    return [t['title'] for t in src if isinstance(t, dict) and t.get('title')][:8]

# ---- college -> areas (which side of campus each college's gate is on) ----
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
    return cs or list(COLLEGE_AREAS.keys())  # unknown area -> show for all

# ---- manager-contact matching ----
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
mgr = []
for m in MP:        # MP list first -> wins exact matches (newer contacts)
    mgr.append({'n': norm(m['name']), 'area': m.get('area',''), 'phone': m['phone'], 'raw': m['name']})
for m in managers:  # SRC managers as fallback / extra coverage
    mgr.append({'n': norm(m['name']), 'area': m['area'], 'phone': m['phone'], 'raw': m['name']})

def match_manager(name):
    n = norm(name)
    if not n: return None
    # exact
    for m in mgr:
        if m['n'] == n: return m
    # containment (manager name inside hostel name or vice versa), require >=4 chars
    best = None
    for m in mgr:
        if len(m['n']) >= 4 and (m['n'] in n or n in m['n']):
            if best is None or len(m['n']) > len(best['n']):
                best = m
    return best

def price_for(name):
    n = norm(name)
    for p in PRICES:
        if p['match'] in n: return p
    return None

clean = []
matched = 0
amen_universe = {}
for r in tight:
    p = pid(r)
    am = amenities(FULL.get(p)) or amenities(R2.get(p)) or amenities(SY.get(p))
    am = sorted(set(am))
    imgs = images(p)
    tags = review_tags(p)
    mm = match_manager(r['name'])
    confirmed = bool(mm)
    if confirmed: matched += 1
    phone = mm['phone'] if mm else (r.get('phone') or '')
    for a in am: amen_universe[a] = amen_universe.get(a,0)+1
    clean.append({
        'name': r['name'], 'area': r['area'], 'category': r['category'],
        'km_from_knust': r['km_from_knust'], 'lat': r['lat'], 'lng': r['lng'],
        'maps_url': r['maps_url'], 'website': r.get('website',''),
        'rating': r['rating'], 'reviews': r['reviews'], 'coord_reliable': r['coord_reliable'],
        'closed': r['closed'],
        'phone': phone, 'manager_phone': (mm['phone'] if mm else ''),
        'confirmed': confirmed,
        'images': imgs, 'amenities': am, 'review_tags': tags,
        'colleges': colleges_for(r['area']),
        'price_from': (GETROOMS.get(r['name']) or price_for(r['name']) or {}).get('from'),
        'rooms': (GETROOMS.get(r['name']) or price_for(r['name']) or {}).get('rooms') or [],
        'price_src': (GETROOMS.get(r['name']) or price_for(r['name']) or {}).get('src') or '',
    })

# ---- MP (Campus-MP) contact list: confirm verified name-variants + add hostels missing from the mapped 501 ----
ALIAS = {  # MP name (lowercase) -> our exact hostel name (verified variants, prevents duplicates)
    'the liberty': 'Liberty hostel',
    'honesty hostel': 'Honesty Student Hostel',
    'rising star (nyberg)': 'Nyberg Hostel',
    'ghana hostels': 'Gaza Hostel',
    'morning star palace': 'Morning Star Hostel',
    'canam executive': 'Canam executive hostel',
}
_by_norm = {}
for r in clean: _by_norm.setdefault(norm(r['name']), r)
for m in MP:
    tgt = ALIAS.get(m['name'].lower())
    if tgt:
        r = _by_norm.get(norm(tgt))
        if r and not r['confirmed']:
            r['confirmed'] = True; r['phone'] = m['phone']; r['manager_phone'] = m['phone']

def _area_norm(a):
    a = (a or '').lower()
    if 'ayeduase' in a or 'newsite' in a or 'new site' in a: return 'Ayeduase'
    if 'kotei' in a: return 'Kotei'
    if 'gaza' in a: return 'Gaza'
    if 'bomso' in a: return 'Bomso'
    if 'kentinkrono' in a or 'kentikrono' in a: return 'Kentinkrono'
    if 'ahinsan' in a: return 'Ahinsan'
    if 'oduom' in a: return 'Oduom'
    return (a.title() or 'Around KNUST')

def _in_clean(name):
    nm = norm(name)
    if len(nm) < 3: return True  # too short to safely add
    for r in clean:
        hn = norm(r['name'])
        if hn == nm or (len(nm) >= 4 and (nm in hn or hn in nm)): return True
    return False

mp_added = 0
_alias_lc = set(ALIAS)
for m in MP:
    if m['name'].lower() in _alias_lc: continue
    if _in_clean(m['name']): continue
    ar = _area_norm(m['area'])
    clean.append({
        'name': m['name'], 'area': ar, 'category': 'Hostel',
        'km_from_knust': None, 'lat': None, 'lng': None,
        'maps_url': 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(m['name'] + ' hostel KNUST Kumasi'),
        'website': '', 'rating': None, 'reviews': 0, 'coord_reliable': False, 'closed': False,
        'phone': m['phone'], 'manager_phone': m['phone'], 'confirmed': True,
        'images': [], 'amenities': [], 'review_tags': [], 'colleges': colleges_for(ar),
        'price_from': None, 'rooms': [], 'price_src': '', 'added_from': 'mp_list',
    })
    mp_added += 1
print('MP-only hostels added (not in mapped set):', mp_added)

clean.sort(key=lambda r: (r['area'], -1 if r['confirmed'] else 0, -(r['rating'] or 0)))

from collections import Counter
meta = {
    'generated': '2026-06-26',
    'total': len(clean),
    'areas': [a for a,_ in Counter(r['area'] for r in clean).most_common()],
    'area_counts': dict(Counter(r['area'] for r in clean).most_common()),
    'colleges': list(COLLEGE_AREAS.keys()),
    'amenities': [a for a,_ in sorted(amen_universe.items(), key=lambda x:-x[1])],
    'confirmed': sum(1 for r in clean if r['confirmed']),
    'with_images': sum(1 for r in clean if r['images']),
    'with_amenities': sum(1 for r in clean if r['amenities']),
    'with_phone': sum(1 for r in clean if r['phone']),
    'with_price': sum(1 for r in clean if r['price_from']),
    'knust': {'lat':6.6745,'lng':-1.5716},
}
with open(os.path.join(OUT,'data.js'),'w',encoding='utf-8') as f:
    f.write('window.META = '+json.dumps(meta,ensure_ascii=False)+';\n')
    f.write('window.HOSTELS = '+json.dumps(clean,ensure_ascii=False)+';\n')

with open(os.path.join(OUT,'knust_hostels.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['Name','Area','Category','Distance_km','Rating','Reviews','Price_from_GHS','Price_source',
                'Phone','Confirmed_Contact','Amenities','Colleges_nearby','Website','Latitude','Longitude',
                'Google_Maps_URL','Image'])
    for r in clean:
        w.writerow([r['name'],r['area'],r['category'],r['km_from_knust'],r['rating'] or '',r['reviews'],
                    r['price_from'] or '',r['price_src'] or '',
                    r['phone'],'yes' if r['confirmed'] else '',' | '.join(r['amenities']),
                    ' | '.join(r['colleges']),r['website'],r['lat'],r['lng'],r['maps_url'],
                    r['images'][0] if r['images'] else ''])

print('total:',meta['total'])
print('confirmed contacts matched:',matched,'of',len(managers),'manager rows')
print('with images:',meta['with_images'],'| with amenities:',meta['with_amenities'])
print('with price:',meta['with_price'],' (getrooms exact-name matches:',sum(1 for r in clean if r['name'] in GETROOMS and r['price_from']),')')
print('amenity universe:',meta['amenities'])
print('unmatched managers (sample):')
matched_names={match_manager(r['name'])['raw'] for r in tight if match_manager(r['name'])}
for m in managers:
    if m['name'] not in matched_names:
        print('   -',m['name'],'|',m['area'])
