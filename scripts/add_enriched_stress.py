"""Submit LLM-enriched stress scenario for operator-alpha."""

import json
import sys
import time
import urllib.request as ur

BASE = "http://localhost:8000/api/v1"

TEXT = """Your screen flashes red. The endpoint counter in the top right is climbing — 12 infected, now 19, now 26. You hear the Slack notification burst from the CFO's channel. Your hands hover over the keyboard but you pull them back. If you type the wrong command on this domain controller, the attacker sees it. They have your domain admin hash. They are watching.

Thirty-one. Thirty-four.

Your mouth is dry. The SOC phone is ringing. You can feel your heartbeat in your fingertips. The EDR console on your left monitor is a wall of red — 847 alerts, scrolling faster than you can read. Half of them are false positives from the detection rule YOU pushed twenty minutes ago. You can't tell which alerts are real lateral movement and which ones are your own IR team remediating.

Thirty-nine infected.

You glance at monitor three. The netflow graph shows 14 gigabytes outbound to an IP in Eastern Europe in the last hour. Customer PII. You feel your stomach drop. Legal needs to know NOW. The CEO is on speaker asking if they should notify the board. You don't have the answer yet.

Forty-two.

Your right hand reaches for the keyboard. You need to isolate three subnets but production is running — 2000 users. Kill the network, you stop the spread but cost the company $200K per hour. Don't kill it, and the counter keeps climbing. Your left hand pulls up the backup domain controller list. Two backup DCs. One of them was accessed three hours ago by the compromised admin account. You don't know which one. Choose wrong and you hand the attacker the backup infrastructure.

Forty-seven. Forty-eight.

The scheduled task you found on HOST-FIN07 is set to fire in eleven minutes. If it triggers, the attacker re-establishes persistence even after you kill their session. You need to disable it across six hosts simultaneously before they notice you found it. You're typing the PowerShell command. Your fingers are shaking slightly. Backspace. Retype. Check the hostname. Check it again.

Fifty-one infected.

The Slack channel explodes. Someone from IT just plugged the quarantined laptop back into the network because a VP asked them to. You feel the heat rise in your chest. Deep breath. Focus. Prioritize. The backup DC — which one is clean? The scheduled task — nine minutes. The network kill switch — make the call. The CEO is still talking. The counter is still climbing.

Fifty-three. You begin typing."""

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
    m = " <<" if g["z_score"] >= 0.2 else ""
    print("  G%2d z=%+.3f%s" % (g["id"], g["z_score"], m))
print()
for sr in d.get("subcortical_regions", []):
    t = " STRONG" if sr["engaged"] and sr["z_score"] >= 1.0 else (" eng" if sr["engaged"] else "")
    print("  %-12s z=%+.3f%s" % (sr["name"], sr["z_score"], t))

# Record
body2 = json.dumps({
    "module_id": "enriched-breach-stress",
    "module_name": "Active Breach: Enriched Stress Experience",
    "group_scores": d["group_scores"],
    "subcortical_regions": d.get("subcortical_regions", []),
}).encode()
req2 = ur.Request(BASE + "/profile/operator-alpha/modules",
    data=body2, headers={"Content-Type": "application/json"})
resp2 = ur.urlopen(req2)
result = json.loads(resp2.read())

print()
print("=== THIS MODULE (enriched) ===")
for k, v in result["dimensions"].items():
    print("  %-28s str=%.4f" % (k, v["strength"]))

# Compare with original
print()
print("=== COMPARE: original vs enriched ===")
r_profile = ur.urlopen(BASE + "/profile/operator-alpha")
p = json.loads(r_profile.read())
# Find both modules
orig = None
enr = None
for m in p["completed_modules"]:
    if m["module_id"] == "active-breach-stress":
        orig = m
    if m["module_id"] == "enriched-breach-stress":
        enr = m

if orig and enr:
    dims = ["procedural_automaticity", "threat_detection", "situational_awareness",
            "strategic_decision", "analytical_synthesis", "stress_resilience"]
    print("  %-28s %10s %10s %10s" % ("dimension", "original", "enriched", "delta"))
    for k in dims:
        o = orig["dimensions"][k]["strength"]
        e = enr["dimensions"][k]["strength"]
        arrow = "+" if e > o else ("-" if e < o else "=")
        print("  %-28s %10.4f %10.4f %+9.4f %s" % (k, o, e, e - o, arrow))

# Profile
print()
print("=== PROFILE (%d modules) ===" % p["total_modules"])
for k, v in p["dimensions"].items():
    pct = v["readiness"] * 100
    n = int(pct / 5)
    bar = "#" * n + "." * (20 - n)
    print("  %-28s %5.1f%% [%s] %s" % (k, pct, bar, v["level"].upper()))
