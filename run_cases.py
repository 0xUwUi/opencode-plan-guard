import sys
import json
import subprocess

H = "/tmp/opencode/harness4.py"
EXPECT = {
    "sed -i": "DENY",
    "echo X >>": "DENY",
    "echo P >": "DENY",
    "cp ": "DENY",
    "mv ": "DENY",
    "rm ": "DENY",
    "touch ": "DENY",
    "chmod ": "DENY",
    "mkdir ": "DENY",
    "ls ; rm": "DENY",
    "cat note.txt && sed": "DENY",
    "git checkout": "DENY",
    "git switch": "DENY",
    "find . -delete": "DENY",
    "find . -exec": "DENY",
    "npm install": "DENY",
    "tee ": "DENY",
    "git status": "EXEC",
    "git diff": "EXEC",
    "git log": "EXEC",
    "git rev-parse": "EXEC",
    "ls -la": "EXEC",
    "cat note.txt": "EXEC",
    "head -3": "EXEC",
    "tail -2": "EXEC",
    "find . -name": "EXEC",
    "grep -n": "EXEC",
    "wc -l": "EXEC",
    "which git": "EXEC",
    "git ls-files": "EXEC",
}


def expect_for(cmd):
    for prefix, want in EXPECT.items():
        if cmd.startswith(prefix):
            return want
    return "?"


def main():
    cmds = sys.argv[1:]
    p = subprocess.run([sys.executable, H, *cmds], capture_output=True, text=True, timeout=2400)
    out = p.stdout
    blocks = [b for b in out.split("CMD ") if b.strip()]
    fails = 0
    for b in blocks:
        lines = b.split("\n")
        first = lines[0]
        rest = "\n".join(lines[1:])
        clean = first.strip()
        if clean[:1] in "\"'":
            clean = clean[1:-1]
        got_cmd = ""
        status = "NO-CALL"
        for line in rest.splitlines():
            if "got=" in line:
                got_cmd = line.split("got=")[1].split(" status=")[0].strip().strip("'\"")
                if "permission.rejected" in line:
                    status = "DENY"
                elif "error=" in line and "error= " not in line and not line.rstrip().endswith("error="):
                    status = "ERROR"
                else:
                    status = "EXEC"
        want = expect_for(clean)
        ack = got_cmd == clean
        ok = ack and (status == want or want == "?")
        if not ok:
            fails += 1
        print(f"{clean[:52]:52} want={want:5} got={status:6} {'PASS' if ok else 'FAIL ack=' + str(ack) + ' actual=' + repr(got_cmd)[:45]}", flush=True)
    print("=== files ===", flush=True)
    print(out.split("=== files ===")[-1].strip())
    print("FAILS", fails)
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
