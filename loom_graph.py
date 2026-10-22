import json
import re
import sys
from collections import defaultdict, deque

GRAPH_PATH = "opensource-job-portal/graphify-out/graph.json"

# Relations that mean "source depends on target".
DEP_RELATIONS = {
    "calls", "indirect_call", "uses", "inherits", "extends",
    "imports", "imports_from", "re_exports", "dynamic_import",
}

VENDOR_MARKERS = (
    ".min.js", "node_modules", "/vendor", "static/js", "static/r1",
    "ckeditor", "jquery", "moment",
)


def is_vendored(path):
    p = (path or "").lower()
    return any(m in p for m in VENDOR_MARKERS)


TEST_PATH_RE = re.compile(
    r"(^|/)(tests?\.py|test_[^/]*\.py|[^/]*_tests?\.py|tests?/|[^/]*\.(test|spec)\.(ts|js))"
)


def is_test_path(path):
    return bool(TEST_PATH_RE.search((path or "").lower()))


class LoomGraph:
    def __init__(self, path=GRAPH_PATH):
        with open(path) as f:
            data = json.load(f)
        self.commit = data.get("built_at_commit")
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.incoming = defaultdict(list)
        for link in data["links"]:
            if link["relation"] in DEP_RELATIONS:
                self.incoming[link["target"]].append(link)

    def is_project_node(self, node):
        if not node:
            return False
        if node.get("external") or node.get("file_type") != "code":
            return False
        path = node.get("source_file") or ""
        return bool(path) and not is_vendored(path)

    def nodes_in_file(self, path):
        return [
            n["id"] for n in self.nodes.values()
            if n.get("source_file") == path and self.is_project_node(n)
        ]

    def find_symbols(self, label, path_hint=None):
        return [
            n["id"] for n in self.nodes.values()
            if n.get("label") == label and self.is_project_node(n)
            and (not path_hint or path_hint in (n.get("source_file") or ""))
        ]

    def trace_impact(self, seed_ids, max_depth=2):
        """Walk incoming dependency edges: who depends on the seeds?"""
        visited = set(seed_ids)
        queue = deque((sid, 0, True) for sid in seed_ids)
        results = []
        while queue:
            nid, depth, all_verified = queue.popleft()
            if depth >= max_depth:
                continue
            for link in self.incoming.get(nid, []):
                src = link["source"]
                if src in visited:
                    continue
                visited.add(src)
                node = self.nodes.get(src)
                if not self.is_project_node(node):
                    continue
                verified = all_verified and link.get("confidence") == "EXTRACTED"
                if depth == 0 and verified:
                    label = "VERIFIED DEPENDENCY"
                elif depth == 0:
                    label = "INFERRED DEPENDENCY"
                else:
                    label = "POTENTIAL (indirect)"
                results.append({
                    "node_id": src,
                    "label": node.get("label"),
                    "file": node.get("source_file"),
                    "line": node.get("source_location"),
                    "depth": depth + 1,
                    "status": label,
                    "via": nid,
                    "relation": link["relation"],
                    "confidence": link.get("confidence"),
                    "edge_file": link.get("source_file"),
                    "edge_line": link.get("source_location"),
                    "is_test": is_test_path(node.get("source_file")),
                })
                queue.append((src, depth + 1, verified))
        order = {"VERIFIED DEPENDENCY": 0, "INFERRED DEPENDENCY": 1, "POTENTIAL (indirect)": 2}
        results.sort(key=lambda r: (order[r["status"]], r["depth"], r["file"] or ""))
        return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python loom_graph.py <file path OR symbol name>")
        return
    arg = sys.argv[1]
    g = LoomGraph()
    if "::" in arg:
        path_hint, label = arg.split("::", 1)
        seeds = g.find_symbols(label, path_hint)
        print(f"Symbol {label} in files matching {path_hint}: {len(seeds)} match(es)")
        for s in seeds:
            n = g.nodes[s]
            print(f"  {n['label']} [{n['source_file']} {n['source_location']}]")
    elif "/" in arg or arg.endswith((".py", ".ts", ".svelte", ".js")):
        seeds = g.nodes_in_file(arg)
        print(f"File {arg}: {len(seeds)} project nodes")
    else:
        seeds = g.find_symbols(arg)
        print(f"Symbol {arg}: {len(seeds)} match(es)")
        for s in seeds:
            n = g.nodes[s]
            print(f"  {n['label']} [{n['source_file']} {n['source_location']}]")
    if not seeds:
        print("No matching nodes found.")
        return
    results = g.trace_impact(seeds)
    prod = [r for r in results if not r["is_test"]]
    tests = [r for r in results if r["is_test"]]
    print()
    print(f"IMPACT: {len(prod)} production components, {len(tests)} test components")
    for title, rows in (("PRODUCTION", prod), ("TESTS", tests)):
        print()
        print(title + " (first 25)")
        for r in rows[:25]:
            print(f"  [{r['status']}] {r['label']} [{r['file']} {r['line']}]")
            print(f"      depth {r['depth']}, {r['relation']} ({r['confidence']}), edge at {r['edge_file']} {r['edge_line']}")


if __name__ == "__main__":
    main()
