import os
import sys
import json
import time
import urllib.request

BASE = os.environ.get("PLAN_GUARD_API", "http://127.0.0.1:4799")
AUTH_FILE = os.environ.get("PLAN_GUARD_AUTH", "/tmp/opencode/auth4799.txt")
ROOT = os.environ.get("PLAN_GUARD_ROOT", "/tmp/opencode/harness")
AUTH = "Basic " + open(AUTH_FILE).read().strip()


def call(method, path, body=None, timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Authorization": AUTH, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except Exception as exc:
        detail = exc.read().decode() if hasattr(exc, "read") else ""
        return "ERR", str(exc) + detail


def messages(sid):
    _, body = call("GET", f"/api/session/{sid}/message")
    try:
        return json.loads(body).get("data", [])
    except Exception:
        return []


def snapshot(sid):
    """返回已出现的 tool id 及其状态（messageID::callID -> status）"""
    out = {}
    for m in messages(sid):
        if m.get("type") != "assistant":
            continue
        for c in m.get("content", []):
            if c.get("type") == "tool":
                out[f"{m['id']}::{c['id']}"] = {
                    "tool": c["name"],
                    "state": c.get("state", {}),
                }
    return out


def wait_new_tool(sid, before, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        current = snapshot(sid)
        new = {k: v for k, v in current.items() if k not in before}
        settled = [v for v in new.values() if v["state"].get("status") in ("completed", "error")]
        if settled:
            return settled[0]
    return None


def new_command_tools(sid, before):
    """本轮新出现的、input 为 {command} 的 shell 调用"""
    current = snapshot(sid)
    out = []
    for k, v in current.items():
        if k in before:
            continue
        data = v["state"].get("input") or {}
        if isinstance(data.get("command"), str):
            out.append(v)
    return out


def main():
    status, body = call("POST", "/api/session", {"location": {"directory": ROOT}})
    if status != 200:
        print("SESSION CREATE FAILED", status, body[:500])
        return
    sid = json.loads(body)["data"]["id"]
    call("POST", f"/api/session/{sid}/agent", {"agent": "plan"})
    print("SESSION", sid)
    for cmd in sys.argv[1:]:
        before = snapshot(sid)
        call("POST", f"/api/session/{sid}/prompt", {"text": f"Run this exact shell command with the shell tool, once: {cmd}"})
        wait_new_tool(sid, before)
        time.sleep(2)
        hits = new_command_tools(sid, before)
        if not hits:
            print(f"CMD {cmd!r}\n  -> NO-CALL")
            continue
        for v in hits:
            st = v["state"]
            err = (st.get("error") or {}).get("type", "")
            print(f"CMD {cmd!r}\n  -> got={st.get('input', {}).get('command')!r} status={st.get('status')} error={err}")
    print("=== files ===")
    for name in ("note.txt", "dup.txt", "empty.txt", "newfile", "gone.txt"):
        import os

        path = os.path.join(ROOT, name)
        print(name, ":", repr(open(path).read()) if os.path.exists(path) else "MISSING")


if __name__ == "__main__":
    main()
