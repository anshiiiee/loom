import ast
import re
import subprocess
import sys

from loom_graph import LoomGraph

ROOT = "opensource-job-portal"
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def git_diff(rev_args):
    cmd = ["git", "-C", ROOT, "diff", "-U0", "--no-color"] + rev_args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("git diff failed: " + r.stderr)
    return r.stdout


def parse_changed_lines(diff_text):
    changed = {}
    current = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            current = path[2:] if path.startswith("b/") else None
            if current:
                changed.setdefault(current, [])
        elif line.startswith("@@") and current:
            m = HUNK_RE.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                changed[current].append((max(start, 1), max(start, 1) + max(count, 1) - 1))
    return changed


def py_def_ranges(path):
    try:
        with open(ROOT + "/" + path) as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return None
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((node.lineno, node.end_lineno))
    return out


def node_line(n):
    loc = n.get("source_location") or ""
    return int(loc[1:]) if loc[1:].isdigit() else None


def innermost_overlaps(defs, s, e):
    hits = [d for d in defs if d[0] <= e and d[1] >= s]
    return [d for d in hits
            if not any(o != d and o[0] >= d[0] and o[1] <= d[1] for o in hits)]


def main():
    g = LoomGraph()
    changed = parse_changed_lines(git_diff(sys.argv[1:]))
    if not changed:
        print("No tracked changes found. (New untracked files do not appear in git diff.)")
        return
    seeds = []
    print("CHANGED FILES AND SYMBOLS")
    for path, ranges in changed.items():
        ids = g.nodes_in_file(path)
        if not ids:
            print(f"  {path}: no project nodes in graph (new file, vendored, or unsupported type)")
            continue
        nodes = [g.nodes[i] for i in ids]
        file_nodes = [n for n in nodes if path.endswith(n["label"])]
        sym_nodes = [n for n in nodes if not path.endswith(n["label"])]
        picked = {}
        defs = py_def_ranges(path) if path.endswith(".py") else None
        for s, e in ranges:
            if defs is not None:
                for d in innermost_overlaps(defs, s, e):
                    for n in sym_nodes:
                        if node_line(n) == d[0]:
                            picked[n["id"]] = n
            else:
                before = [n for n in sym_nodes if node_line(n) and node_line(n) <= s]
                if before:
                    n = max(before, key=node_line)
                    picked[n["id"]] = n
        print(f"  {path}  (changed lines: {ranges})")
        if picked:
            for n in picked.values():
                print(f"      symbol: {n['label']} [{n['source_location']}]")
            seeds.extend(picked.keys())
        else:
            print("      no symbol matched; treating as file-level change")
            seeds.extend(n["id"] for n in file_nodes)
    if not seeds:
        print("Nothing to trace.")
        return
    results = [r for r in LoomGraph.trace_impact(g, seeds) if r["node_id"] not in seeds]
    fallback_note = ""
    if not results:
        file_seeds = []
        for path in changed:
            file_seeds.extend(
                n["id"] for n in (g.nodes[i] for i in g.nodes_in_file(path))
                if path.endswith(n["label"])
            )
        results = [r for r in LoomGraph.trace_impact(g, file_seeds) if r["node_id"] not in seeds]
        fallback_note = "No dependents of the changed symbol itself; showing FILE-LEVEL dependents instead."
    prod = [r for r in results if not r["is_test"]]
    tests = [r for r in results if r["is_test"]]
    print()
    if fallback_note:
        print(fallback_note)
    print(f"IMPACT: {len(prod)} production components, {len(tests)} test components")
    for title, rows in (("PRODUCTION", prod), ("TESTS", tests)):
        print()
        print(title + " (first 10)")
        for r in rows[:10]:
            print(f"  [{r['status']}] {r['label']} [{r['file']} {r['line']}]")
            print(f"      depth {r['depth']}, {r['relation']} ({r['confidence']}), edge at {r['edge_file']} {r['edge_line']}")
    print()
    print("HEURISTIC TEST CANDIDATES (same-folder naming convention, NOT graph-verified)")
    cands = heuristic_tests(list(changed.keys()))
    for c in cands:
        print("  " + c)
    if not cands:
        print("  none found")


def heuristic_tests(changed_paths):
    import os
    out = []
    for path in changed_paths:
        folder = os.path.dirname(path)
        for name in ("tests.py", "test_" + os.path.basename(path)):
            candidate = folder + "/" + name
            if os.path.exists(ROOT + "/" + candidate):
                out.append(candidate)
    return out


if __name__ == "__main__":
    main()
