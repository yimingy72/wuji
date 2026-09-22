# 当前开发线与历史归档

日期：2026-09-22。依据：用户明确确认舍弃 Cairn 路线，并授权归档旧线、调整工作区入口。

## 唯一开发主线

- 分支：`codex/vnext-maf`。
- 本机活动工作树：`work/worktrees/vnext-maf/`（相对共享仓库主目录）。先以 `git worktree list` 核对实际位置。
- 当前架构：Wuji 自有 Blackboard / Scheduler、Python MAF、ModelGate / ToolGate、LiteLLM 及 Task 双容器 Pod；权威正文见 [Spec](vnext/SPEC.md)、[Plan](vnext/PLAN.md)与[实施决定](vnext/decision-register.md)。
- 当前阶段与真实验收范围：[vNext](stages/vnext-maf/acceptance.md)、[首用](stages/first-use/acceptance.md)。归档操作不增加任何业务验收结论。

为保留现有开发工作树及运行路径，主目录使用 vNext 的 detached HEAD 快照，不占用第二份 `codex/vnext-maf` 检出，也不建立另一条开发主线。在本机执行开发、提交或构建时进入上述活动工作树；主目录快照不会自动跟随分支的新提交。新克隆可以直接检出 `codex/vnext-maf`，无需复制本机的工作树布局。

## Cairn / W1 归档

- 已退役的本地分支：`codex/github-upload`。
- 旧提交：`c9ec37176420362230dfac0ae917f18d8a6b2d07`，包含相对 vNext 独有的历史架构草案提交。
- 归档提交：`86e1bd44bf8019c25d0f0bf968913248525aad0b`。
- 本地归档标签：`archive/cairn-retired-2026-09-22`。
- 本机额外文件备份：主目录下 `work/archives/cairn-retired-2026-09-22/`，包含原文件、补丁与 SHA-256 清单，不进入 Git。

归档提交逐字节保留原来的 8 个已修改文件和 1 个未跟踪文件，包括协作规则整理及旧夹具/测试的上下文窗口调整。这些是既有未提交内容的保存，不是新的业务实现或测试通过声明；未将旧线修改自动套入 vNext。归档中的原始文件末尾空行也保持原样。

可在不切换现有工作树的情况下查看历史：

```sh
git show archive/cairn-retired-2026-09-22:AGENTS.md
git show --stat archive/cairn-retired-2026-09-22
```

需要恢复为可检出的本地历史分支时：

```sh
git branch archive/cairn-restored archive/cairn-retired-2026-09-22
```

旧源码、验收证据和已有历史工作树保留。共享主目录包含 `.git` 和嵌套工作树，不是可以整目录删除的旧副本。

## 远端与部署边界

本次仅整理本地 Git 和文档入口；没有推送、删除远端分支或更改 GitHub 默认分支。远端仍可能以旧线作为默认入口，不能将本次本地归档描述为远端已完成切换。

本次不调整 Kubernetes、镜像、服务、数据库、密钥或运行文件。代码提交、部署镜像与被测 SHA 继续分别记录；主目录快照更新不代表发布新版本。
