# Add Otumfuo Osei Tutu II Hostel (SRC Hostel) — on-campus, near Unity Hall / Islamic Centre
import json, re, csv, io

NAME = "Otumfuo Osei Tutu II Hostel (SRC Hostel)"
LAT, LNG = 6.6816, -1.5716
KM = 0.79
CID = 16503272418921201044
MAPS_URL = f"https://www.google.com/maps?cid={CID}"
COLLEGES = ["Engineering", "Science", "Art & Built Environment",
            "Humanities & Social Sciences (KSB)", "Health Sciences"]

record = {
    "name": NAME, "area": "On Campus (KNUST)", "category": "Lodging",
    "km_from_knust": KM, "lat": LAT, "lng": LNG, "maps_url": MAPS_URL,
    "website": "", "rating": None, "reviews": 0, "coord_reliable": True,
    "closed": False, "phone": "", "manager_phone": "", "confirmed": False,
    "images": [], "amenities": [], "review_tags": [], "colleges": COLLEGES,
    "price_from": None, "rooms": [], "price_src": "", "type": "Hostel",
}

# ---- data.js ----
txt = open("data.js", encoding="utf-8").read()
meta = json.loads(re.search(r"window\.META = (\{.*?\});", txt, re.S).group(1))
arr = json.loads(re.search(r"window\.HOSTELS = (\[.*\]);?\s*$", txt, re.S).group(1))

if any(h["name"] == NAME for h in arr):
    print("Already present — aborting."); raise SystemExit

arr.append(record)
meta["total"] = len(arr)
meta["area_counts"]["On Campus (KNUST)"] = meta["area_counts"].get("On Campus (KNUST)", 0) + 1
meta["type_counts"]["Hostel"] = meta["type_counts"].get("Hostel", 0) + 1

out = ("window.META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
       + "window.HOSTELS = " + json.dumps(arr, ensure_ascii=False) + ";\n")
open("data.js", "w", encoding="utf-8").write(out)
print(f"data.js updated -> total {meta['total']}, On Campus {meta['area_counts']['On Campus (KNUST)']}")

# ---- knust_hostels.csv ----
row = [NAME, "On Campus (KNUST)", "Hostel", "Lodging", KM, "", 0, "", "", "",
       "", "", " | ".join(COLLEGES), "", LAT, LNG, MAPS_URL, ""]
with open("knust_hostels.csv", "a", encoding="utf-8-sig", newline="") as f:
    csv.writer(f).writerow(row)
print("knust_hostels.csv appended")
