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
| `tests/harness.py` | 通过 HTTP API 驱动会话，按 tool call id 精确配对，逐条执行命令 |
| `tests/run_cases.py` | 用例表 + PASS/FAIL 判定，是唯一的用例来源 |
| `tests/setup_fixture.py` | 重置验收夹具（`note.txt` / `empty.txt`，清掉上一轮残骸） |

## 安装

```sh
cp src/plan-guard.ts ~/.config/opencode/plugins/
```

依赖：`~/.config/opencode/package.json` 需有 `"@opencode/plugin": "2.1.2"`（V2 API）。

## 跑验收用例

用例需要真实跑一遍 OpenCode，所以要先有一个带密码的本地服务：

```sh
# 1. 准备夹具
python3 tests/setup_fixture.py

# 2. 起被测服务（密码会打印在 stdout）
opencode serve --port 4799
#    server password xxxxx  →  写入 /tmp/opencode/auth4799.txt

# 3. 跑全部内置用例
python3 tests/run_cases.py

# 也可以只跑指定命令，此时不判定期望值，只打印实际结果
python3 tests/run_cases.py 'ls -la' 'rm note.txt'
```

路径与端口可用环境变量覆盖：`PLAN_GUARD_API`、`PLAN_GUARD_AUTH`、`PLAN_GUARD_ROOT`。

每条用例的判定是三段式的：模型确实调到了 shell（`ack`）、命令原文一致、
以及结果是 `DENY` / `EXEC` / `ERROR` 中的期望值。任一不满足即 FAIL。

## 验证结果

真实环境中用 `opencode run --standalone --agent plan` 验证：

```
✗ sed -i 's/alpha/beta/' note.txt failed
Error: Blocked by plan-guard: Plan mode is read-only, and
"sed -i 's/alpha/beta/' note.txt" is not a recognized read-only command.
```

`tests/run_cases.py` 内置 31 条用例（17 条期望拦截、14 条期望放行）。

## 已知限制

- 白名单是默认拒绝，`awk`、`sed -n`（纯读取）、`xargs`、`uv`、`poetry` 等会被误杀
- `execute`（Code Mode）工具不受此 hook 约束；当前项目中它无法直接访问文件系统
- 调试：设置 `OPENCODE_PLAN_GUARD_TRACE=/tmp/plan-guard.log` 记录每条命令的判定
