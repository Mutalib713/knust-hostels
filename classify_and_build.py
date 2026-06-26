# -*- coding: utf-8 -*-
"""Assign accurate areas from reverse-geocoded suburbs, tighten to the KNUST
student belt + on-campus, then rebuild CSV + data.js."""
import json, csv, os, sys, math, re
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'

H = json.load(open(os.path.join(OUT, 'hostels_final.json'), encoding='utf-8'))
cache = json.load(open(os.path.join(OUT, 'geo_cache.json'), encoding='utf-8'))

# hostels that have been renamed (keep old name in the label so search still finds it)
RENAMES = {'wilkado hostel': 'Osei Sarfo-Kantanka Hostel (formerly Wilkado)'}
for _r in H:
    _nl = (_r.get('name') or '').strip().lower()
    if _nl in RENAMES:
        _r['name'] = RENAMES[_nl]
KLAT, KLNG = 6.6745, -1.5716
def hav(la1, lo1, la2, lo2):
    R=6371.0; dla=math.radians(la2-la1); dlo=math.radians(lo2-lo1)
    a=math.sin(dla/2)**2+math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlo/2)**2
    return 2*R*math.asin(math.sqrt(a))
def gkey(r): return f"{round(r['lat'],5)},{round(r['lng'],5)}"

# real KNUST campus boundary (OpenStreetMap) -> point-in-polygon for on-campus
CAMPUS = json.load(open(os.path.join(OUT, 'campus_rings_kumasi.json')))
def _in_ring(lon, lat, ring):
    inside=False; n=len(ring); j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        if ((yi>lat)!=(yj>lat)) and (lon<(xj-xi)*(lat-yi)/(yj-yi)+xi): inside=not inside
        j=i
    return inside
def in_campus(lat, lng): return any(_in_ring(lng, lat, r) for r in CAMPUS)

# canonical suburb -> display area  (KNUST student belt only)
def canon(suburb):
    s = (suburb or '').lower()
    table = [
        (('ayeduase','ayiduase','ayuduase'), 'Ayeduase'),
        (('bomso',), 'Bomso'),
        (('kotei','kotie'), 'Kotei'),
        (('ayigya','ayija'), 'Ayigya'),
        (('kentinkrono','kentikrono','kentinkurono'), 'Kentinkrono'),
        (('boadi',), 'Boadi'),
        (('deduako','deduako'), 'Deduako'),
        (('susuanso','susanso','sisuanso'), 'Susuanso (campus edge)'),
        (('oforikrom',), 'Oforikrom'),
        (('emena',), 'Emena'),
        (('maxima',), 'Maxima'),
        (('anloga',), 'Anloga Junction'),
        (('oduom',), 'Oduom'),
        (('appiadu','apiadu'), 'Appiadu'),
        (('gyinyase','gyinyasi','gyenyase'), 'Gyinyase'),
        (('anwomaso','anomaso'), 'Anwomaso'),
    ]
    for keys, name in table:
        if any(k in s for k in keys):
            return name
    return None  # not in the student belt -> will be dropped

HALL_RE = re.compile(r'\b(university hall|unity hall|republic hall|independence hall|africa hall|'
                     r'queen.?s? hall|queen elizabeth|katanga|brunei|hall 7|impact hall|'
                     r'continental hall|gusss|src hostel|knust hall)\b', re.I)

# enrich
for r in H:
    g = cache.get(gkey(r), {})
    r['osm_suburb'] = g.get('suburb', '')
    r['osm_county'] = g.get('county', '')
    r['km'] = round(hav(r['lat'], r['lng'], KLAT, KLNG), 2) if r['lat'] else None
    r['_canon'] = canon(r['osm_suburb'])

# data-driven centroids for each belt area (from points that got a clean suburb)
pts = defaultdict(list)
for r in H:
    if r['_canon'] and r['lat']:
        pts[r['_canon']].append((r['lat'], r['lng']))
CENTROID = {a: (sum(p[0] for p in v)/len(v), sum(p[1] for p in v)/len(v)) for a, v in pts.items()}

def nearest_belt(r):
    if not r['lat'] or not CENTROID: return (None, None)
    a, c = min(CENTROID.items(), key=lambda kv: hav(r['lat'], r['lng'], kv[1][0], kv[1][1]))
    return a, round(hav(r['lat'], r['lng'], c[0], c[1]), 2)

# final classification
kept, dropped = [], []
for r in H:
    # Gaza: a distinct (slightly off-campus) hostel pocket NE of campus
    gaza = r['lat'] is not None and hav(r['lat'], r['lng'], 6.6871, -1.5553) <= 0.5
    on_campus = (r['lat'] is not None and in_campus(r['lat'], r['lng'])) or (
        bool(HALL_RE.search(r['name'])) and r['km'] is not None and r['km'] <= 1.6)
    area = None
    if gaza:
        area = 'Gaza'
    elif on_campus:
        area = 'On Campus (KNUST)'
    elif r['_canon']:
        area = r['_canon']
    else:
        nb, nd = nearest_belt(r)
        if nb and nd is not None and nd <= 1.6:   # close to a belt centroid -> adopt it
            area = nb
    # distance backstop: students want CLOSE; drop anything beyond 6 km
    if area and r['km'] is not None and r['km'] > 6 and area not in ('On Campus (KNUST)', 'Gaza'):
        area = None
    if area:
        r['area'] = area
        kept.append(r)
    else:
        dropped.append(r)

# clean output rows
def slim(r):
    return {k: r[k] for k in ('name','category','area','km','address','lat','lng','maps_url',
                              'phone','website','rating','reviews','coord_reliable','closed','osm_suburb')}
near = [slim(r) for r in kept]
near = [{**d, 'km_from_knust': d.pop('km')} for d in near]

# order areas: On Campus first, then by distance of centroid to KNUST
def area_rank(a):
    if a == 'On Campus (KNUST)': return -2
    if a == 'Gaza': return -1
    pts2 = [r for r in near if r['area']==a and r['km_from_knust'] is not None]
    return sum(r['km_from_knust'] for r in pts2)/len(pts2) if pts2 else 999
areas_sorted = sorted(set(r['area'] for r in near), key=area_rank)
near.sort(key=lambda r:(areas_sorted.index(r['area']), -(r['rating'] or 0), -(r['reviews'] or 0)))

# CSV
with open(os.path.join(OUT,'knust_hostels.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['Name','Area','Category','Distance_km_from_KNUST','Rating','Reviews','Phone','Website',
                'Address','Latitude','Longitude','Google_Maps_URL','Location_Reliable','Closed'])
    for r in near:
        w.writerow([r['name'],r['area'],r['category'],r['km_from_knust'],r['rating'] or '',r['reviews'] or 0,
                    r['phone'],r['website'],r['address'],r['lat'],r['lng'],r['maps_url'],
                    'yes' if r['coord_reliable'] else 'approx','yes' if r['closed'] else 'no'])

# data.js
meta = {
  'generated':'2026-06-26','total':len(near),
  'areas':areas_sorted,
  'area_counts':dict(Counter(r['area'] for r in near)),
  'with_phone':sum(1 for r in near if r['phone']),
  'with_rating':sum(1 for r in near if r['rating']),
  'gps_verified':sum(1 for r in near if r['coord_reliable']),
  'on_campus':sum(1 for r in near if r['area']=='On Campus (KNUST)'),
  'categories':[c for c,_ in Counter(r['category'] for r in near).most_common()],
  'knust':{'lat':KLAT,'lng':KLNG},
}
with open(os.path.join(OUT,'data.js'),'w',encoding='utf-8') as f:
    f.write('window.META = '+json.dumps(meta,ensure_ascii=False)+';\n')
    f.write('window.HOSTELS = '+json.dumps(near,ensure_ascii=False)+';\n')
json.dump(near, open(os.path.join(OUT,'hostels_tight.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=2)

print('KEPT (KNUST belt + on-campus):', len(near))
print('DROPPED (too far / wrong area):', len(dropped))
print('on campus:', meta['on_campus'])
print()
print('--- FINAL by area ---')
for a in areas_sorted:
    print(f"{meta['area_counts'][a]:3d}  {a}")
print()
print('--- DROPPED suburbs (top) ---')
for s,n in Counter((r['osm_suburb'] or '(none)') for r in dropped).most_common(20):
    print(f'{n:3d}  {s}')
print()
print('--- on-campus names (sample) ---')
for r in near:
    if r['area']=='On Campus (KNUST)':
        print('   ', r['name'][:40], '|', r['osm_suburb'], '| km', r['km_from_knust'])
