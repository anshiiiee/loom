import json, subprocess
from collections import Counter

ROOT = "opensource-job-portal"
data = json.load(open(ROOT + "/graphify-out/graph.json"))
nodes = data["nodes"]
links = data["links"]
by_id = {n["id"]: n for n in nodes}

head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
print("Graph built at:", data["built_at_commit"])
print("Repo HEAD now: ", head)
print("Graph stale?  ", head != data["built_at_commit"])

def file_of(i):
    return by_id.get(i, {}).get("source_file") or ""

def is_test(p):
    return "test" in p.lower()

stats = Counter()
for l in links:
    sf = file_of(l["source"])
    tf = file_of(l["target"])
    if not sf or not tf:
        continue
    kind = ("test" if is_test(sf) else "prod") + "->" + ("test" if is_test(tf) else "prod")
    scope = "same-file" if sf == tf else "cross-file"
    stats[(l["relation"], kind, scope)] += 1

print()
print("KEY RELATIONS BY KIND AND SCOPE")
for rel in ("calls", "indirect_call", "uses", "inherits", "imports"):
    print(rel)
    for (r, kind, scope), c in sorted(stats.items(), key=lambda x: -x[1]):
        if r == rel:
            print(f"  {kind:11} {scope:11} {c}")

print()
print("IMPACT TRACE TEST: who depends on the JobAlert model?")
target = None
for n in nodes:
    if n.get("label") == "JobAlert" and (n.get("source_file") or "").endswith("peeldb/models.py"):
        target = n
        break

if target is None:
    print("JobAlert node not found")
else:
    print("Found:", target["id"], target.get("source_location"))
    skip = {"contains", "rationale_for"}
    incoming = [l for l in links if l["target"] == target["id"] and l["relation"] not in skip]
    print("Incoming dependency edges:", len(incoming))
    for l in incoming[:15]:
        s = by_id.get(l["source"], {})
        print(f"  {s.get('label')} [{s.get('source_file')}] --{l['relation']}--> JobAlert  ({l.get('confidence')}, edge at {l.get('source_file')} {l.get('source_location')})")
