# P08 versioned memory input focused fix

状态：定向单元行为通过；完整 P08 仍为 `not_run/未验证`。测试运行时基线 HEAD 为 `00bc81432a74bcdda5c9a21295634cf995d46a00`，Worker 七路径在该 HEAD 与 SOURCE_ONLY `65e44725ecb62352f4d599495847c12fa388048c` 间无差异。测试时的 production/test working-tree 内容随后未改动地提交为 `255d319eb5334a047238c7e8313d277d6bd37f22`；精确文件摘要见 [binding.json](binding.json)。

生产 RED 已到达 `PinnedMemoryContextProvider.before_run`：它把一个 JSON `str` 直接传给 `Message.contents`，公开 MAF `Message` 将字符串按字符解释为 content 序列，读取 `Message.text` 时得到字符间带空格的损坏 JSON。更早一次失败是测试未给公开 `SessionContext` 的必需 `input_messages`，属于 fixture 修正，不登记为产品 finding。

修复只把完整 JSON 文本包装为一个 content 项。定向 GREEN 为 `1 passed, 1 warning in 0.87s`；warning 是固定 SDK 对 `AgentFileStore` 的 experimental 状态，未隐藏。用例还确认 provider 只注入完整版本化文本，不增加 tools/instructions/model client，并在同一固定 state 下内容变化时拒绝。

- [生产 RED 人工摘录/摘要](red.txt)
- [定向 GREEN 可见输出人工转录](green.txt)
- [代码与测试绑定](binding.json)

`red.txt` 不是 shell 重定向保存的原始完整 stdout，而是从当时可见工具输出人工转录的摘录；pytest 自身还显示 `Full output truncated (10 lines hidden)`，未保留那 10 行的原始流文件。`green.txt` 同样是完整可见输出的人工转录，不冒充原始流。没有为补文档而重跑。

本检查没有执行 SDK 模型请求、ToolGate、Host、PostgreSQL、HTTP、浏览器或 capability 发布；没有 HTTP 报文。它只证明“版本化记忆输入/保存恢复”中的输入适配层，不证明自动记忆学习或原生 Harness FileMemoryProvider。
