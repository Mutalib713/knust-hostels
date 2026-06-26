# -*- coding: utf-8 -*-
"""Merge + clean both Apify Google Maps runs into the final KNUST hostel dataset."""
import json, re, os, sys, math, csv
sys.stdout.reconfigure(encoding='utf-8')

TR = r'C:\Users\mutal\.claude\projects\C--Users-mutal-skills\35adc9b3-602b-448c-83ac-f38b924f1253\tool-results'
RUN1 = os.path.join(TR, 'mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782457366179.txt')  # 150, has placeId
RUN2 = os.path.join(TR, 'mcp-7e675312-4441-46fb-94ba-7aaa9669b26f-get-dataset-items-1782458563605.txt')  # 527, has placeId
OUT = r'C:\Users\mutal\skills\knust-hostels'

items = []
for f in (RUN1, RUN2):
    items += json.load(open(f, encoding='utf-8'))['items']
print('combined raw items:', len(items))

# ---------- helpers ----------
KLAT, KLNG = 6.6745, -1.5716
def hav(la1, lo1, la2, lo2):
    R = 6371.0
    dla = math.radians(la2-la1); dlo = math.radians(lo2-lo1)
    a = math.sin(dla/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlo/2)**2
    return 2*R*math.asin(math.sqrt(a))

BELT = {
    'Ayeduase': (6.6785, -1.5560), 'Bomso': (6.6850, -1.5790),
    'Ayigya': (6.6915, -1.5640), 'Kotei': (6.6880, -1.5380),
    'Kentinkrono': (6.7080, -1.5680), 'Boadi': (6.6720, -1.5230),
    'Deduako': (6.6640, -1.5360), 'Anloga Junction': (6.6960, -1.5740),
    'Oforikrom': (6.6790, -1.5860), 'Emena': (6.7180, -1.5520),
    'Maxima': (6.7010, -1.5560),
}
WIDER = dict(BELT, **{
    'Nhyiaeso': (6.6830, -1.6290), 'Kwadaso': (6.6890, -1.6460),
    'Tafo': (6.7350, -1.6060), 'Asuoyeboa': (6.6920, -1.6680),
    'Ampabame': (6.6080, -1.6320), 'Bantama': (6.7050, -1.6280),
    'Suntreso': (6.6950, -1.6420), 'Santasi': (6.6620, -1.6420),
    'Atonsu': (6.6480, -1.5680), 'Ahinsan': (6.6560, -1.5950),
    'Asokore Mampong': (6.7200, -1.5350), 'Asokwa': (6.6650, -1.5950),
})

ACCOMM_CATS = {'Hostel','Hotel','Guest house','Lodging','Bed & breakfast',
               'Student dormitory','Group accommodation','Housing complex','Resort hotel','Motel','Inn'}
NAME_KW = ['hostel','hall','lodge','lodging','residenc','residency',' inn','inn ','guest house',
           'guesthouse','suites','court','apartment','annex','dormitor']
EXCLUDE_EXACT = {'nhyiaeso','dakodwom','odeneho kwadaso','angola junction','bakana plaza',
                 'notice boardgh','ipmc kumasi','chokmarh','christian service university',
                 'kessben university college','daybreak house','knust gymnasium','ahinsan estate',
                 'aputuogye','kk','nhyiaeso','dakodwom'}
EXCLUDE_KW = ['restaurant','gas station','totalenergies','museum','gymnasium','university college',
              'clothing','fashion','tailor','newspaper','media group','tour','warehouse','atelier',
              'pharmacy','hospital','school','church','bank','filling station']

def is_accom(it):
    cat = (it.get('categoryName') or '').strip()
    title = (it.get('title') or '').strip()
    tl = title.lower()
    if not title or tl in EXCLUDE_EXACT:
        return False
    if any(k in tl for k in ['bus stop','bus station','taxi rank','lorry station','bus terminal']):
        return False
    # explicit non-accommodation categories override unless name clearly says hostel/hall
    namey = any(k in tl for k in ['hostel','hall','lodge',' inn','residence','dormitor'])
    if not namey:
        if any(k in (cat or '').lower() for k in EXCLUDE_KW):
            return False
        if any(k in tl for k in EXCLUDE_KW):
            return False
    if cat in ACCOMM_CATS:
        return True
    if any(k in tl for k in NAME_KW):
        return True
    return False

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

# ---------- dedup by placeId, then by name+proximity ----------
by_pid = {}
no_pid = []
for it in items:
    pid = it.get('placeId')
    if pid:
        # keep the record with more reviews / longer address (richer)
        prev = by_pid.get(pid)
        if prev is None or (it.get('reviewsCount') or 0) > (prev.get('reviewsCount') or 0):
            by_pid[pid] = it
    else:
        no_pid.append(it)
records = list(by_pid.values()) + no_pid
print('after placeId dedup:', len(records))

# filter to accommodation
accom = [it for it in records if is_accom(it)]
print('accommodation after filter:', len(accom))

# name + proximity dedup (merge same-name within 300 m; keep distinct locations separate)
accom.sort(key=lambda it: -(it.get('reviewsCount') or 0))  # prefer richer first
final = []
for it in accom:
    n = norm(it.get('title'))
    la, lo = it.get('location.lat'), it.get('location.lng')
    dup = False
    for u in final:
        if norm(u.get('title')) == n:
            ula, ulo = u.get('location.lat'), u.get('location.lng')
            if la and lo and ula and ulo:
                if hav(la, lo, ula, ulo) < 0.3:
                    dup = True; break
            else:
                dup = True; break
    if not dup:
        final.append(it)
print('after name+proximity dedup:', len(final))

# ---------- flag shared/fallback coordinates ----------
from collections import Counter
cc = Counter((round(it['location.lat'],5), round(it['location.lng'],5)) for it in final if it.get('location.lat'))
shared = {k for k,v in cc.items() if v > 1}

def area_for(it, km):
    table = BELT if (km is not None and km <= 7) else WIDER
    la, lo = it.get('location.lat'), it.get('location.lng')
    # text hint first
    blob = ' '.join(str(it.get(k) or '') for k in ('neighborhood','address','searchString'))
    for name in WIDER:
        if re.search(r'\b'+re.escape(name.split()[0]), blob, re.I):
            return name
    if la and lo:
        return min(table.items(), key=lambda kv: hav(la,lo,kv[1][0],kv[1][1]))[0]
    return it.get('neighborhood') or 'Kumasi'

# ---------- build clean records ----------
clean = []
for it in final:
    la, lo = it.get('location.lat'), it.get('location.lng')
    km = round(hav(la, lo, KLAT, KLNG), 2) if (la and lo) else None
    coord_ok = not (la and (round(la,5), round(lo,5)) in shared)
    clean.append({
        'name': (it.get('title') or '').strip(),
        'category': (it.get('categoryName') or '').strip() or 'Accommodation',
        'area': area_for(it, km),
        'km_from_knust': km,
        'address': (it.get('address') or '').strip(),
        'lat': la, 'lng': lo,
        'coord_reliable': coord_ok,
        'maps_url': it.get('url') or '',
        'phone': (it.get('phone') or '').strip(),
        'website': (it.get('website') or '').strip(),
        'rating': it.get('totalScore'),
        'reviews': it.get('reviewsCount') or 0,
        'closed': bool(it.get('permanentlyClosed') or it.get('temporarilyClosed')),
    })

# keep KNUST catchment (<=7km) as the primary dataset; note the rest
near = [r for r in clean if r['km_from_knust'] is not None and r['km_from_knust'] <= 7]
far  = [r for r in clean if not (r['km_from_knust'] is not None and r['km_from_knust'] <= 7)]
near.sort(key=lambda r: (r['area'], -(r['reviews'] or 0)))

json.dump(near, open(os.path.join(OUT,'hostels_final.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(far,  open(os.path.join(OUT,'hostels_far_kumasi.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)

print()
print('FINAL KNUST-area hostels (<=7km):', len(near))
print('Also found, wider Kumasi (>7km):', len(far))
print('records with unreliable (shared) coords:', sum(1 for r in near if not r['coord_reliable']))
print()
print('--- by AREA (nearest locality) ---')
for a,n in Counter(r['area'] for r in near).most_common():
    print(f'{n:3d}  {a}')
print()
print('--- spot-check: famous Ayeduase/Bomso hostels captured? ---')
for key in ['frontline','franco','evandy','evandi','wagyingo','amen','asabek','providence','happy family','flint','elshadai','rising sun','anarosa','west end','nyberg','jita','ultimate','standard','kharis','de-lisa','delisa','nyame mireku','urban platinum','four seasons','achiba','destiny view']:
    hits=[r['name'] for r in near if key in r['name'].lower()]
    if hits: print(f'  {key:14s}: {hits}')
