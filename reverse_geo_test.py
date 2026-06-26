# -*- coding: utf-8 -*-
"""Test Nominatim reverse geocoding granularity for a few KNUST points."""
import json, sys, time, ssl, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

H = json.load(open(r'C:\Users\mutal\skills\knust-hostels\hostels_final.json', encoding='utf-8'))
byname = {r['name']: r for r in H}

def pick(substr):
    for r in H:
        if substr.lower() in r['name'].lower():
            return r
    return None

tests = []
for s in ['University Hall', 'Independence Hall', 'Frontline', 'Flint', 'Evandy', 'Wagyingo',
          'Ikes Cultural', 'Kharis', 'Achiba', 'Urban Platinum']:
    r = pick(s)
    if r: tests.append(r)

UA = 'knust-hostels-research/1.0 (educational student project)'
def rev(lat, lng):
    q = urllib.parse.urlencode({'lat': lat, 'lon': lng, 'format': 'jsonv2', 'zoom': 18, 'addressdetails': 1})
    req = urllib.request.Request('https://nominatim.openstreetmap.org/reverse?' + q, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
        return json.load(resp)

for r in tests:
    try:
        d = rev(r['lat'], r['lng'])
        a = d.get('address', {})
        keys = ['neighbourhood','quarter','suburb','village','hamlet','residential','city_district','town','municipality','county']
        picked = {k: a[k] for k in keys if k in a}
        print(f"{r['name'][:26]:26s} ({r['lat']:.4f},{r['lng']:.4f}) km={r['km_from_knust']}")
        print(f"    -> {picked}")
    except Exception as e:
        print(f"{r['name'][:26]:26s} ERROR {e}")
    time.sleep(1.2)
