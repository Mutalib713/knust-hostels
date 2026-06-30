# -*- coding: utf-8 -*-
"""Cross-check the Korley Boye 'KNUST Hostels List' poster against data.js.
Reports: NEW (not in DB), FILL (DB had no phone), CONFLICT (different phone), OK."""
import json, re, os, difflib, sys
sys.stdout.reconfigure(encoding='utf-8')
OUT = r'C:\Users\mutal\skills\knust-hostels'

# poster name (normalised) -> exact DB name, for spelling variants the matcher can't catch
ALIAS = {
 'waygingo': 'Wagyingo Main Hostel', 'theliberty': 'Liberty hostel',
 'risingstarnyberg': 'Nyberg Hostel', 'ghanahostels': 'Gaza Hostel',
 'honestyhostel': 'Honesty Student Hostel',
}

# (name, area, phone) — transcribed from the poster image
POSTER = [
 ("Abundant Grace","Ayeduase New Site","0246393376"),("Adom","Ayeduase","0244462754"),
 ("Afrim","Ayeduase","0243414677"),("Amanda","Ayeduase","0549268839"),
 ("Amen Main","Ayeduase","0277460637"),("Amen Annex","Ayeduase","0277461637"),
 ("Amen Inn","Ayeduase","0206301037"),("American House","Ayeduase New Site","0208133921"),
 ("Andan","Gaza Area, KNUST","0249481310"),("Blue Ark","Bomso","0208177888"),
 ("Asansik","Ayeduase Last Stop","0245923536"),("B Executives","Ayeduase","0242677171"),
 ("Banivillias","Gaza Area KNUST","0244627917"),("Beacon Hostel","Ayeduase","0242083101"),
 ("By His Grace","Ayeduase","0277090109"),("Canam Gold","Kotei Extension","0244991398"),
 ("Canam Exec.","Kotei Extension","0244991398"),("Casa Maria","Ayeduase","0244991398"),
 ("Celia Royal","Kotei","0245970318"),("Ceros Hostel","Kotei New Site","0277249367"),
 ("Charis","Kotei New Site","0244702577"),("Cresthaven","Kotei","0245918484"),
 ("Crystal Rose","Gaza","0206549570"),("Darkens Int'","Ayeduase","0261501548"),
 ("Manchester","Kotei","0243844605"),("Mass","Kotei","0203919781"),
 ("Millennium light","Ayeduase","0508122201"),("Morning Star","Ayeduase","0244928138"),
 ("Morning Star","Bomso","0245247533"),("Nana Addomah","Ayeduase","0247914420"),
 ("Nevada","Ayeduase","0546822770"),("No Weapon","Kotei","0542635351"),
 ("No Weapon.Ann","Kotei","0542635351"),("Nyame Mireku","Ayeduase","0245396040"),
 ("Ountak Hostel","Newsite","0245396040"),("Orange Hostel","Kotei","0244383345"),
 ("Outlook Hostel","New Site","0546208066"),("Pii Hostel","Ayeduase","0245787825"),
 ("Piramang Hostel","New Site","0549355660"),("Premier Tower","Kotei","0244025917"),
 ("Providence","Kotei","0276719597"),("P B & D","Ayeduase","0246288768"),
 ("Richbad","Kotei","0559886768"),("Rising Star(Nyberg)","Kotei","0244572800"),
 ("Rising Sun","Ayeduase","0245725800"),("Royal Gate Hostel","Bomso Gate","0244363320"),
 ("Shalom Kigutz","Ayeduase","0244756911"),("Shepherdsville","Kotei","0246333048"),
 ("Stompa","Kotei","0246305965"),("Splendor","Ayeduase","0204609165"),
 ("Standard","Bomso","0208186440"),
 ("Suncity","Kentinkrono","0244616248"),("The Best","Kotei","0244252764"),
 ("The Hopes Comm.","Ayeduase","0558526643"),("The Liberty","Kotei","0240983470"),
 ("Think Jesus","Ahinsan","0264983424"),("Thy Kingdom Come","Ayeduase","0244826656"),
 ("Thy Will be Done","Kotei","0548468613"),("Ultimate Hostel","Bomso","0247154197"),
 ("Victory Towers","Ayeduase","0279715421"),("Waygingo","Ayeduase","0549678089"),
 ("Western","Ayeduase","0243881354"),("Whitem House","Kotei","0543104061"),
 ("Whitpam A","Kotei","0547105598"),("Whitpam B","Newsite","0249482939"),
 ("Zoro","Kentinkrono","0262904249"),("DeLisa Hostel Ann","Ayeduase New Site","0244282654"),
 ("DeLisa Hostel Main","Kotei","0244282694"),("Destiny View","Kentinkrono","0241676204"),
 ("Devlaipah","Kotei","0242861466"),("Divine karma","Ayeduase","0543030093"),
 ("Enin","Newsite","0242803555"),("Fosua Homes","Ayeduase New Site","0552792325"),
 ("Fun XXL","Kotei","0246612462"),("F Plaza","Ayeduase New Site","0246761099"),
 ("Franco Hostel","Kotei","0553005120"),("Frontline Apartment","Ayeduase","0276907186"),
 ("Frontline Court","Ayeduase, Kotei","0276907186"),("Frontline Inn","Ayeduase","0208172263"),
 ("Georgia Hostel","Gaza","0243966830"),("Ghana Hostels","Gaza","0243986830"),
 ("Glory be to God","Ayeduase","0242002594"),("Happy Family","Ayeduase","0243787505"),
 ("High Achievers","Newsite","0247601078"),("Honesty Hostel","Ahinsan East","0244288299"),
 ("Hydes","Kotei Extension","0244372453"),("JNS","Bomso","0248552575"),
 ("Jenest Hostel","Ayeduase Gate","0548568078"),("Jalex Hostel","Ayeduase","0208149653"),
 ("Jecado Hostel","Ayeduase","0243138339"),("Jita Hostel","Ayeduase","0244979700"),
 ("Jita 2","Ayeduase","0268693113"),("Johannes","Kotei","0248299373"),
 ("Kgee","Newsite","0549414552"),("Kwayekwaa","Kotei","0244587382"),
 ("LongIsland","Kotei","0534247775"),
]

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def core(s):  # drop only the trailing generic accommodation word (NOT main/inn/house — those distinguish buildings)
    return re.sub(r'(hostels|hostel|hostle|hotel|lodge|apartments|apartment)$', '', norm(s))
def pn(p): return re.sub(r'\D', '', p or '').lstrip('0')

META = HOSTELS = None
for line in open(os.path.join(OUT, 'data.js'), encoding='utf-8'):
    if line.startswith('window.META = '): META = json.loads(line[14:].rstrip().rstrip(';'))
    elif line.startswith('window.HOSTELS = '): HOSTELS = json.loads(line[17:].rstrip().rstrip(';'))

by_norm, by_core, allk = {}, {}, []
for h in HOSTELS:
    by_norm.setdefault(norm(h['name']), h)
    by_core.setdefault(core(h['name']), h)
    allk.append(norm(h['name']))

def find(name):
    n, c = norm(name), core(name)
    if n in ALIAS: return by_norm.get(norm(ALIAS[n]))
    if n in by_norm: return by_norm[n]
    if len(c) >= 4 and c in by_core: return by_core[c]
    for k, h in by_norm.items():               # containment
        if len(n) >= 5 and len(k) >= 5 and (n in k or k in n): return h
    m = difflib.get_close_matches(n, allk, n=1, cutoff=0.84)
    return by_norm[m[0]] if m else None

new, fill, conflict, ok = [], [], [], []
for name, area, phone in POSTER:
    h = find(name)
    if not h:
        cm = difflib.get_close_matches(norm(name), allk, n=1, cutoff=0.6)
        new.append((name, area, phone, by_norm[cm[0]]['name'] if cm else '—'))
    elif not h.get('phone'):
        fill.append((name, h['name'], phone))
    elif pn(h['phone']) == pn(phone):
        ok.append((name, h['name']))
    else:
        conflict.append((name, h['name'], h['phone'], phone, 'CONFIRMED' if h.get('confirmed') else 'unconfirmed'))

print(f"poster={len(POSTER)}  matched={len(POSTER)-len(new)}  NEW={len(new)}  FILL={len(fill)}  CONFLICT={len(conflict)}  OK={len(ok)}")
print("\n=== NEW (not in DB; nearest existing name shown) ===")
for n in new: print(f"  + {n[0]:24} | {n[1]:18} | {n[2]}   (nearest: {n[3]})")
print("\n=== FILL (DB has no phone -> poster supplies one) ===")
for f in fill: print(f"  ~ {f[0]:24} -> {f[1]:32} | {f[2]}")
print("\n=== CONFLICT (different phone) ===")
for c in conflict: print(f"  ! {c[0]:22} -> {c[1]:28} | DB:{c[2]:14} poster:{c[3]:14} [{c[4]}]")
print(f"\n=== OK (phone already matches) — {len(ok)} ===")
print('   ', ', '.join(o[0] for o in ok))
