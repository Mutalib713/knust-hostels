# -*- coding: utf-8 -*-
"""Deep de-dup + cleanup pass over data.js (run AFTER kosass_merge.py).

Two jobs:
  1) Drop nameless junk entries that KOSASS carries ("No Name", "Homestel (No Name) N",
     "Unnamed Hostel") — unsearchable, mostly no phone/coords.
  2) Merge high-confidence duplicate pairs (same place listed twice — usually a KOSASS
     spelling variant of an existing Google entry that didn't match in the merge).

Safeguards against wrong merges:
  - A pair is a duplicate only with a strong signal: same valid phone + similar name,
    near-identical name (same area or GPS<60m), or GPS<18m + clear name overlap.
  - `separate_buildings()` blocks merging annexes/wings/numbered blocks of one chain
    (Amen Annex vs Amen Main, Celia Royale Annex vs Main, Franco Hostel vs Annex …).
  - When merging, the richer record (rating/reviews/images) is kept and the other's
    unique fields (registration, digital address, prices, capacity) are folded in.

Usage:  python kosass_dedupe.py --dry   (report only)   |   python kosass_dedupe.py
Re-runnable (idempotent once applied).
"""
import json, re, os, csv, math, subprocess, sys, difflib
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.dirname(os.path.abspath(__file__))
DRY = '--dry' in sys.argv

def load_datajs():
    js = ('global.window={};require(%r);process.stdout.write(JSON.stringify({M:window.META,H:window.HOSTELS}));'
          % os.path.join(OUT, 'data.js').replace('\\', '/'))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, encoding='utf-8')
    if r.returncode: raise SystemExit('node load failed:\n' + r.stderr)
    d = json.loads(r.stdout); return d['M'], d['H']

META, H = load_datajs()

def digits(p):
    d = re.sub(r'\D', '', p or '')
    if len(d) == 12 and d.startswith('233'): d = '0' + d[3:]
    if len(d) == 9: d = '0' + d
    return d
def valid_phone(p):
    d = digits(p); return d if len(d) == 10 and set(d) != {'0'} else ''
def nkey(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def nameless(r):
    n = (r.get('name') or '').strip()
    return (not n) or bool(re.search(r'no ?name|unnamed', n, re.I))

def hav(a, b):
    R = 6371000.0; la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))
def coord(r):
    return (r['lat'], r['lng']) if r.get('lat') is not None and r.get('coord_reliable') else None

# building-suffix guard: tokens keeping annex/main/2/etc, only stripping generic words
GEN = {'hostel','hostels','lodge','homestel','homestels','residence','the','knust','guest',
       'house','ltd','limited','student','students','hotel','apartment','apartments'}
BUILD = {'annex','main','2','3','ii','iii','new','onyx','opal','gold','hall','court','inn',
         'block','wing','east','west','north','south','extension','ext','phase','premium',
         '1','i','2nd','3rd','a','b','c','pearl','ruby','jade','silver','platinum'}
def btoks(s):
    return {t for t in re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split() if t and t not in GEN}
def separate_buildings(a, b):
    diff = btoks(a).symmetric_difference(btoks(b))
    return bool(diff) and diff <= BUILD          # differ ONLY by building words -> keep apart

def cname(s):
    """core name for similarity: drop generic/filler words, then alnum only.
    So 'De Nad Hostel.'=='Denad', 'R and B Hostel'=='R & B Hostel', 'Classic Homestel'=='Classic Hostel'."""
    s = re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower())
    toks = [t for t in s.split() if t and t not in (GEN | {'and'})]
    return ''.join(toks)
def ratio(a, b): return difflib.SequenceMatcher(None, cname(a), cname(b)).ratio()

# pairs deliberately kept separate (distinct places despite a similar name / shared phone)
EXCLUDE = {frozenset(['La Casa Maria', 'Casa Maria']),
           frozenset(['Christian Hostel', 'Christiana Homestel'])}

# ---------- 1) drop nameless ----------
before = len(H)
dropped = [r for r in H if nameless(r)]
H = [r for r in H if not nameless(r)]
print('=== 1) nameless entries dropped: %d ===' % len(dropped))
for r in dropped[:6]: print('   -', repr(r['name']), '| phone', valid_phone(r.get('phone')) or '-')
if len(dropped) > 6: print('   … +%d more' % (len(dropped) - 6))

# ---------- 2) find duplicate pairs ----------
def is_dup(a, b):
    if frozenset([a['name'], b['name']]) in EXCLUDE: return None
    if separate_buildings(a['name'], b['name']): return None
    if not cname(a['name']) or not cname(b['name']): return None
    pa, pb = valid_phone(a['phone']), valid_phone(b['phone'])
    ca, cb = coord(a), coord(b)
    dist = hav(ca, cb) if ca and cb else None
    r = ratio(a['name'], b['name'])                 # similarity on CORE names
    samep = pa and pa == pb
    tokover = bool(btoks(a['name']) & btoks(b['name']))
    # signals (core-name similarity is the discriminator, so shared-manager-phone across
    # genuinely different hostels — THE BEST vs His Majesty — is rejected)
    if samep and r >= 0.80: return 'same-phone+name'
    if r >= 0.90 and (a['area'] == b['area'] or (dist is not None and dist < 60)): return 'near-identical-name'
    if dist is not None and dist < 18 and tokover and r >= 0.62: return 'same-spot+name'
    return None

n = len(H)
parent = list(range(n))
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(x, y): parent[find(x)] = find(y)

pairs = []
for i in range(n):
    for j in range(i+1, n):
        why = is_dup(H[i], H[j])
        if why:
            pairs.append((i, j, why)); union(i, j)

clusters = {}
for i in range(n): clusters.setdefault(find(i), []).append(i)
dupclusters = [idxs for idxs in clusters.values() if len(idxs) > 1]

print('\n=== 2) duplicate clusters to merge: %d (from %d flagged pairs) ===' % (len(dupclusters), len(pairs)))
def richness(r):
    return ((1 if r.get('rating') else 0)*3 + (r.get('reviews') or 0)*0.01 + len(r.get('images') or [])
            + (2 if r.get('confirmed') else 0) + (1 if r.get('coord_reliable') else 0)
            + (2 if r.get('added_from') != 'kosass' else 0))   # prefer the Google-mapped record as keeper
for idxs in sorted(dupclusters, key=lambda c: -len(c)):
    rs = sorted((H[i] for i in idxs), key=richness, reverse=True)
    keep = rs[0]
    print('  KEEP %-30s [%s]  <=  %s' % (keep['name'][:30], keep['area'],
          ' + '.join('%s(%s,%s)' % (x['name'][:22], x['area'], x.get('added_from','google')) for x in rs[1:])))

# ---------- 3) apply merges ----------
def merge_into(keep, other):
    # phone / confirmed
    pk, po = valid_phone(keep.get('phone')), valid_phone(other.get('phone'))
    if pk and po and pk == po: keep['confirmed'] = True
    if not pk and po: keep['phone'] = other.get('phone')
    keep['confirmed'] = bool(keep.get('confirmed') or other.get('confirmed'))
    # fill scalars if missing on keeper
    for f in ['website','price_from','price_src','rating','reviews','digital_address','zone',
              'reg_no','rooms_total','male_cap','female_cap','kosass_slug','kosass_manager_phone']:
        if not keep.get(f) and other.get(f): keep[f] = other[f]
    keep['registered'] = bool(keep.get('registered') or other.get('registered'))
    if other.get('kosass_verified'): keep['kosass_verified'] = True
    # unions
    for f in ['images','amenities','review_tags']:
        seen = list(keep.get(f) or [])
        for v in (other.get(f) or []):
            if v not in seen: seen.append(v)
        keep[f] = seen
    if not keep.get('rooms') and other.get('rooms'): keep['rooms'] = other['rooms']
    if not keep.get('kosass_prices') and other.get('kosass_prices'): keep['kosass_prices'] = other['kosass_prices']
    # better coords: prefer a reliable coord if keeper lacks one
    if not keep.get('coord_reliable') and other.get('coord_reliable'):
        keep['lat'], keep['lng'], keep['coord_reliable'] = other['lat'], other['lng'], True
        keep['km_from_knust'] = other.get('km_from_knust', keep.get('km_from_knust'))

drop_idx = set()
for idxs in dupclusters:
    rs = sorted(idxs, key=lambda i: richness(H[i]), reverse=True)
    keep = H[rs[0]]
    for i in rs[1:]:
        merge_into(keep, H[i]); drop_idx.add(i)
H2 = [r for i, r in enumerate(H) if i not in drop_idx]

print('\nSUMMARY: %d -> %d  (dropped %d nameless, merged %d dup records)'
      % (before, len(H2), len(dropped), len(drop_idx)))

if DRY:
    print('\n[dry run — no files written]'); sys.exit(0)

H = H2
# ---------- recompute META ----------
from collections import Counter
type_order = ['Hostel','Guest house & Hotel','Apartment / Self-contained','Homestel (family home)']
tc = Counter(r.get('type','Hostel') for r in H); ac = Counter(r['area'] for r in H)
amen = Counter()
for r in H:
    for a in r.get('amenities', []): amen[a] += 1
META.update({
    'total': len(H), 'areas': [a for a,_ in ac.most_common()], 'area_counts': dict(ac.most_common()),
    'types': [t for t in type_order if tc.get(t)] + [t for t in tc if t not in type_order],
    'type_counts': {**{t: tc[t] for t in type_order if tc.get(t)}, **{t: tc[t] for t in tc if t not in type_order}},
    'amenities': [a for a,_ in amen.most_common()],
    'confirmed': sum(1 for r in H if r.get('confirmed')), 'with_images': sum(1 for r in H if r.get('images')),
    'with_amenities': sum(1 for r in H if r.get('amenities')), 'with_phone': sum(1 for r in H if r.get('phone')),
    'with_price': sum(1 for r in H if r.get('price_from')),
    'registered_count': sum(1 for r in H if r.get('registered')),
    'with_digital': sum(1 for r in H if r.get('digital_address')),
})
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(META, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(H, ensure_ascii=False) + ';\n')
with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name','Area','Type','Category','Distance_km','Rating','Reviews','Price_from_GHS','Price_source',
                'Phone','Confirmed_Contact','KNUST_Registered','Reg_No','Digital_Address','Rooms_Total','Male_Cap',
                'Female_Cap','Amenities','Colleges_nearby','Website','Latitude','Longitude','Google_Maps_URL','Image'])
    for r in H:
        w.writerow([r['name'],r['area'],r.get('type',''),r.get('category',''),r.get('km_from_knust'),
                    r.get('rating') or '',r.get('reviews'),r.get('price_from') or '',r.get('price_src') or '',
                    r.get('phone'),'yes' if r.get('confirmed') else '','yes' if r.get('registered') else '',
                    r.get('reg_no',''),r.get('digital_address',''),r.get('rooms_total',''),r.get('male_cap',''),
                    r.get('female_cap',''),' | '.join(r.get('amenities',[])),' | '.join(r.get('colleges',[])),
                    r.get('website',''),r.get('lat'),r.get('lng'),r.get('maps_url'),(r.get('images') or [''])[0]])
print('\nwrote data.js + knust_hostels.csv  ->  total now', len(H))
