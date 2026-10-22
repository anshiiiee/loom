import json
from collections import Counter

PATH = "opensource-job-portal/graphify-out/graph.json"

with open(PATH) as f:
    data = json.load(f)

print("Top-level type:", type(data).__name__)
if isinstance(data, dict):
    print("Top-level keys:", list(data.keys()))
    for key, value in data.items():
        if isinstance(value, list):
            print(f"  {key}: list of {len(value)}")
        elif isinstance(value, dict):
            print(f"  {key}: dict with keys {list(value.keys())[:10]}")
        else:
            print(f"  {key}: {value!r}")

nodes = data.get("nodes", []) if isinstance(data, dict) else []
edges = data.get("edges", data.get("links", [])) if isinstance(data, dict) else []

print()
print("Node count:", len(nodes))
print("Edge count:", len(edges))

if nodes:
    print()
    print("Sample node:")
    print(json.dumps(nodes[0], indent=2)[:600])
    print("Node fields:", sorted({k for n in nodes for k in n.keys()}))
    for field in ("type", "kind", "label", "file_type", "community"):
        if field in nodes[0]:
            counts = Counter(str(n.get(field)) for n in nodes)
            print(f"Distinct '{field}' values: {len(counts)}")
            print("  top 10:", counts.most_common(10))

if edges:
    print()
    print("Sample edge:")
    print(json.dumps(edges[0], indent=2)[:600])
    print("Edge fields:", sorted({k for e in edges for k in e.keys()}))
    for field in ("relation", "type", "kind", "label", "confidence"):
        if field in edges[0]:
            counts = Counter(str(e.get(field)) for e in edges)
            print(f"Distinct '{field}' values: {len(counts)}")
            print("  top 10:", counts.most_common(10))
