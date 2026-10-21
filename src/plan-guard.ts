import { Plugin } from "@opencode/plugin"

/**
 * Plan 模式只读守卫（plan-guard）
 *
 * 为什么需要：OpenCode 内置的 `plan` agent 只配置了 `edit → deny`
 * （外加 `~/.opencode/plan/*` 的例外），但它的 **shell 权限仍走普通的
 * allow/ask 策略**。也就是说模型在 Plan 模式下用 shell 写文件
 * （`sed -i`、`echo >>`、`cp`、`mv`、`chmod`、`npm install` …）
 * 不会被任何规则拦住，只会"嘴上说"自己在只读模式。
 *
 * 本插件在 `ctx.permission.hook("evaluate")` 追加硬性检查：
 * 当前 agent 是 `plan` 时，每条 shell 命令必须命中只读白名单才放行，
 * 否则把判定改为 `deny`（优先级高于 allow 和「总是允许」）。
 *
 * 判定策略：
 *   1. 按 `;` `&&` `||` `|` `$(` 拆段，逐段校验
 *   2. 任何含 `<` `>` 或反引号的命令直接拒绝（重定向/命令替换都能写文件）
 *   3. 其余交给只读正则表；未命中即拒绝（默认拒绝，宁可误杀）
 *
 * 单条命令放行后，同一次工具调用里的其他命令仍逐条检查，
 * 因为 OpenCode 会把 `ls ; rm x` 拆成 `["ls", "rm x"]` 多项 resource。
 *
 * 调试：设置环境变量 OPENCODE_PLAN_GUARD_TRACE=/tmp/plan-guard.log
 * 即可记录每条命令的判定结果。
 *
 * 关闭：删除本文件，或在 opencode.json(c) 的 plugins 里加 "-plan-guard"。
 */

const GUARDED_AGENT = "plan"

// 只读命令白名单：整段正则匹配。
const READ_ONLY: RegExp[] = [
  // 列目录 / 读文件
  /^(ls|ll|la|dir)(?:\s+[^\s;&|<>`]+)*$/,
  /^cat(?:\s+-[a-zA-Z]+)*\s+[^<>`;&|]*$/,
  /^head(?:\s+-\d+)?(?:\s+-[a-zA-Z]+)*\s+[^<>`;&|]*$/,
  /^tail(?:\s+-\d+)?(?:\s+-[a-zA-Z]+)*\s+[^<>`;&|]*$/,
  /^wc(?:\s+-[a-zA-Z]+)*\s+[^<>`;&|]*$/,
  /^(stat|file)\b[^<>`;&|]*$/,
  /^tree(?:\s+-[a-zA-Z]+)*\s+[^<>`;&|]*$/,
  /^(basename|dirname|realpath|readlink|du|df|nl|column)\b[^<>`;&|]*$/,

  // 搜索
  /^(grep|egrep|fgrep|rg)(?:\s+-(?:[a-zA-Z]|--[a-zA-Z-]+))*\s+[^<>`;&|]*$/,
  /^find\b(?!.*-(?:delete|exec|execdir|ok|okdir|fprint\w*|fprintf)\b)[^<>`;&|]*$/,

  // git 只读子命令
  /^git\s+(status|diff|log|show|branch|blame|rev-parse|ls-files|ls-tree|shortlog|describe|cat-file|show-ref|reflog|for-each-ref)\b[^<>`;&|]*$/,
  /^git\s+stash\s+list[^<>`;&|]*$/,
  /^git\s+worktree\s+list[^<>`;&|]*$/,
  /^git\s+config\s+--get\S*[^<>`;&|]*$/,

  // 系统信息
  /^(ps|pwd|date|whoami|id|groups|hostname|uname|nproc|uptime|which|type|whereis|locale|true|false|test|echo|printf|diff|cmp|comm|jq|cut|sort|uniq|od|xxd|strings|md5sum|sha1sum|sha256sum|cksum|seq|man)\b[^<>`;&|]*$/,

  // 代码类只读调用（-c/-e 之外的写法一律拒绝）
  /^cd(?:\s+[^<>`;&|]*)?$/,
  /^python3?\s+(?:-c|-version|-V|-h)\b[^<>`;&|]*$/,
  /^node\s+(?:-v|--version|-e\s+[^<>`;&|]*|-p\s+[^<>`;&|]*)$/,
  /^tsc\s+--noEmit\b[^<>`;&|]*$/,
  /^ruff\s+(?:check|format\s+--check)\b[^<>`;&|]*$/,
]

const SEGMENT = /\s*(?:&&|\|\||;|\||\n|\$\()\s*/g

function segments(command: string): string[] {
  const parts: string[] = []
  let last = 0
  let match: RegExpExecArray | null
  SEGMENT.lastIndex = 0
  while ((match = SEGMENT.exec(command))) {
    parts.push(command.slice(last, match.index))
    last = match.index + match[0].length
  }
  parts.push(command.slice(last))
  return parts.map((part) => part.trim()).filter(Boolean)
}

function check(command: string): { ok: boolean; why?: string } {
  const parts = segments(command.trim())
  if (!parts.length) return { ok: false, why: "the command is empty" }
  for (const part of parts) {
    if (/[<>`]/.test(part)) return { ok: false, why: `it contains redirection or substitution ("${part}")` }
    if (!READ_ONLY.some((re) => re.test(part))) {
      return { ok: false, why: `"${part}" is not a recognized read-only command` }
    }
  }
  return { ok: true }
}

export default Plugin.define({
  id: "plan-guard",
  async setup(ctx) {
    await ctx.permission.hook("evaluate", (event) => {
      if (event.action !== "shell") return
      if (event.agent !== GUARDED_AGENT) return

      const resources = event.resources ?? []
      for (const command of resources) {
        const verdict = check(command)
        if (verdict.ok) continue
        event.effect = "deny"
        event.message =
          `Blocked by plan-guard: Plan mode is read-only, and ${verdict.why}. ` +
          `Switch to the build agent to run commands that modify files or system state.`
        return
      }
    })

    return () => {}
  },
})
