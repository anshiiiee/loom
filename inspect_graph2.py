import json
from collections import Counter

PATH = "opensource-job-portal/graphify-out/graph.json"
data = json.load(open(PATH))
nodes = data["nodes"]
links = data["links"]
by_id = {n["id"]: n for n in nodes}

print("ALL RELATION TYPES")
for rel, c in Counter(l["relation"] for l in links).most_common():
    print(f"  {rel}: {c}")

dangling = sum(1 for l in links if l["source"] not in by_id or l["target"] not in by_id)
print()
print("Edges with a missing endpoint node:", dangling)

print()
print("NODE 'type' field:", Counter(str(n.get("type")) for n in nodes).most_common(10))
print("NODE 'external' field:", Counter(str(n.get("external")) for n in nodes).most_common(5))

def is_vendored(path):
    p = (path or "").lower()
    return (".min.js" in p or "node_modules" in p or "/vendor" in p
            or "static/js" in p or "ckeditor" in p or "jquery" in p)

vend = [n for n in nodes if is_vendored(n.get("source_file"))]
print()
print("Nodes in likely vendored files:", len(vend), "of", len(nodes))

tests = [n for n in nodes if "test" in (n.get("source_file") or "").lower()]
print("Nodes in files with 'test' in the path:", len(tests))

print()
print("TOP-LEVEL FOLDERS (by node count)")
top = Counter((n.get("source_file") or "NONE").split("/")[0] for n in nodes)
for k, c in top.most_common(12):
    print(f"  {k}: {c}")

print()
print("FILES WITH MOST NODES")
files = Counter(n.get("source_file") for n in nodes)
for k, c in files.most_common(10):
    print(f"  {k}: {c}")

def show(l):
    s = by_id.get(l["source"], {})
    t = by_id.get(l["target"], {})
    print(f"  {s.get('label')} [{s.get('source_file')} {s.get('source_location')}]")
    print(f"    --{l['relation']}--> {t.get('label')} [{t.get('source_file')} {t.get('source_location')}]")
    print(f"    edge at {l.get('source_file')} {l.get('source_location')}, {l.get('confidence')}")

print()
print("SAMPLE EDGES (to check direction)")
for rel in ("calls", "contains", "imports_from", "inherits", "uses", "references"):
    print(f"--- {rel}")
    shown = 0
    for l in links:
        s = by_id.get(l["source"], {})
        if l["relation"] == rel and not is_vendored(s.get("source_file")):
            show(l)
            shown += 1
            if shown == 2:
                break
