"""Submit SA-targeted content for operator-alpha."""

import json
import sys
import time
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"

TEXT = """You are the sole analyst on a night shift watching six monitors. Monitor one shows the North American perimeter — three firewalls spanning New York, Chicago, and Dallas, each filtering traffic for forty VLANs. Monitor two displays the European segment — London and Frankfurt datacenters with an active failover tunnel between them. Monitor three is your SIEM correlation dashboard aggregating 14,000 events per second across all sites. Monitor four tracks the DMZ: web servers, mail relays, and the VPN concentrator that 300 remote workers are connected through right now. Monitor five is the endpoint detection console showing agent status for 4,200 workstations — green, yellow, red dots scattered across an interactive floor map of six buildings. Monitor six is the threat intelligence feed scrolling new IOCs every few minutes.

Right now, simultaneously: Chicago firewall shows a 40% spike in outbound UDP. The London-Frankfurt tunnel is flapping — up, down, up — causing BGP reconvergence that shifts European traffic through a backup path you have not monitored in weeks. Three endpoints on the fourth floor of Building C just went yellow — their agents stopped reporting within the same 90-second window. The VPN concentrator CPU is at 89%. A new IOC just dropped matching a hash you saw in yesterday's email quarantine.

You need to hold all of this in your head at once. Which signal is the real threat? Which is operational noise? The Chicago UDP spike could be a DNS amplification attack or just a backup job. The London tunnel flap could be an infrastructure issue or someone forcing a route change. The three yellow endpoints could be a patch reboot or the first sign of lateral movement. The VPN load could be normal end-of-quarter surge or a credential stuffing attack. You must continuously scan all six screens, mentally prioritize, re-prioritize as new data arrives, and decide where to focus your limited attention without losing track of the other five."""

body = json.dumps({"text": TEXT}).encode()
req = ur.Request(BASE + "/predict", data=body,
    headers={"Content-Type": "application/json"})
resp = ur.urlopen(req)
d = json.loads(resp.read())

if "job_id" in d:
    job_id = d["job_id"]
    print("Job %s submitted, waiting..." % job_id)
    for i in range(120):
        time.sleep(5)
        r = ur.urlopen(BASE + "/jobs/" + job_id)
        d = json.loads(r.read())
        if d["status"] == "complete":
            print("Done after %ds" % ((i + 1) * 5))
            break
        if (i + 1) % 12 == 0:
            print("  %ds..." % ((i + 1) * 5))

if d.get("status") and d["status"] != "complete":
    print("Prediction didn't finish")
    sys.exit(1)

# Show predictions
print()
print("=== PREDICTION ===")
for g in sorted(d["group_scores"], key=lambda x: x["id"]):
    m = " << MOD" if g["z_score"] >= 0.2 else ""
    print("  G%2d z=%+.3f%s" % (g["id"], g["z_score"], m))
print()
for sr in d.get("subcortical_regions", []):
    t = " << STRONG" if sr["engaged"] and sr["z_score"] >= 1.0 else (" eng" if sr["engaged"] else "")
    print("  %-12s z=%+.3f%s" % (sr["name"], sr["z_score"], t))

# Record
body2 = json.dumps({
    "module_id": "soc-night-shift-sa",
    "module_name": "SOC Night Shift: Multi-Monitor Triage",
    "group_scores": d["group_scores"],
    "subcortical_regions": d.get("subcortical_regions", []),
}).encode()
req2 = ur.Request(BASE + "/profile/operator-alpha/modules",
    data=body2, headers={"Content-Type": "application/json"})
resp2 = ur.urlopen(req2)
result = json.loads(resp2.read())

print()
print("=== THIS MODULE ===")
for k, v in result["dimensions"].items():
    t = "COVERED" if v["covered"] else "  gap "
    print("  %s %-30s str=%+.3f" % (t, k, v["strength"]))

# Profile
print()
print("=== PROFILE ===")
r3 = ur.urlopen(BASE + "/profile/operator-alpha")
p = json.loads(r3.read())
print("Modules: %d" % p["total_modules"])
for k, v in p["dimensions"].items():
    pct = v["coverage"] * 100
    n = int(v["coverage"] * 20)
    bar = "#" * n + "." * (20 - n)
    print("  %-30s %5.1f%% [%s] mods=%d" % (k, pct, bar, v["module_count"]))

print()
r4 = ur.urlopen(BASE + "/profile/operator-alpha/gaps")
g = json.loads(r4.read())
if g["all_clear"]:
    print("ALL CLEAR - no gaps remaining")
else:
    print("GAPS:")
    for gap in g["gaps"]:
        bl = " BLOCKED:%s" % ",".join(gap["blocked_by"]) if gap["blocked_by"] else ""
        print("  %s %s cov=%d%%%s" % (gap["severity"].upper(), gap["dimension"],
            gap["current_coverage"]*100, bl))
