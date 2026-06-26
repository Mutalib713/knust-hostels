# -*- coding: utf-8 -*-
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'
rings = json.load(open(os.path.join(OUT,'campus_rings.json')))

# keep only rings located in Kumasi (KNUST), drop the stray Accra ring
def ring_bbox(r):
    lons=[p[0] for p in r]; lats=[p[1] for p in r]
    return min(lons),max(lons),min(lats),max(lats)
kept=[]
for r in rings:
    mnlo,mxlo,mnla,mxla = ring_bbox(r)
    cx=(mnlo+mxlo)/2; cy=(mnla+mxla)/2
    if -1.62 < cx < -1.54 and 6.64 < cy < 6.72:
        kept.append(r); print('keep ring pts=%d bbox lng[%.4f,%.4f] lat[%.4f,%.4f]'%(len(r),mnlo,mxlo,mnla,mxla))
    else:
        print('DROP stray ring pts=%d bbox lng[%.4f,%.4f] lat[%.4f,%.4f]'%(len(r),mnlo,mxlo,mnla,mxla))
json.dump(kept, open(os.path.join(OUT,'campus_rings_kumasi.json'),'w'))

def in_ring(lon,lat,ring):
    inside=False; n=len(ring); j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        if ((yi>lat)!=(yj>lat)) and (lon<(xj-xi)*(lat-yi)/(yj-yi)+xi): inside=not inside
        j=i
    return inside
def on_campus(lat,lng): return any(in_ring(lng,lat,r) for r in kept)

H=json.load(open(os.path.join(OUT,'hostels_final.json'),encoding='utf-8'))
cache=json.load(open(os.path.join(OUT,'geo_cache.json'),encoding='utf-8'))
def gk(r): return f"{round(r['lat'],5)},{round(r['lng'],5)}"
inside=[r for r in H if r['lat'] and on_campus(r['lat'],r['lng'])]
inside.sort(key=lambda r:r['km_from_knust'] if r['km_from_knust'] is not None else 9)
print('\nINSIDE campus:',len(inside),'of',len(H))
print('--- all on-campus hostels (name | km | osm_suburb) ---')
for r in inside:
    sub=cache.get(gk(r),{}).get('suburb','')
    print(f"  {r['name'][:40]:40s} {r['km_from_knust']:>4}km  {sub}")
