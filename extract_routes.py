#!/usr/bin/env python3
"""
Extract at-risk Muni route shapes from GTFS data into routes.json.
Run from muni-awareness/ directory:
  python3 extract_routes.py ~/Downloads/muni_gtfs-current
"""

import csv
import json
import sys
from collections import defaultdict

GTFS_DIR = sys.argv[1] if len(sys.argv) > 1 else "../Downloads/muni_gtfs-current"

AT_RISK = {
    "2":   "Sutter",
    "6":   "Hayes-Parnassus",
    "15":  "Bayview Hunters Point Express",
    "18":  "46th Avenue",
    "23":  "Monterey",
    "27":  "Bryant",
    "31":  "Balboa",
    "33":  "Ashbury-18th St",
    "35":  "Eureka",
    "36":  "Teresita",
    "37":  "Corbett",
    "39":  "Coit",
    "55":  "Dogpatch",
    "56":  "Rutland",
    "57":  "Parkmerced",
    "58":  "Lake Merced",
    "66":  "Quintara",
    "67":  "Bernal Heights",
    "1X":  "California Express",
    "30X": "Marina Express",
}

def read_csv(filename):
    with open(f"{GTFS_DIR}/{filename}", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

print("Reading routes.txt...")
routes = read_csv("routes.txt")
# route_short_name -> route_id
short_to_id = {r["route_short_name"].strip(): r["route_id"].strip() for r in routes}

at_risk_route_ids = {}
for short_name in AT_RISK:
    rid = short_to_id.get(short_name)
    if rid:
        at_risk_route_ids[rid] = short_name
    else:
        print(f"  WARNING: route {short_name!r} not found in routes.txt")

print(f"Found {len(at_risk_route_ids)} at-risk routes in GTFS")

print("Reading trips.txt...")
trips = read_csv("trips.txt")
# route_id -> set of (direction_id, shape_id) — one shape per direction
route_shapes = defaultdict(dict)
for t in trips:
    rid = t["route_id"].strip()
    if rid in at_risk_route_ids:
        dir_id = t.get("direction_id", "0").strip()
        sid = t["shape_id"].strip()
        # Keep first shape_id seen per direction
        if dir_id not in route_shapes[rid]:
            route_shapes[rid][dir_id] = sid

print("Reading shapes.txt...")
all_shape_ids = set()
for dirs in route_shapes.values():
    all_shape_ids.update(dirs.values())

# shape_id -> list of [lat, lng] sorted by sequence
shape_coords = defaultdict(list)
with open(f"{GTFS_DIR}/shapes.txt", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    raw = defaultdict(list)
    for row in reader:
        sid = row["shape_id"].strip()
        if sid not in all_shape_ids:
            continue
        seq = int(row["shape_pt_sequence"].strip())
        lat = round(float(row["shape_pt_lat"]), 5)
        lng = round(float(row["shape_pt_lon"]), 5)
        raw[sid].append((seq, lat, lng))
    for sid, pts in raw.items():
        pts.sort(key=lambda x: x[0])
        shape_coords[sid] = [[lat, lng] for _, lat, lng in pts]

print(f"Extracted shapes for {len(shape_coords)} shape_ids")

# Build output
output = {}
for rid, short_name in at_risk_route_ids.items():
    dirs = route_shapes.get(rid, {})
    shapes = []
    for dir_id in sorted(dirs):
        sid = dirs[dir_id]
        coords = shape_coords.get(sid, [])
        if coords:
            shapes.append(coords)
    if shapes:
        output[short_name] = {
            "name": AT_RISK[short_name],
            "shapes": shapes,
        }
    else:
        print(f"  WARNING: no shape data for route {short_name}")

out_path = "routes.json"
with open(out_path, "w") as f:
    json.dump(output, f, separators=(",", ":"))

size_kb = len(json.dumps(output, separators=(",", ":"))) / 1024
print(f"\nWrote {out_path} — {len(output)} routes, {size_kb:.1f} KB")
