"""Record SOC incident module for a fresh operator and show readiness results."""

import json
import time
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"

# Poll for cached prediction result
job_id = "95a9c6d0"
for _ in range(30):
    r = ur.urlopen(BASE + "/jobs/" + job_id)
    d = json.loads(r.read())
    if d["status"] == "complete":
        break
    time.sleep(5)

if d["status"] != "complete":
    print("Still running after 150s, try later")
    exit()

# Delete old operator if exists
try:
    req = ur.Request(BASE + "/profile/operator-alpha", method="DELETE")
    ur.urlopen(req)
except Exception:
    pass

# Record module
body = json.dumps({
    "module_id": "soc-dns-c2-lateral",
    "module_name": "SOC Incident: DNS C2 + Lateral Movement",
    "group_scores": d["group_scores"],
    "subcortical_regions": d.get("subcortical_regions", []),
}).encode()
req = ur.Request(
    BASE + "/profile/operator-alpha/modules",
    data=body,
    headers={"Content-Type": "application/json"},
)
resp = ur.urlopen(req)
result = json.loads(resp.read())

print("=== PREDICTION INPUTS ===")
print()
for g in sorted(d["group_scores"], key=lambda x: x["id"]):
    above = ">>MODERATE" if g["z_score"] >= 0.2 else ""
    print("  G%2d  z=%+.3f  %s" % (g["id"], g["z_score"], above))
print()
for sr in d.get("subcortical_regions", []):
    tag = "STRONG" if sr["engaged"] and sr["z_score"] >= 1.0 else ("engaged" if sr["engaged"] else "")
    print("  %-12s  z=%+.3f  %s" % (sr["name"], sr["z_score"], tag))

print()
print("=== DIMENSION DETECTION (per-module) ===")
print()
for k, v in result["dimensions"].items():
    tag = "COVERED" if v["covered"] else "  gap "
    print("  %s  %-30s  strength=%+.3f  srk=%s" % (tag, k, v["strength"], v["srk_mode"]))
    det = v["details"]
    parts = []
    for dk, dv in det.items():
        if isinstance(dv, bool):
            if dv:
                parts.append(dk)
        elif isinstance(dv, float):
            parts.append("%s=%+.3f" % (dk, dv))
    print("         " + ", ".join(parts))
    print()

print("=== OPERATOR PROFILE ===")
print()
r2 = ur.urlopen(BASE + "/profile/operator-alpha")
p = json.loads(r2.read())
print("Operator: %s  |  Modules: %d" % (p["operator_id"], p["total_modules"]))
print()
for k, v in p["dimensions"].items():
    pct = v["coverage"] * 100
    n = int(v["coverage"] * 20)
    bar = "#" * n + "." * (20 - n)
    print("  %-30s %5.1f%% [%s]  strength=%+.3f" % (k, pct, bar, v["mean_strength"]))

print()
print("=== GAP ANALYSIS ===")
print()
r3 = ur.urlopen(BASE + "/profile/operator-alpha/gaps")
g = json.loads(r3.read())
if g["all_clear"]:
    print("  All 6 dimensions covered. No gaps.")
else:
    for gap in g["gaps"]:
        blocked = ""
        if gap["blocked_by"]:
            blocked = "  BLOCKED BY: " + ", ".join(gap["blocked_by"])
        print("  [%-8s] %s" % (gap["severity"].upper(), gap["dimension"]))
        print("             coverage=%d%%%s" % (gap["current_coverage"] * 100, blocked))
        print("             SRK risk: %s" % gap["srk_error_risk"])
        print("             %s" % gap["message"])
        print()
