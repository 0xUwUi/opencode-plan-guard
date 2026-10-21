# Plan 拦截插件的验证用例

本文件只用于验证 `plan-guard` 插件。逐条执行下面命令，记录实际结果。

## 夹具

```sh
mkdir -p /tmp/opencode/guard-test && cd /tmp/opencode/guard-test
printf 'alpha\n' > note.txt
printf 'gamma\n' > empty.txt
```

## 用例

| # | 命令 | 期望 | 实际 |
|---|------|------|------|
| 1 | `sed -i 's/alpha/beta/' note.txt` | plan 下被拦截 |  |
| 2 | `echo X >> note.txt` | plan 下被拦截 |  |
| 3 | `echo X > note.txt` | plan 下被拦截 |  |
| 4 | `cp note.txt dup.txt` | plan 下被拦截 |  |
| 5 | `git status` | 放行 |  |
| 6 | `ls -la` | 放行 |  |
| 7 | `find . -name '*.txt'` | 放行 |  |
| 8 | `find /tmp -newer note.txt` | 放行 |  |
| 9 | `cat note.txt` | 放行 |  |
| 10 | `head -5 note.txt` | 放行 |  |
| 11 | `ls ; rm note.txt` | plan 下被拦截 |  |
| 12 | `cat note.txt && sed -i 's/a/b/' empty.txt` | plan 下被拦截 |  |
| 13 | `~/.opencode/plan/../x.sh` 写入 | 报告结果 |  |
