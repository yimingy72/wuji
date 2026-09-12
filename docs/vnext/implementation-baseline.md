# P00 实际实施基线

日期：2026-09-13；来源：当前主代理命令与 SOL xhigh 只读基线核查。未运行产品测试或目标/模型请求。

## 代码与工作树

| 对象 | 实际核对 |
| --- | --- |
| 起点 HEAD | `1d73a767599732d9a53f81ad2cc553f4bf11d84e` |
| 主目录 | `/Users/yym1ng/Documents/ChatGPT/wuji`；`codex/github-upload`；保留上一轮7份文档修改和3份未跟踪架构草案 |
| 执行工作树 | `/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf`；`codex/vnext-maf`；此前无重构实现提交 |
| 初始未跟踪文件 | `docs/vnext/SPEC.md` / `PLAN.md` / `REVIEW.md`，逐字节等于下载包 `source/V1_*`；现已在该 source 归档中保留，顶层导入v2 |
| 旧准备记录 | `.superpowers/sdd/PLAN` 的 v1 台账为 P00 in_progress，没有已完成代码；保留并新建 v2 台账 |
| CodeGraph | 两工作树没有 `.codegraph/`；回退 `rg` 与源码读取 |
| 旧源码迁移头 | `20260911_0008`，静态链从 `20260909_0001` 到 0008；数据库实际 current 未核对 |

## 设计来源与完整性

源目录是用户指定的 `/Users/yym1ng/Downloads/wuji_maf_redesign_v2`。45 个文件已导入；其中44个清单条目的字节数和 SHA-256 均与 `artifact_manifest.json` 一致，manifest 本身排除自引用。不是用旧公开 SHA 替代本地基准。

| v2文件 | SHA-256 |
| --- | --- |
| SPEC.md | `9525842dfa9421456521946ab2ba8aae62e1e7642bb42dfce1c501cd25ade05d` |
| PLAN.md | `435c57bb25533af34dd0bf19c1a6cc2a167cdbfb6a7f4d59cda53f520bbf24a8` |
| REVIEW.md | `79d8cbbe705ab302f8f0993f0da6572b277be7a013ad0a11f86b76066309be9e` |

本轮实际确认的是文件完整性；源包原 `VALIDATION_REPORT.md` 的10项文档检查属于原包事实，本轮不将其作为产品验收。实施记录会增量保存在清单之外的本目录文件；重新验证原包严格文件集合时使用原下载目录，仓库导入核对清单所列条目而不把新增实施记录误作原件。

## 工具与环境现状

| 项目 | 实际结果 / 边界 |
| --- | --- |
| 主机 | Darwin arm64 |
| 默认 Python / Node / pnpm | Python 3.14.6、Node v26.0.0、pnpm 11.19.0；与旧项目声明不同 |
| 默认 uv | 失败：pyenv 未安装仓库声明的3.13.15；不能使用默认 shim 执行同步 |
| 隔离树已有工具链 | `work/toolchain/bin/uv` 实测0.12.11；受管Python实测3.13.15；Node/pnpm可执行链接已存在，P01需核对其实际执行版本 |
| bootstrap重建 | 当前受跟踪manifest/bootstrap仅覆盖Darwin-x86_64/Linux-x86_64，没有本机arm64的从零安装入口 |
| 项目依赖 | 无`.venv`/`node_modules`；pytest/alembic/wuji_api 未装；不能据此声称旧测试失败或通过 |
| Docker | CLI29.6.2存在，daemon不可连接；无法枚举持久容器，不将其说成“没有旧容器” |
| PostgreSQL | 默认PATH无psql；libpq18.4客户端存在，5432无响应，未发现postgres进程；本轮未连接任何数据库 |
| 当前运行 | 未发现Wuji常用API/Web/数据库监听；Kubernetes及旧持久资源未核验，不启动Docker/旧平台探测 |

`node scripts/check-toolchain.mjs` 以默认PATH执行失败，原因为 Node26与固定Node24不符；这是环境前置条件，不是业务测试失败。后续选用已核验工具或为新项目提供可复现的独立入口。

## 组件、依赖与验证入口

跟踪路径、未跟踪文件与排除文档/依赖目录的内容检索均未找到 `TopologyFlowCanvas` 或 `@xyflow/react` 实现；正式web manifest和锁也无该依赖。没有MAF运行包；新画布将按P14创建一个正式实现，不以旧spike替代。

旧执行依赖仍有 Cairn 固定SHA和Pi 0.73.0；新Python workspace必须独立锁定和启动。根旧pytest `testpaths` 只有 `apps/api/tests`；新验证必须显式收集 `tests/vnext`、Node Supervisor和正式web/浏览器路径。现有 `check` / `build` 的部分入口指向frontend spike，不能作为新正式web验证。

P00代表命令是 `git status --short`、`git rev-parse HEAD`、`git worktree list`、`git ls-files '*TopologyFlowCanvas*'`、`git grep -n '@xyflow/react'` 与未跟踪/内容补充检索。无匹配的退出码1与未执行分开记录。已核对当前工作树没有v1业务代码/数据迁移；只有文档准备，故不需要将不存在的v1业务表迁为v2。

## 授权与后续

用户明确授权按v2开发、常规可逆修复、本地依赖/无敏感测试环境及本地提交，允许SOL xhigh或GPT-6 xhigh子代理。主代理负责最终集成和验收；当前Default执行已批准方案，不声称自行进入Plan模式。

没有收费目标模型/外部目标、旧部署停机/切换、用户数据删除、推送或发布授权。P00的来源与基线整理完成不代表AC-072完整迁移演练或任何G1—G5通过；这些证据由后续对应任务产生。环境前置缺失由P01/P02处理，不启动全套旧回归。
