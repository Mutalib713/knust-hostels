# -*- coding: utf-8 -*-
"""Reverse-geocode every hostel coordinate to its real OSM suburb (Nominatim)."""
import json, sys, time, ssl, os, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'
CACHE = os.path.join(OUT, 'geo_cache.json')

SSL_CTX = ssl.create_default_context(); SSL_CTX.check_hostname = False; SSL_CTX.verify_mode = ssl.CERT_NONE
UA = 'knust-hostels-research/1.0 (educational student project)'

H = json.load(open(os.path.join(OUT, 'hostels_final.json'), encoding='utf-8'))
cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}

def key(r): return f"{round(r['lat'],5)},{round(r['lng'],5)}"
uniq = {}
for r in H:
    if r['lat'] is not None:
        uniq.setdefault(key(r), (r['lat'], r['lng']))
todo = [k for k in uniq if k not in cache]
print(f'total points={len(H)} unique coords={len(uniq)} cached={len(cache)} to_do={len(todo)}', flush=True)

def rev(lat, lng):
    q = urllib.parse.urlencode({'lat': lat, 'lon': lng, 'format': 'jsonv2', 'zoom': 18, 'addressdetails': 1})
    req = urllib.request.Request('https://nominatim.openstreetmap.org/reverse?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
        return json.load(resp)

for i, k in enumerate(todo, 1):
    lat, lng = uniq[k]
    for attempt in (1, 2):
        try:
            a = rev(lat, lng).get('address', {})
            cache[k] = {
                'suburb': a.get('suburb') or a.get('neighbourhood') or a.get('quarter') or a.get('village') or a.get('hamlet') or '',
                'county': a.get('county') or a.get('city_district') or a.get('municipality') or '',
                'city': a.get('city') or a.get('town') or '',
            }
            break
        except Exception as e:
            if attempt == 2:
                cache[k] = {'suburb': '', 'county': '', 'city': '', 'error': str(e)[:60]}
            time.sleep(2)
    if i % 25 == 0:
        json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'  ...{i}/{len(todo)} done', flush=True)
    time.sleep(1.1)

json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
print('DONE. cached total:', len(cache), flush=True)
from collections import Counter
print('--- suburb distribution ---', flush=True)
for s, n in Counter(v.get('suburb','(none)') for v in cache.values()).most_common(40):
    print(f'{n:3d}  {s}', flush=True)
