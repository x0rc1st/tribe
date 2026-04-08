"""Submit stress resilience content for operator-alpha."""

import json
import sys
import time
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"

TEXT = """ALERT: Active breach in progress. Ransomware is spreading across the network right now. You have 4 minutes before it reaches the backup servers. The attacker is inside — they have domain admin credentials and they are watching you. Every command you type on the domain controller, they can see. If you lock their account, they will trigger the payload immediately from three other compromised machines you haven't found yet. The CEO is on the phone demanding answers. Legal needs to know if customer PII has been exfiltrated — the attacker's staging server shows 14GB of outbound transfers in the last hour to an IP in a non-extradition country. Your EDR console shows 847 alerts. 340 are false positives from the detection rule you pushed 20 minutes ago trying to contain this. You can't tell which of the remaining 507 are real lateral movement and which are your own IR team's activity. The clock is ticking. Three of your containment actions failed because the attacker anticipated them — they disabled Windows Defender via GPO before you noticed, they added a secondary C2 channel over DNS that your firewall isn't blocking, and they planted a scheduled task that will re-establish persistence even if you kill their current session. You must simultaneously: isolate the three subnets without killing production for the 2000 users still working, preserve forensic evidence on the six compromised hosts before the attacker wipes logs, decide whether to pull the internet kill switch knowing it will cost the company $200K per hour in lost revenue, and figure out which of your two backup domain controllers is clean. One of them was accessed 3 hours ago by the compromised admin account — but you don't know which one. Choose wrong and you hand the attacker the backup too. Make the call. Now."""

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

print()
print("=== PREDICTION ===")
for g in sorted(d["group_scores"], key=lambda x: x["id"]):
    m = " << " if g["z_score"] >= 0.2 else ""
    print("  G%2d %-40s z=%+.3f%s" % (g["id"], g["name"][:40], g["z_score"], m))
print()
for sr in d.get("subcortical_regions", []):
    t = " << STRONG" if sr["engaged"] and sr["z_score"] >= 1.0 else (" eng" if sr["engaged"] else "")
    print("  %-12s z=%+.3f%s" % (sr["name"], sr["z_score"], t))

# Record
body2 = json.dumps({
    "module_id": "active-breach-stress",
    "module_name": "Active Breach: Ransomware Under Pressure",
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
    print("  %-28s str=%.4f" % (k, v["strength"]))

# Profile
print()
print("=== PROFILE (4 modules) ===")
r3 = ur.urlopen(BASE + "/profile/operator-alpha")
p = json.loads(r3.read())
print("Modules: %d" % p["total_modules"])
for k, v in p["dimensions"].items():
    pct = v["readiness"] * 100
    n = int(pct / 5)
    bar = "#" * n + "." * (20 - n)
    print("  %-28s %5.1f%% [%s] %s" % (k, pct, bar, v["level"].upper()))

print()
r4 = ur.urlopen(BASE + "/profile/operator-alpha/gaps")
g = json.loads(r4.read())
if g["all_clear"]:
    print("ALL CLEAR")
else:
    for gap in g["gaps"]:
        print("  %s %s %.1f%%" % (gap["severity"].upper(), gap["dimension"], gap["readiness"] * 100))
