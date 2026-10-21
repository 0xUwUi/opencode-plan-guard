"""准备验收夹具。

用法：
    python3 tests/setup_fixture.py [目标目录]

默认目标 /tmp/opencode/harness，与 harness.py 的 ROOT 一致。
每次运行都会把夹具文件重置为初始状态，并清掉上一轮用例留下的残骸，
这样"文件有没有被改"才是可信的判据。
"""

import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PLAN_GUARD_ROOT", "/tmp/opencode/harness")

INITIAL = {"note.txt": "alpha\n", "empty.txt": "gamma\n"}
LEFTOVERS = ("dup.txt", "moved.txt", "newfile", "gone.txt", "x.txt")


def main():
    os.makedirs(ROOT, exist_ok=True)
    for name, text in INITIAL.items():
        with open(os.path.join(ROOT, name), "w") as fh:
            fh.write(text)
    for name in LEFTOVERS:
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            os.remove(path)
    newdir = os.path.join(ROOT, "newdir")
    if os.path.isdir(newdir) and not os.listdir(newdir):
        os.rmdir(newdir)

    print("fixture ready:", ROOT)
    for name, text in INITIAL.items():
        print(f"  {name}: {text!r}")
    print()
    print("下一步：确保 4799 口的 opencode serve 已启动，")
    print("       且密码写在 /tmp/opencode/auth4799.txt，然后运行")
    print("       python3 tests/run_cases.py")


if __name__ == "__main__":
    main()
