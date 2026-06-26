# -*- coding: utf-8 -*-
"""Fetch the real KNUST campus boundary from OpenStreetMap (Overpass) and test
point-in-polygon against the hostels the user says are on campus."""
import json, sys, ssl, urllib.request, urllib.parse, os
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'
SSL_CTX = ssl.create_default_context(); SSL_CTX.check_hostname=False; SSL_CTX.verify_mode=ssl.CERT_NONE

Q = """[out:json][timeout:90];
(
  way["amenity"="university"]["name"~"Kwame Nkrumah",i];
  relation["amenity"="university"]["name"~"Kwame Nkrumah",i];
  way["amenity"="university"]["name"~"KNUST",i];
  relation["amenity"="university"]["name"~"KNUST",i];
);
out geom;"""

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter",
             "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

data = None
for ep in ENDPOINTS:
    try:
        req = urllib.request.Request(ep, data=urllib.parse.urlencode({'data': Q}).encode(),
                                     headers={'User-Agent': 'knust-hostels-research/1.0'})
        with urllib.request.urlopen(req, timeout=90, context=SSL_CTX) as r:
            data = json.load(r)
        print('OK via', ep); break
    except Exception as e:
        print('fail', ep, str(e)[:80])

if not data:
    print('NO DATA'); sys.exit(1)

# collect rings (each way's geometry as a lat/lng ring)
rings = []
for el in data.get('elements', []):
    if el.get('type') == 'way' and el.get('geometry'):
        ring = [(p['lon'], p['lat']) for p in el['geometry']]
        if len(ring) >= 4:
            rings.append(ring)
    if el.get('type') == 'relation':
        for m in el.get('members', []):
            if m.get('role') == 'outer' and m.get('geometry'):
                ring = [(p['lon'], p['lat']) for p in m['geometry']]
                if len(ring) >= 4:
                    rings.append(ring)
print('rings:', len(rings), '| ring sizes:', [len(r) for r in rings][:10])
# bbox of all rings
allpts = [p for r in rings for p in r]
if allpts:
    lons=[p[0] for p in allpts]; lats=[p[1] for p in allpts]
    print(f'bbox lng [{min(lons):.4f},{max(lons):.4f}] lat [{min(lats):.4f},{max(lats):.4f}]')
json.dump(rings, open(os.path.join(OUT,'campus_rings.json'),'w'), ensure_ascii=False)

def in_ring(lon, lat, ring):
    inside=False; n=len(ring); j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        if ((yi>lat)!=(yj>lat)) and (lon < (xj-xi)*(lat-yi)/(yj-yi)+xi):
            inside=not inside
        j=i
    return inside
def on_campus(lat,lng): return any(in_ring(lng,lat,r) for r in rings)

H = json.load(open(os.path.join(OUT,'hostels_final.json'), encoding='utf-8'))
print('\n--- user-named hostels (should be ON campus) ---')
for s in ['spring','shaba','steven','paris','transport','tep ','t.e.p','independence hall','university hall']:
    for r in H:
        if s in r['name'].lower():
            ic = on_campus(r['lat'], r['lng']) if r['lat'] else False
            print(f"  {r['name'][:34]:34s} km={r['km_from_knust']:>4} inCampus={ic}  (osm was {r.get('osm_suburb','?')})")

inside_all = [r for r in H if r['lat'] and on_campus(r['lat'], r['lng'])]
print(f'\nTOTAL hostels inside KNUST campus polygon: {len(inside_all)} of {len(H)}')
