<a id="top"></a>

<h1 align="center">XingJian</h1>

<p align="center"><em>天行健，君子以自强不息。</em></p>

<p align="center">
  <b>English</b> &nbsp;|&nbsp; <a href="#zh">中文</a>
</p>

> **xingjian is a pathway to autodidact — for a human, and for an AI agent:**
> every change is either a *falsifiable* effort, **verified** step forward (tests green → committed)
> or it is erased (tests red → reverted).

We believe human cognitive limitions is design features need to be respected not
bugs to be fixed in AI era. This repo starts by respecting one feature of your brain:

- Your mind starts to wonder if the latency between your action and feedback becomes larger than 1s. 

## What's in this repo

| Path | What it is |
|---|---|
| `xingjian.py` | The Xingjian watcher: pure-stdlib Python, watches your saves, enforces the loop |
| `src/cross_entropy.py` | A minimal, pedagogical `torch.nn.CrossEntropyLoss` — built *with* this watcher (see `git log`) |
| `tests/test_cross_entropy.py` | 16 unittest cases doubling as usage docs for the loss |

## Quick start

```bash
uv run python xingjian.py --detach     # start in background — terminal stays free
tail -f .xingjian.log                  # watch verdicts (optional)
uv run python xingjian.py --stop       # stop
```

## The loop

Every save of a `.py` file triggers the **two-stage gate**:

1. **Execute each saved file** — a failing top-level `assert` is red.
   (Test files included: every saved `.py` file is run.)
2. **Run the test suite** (default: `uv run python -m unittest -v`,
   change with `--cmd "uv run pytest -q"` or `"npm test"`).

```
✅ green → committed 31dd37b: xingjian: working 08:27:29     (work is kept)
❌ red (check_bad.py failed) → REVERTING your change    (work is DELETED)
   Removing check_bad.py
   back to last green commit. take a smaller step!
```

Red means `git reset --hard HEAD` **and** `git clean -fd` — failing edits *and*
failing new files are destroyed. That is the point: the threat of losing work
is what forces genuinely small steps.

### Safety checks at startup

Refuses to start unless: inside a git repo, at least one commit exists, the
working tree is clean, and the gate passes once (baseline green). A revert can
only ever destroy the change made *after* you started watching.

### Flags

| Flag | Effect |
|---|---|
| `--detach` / `--stop` | Background mode; logs to `.xingjian.log`, pid in `.xingjian.pid` |
| `--cmd CMD` | Swap the test gate (pytest, npm, go test, ...) |
| `--run-timeout SECONDS` | Saved file that hangs → fails the gate (default 15) |
| `--no-run-changed` | Suite-only gate; don't execute saved files |
| `--keep-new` | Red resets edits but spares brand-new files (Xingjian-lite) |

## Rules to live by (the watcher enforces the rest)

- **Tiny, smaller and quicker steps.** If you can't say the change in one sentence, split it. Like running, make sure foot directly under your hip.
- **After a revert, shrink — never retry the same change.**
- **Only committed work survives.** Stray files in the repo get committed on the next green save; keep the tree intentional.

---

<a id="zh"></a>

<h1 align="center">XingJian</h1>

<p align="center"><em>天行健，君子以自强不息。</em></p>

<p align="center">
  <a href="#top">English</a> &nbsp;|&nbsp; <b>中文</b>
</p>

> **xingjian 是一条自学之路——为人，亦为 AI 代理：**
> 每一次修改要么是**可证伪**的尝试、**可验证**的前进（测试绿色 → 已提交），
> 要么被抹去（测试红色 → 已回退）。未经验证的东西无法留存，因此
> 代码库只能朝一个方向前进：被证明更好。


## 本仓库内容

| 路径 | 说明 |
|---|---|
| `xingjian.py` | Xingjian 监视器：纯标准库 Python，监视文件保存，执行工作流 |
| `src/cross_entropy.py` | 一个极简的教学版 `torch.nn.CrossEntropyLoss`——配合监视器构建（见 `git log`） |
| `tests/test_cross_entropy.py` | 16 个 unittest 用例，同时也可作为该 loss 的使用文档 |

## 快速开始

```bash
uv run python xingjian.py --detach     # 后台启动——终端不受影响
tail -f .xingjian.log                  # 查看判定结果（可选）
uv run python xingjian.py --stop       # 停止
```

## 工作流

每次保存 `.py` 文件都会触发**两阶段关卡**：

1. **执行每个保存的文件**——顶层 `assert` 失败即为红色。
   （测试文件也不例外：每个保存的 `.py` 文件都会被执行。）
2. **运行测试套件**（默认：`uv run python -m unittest -v`，
   可通过 `--cmd "uv run pytest -q"` 或 `"npm test"` 更改）。

```
✅ 绿色 → 已提交 31dd37b: xingjian: working 08:27:29     （工作成果被保留）
❌ 红色 (check_bad.py 失败) → 正在回退你的修改    （工作成果被删除）
   正在移除 check_bad.py
   回退到上一个绿色提交。请使用更小的步骤！
```

红色意味着 `git reset --hard HEAD` **并且** `git clean -fd`——失败的编辑*和*
失败的新文件都会被销毁。这正是其意义所在：失去工作的威胁
迫使你真正采用足够小的步骤。

### 启动时的安全检查

除非满足以下条件，否则拒绝启动：位于 git 仓库中、至少存在一次提交、
工作区干净，且关卡至少通过一次（基线绿色）。回退只能销毁
你开始监视*之后*所做的修改。

### 参数

| 参数 | 效果 |
|---|---|
| `--detach` / `--stop` | 后台模式；日志写入 `.xingjian.log`，进程 ID 保存在 `.xingjian.pid` |
| `--cmd CMD` | 替换测试关卡（pytest、npm、go test 等） |
| `--run-timeout SECONDS` | 保存的文件挂起 → 关卡失败（默认 15 秒） |
| `--no-run-changed` | 仅运行测试套件；不执行保存的文件 |
| `--keep-new` | 红色时重置编辑但保留新创建的文件（Xingjian-lite 模式） |

## 遵循的准则（其余由监视器强制执行）

- **更小、更快的步骤。** 如果你无法用一句话描述这个修改，就拆开它。就像跑步，让脚掌垂直落在髋部正下方。
- **回退后，缩小范围——永远不要重试同样的修改。**
- **只有已提交的工作才能留存。** 仓库中的零散文件会在下一次绿色保存时被提交；保持工作目录的整洁。
