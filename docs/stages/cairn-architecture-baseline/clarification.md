# 架构后续澄清：Task 主体与 Cairn 核心边界

- 状态：approved / 2026-09-11用户最终确认单Task Pod双容器，并授权更新Spec/Plan后开始开发；实现证据按新阶段记录。
- 修订基准：eee81b4746a27cba633769c3cdf0fcdf60198028。原944e95b文档检查及旧验收事实保留，只适用于当时版本。
- 用户已明确：Task是完整业务主体，统筹目标/起点/终点、场景、工具、约束、模型预算和外部执行控制；Cairn Project是其探索上下文。Cairn黑板核心不改，适配集中于Dispatcher/Worker/模型/工具与平台外围。
- 已明确的执行粒度：多个Agent在同一个Agent执行容器中运行，共用同一Kali执行容器；最终选定一个Task Pod、agent和kali两个容器；agent容器动态运行多个Agent。双Pod及单容器方案均不作为首版。

## 已确认的内容修订

1. 保留Wuji Task及业务标识；不把Task改成仅有origin/goal的Cairn别名，也不维护面向用户的第二套任务编辑流程。
2. 不修改Cairn Server、数据库、Fact/Intent/Hint和原生读写/完成协议；删除上一版要求核心新增外部Task字段、停止态创建、幂等回执及事务事件的条款。
3. 未启动任务由外部执行许可和所有Dispatcher派发入口共同阻止执行，不依赖修改Cairn默认active状态。响应丢失先核对，不能承诺原生没有的幂等/事件保证。
4. 工作文件通过共享Kali目录和MCP直接交接；正式证据/报告/长期归档再登记Artifact。每Agent工作目录与共享目录分开，Artifact上传不成为日常文件协作前提。
5. Runtime attempt解释为执行环境代次；Kali重建/重新初始化并重新授权时产生新代次，普通工具调用或Agent重启不自动增加。

## 已确认的部署取舍

单Pod多容器可以保留Agent/Kali的进程、文件和凭据分离，并简化整体资源所有权；同Pod共享网络，原生NetworkPolicy不能按容器分别设置出网规则。单Pod方案已被确认，Pod生命周期由Task Runtime Controller唯一拥有，Cairn只在Agent容器中创建会话/子进程；不能让两个后端分别创建/删除同一个Pod。

元刃原件中的runtime进程、端口和共享文件观察说明工具环境共用，不能据此判断Agent所在Pod；原件缺少Pod完整容器清单及Agent部署证据。原文“分离架构”还用于指Prompt-Model解耦，不能当成两个Pod的证明。

本轮仍仅文档整理和只读资料核对，无安装、构建、业务测试、模型调用、迁移或部署；原预算与历史验收不变。本澄清不是运行验收；后续开发见[执行基础Spec](../phase-1c-runtime-foundation/spec.md)。
