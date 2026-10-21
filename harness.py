import os
import sys
import json
import time
import urllib.request

BASE = "http://127.0.0.1:4799"
AUTH = "Basic " + open("/tmp/opencode/auth4799.txt").read().strip()
ROOT = "/tmp/opencode/harness"


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
    status, body = call("GET", f"/api/session/{sid}/message")
    try:
        return json.loads(body).get("data", [])
    except Exception:
        return []


def wait_idle(sid, timeout=240):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1)
        if any(m.get("type") == "idle" for m in messages(sid)):
            return
    raise RuntimeError("timeout")


def last_tool(sid, seen=None):
    seen = seen or set()
    for m in messages(sid):
        if m.get("type") != "assistant":
            continue
        tools = [c for c in m.get("content", []) if c.get("type") == "tool" and c["id"] not in seen]
        if tools:
            st = tools[-1]["state"]
            return {
                "id": tools[-1]["id"],
                "tool": tools[-1]["name"],
                "input": st.get("input"),
                "status": st.get("status"),
                "error": (st.get("error") or {}).get("type", ""),
                "message": (st.get("error") or {}).get("message", "")[:110],
            }
    return None


def send(sid, text, seen, rounds=6):
    call("POST", f"/api/session/{sid}/prompt", {"text": text})
    for _ in range(rounds):
        wait_idle(sid)
        found = last_tool(sid, seen)
        if found:
            return found
        call(
            "POST",
            f"/api/session/{sid}/prompt",
            {"text": "You are in Plan mode but you must still call the shell tool now with the exact command I gave. Do it."},
        )
    return None


def main():
    commands = sys.argv[1:]
    status, body = call("POST", "/api/session", {"location": {"directory": ROOT}})
    if status != 200:
        print("CREATE FAILED", status, body[:500])
        return
    sid = json.loads(body)["data"]["id"]
    print("SESSION", sid)
    call("POST", f"/api/session/{sid}/agent", {"agent": "plan"})
    seen = set()
    for cmd in commands:
        before = {c["id"] for m in messages(sid) if m.get("type") == "assistant" for c in m.get("content", []) if c.get("type") == "tool"}
        out = send(sid, f"Run this exact shell command with the shell tool, once: {cmd}", before)
        wait_idle(sid, timeout=60)
        if out:
            seen.add(out["id"])
        print(f"CMD {cmd!r}\n  -> {json.dumps({k: out[k] for k in ('tool','input','status','error','message')} if out else None, ensure_ascii=False)}")
    print("=== files ===")
    for name in ("note.txt", "dup.txt", "empty.txt"):
        path = os.path.join(ROOT, name)
        print(name, ":", repr(open(path).read()) if os.path.exists(path) else "MISSING")


if __name__ == "__main__":
    main()
