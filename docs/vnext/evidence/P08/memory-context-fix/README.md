# P08 versioned memory input focused fix

状态：定向单元行为通过；完整 P08 仍为 `not_run/未验证`。基线 HEAD 为 `00bc81432a74bcdda5c9a21295634cf995d46a00`，Worker 七路径在该 HEAD 与 SOURCE_ONLY `65e44725ecb62352f4d599495847c12fa388048c` 间无差异；修复和测试为未提交 dirty diff。

生产 RED 已到达 `PinnedMemoryContextProvider.before_run`：它把一个 JSON `str` 直接传给 `Message.contents`，公开 MAF `Message` 将字符串按字符解释为 content 序列，读取 `Message.text` 时得到字符间带空格的损坏 JSON。更早一次失败是测试未给公开 `SessionContext` 的必需 `input_messages`，属于 fixture 修正，不登记为产品 finding。

修复只把完整 JSON 文本包装为一个 content 项。定向 GREEN 为 `1 passed, 1 warning in 0.87s`；warning 是固定 SDK 对 `AgentFileStore` 的 experimental 状态，未隐藏。用例还确认 provider 只注入完整版本化文本，不增加 tools/instructions/model client，并在同一固定 state 下内容变化时拒绝。

- [生产 RED](red.txt)
- [定向 GREEN](green.txt)

本检查没有执行 SDK 模型请求、ToolGate、Host、PostgreSQL、HTTP、浏览器或 capability 发布；没有 HTTP 报文。它只证明“版本化记忆输入/保存恢复”中的输入适配层，不证明自动记忆学习或原生 Harness FileMemoryProvider。
