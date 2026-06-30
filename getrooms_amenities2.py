# -*- coding: utf-8 -*-
"""Enrich amenities from the FULL getrooms KNUST crawl (apify website-content-crawler,
.product text). Reads the saved tool-result JSON, extracts each hostel's Facilities,
maps to canonical amenities, matches to our DB by name, and merges. Idempotent."""
import json, re, os, csv, glob
from collections import Counter
OUT = r'C:\Users\mutal\skills\knust-hostels'
TR = r'C:\Users\mutal\.claude\projects\C--Users-mutal-skills\d1d1f1e5-bcce-4266-a425-6cf53b7fdd59\tool-results'

# newest get-dataset-items result file(s)
files = sorted(glob.glob(os.path.join(TR, 'mcp-7e675312-*get-dataset-items*.txt')), key=os.path.getmtime)
items = []
for fp in files:
    try:
        d = json.loads(open(fp, encoding='utf-8').read())
        for it in d.get('items', []):
            if it.get('url') and it.get('text') and '/hostels/' in it['url']:
                items.append(it)
    except Exception:
        pass
# dedupe by url
seen = {}
for it in items: seen[it['url']] = it
items = list(seen.values())
print('getrooms hostel pages found in saved results:', len(items))

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def core(s): return re.sub(r'(hostels?|hostle|hotel|lodge|apartments?|inn|house|homes?)$', '', norm(s))

def fac_text(text):
    m = re.search(r'Facilities(.*?)(?:Location|Potential Price|Room Types|Manager|Digital Address|Owner|Secure Your Room|Category|Related|About |$)', text, re.S | re.I)
    return (m.group(1) if m else '')

def to_amenities(t):
    t = t.lower(); am = set()
    if 'wifi' in t or 'wi-fi' in t or 'internet' in t: am.add('Wi-Fi')
    if 'air cond' in t or 'air-cond' in t or 'aircond' in t or 'conditioner' in t: am.add('Air-conditioned')
    if 'kitchen' in t or 'cooking' in t or 'free gas' in t: am.add('Kitchen')
    if 'study' in t or 'reading room' in t: am.add('Study room')
    if 'water' in t: am.add('Water')
    if 'cctv' in t or 'security' in t or 'guard' in t or 'fire exting' in t: am.add('Security')
    if 'generator' in t or 'standby' in t or 'backup' in t: am.add('Backup power')
    if re.search(r'\btv\b|dstv|television', t): am.add('TV')
    if 'self-contain' in t or 'self contain' in t: am.add('Self-contained')
    if 'parking' in t: am.add('Parking')
    if 'laundry' in t: am.add('Laundry service')
    if 'pool' in t or 'swimming' in t: am.add('Pool')
    if 'gym' in t or 'fitness' in t: am.add('Fitness center')
    return am

# load DB
META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '): META = json.loads(line[14:].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '): HOSTELS = json.loads(line[17:].rstrip().rstrip(';'))
by_norm, by_core = {}, {}
for h in HOSTELS:
    by_norm.setdefault(norm(h['name']), h)
    by_core.setdefault(core(h['name']), h)

def slug_to_db(url):
    m = re.search(r'/hostels/([^/?]+)', url)
    if not m: return None
    s = re.sub(r'-(kumasi|knust)$', '', m.group(1)).replace('-', ' ')
    n, c = norm(s), core(s)
    if n in by_norm: return by_norm[n]
    if len(c) >= 4 and c in by_core: return by_core[c]
    for k, h in by_norm.items():
        if len(n) >= 6 and len(k) >= 6 and (n in k or k in n): return h
    return None

matched, unmatched = {}, []
for it in items:
    fa = to_amenities(fac_text(it['text']))
    if not fa: continue
    h = slug_to_db(it['url'])
    if h: matched[h['name']] = matched.get(h['name'], set()) | fa
    else: unmatched.append(it['url'].split('/hostels/')[-1].rstrip('/'))

added = 0
for h in HOSTELS:
    if h['name'] in matched:
        before = set(h.get('amenities') or [])
        h['amenities'] = sorted(before | matched[h['name']])
        if h['amenities'] != sorted(before): added += 1

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

print(f"matched to DB: {len(matched)}   amenity rows updated: {added}")
print(f"hostels with amenities now: {META['with_amenities']}")
print(f"unmatched getrooms slugs ({len(unmatched)}):", ', '.join(unmatched[:30]))
