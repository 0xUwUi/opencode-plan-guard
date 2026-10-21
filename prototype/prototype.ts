import { appendFileSync, readFileSync } from "node:fs"

// ===== Plan 只读守卫（原型，跑用例用）=====
const LOG = "/tmp/opencode-guard.log"

const DENY = [
  /\b(rm|rmdir|mv|cp|dd|truncate|shred|chmod|chown|chgrp|install|touch|mkdir|ln|patch|tee|sed|rsync|curl|wget)\b/,
  /\bgit\b/, /\bnpm\b/, /\bpip3?\b/, /\b(apt|apt-get|dnf|yum|pacman|brew)\b/,
  /\bxargs\b/, /\bawk\b/, /\bvim?\b/, /\bnano\b/,
]

const READ_ONLY = [
  /^(ls|ll|la|dir)(?:\s+[^\s;&|<>]+)*$/,
  /^cat(?:\s+-[a-zA-Z]+)*\s+[^<>;&|]*$/,
  /^head(?:\s+-\d+)?(?:\s+-[a-zA-Z]+)*\s+[^<>;&|]*$/,
  /^tail(?:\s+-\d+)?(?:\s+-[a-zA-Z]+)*\s+[^<>;&|]*$/,
  /^(grep|rg|fgrep)(?:\s+-[a-zA-Z0-9:=]+)*\s+.*$/,
  /^git\s+(status|diff|log|show|branch|blame|rev-parse|ls-files)\b[^<>;&|]*$/,
  /^git\s+config\s+--get[^<>;&|]*$/,
  /^find\b(?!.*-(?:delete|exec|execdir|ok|fprint\w*)\b)[^<>;&|]*$/,
  /^(ps|pwd|cd|date|whoami|uname|which|type|test|true|printf|echo|wc|stat|file|diff|cmp|jq|sort|uniq|cut|realpath|basename|dirname)\b[^<>;&|]*$/,
  /^(python3?|node)\s+-(c|e|p|v|-version)\b[^<>;&|]*$/,
]

const SEG = /\s*(?:&&|\|\||;|\||\$\()\s*/g

function segs(cmd: string): string[] {
  const out: string[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = SEG.exec(cmd))) {
    out.push(cmd.slice(last, m.index))
    last = m.index + m[0].length
  }
  out.push(cmd.slice(last))
  return out.map((s) => s.trim()).filter(Boolean)
}

function readOnly(input: any): { ok: boolean; why: string } {
  let command = ""
  if (input?.command) command = input.command
  else if (input?.code) command = ""            // execute(code=...) 由 execute 权限处理
  else return { ok: true, why: "no-command" }
  const parts = segs(command)
  if (!parts.length) return { ok: false, why: "empty" }
  for (const s of parts) {
    if (/[<>`]/.test(s)) return { ok: false, why: "redirect:" + s }
    if (DENY.some((r) => r.test(s))) return { ok: false, why: "deny-verb:" + s }
    if (!READ_ONLY.some((r) => r.test(s))) return { ok: false, why: "not-whitelisted:" + s }
  }
  return { ok: true, why: "whitelisted" }
}

function log(line: string) {
  try { appendFileSync(LOG, line + "\n") } catch {}
}

export default {
  id: "plan-guard-proto",
  async setup(ctx: any) {
    await ctx.permission.hook("evaluate", (event: any) => {
      const src = event.source
      let tool = "?"
      let input: any = undefined
      try {
        const raw = readFileSync(`/tmp/opencode-probe/${event.sessionID}.json`, "utf8")
        void raw
      } catch {}
      log(`${new Date().toISOString()} agent=${event.agent} action=${event.action} res=${JSON.stringify(event.resources)} source=${JSON.stringify(src ?? null)} effect=${event.effect}`)
    })
    return () => {}
  },
}
