"""Submit content for prediction, record for an operator, show updated profile."""

import json
import sys
import time
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"

OPERATOR = sys.argv[1] if len(sys.argv) > 1 else "operator-alpha"
MODULE_ID = sys.argv[2] if len(sys.argv) > 2 else "module-" + str(int(time.time()))
MODULE_NAME = sys.argv[3] if len(sys.argv) > 3 else MODULE_ID

TEXT = """Look at these firewall logs. 10:03:14 ALLOW TCP 192.168.1.45:49221 > 8.8.8.8:443. 10:03:14 ALLOW TCP 192.168.1.45:49222 > 8.8.8.8:443. 10:03:15 ALLOW TCP 192.168.1.45:49223 > 8.8.4.4:443. 10:03:15 ALLOW TCP 192.168.1.102:51001 > 104.26.10.5:80. 10:03:16 ALLOW TCP 192.168.1.45:49224 > 185.220.101.34:443. 10:03:16 ALLOW TCP 192.168.1.102:51002 > 104.26.10.5:80. 10:03:17 ALLOW TCP 192.168.1.45:49225 > 185.220.101.34:443. 10:03:17 DENY UDP 192.168.1.45:53 > 185.220.101.34:53. 10:03:18 ALLOW TCP 192.168.1.45:49226 > 185.220.101.34:8080. 10:03:18 ALLOW TCP 192.168.1.67:22 > 10.0.0.1:22. 10:03:19 DENY TCP 192.168.1.45:49227 > 185.220.101.34:4444. Port 4444. Metasploit default. The IP shifted from Google DNS to a known Tor exit node. Sequential source ports. DNS over non-standard port denied. Spot the pattern."""

# Submit prediction
body = json.dumps({"text": TEXT}).encode()
req = ur.Request(BASE + "/predict", data=body,
    headers={"Content-Type": "application/json"})
resp = ur.urlopen(req)
d = json.loads(resp.read())

if "job_id" in d:
    job_id = d["job_id"]
    print("Job %s submitted, waiting..." % job_id)
    for i in range(60):
        time.sleep(5)
        r = ur.urlopen(BASE + "/jobs/" + job_id)
        d = json.loads(r.read())
        if d["status"] == "complete":
            print("Done after %ds" % ((i + 1) * 5))
            break
        print("  %ds..." % ((i + 1) * 5))

if d.get("status") and d["status"] != "complete":
    print("Prediction didn't finish")
    sys.exit(1)

# Show predictions
print()
print("=== PREDICTION ===")
print()
for g in sorted(d["group_scores"], key=lambda x: x["id"]):
    marker = " << MODERATE" if g["z_score"] >= 0.2 else ""
    print("  G%2d  z=%+.3f%s" % (g["id"], g["z_score"], marker))
print()
for sr in d.get("subcortical_regions", []):
    tag = " << STRONG" if sr["engaged"] and sr["z_score"] >= 1.0 else (" engaged" if sr["engaged"] else "")
    print("  %-12s  z=%+.3f%s" % (sr["name"], sr["z_score"], tag))

# Record for operator
body2 = json.dumps({
    "module_id": MODULE_ID,
    "module_name": MODULE_NAME,
    "group_scores": d["group_scores"],
    "subcortical_regions": d.get("subcortical_regions", []),
}).encode()
req2 = ur.Request(BASE + "/profile/" + OPERATOR + "/modules",
    data=body2, headers={"Content-Type": "application/json"})
resp2 = ur.urlopen(req2)
result = json.loads(resp2.read())

print()
print("=== THIS MODULE's DIMENSIONS ===")
print()
for k, v in result["dimensions"].items():
    tag = "COVERED" if v["covered"] else "  gap "
    print("  %s  %-30s  str=%+.3f" % (tag, k, v["strength"]))

# Show updated profile
print()
print("=== UPDATED PROFILE: %s ===")
print()
r3 = ur.urlopen(BASE + "/profile/" + OPERATOR)
p = json.loads(r3.read())
print("Modules: %d" % p["total_modules"])
print()
for k, v in p["dimensions"].items():
    pct = v["coverage"] * 100
    n = int(v["coverage"] * 20)
    bar = "#" * n + "." * (20 - n)
    print("  %-30s %5.1f%% [%s]  mods=%d  str=%+.3f" % (
        k, pct, bar, v["module_count"], v["mean_strength"]))

# Gaps
print()
r4 = ur.urlopen(BASE + "/profile/" + OPERATOR + "/gaps")
g = json.loads(r4.read())
if g["all_clear"]:
    print("  ALL CLEAR - no gaps")
else:
    print("=== GAPS ===")
    print()
    for gap in g["gaps"]:
        blocked = ""
        if gap["blocked_by"]:
            blocked = " [BLOCKED: %s]" % ", ".join(gap["blocked_by"])
        print("  %s %s  cov=%d%%%s" % (
            gap["severity"].upper(), gap["dimension"],
            gap["current_coverage"] * 100, blocked))
