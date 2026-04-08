"""Seed operator analyst-001 with realistic video-equivalent module data."""

import json
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"


def record(op, mid, mname, gs, sc):
    body = json.dumps({
        "module_id": mid,
        "module_name": mname,
        "group_scores": gs,
        "subcortical_regions": sc,
    }).encode()
    req = ur.Request(
        f"{BASE}/profile/{op}/modules",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    resp = ur.urlopen(req)
    result = json.loads(resp.read())
    covered = [k for k, v in result["dimensions"].items() if v["covered"]]
    print(f"  {mname}: {len(covered)} dims -> {covered}")


print("Recording video-equivalent modules for analyst-001...")
print()

# Module 3: SOC Dashboard Monitoring video — strong SA + synthesis
record("analyst-001", "htb-soc-dashboard-vid", "SOC Dashboard Monitoring (video)", [
    {"id": 1, "z_score": 0.42}, {"id": 2, "z_score": 0.35},
    {"id": 3, "z_score": 0.88}, {"id": 4, "z_score": 0.15},
    {"id": 5, "z_score": 0.72}, {"id": 6, "z_score": 0.38},
    {"id": 7, "z_score": 0.41}, {"id": 8, "z_score": 0.56},
    {"id": 9, "z_score": 0.18}, {"id": 10, "z_score": 0.12},
], [
    {"name": "Thalamus", "z_score": 0.52, "group_ids": [3, 5], "engaged": False},
    {"name": "Hippocampus", "z_score": 1.21, "group_ids": [7], "engaged": True},
    {"name": "Putamen", "z_score": 0.31, "group_ids": [2], "engaged": False},
    {"name": "Amygdala", "z_score": 0.22, "group_ids": [9], "engaged": False},
])

# Module 4: Timed CTF speedrun video — procedural + threat
record("analyst-001", "htb-ctf-speedrun-vid", "Timed CTF Speedrun (video)", [
    {"id": 1, "z_score": 0.55}, {"id": 2, "z_score": 1.12},
    {"id": 3, "z_score": 0.61}, {"id": 4, "z_score": 0.08},
    {"id": 5, "z_score": 0.48}, {"id": 6, "z_score": 0.72},
    {"id": 7, "z_score": 0.33}, {"id": 8, "z_score": 0.29},
    {"id": 9, "z_score": 0.65}, {"id": 10, "z_score": -0.15},
], [
    {"name": "Putamen", "z_score": 1.35, "group_ids": [2], "engaged": True},
    {"name": "Pallidum", "z_score": 0.88, "group_ids": [2], "engaged": True},
    {"name": "Amygdala", "z_score": 0.91, "group_ids": [9], "engaged": True},
    {"name": "Hippocampus", "z_score": 0.65, "group_ids": [7], "engaged": True},
    {"name": "Caudate", "z_score": 0.72, "group_ids": [1], "engaged": True},
    {"name": "Accumbens", "z_score": 0.58, "group_ids": [6], "engaged": False},
])

# Module 5: Tabletop IR exercise video — strategic + analytical
record("analyst-001", "htb-tabletop-ir-vid", "Tabletop IR Exercise (video)", [
    {"id": 1, "z_score": 0.88}, {"id": 2, "z_score": 0.22},
    {"id": 3, "z_score": 0.95}, {"id": 4, "z_score": 0.31},
    {"id": 5, "z_score": 0.61}, {"id": 6, "z_score": 0.45},
    {"id": 7, "z_score": 0.52}, {"id": 8, "z_score": 0.73},
    {"id": 9, "z_score": 0.42}, {"id": 10, "z_score": 0.38},
], [
    {"name": "Hippocampus", "z_score": 1.42, "group_ids": [7], "engaged": True},
    {"name": "Caudate", "z_score": 0.81, "group_ids": [1], "engaged": True},
    {"name": "Thalamus", "z_score": 0.61, "group_ids": [3, 5], "engaged": True},
    {"name": "Amygdala", "z_score": 0.55, "group_ids": [9], "engaged": True},
])

# Show updated profile
print()
r = ur.urlopen(f"{BASE}/profile/analyst-001")
p = json.loads(r.read())
total = p["total_modules"]
print(f"Operator: {p['operator_id']} | Total modules: {total}")
print()
for k, v in p["dimensions"].items():
    pct = v["coverage"] * 100
    bar = "#" * int(v["coverage"] * 20) + "." * (20 - int(v["coverage"] * 20))
    print(f"  {k:30s} {pct:5.1f}% [{bar}] mods={v['module_count']}")

print()
r2 = ur.urlopen(f"{BASE}/profile/analyst-001/gaps")
g = json.loads(r2.read())
print(f"Gaps: {len(g['gaps'])} | All clear: {g['all_clear']}")
for gap in g["gaps"]:
    b = f" BLOCKED:{','.join(gap['blocked_by'])}" if gap["blocked_by"] else ""
    print(f"  {gap['severity'].upper():8s} {gap['dimension']}{b}")
