# -*- coding: utf-8 -*-
"""Layer the official KNUST KOSASS portal data onto the live data.js.

Reads:  data.js (current source of truth) + kosass_residences.json (scraped snapshot)
Writes: data.js + knust_hostels.csv

Design:
  * ENRICH existing matches with: registered/registration no., Ghana Post digital
    address, official zone, room count + male/female capacity, per-room-type price
    ranges, KOSASS slug/images.
  * CONTACT cross-check (user rule: "check if they match, I don't know if KOSASS is
    up to date"): never overwrite a phone we already have. If ours == KOSASS manager
    number -> mark confirmed (official portal corroborates us). If we have none ->
    fill from KOSASS but DO NOT mark confirmed (unverified). Owner/porter numbers are
    kept OUT of the public data.js (privacy) — manager number only.
  * ADD every unmatched KOSASS residence (hostels + family "homestels").
Re-runnable: strips any previous KOSASS layer first (added_from=='kosass' rows and
kosass_* fields), then re-applies.
"""
import json, re, os, csv, math, subprocess, sys, difflib
sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.dirname(os.path.abspath(__file__))
KNUST = (6.6745, -1.5716)

# ---------- load current data.js via node (robust against JS formatting) ----------
def load_datajs():
    js = ('global.window={};require(%r);'
          'process.stdout.write(JSON.stringify({M:window.META,H:window.HOSTELS}));'
          % os.path.join(OUT, 'data.js').replace('\\', '/'))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, encoding='utf-8')
    if r.returncode: raise SystemExit('node load failed:\n' + r.stderr)
    d = json.loads(r.stdout)
    return d['M'], d['H']

META, H = load_datajs()
KOS = json.load(open(os.path.join(OUT, 'kosass_residences.json'), encoding='utf-8'))['residences']
KOS = [k for k in KOS if k.get('residenceType') != 'Obuasi_Campus'
       and (k.get('location') or {}).get('name', '') != 'Obuasi']

# ---------- strip any previous KOSASS layer (idempotent re-run) ----------
KOS_FIELDS = ['registered', 'reg_no', 'digital_address', 'zone', 'rooms_total',
              'male_cap', 'female_cap', 'kosass_slug', 'kosass_manager_phone',
              'kosass_verified', 'kosass_prices']
H = [r for r in H if r.get('added_from') != 'kosass']
for r in H:
    for f in KOS_FIELDS:
        r.pop(f, None)

# ---------- helpers ----------
def digits(p):
    d = re.sub(r'\D', '', p or '')
    if len(d) == 12 and d.startswith('233'): d = '0' + d[3:]
    if len(d) == 9: d = '0' + d
    return d

def clean_phone(raw):
    """Return the phone as given only if it's a real Ghana number; else '' (KOSASS uses 'N/A', '00000000000', etc.)."""
    raw = (raw or '').strip()
    d = digits(raw)
    return raw if (len(d) == 10 and set(d) != {'0'}) else ''

def valid_digital(da):
    """Ghana Post GPS is XX-NNN-NNNN. Drop placeholders like AK-000-0000."""
    da = (da or '').strip()
    dig = re.sub(r'\D', '', da)
    if len(dig) < 6 or set(dig) == {'0'}: return ''
    return da

STOP = {'hostel','hostels','lodge','the','knust','homestel','homestels','guest','house',
        'inn','court','courts','annex','hall','residence','apartment','apartments',
        'student','students','executive','new','site','block','and'}
def nkey(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def toks(s):
    return {t for t in re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()
            if len(t) >= 3 and t not in STOP}

def haversine(a, b):
    R = 6371.0; la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))

def kcoords(k):  # KOSASS stores [lng, lat]
    c = (k.get('gpsAddress') or {}).get('coordinates') or [0, 0]
    if c and c[0] not in (0, None) and c[1] not in (0, None):
        return (c[1], c[0])
    return None

AREA_MAP = {
    'Ayeduase, North-Side': 'Ayeduase', 'Ayeduase, South-Side': 'Ayeduase',
    'Ayeduase New-Site': 'Ayeduase', 'Kotei': 'Kotei', 'Bomso': 'Bomso',
    'Boadi': 'Boadi', 'Gaza': 'Gaza', 'Kentinkrono': 'Kentinkrono',
    'Ayigya': 'Ayigya', 'Gyinyase': 'Gyinyase', 'Emena': 'Emena',
    'Ahinsan': 'Ahinsan', 'Maxima': 'Kotei',
}
def area_for(k):
    nm = (k.get('location') or {}).get('name', '')
    return AREA_MAP.get(nm, nm or 'Around KNUST')

COLLEGE_AREAS = {
 'Engineering': {'Ayeduase','On Campus (KNUST)','Gaza','Bomso','Oforikrom'},
 'Science': {'On Campus (KNUST)','Ayeduase','Bomso','Ayigya','Susuanso (campus edge)','Gaza'},
 'Art & Built Environment': {'Ayeduase','On Campus (KNUST)','Gaza','Bomso'},
 'Humanities & Social Sciences (KSB)': {'Bomso','Ayigya','Ayeduase','On Campus (KNUST)','Anloga Junction','Oforikrom','Susuanso (campus edge)'},
 'Health Sciences': {'Ayigya','Kentinkrono','Bomso','Emena','Anloga Junction','On Campus (KNUST)'},
 'Agriculture & Natural Resources': {'Kotei','Oduom','Boadi','Deduako','Anwomaso','Appiadu','Gyinyase'},
}
def colleges_for(area):
    cs = [c for c, a in COLLEGE_AREAS.items() if area in a]
    return cs or list(COLLEGE_AREAS.keys())

def num(s):
    m = re.search(r'([\d,]+(?:\.\d+)?)', s or '')
    return float(m.group(1).replace(',', '')) if m else None

def fmt_range(s):
    s = re.sub(r'\.00\b', '', (s or '')).strip()
    s = re.sub(r'\s*-\s*', ' – ', s); s = re.sub(r'\s+', ' ', s)
    return s

ROOM_LABEL = {'oneInOne': '1-in-1', 'twoInOne': '2-in-1', 'threeInOne': '3-in-1',
              'fourInOne': '4-in-1', 'others': 'Other'}
def kos_prices(k):
    """-> (rooms_list[[label,'GHS x – y'],...], price_from_number)."""
    cat = (k.get('rClass') or {}).get('category') or {}
    act = k.get('actualPrices') or {}
    rooms, lows = [], []
    for key in ['oneInOne', 'twoInOne', 'threeInOne', 'fourInOne', 'others']:
        v = (act.get(key) or '').strip() or (cat.get(key) or '').strip()
        if v:
            rooms.append([ROOM_LABEL[key], 'GHS ' + fmt_range(v)])
            lo = num(v)
            if lo: lows.append(lo)
    return rooms, (min(lows) if lows else None)

def kos_type(k):
    return 'Homestel (family home)' if k.get('residenceType') == 'Homestel' else 'Hostel'

def kos_images(k):
    slug = k.get('slug') or ''
    base = 'https://kosass.knust.edu.gh/api/images/' + slug + '/'
    out = []
    if k.get('coverImage'): out.append(base + k['coverImage'])
    for im in (k.get('images') or []):
        if im and (base + im) not in out: out.append(base + im)
    return out[:4]

# ---------- build match index over existing ----------
by_key = {}
for i, r in enumerate(H):
    by_key.setdefault(nkey(r['name']), []).append(i)
ex_tokens = [toks(r['name']) for r in H]
ex_coord = [((r['lat'], r['lng']) if r.get('coord_reliable') and r.get('lat') else None) for r in H]

def sig(tkset): return ' '.join(sorted(tkset))

used = set()
def find_match(k):
    """High-precision match. Accept only when: exact normalized name; identical
    significant-token set; >=2 shared tokens; strong string similarity; or GPS
    within 180 m — always corroborated by same area or GPS. Blocks single shared
    person-name token across differing types (homestel vs hostel)."""
    kk = nkey(k['name']); kt = toks(k['name']); kc = kcoords(k); karea = area_for(k)
    khome = k.get('residenceType') == 'Homestel'
    # 1) exact normalized name
    for i in by_key.get(kk, []):
        if i not in used: return i
    if not kt: return None
    ksig = sig(kt)
    best, best_score = None, 0.0
    for i in range(len(ex_tokens)):      # only original base records are match targets
        if i in used or not ex_tokens[i]: continue
        inter = kt & ex_tokens[i]
        if not inter: continue
        near = bool(kc and ex_coord[i] and haversine(kc, ex_coord[i]) < 0.18)  # 180 m
        area_ok = (H[i]['area'] == karea)
        if not (area_ok or near): continue          # never merge across area without GPS
        equal = (kt == ex_tokens[i])
        ratio = difflib.SequenceMatcher(None, ksig, sig(ex_tokens[i])).ratio()
        strong = any(len(t) >= 4 for t in inter)
        ex_home = str(H[i].get('type', '')).startswith('Homestel')
        # guard: a single shared token across different product types is too weak
        if len(inter) == 1 and (khome != ex_home) and not near:
            continue
        ok = equal or len(inter) >= 2 or ratio >= 0.82 or (near and strong)
        if ok:
            score = ratio + (0.5 if area_ok else 0) + (1.0 if near else 0) \
                    + 0.3 * len(inter) + (0.6 if equal else 0)
            if score > best_score: best, best_score = i, score
    return best

# ---------- apply ----------
stats = dict(exact=0, fuzzy=0, new_hostel=0, new_homestel=0,
             cross_confirmed=0, contact_filled=0, contact_conflict=0,
             price_filled=0, images_filled=0, digital=0, registered=0)
fuzzy_samples, new_samples = [], []

def enrich(r, k, fuzzy=False):
    r['registered'] = bool(k.get('registered'))
    if k.get('registered'): stats['registered'] += 1
    if k.get('registrationNumber'): r['reg_no'] = k['registrationNumber']
    da = valid_digital(k.get('digitalAddress'))
    if da: r['digital_address'] = da; stats['digital'] += 1
    z = ((k.get('location') or {}).get('zone') or {}).get('name')
    if z: r['zone'] = z
    if k.get('roomsTotal'): r['rooms_total'] = k['roomsTotal']
    if k.get('maleCapacity') is not None: r['male_cap'] = k['maleCapacity']
    if k.get('femaleCapacity') is not None: r['female_cap'] = k['femaleCapacity']
    if k.get('slug'): r['kosass_slug'] = k['slug']
    # contacts (manager only, cross-checked)
    km = digits(clean_phone(k.get('managersContact')))
    ours = digits(r.get('phone'))
    if km:
        if ours and ours == km:
            r['confirmed'] = True; r['kosass_verified'] = True; stats['cross_confirmed'] += 1
        elif not ours:
            r['phone'] = k['managersContact'].strip(); stats['contact_filled'] += 1
        elif ours != km:
            r['kosass_manager_phone'] = k['managersContact'].strip(); stats['contact_conflict'] += 1
    # prices
    rooms, pf = kos_prices(k)
    if rooms:
        r['kosass_prices'] = rooms
        if not r.get('rooms'): r['rooms'] = rooms
        if not r.get('price_from') and pf:
            r['price_from'] = int(pf); r['price_src'] = 'KNUST KOSASS portal'; stats['price_filled'] += 1
    # images
    if not r.get('images'):
        imgs = kos_images(k)
        if imgs: r['images'] = imgs; stats['images_filled'] += 1

for k in KOS:
    i = find_match(k)
    if i is not None:
        used.add(i)
        exact = nkey(H[i]['name']) == nkey(k['name'])
        stats['exact' if exact else 'fuzzy'] += 1
        if not exact and len(fuzzy_samples) < 30:
            fuzzy_samples.append((k['name'], H[i]['name'], H[i]['area']))
        enrich(H[i], k, fuzzy=not exact)
    else:
        area = area_for(k)
        c = kcoords(k)
        rooms, pf = kos_prices(k)
        typ = kos_type(k)
        stats['new_homestel' if typ.startswith('Homestel') else 'new_hostel'] += 1
        rec = {
            'name': k['name'].strip(), 'area': area, 'category': 'Lodging',
            'km_from_knust': round(haversine(c, KNUST), 2) if c else None,
            'lat': c[0] if c else None, 'lng': c[1] if c else None,
            'maps_url': ('https://www.google.com/maps/search/?api=1&query=%f,%f' % (c[0], c[1]))
                         if c else 'https://www.google.com/maps/search/?api=1&query=' +
                         re.sub(r'\s+', '%20', k['name'] + ' KNUST Kumasi'),
            'website': '', 'rating': k.get('ratingAverage') or None,
            'reviews': k.get('ratingQuantity') or 0,
            'coord_reliable': bool(c), 'closed': False,
            'phone': clean_phone(k.get('managersContact')),
            'manager_phone': '', 'confirmed': False,
            'images': kos_images(k), 'amenities': [], 'review_tags': [],
            'colleges': colleges_for(area),
            'price_from': int(pf) if pf else None, 'rooms': rooms,
            'price_src': 'KNUST KOSASS portal' if pf else '',
            'type': typ, 'added_from': 'kosass',
        }
        enrich(rec, k)             # add registered/digital/zone/capacity/etc.
        rec['added_from'] = 'kosass'
        if len(new_samples) < 30: new_samples.append((k['name'], area, typ))
        H.append(rec)

# ---------- drop broken KOSASS images (many server refs 500) ----------
# allowlist produced by validating every kosass image URL with curl (see README refresh notes)
GOOD_IMG = set()
_gp = os.path.join(OUT, 'kosass_img_allowlist.txt')
if os.path.exists(_gp):
    GOOD_IMG = {l.strip() for l in open(_gp, encoding='utf-8') if l.strip()}
if GOOD_IMG:
    dropped = 0
    for r in H:
        if r.get('images'):
            kept = [u for u in r['images'] if 'kosass.knust.edu.gh' not in u or u in GOOD_IMG]
            dropped += len(r['images']) - len(kept)
            r['images'] = kept
    print('broken KOSASS images dropped:', dropped)

# ---------- recompute META ----------
from collections import Counter
type_order = ['Hostel', 'Guest house & Hotel', 'Apartment / Self-contained', 'Homestel (family home)']
tc = Counter(r.get('type', 'Hostel') for r in H)
ac = Counter(r['area'] for r in H)
amen = Counter()
for r in H:
    for a in r.get('amenities', []): amen[a] += 1
META.update({
    'total': len(H),
    'areas': [a for a, _ in ac.most_common()],
    'area_counts': dict(ac.most_common()),
    'types': [t for t in type_order if tc.get(t)] + [t for t in tc if t not in type_order],
    'type_counts': {**{t: tc[t] for t in type_order if tc.get(t)},
                    **{t: tc[t] for t in tc if t not in type_order}},
    'confirmed': sum(1 for r in H if r.get('confirmed')),
    'with_images': sum(1 for r in H if r.get('images')),
    'with_amenities': sum(1 for r in H if r.get('amenities')),
    'with_phone': sum(1 for r in H if r.get('phone')),
    'with_price': sum(1 for r in H if r.get('price_from')),
    'registered_count': sum(1 for r in H if r.get('registered')),
    'with_digital': sum(1 for r in H if r.get('digital_address')),
    'source': 'Google Maps + Campus-MP/SRC lists + official KNUST KOSASS portal',
})

# ---------- write ----------
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.META = ' + json.dumps(META, ensure_ascii=False) + ';\n')
    f.write('window.HOSTELS = ' + json.dumps(H, ensure_ascii=False) + ';\n')

with open(os.path.join(OUT, 'knust_hostels.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Name','Area','Type','Category','Distance_km','Rating','Reviews','Price_from_GHS',
                'Price_source','Phone','Confirmed_Contact','KNUST_Registered','Reg_No','Digital_Address',
                'Rooms_Total','Male_Cap','Female_Cap','Amenities','Colleges_nearby','Website',
                'Latitude','Longitude','Google_Maps_URL','Image'])
    for r in H:
        w.writerow([r['name'], r['area'], r.get('type',''), r.get('category',''), r.get('km_from_knust'),
                    r.get('rating') or '', r.get('reviews'), r.get('price_from') or '', r.get('price_src') or '',
                    r.get('phone'), 'yes' if r.get('confirmed') else '',
                    'yes' if r.get('registered') else '', r.get('reg_no',''), r.get('digital_address',''),
                    r.get('rooms_total',''), r.get('male_cap',''), r.get('female_cap',''),
                    ' | '.join(r.get('amenities',[])), ' | '.join(r.get('colleges',[])), r.get('website',''),
                    r.get('lat'), r.get('lng'), r.get('maps_url'), (r.get('images') or [''])[0]])

# ---------- report ----------
print('=== KOSASS merge report ===')
print('existing base:', len(H) - stats['new_hostel'] - stats['new_homestel'], '| final total:', len(H))
for k, v in stats.items(): print('  %-18s %d' % (k, v))
print('\ntypes:', dict(META['type_counts']))
print('registered:', META['registered_count'], '| with digital addr:', META['with_digital'],
      '| confirmed contacts:', META['confirmed'], '| with price:', META['with_price'])
print('\nFUZZY matches (KOSASS name  ->  our name  [area]) — eyeball for false merges:')
for a, b, ar in fuzzy_samples: print('   %-32s -> %-32s [%s]' % (a[:32], b[:32], ar))
print('\nNEW entries added (sample):')
for a, ar, t in new_samples: print('   %-34s %-12s %s' % (a[:34], ar, t))
