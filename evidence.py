import subprocess

ROOT = "opensource-job-portal"
MAX_DIFF_CHARS = 3000
MAX_SNIPPET_LINES = 25


def get_diff_text(rev_args):
    cmd = ["git", "-C", ROOT, "diff", "-U2", "--no-color"] + rev_args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git diff failed: " + r.stderr)
    text = r.stdout
    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n... [diff truncated]"
    return text


def read_snippet(path, line, before=2, after=MAX_SNIPPET_LINES):
    """Return real lines from the repo around a graph line number."""
    try:
        with open(ROOT + "/" + path) as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    start = max(line - 1 - before, 0)
    end = min(line - 1 + after, len(lines))
    return "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))


def snippet_for_node(file, location):
    loc = (location or "")[1:]
    if not loc.isdigit():
        return None
    return read_snippet(file, int(loc))


if __name__ == "__main__":
    import sys
    path, line = sys.argv[1], int(sys.argv[2])
    print(read_snippet(path, line))
