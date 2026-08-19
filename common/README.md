# common：两期共用规范

只放**一期与二期都要遵守**的东西。任何只服务一条流水线的文档都不该在这里。

| 文件 | 作用 | 谁用 |
|---|---|---|
| `MATH-WRITING-GUIDE.md` | 数学写作范式（Halmos / Tao / Evan Chen 归纳） | 一期写手提示词特调 ＋ 二期块写手/拼接器 |
| `ASK-HUMAN-CONVENTION.md` | agent 向人提问时的大白话规范（不许甩术语） | 两期所有会向人提问的 agent |
| `AGENT_HARNESS.md` | DSH 角色行/派发机制说明 | 两期 operator |
| `PRETEST-RUNS.md` | 预测试产物落盘约定：一律进 `runs/pretest/`，git 只留结论 | 两期 |
| `TECH-ROADMAP.md` | 跨期技术路线 | 两期 |

## 两条铁律（两期通用）

**1. 派发必须走 preset 角色行。**
角色行是 route / 预算 / 工具锁的唯一执行真相。通用 `workflow` / `subagent` 派发会丢掉全部三样——`workflow` 的 `agent()` 连 `maxTokens` 选项都不存在，所以"reasoning 计入 maxTokens，重推理模型给 65536"这条教训在那条路径上**表达不出来**。
明文依据：`phase1-ab-eval/contracts/EXECUTION_CONTRACT.md` §7。

**2. agent 只回文本，operator 落盘。**
写手/判官/块写手都是零工具角色（`toolFilter.allow: []`），**物理上不可能自己写文件**——这是闭卷设计的必然结果，不是缺陷。想让 agent 自己落盘就得换成有工具的通用 agent，那等于同时破坏铁律 1 和闭卷性。

## 模型自述不算证据

2026-08-17 的记录：探针问 deepseek-v4-flash "你有什么工具"，它**编了一个工具列表**；但子会话真实事件流里 `tool_call_events_in_child_session: 0`，系统提示中也确实没有工具定义。

所以工具锁的硬依据是 **mount-validated 的 preset 配置 ＋ 子会话事件流**，不是模型说了什么。
