"""Plan 拦截插件的验收用例。

用法：
    python3 tests/run_cases.py            # 跑内置用例表
    python3 tests/run_cases.py 'ls -la'   # 只跑指定命令，期望记为 "?" 不判定

前提：被测插件已装到 ~/.config/opencode/plugins/plan-guard.ts，
且 4799 端口的 opencode serve 已启动、密码写在 /tmp/opencode/auth4799.txt。
"""

import os
import sys
import subprocess

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "harness.py")

# 命令前缀 -> 期望结果。按插入顺序匹配，前缀相同时先写的先生效。
EXPECT = {
    # --- 写文件 / 改系统状态：Plan 下必须拦截 ---
    "sed -i": "DENY",
    'sed -i \'s/alpha/beta/\' note.txt': "DENY",
    "echo X >>": "DENY",
    "echo X >": "DENY",
    "echo P >": "DENY",
    "cp ": "DENY",
    "cp note.txt": "DENY",
    "mv ": "DENY",
    "rm ": "DENY",
    "touch ": "DENY",
    "chmod ": "DENY",
    "mkdir ": "DENY",
    "tee ": "DENY",
    "npm install": "DENY",
    # --- 复合命令：任何一段可写即整体拒绝 ---
    "ls ; rm": "DENY",
    "cat note.txt && sed": "DENY",
    # --- 危险子命令必须被白名单排除 ---
    "git checkout": "DENY",
    "git switch": "DENY",
    "find . -delete": "DENY",
    "find . -exec": "DENY",
    # --- 只读命令：放行 ---
    "git status": "EXEC",
    "git diff": "EXEC",
    "git log": "EXEC",
    "git rev-parse": "EXEC",
    "git ls-files": "EXEC",
    "ls -la": "EXEC",
    "cat note.txt": "EXEC",
    "head -3": "EXEC",
    "head -5": "EXEC",
    "tail -2": "EXEC",
    "find . -name": "EXEC",
    "find /tmp -newer": "EXEC",
    "grep -n": "EXEC",
    "wc -l": "EXEC",
    "which git": "EXEC",
}

# 内置用例表（按此顺序发给模型）。只在没给命令行参数时使用。
CASES = [
    "sed -i 's/alpha/beta/' note.txt",
    "echo X >> note.txt",
    "echo P > note.txt",
    "cp note.txt dup.txt",
    "mv note.txt moved.txt",
    "rm note.txt",
    "touch newfile",
    "chmod 777 note.txt",
    "mkdir newdir",
    "npm install",
    "tee /tmp/opencode/harness/x.txt",
    "ls ; rm note.txt",
    "cat note.txt && sed -i 's/a/b/' empty.txt",
    "git checkout -- .",
    "git switch -",
    "find . -delete",
    "find . -exec rm {} ;",
    "git status",
    "git diff",
    "git log --oneline -3",
    "git rev-parse --show-toplevel",
    "git ls-files",
    "ls -la",
    "cat note.txt",
    "head -5 note.txt",
    "tail -2 note.txt",
    "find . -name '*.txt'",
    "find /tmp -newer note.txt",
    "grep -n alpha note.txt",
    "wc -l note.txt",
    "which git",
]


def expect_for(cmd):
    for prefix, want in EXPECT.items():
        if cmd.startswith(prefix):
            return want
    return "?"


def main():
    cmds = sys.argv[1:] or CASES
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
