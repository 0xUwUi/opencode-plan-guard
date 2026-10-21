# opencode-plan-guard

OpenCode V2 插件：让 Plan 模式真正只读。

## 背景

OpenCode 内置 `plan` agent 的权限只配置了：

```
edit *                  → deny
edit ~/.opencode/plan/* → allow
```

**shell 没有任何 plan 专属规则**，仍走普通的 allow/ask 策略。因此模型在 Plan 模式下
用 shell 写文件不会被阻止，实测可直接执行成功：

```sh
sed -i 's/alpha/beta/' note.txt     # 成功修改
echo X >> note.txt                  # 成功追加
cp note.txt dup.txt                 # 成功复制
```

## 方案

在 `ctx.permission.hook("evaluate")` 上追加硬性检查：当前 agent 是 `plan` 时，
每条 shell 命令必须命中只读白名单才放行，否则把判定改为 `deny`
（优先级高于 allow，也高于「总是允许」）。

判定逻辑：

1. 按 `;` `&&` `||` `|` `$(` 拆段，逐段校验
2. 任何含 `<` `>` 或反引号的命令直接拒绝（重定向/命令替换都能写文件）
3. 其余交给只读正则表，未命中即拒绝（默认拒绝，宁可误杀）

## 文件说明

| 路径 | 说明 |
|---|---|
| `src/plan-guard.ts` | **插件本体**，与 `~/.config/opencode/plugins/plan-guard.ts` 一致 |
| `prototype/prototype.ts` | 早期原型（会误杀 `git status`），保留作历史 |
| `plan-guard-tests.md` | 手工验收用例表 |
| `harness.py` | 通过 HTTP API 驱动会话、逐条执行用例的测试脚本 |
| `harness4.py` | 改进版：按 tool call id 精确配对，支持复合命令 |
| `run_cases.py` | 用例运行器，输出 PASS/FAIL 汇总 |

## 安装

```sh
cp src/plan-guard.ts ~/.config/opencode/plugins/
```

依赖：`~/.config/opencode/package.json` 需有 `"@opencode/plugin": "2.1.2"`（V2 API）。

## 验证结果

真实环境中用 `opencode run --standalone --agent plan` 验证：

```
✗ sed -i 's/alpha/beta/' note.txt failed
Error: Blocked by plan-guard: Plan mode is read-only, and
"sed -i 's/alpha/beta/' note.txt" is not a recognized read-only command.
```

文件未被修改，`git status` 等只读命令正常放行。

## 已知限制

- 白名单是默认拒绝，`awk`、`sed -n`（纯读取）、`xargs`、`uv`、`poetry` 等会被误杀
- `execute`（Code Mode）工具不受此 hook 约束；当前项目中它无法直接访问文件系统
- 调试：设置 `OPENCODE_PLAN_GUARD_TRACE=/tmp/plan-guard.log` 记录每条命令的判定
