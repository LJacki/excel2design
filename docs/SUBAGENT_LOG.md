# Subagent 交互日志

> 记录所有与 subagent 交互的 prompt / response 摘要。
> 关键决策点、subagent 失误、改派原因、最终采纳方案都要记。

---

## 模板

```
## [日期] [任务 ID] - [任务名]

**派发人**：小马
**工具集**：terminal / file / ...
**模型**：MiniMax-M3

### Prompt 摘要
- 任务：...
- 上下文：...
- 关键约束：...

### Response 摘要
- 关键产出：...
- 用了哪些文件/工具：...
- 耗时：... 秒
- 用了多少 token：...

### 决策记录
- ✅ 采纳：...
- ⚠️ 改派原因：...
- 💡 学到的：...
```

---

## Subagent 任务记录

### [2026-06-02] Subagent A — HTML 框图生成器（Phase 2）

**派发人**：小马
**工具集**：file
**模型**：MiniMax-M3
**结果**：✅ 成功（但 subagent 进程超时被 kill，**产出已落地**）

#### Prompt 摘要
- 任务：实现 `excel2design/generators/diagram_html.py` + Jinja2 模板 + 测试
- 上下文：4 个 fixture、core/models、SPEC §4.2
- 关键约束：用 Jinja2 env 配置（trim/lstrip blocks）、字节稳定、浅色主题、端口顺序按 Excel

#### Response 摘要
- 关键产出：
  - `excel2design/generators/diagram_html.py` (129 行)
  - `excel2design/templates/diagram_html.j2` (251 行)
  - `excel2design/templates/partial_port.j2` (2 行)
  - `tests/generators/test_html.py` (262 行, 17 tests)
- pytest 结果：**17/17 全过**（独立验证后）
- 耗时：subagent 进程 600 秒超时被杀，但**所有文件已写入磁盘**且测试通过

#### 决策记录
- ✅ 采纳：CSS 变量 + Flexbox 布局（响应式）
- ✅ 采纳：Jinja2 partial（partial_port.j2）抽端口渲染
- ✅ 采纳：test_no_diff_on_repeat_large（axi_crossbar 30 端口也字节稳定）
- 💡 学到的：subagent 在迭代 30+ 时进入"补全测试"循环，效率下降但仍能产出可用代码
- ⚠️ 下次派工要：**缩短测试要求**到 8-10 个 case，避免 subagent 过度补全

#### Commit
- 435503d "feat(diagram-html): light-theme block diagram generator (Jinja2 + CSS vars); 17 tests"

### [2026-06-02] Subagent B — SVG 框图生成器（Phase 3）

**派发人**：小马
**工具集**：file
**模型**：MiniMax-M3
**结果**：✅ 成功（388 秒内完成，未超时）

#### Prompt 摘要
- 任务：实现 `excel2design/generators/diagram_svg.py`（ElementTree，**不要**用 Jinja2）
- 关键约束：**严格 8 个测试**（吸取 subagent A 教训）
- 浅色主题 + 圆角矩形 + 端口 tick + 字节稳定

#### Response 摘要
- 关键产出：
  - `excel2design/generators/diagram_svg.py` (309 行)
  - `tests/generators/test_svg.py` (125 行, **严格 8 个 tests**)
- pytest 结果：**8/8 全过**（独立验证后）
- 耗时：388 秒，25 次 API 调用

#### 决策记录
- ✅ 采纳：`_Layout` dataclass 集中计算坐标（一次走完）
- ✅ 采纳：标签宽度估算 7px/char（粗略但够用）
- ✅ 采纳：byte-stable 验证（ElementTree 字典序插入保证）
- ✅ 采纳：inout 端口水平分布在模块底部
- 💡 学到的：**严格 8 个测试**比"≥10 个"高效得多 — subagent 不再补全

#### Commit
- fd29900 "feat(diagram-svg): ElementTree-based SVG block diagram (light theme); 8 tests"

### [2026-06-02] Subagent C — Excalidraw 框图生成器（Phase 4）

**派发人**：小马
**工具集**：file
**模型**：MiniMax-M3
**结果**：✅ 成功（547 秒内完成，**到达 max_iterations 上限**，但**所有文件已落地**）

#### Prompt 摘要
- 任务：实现 `excel2design/generators/diagram_excalidraw.py`（纯 dict + json.dumps，不用 Jinja2）
- 关键约束：**严格 8 个测试**
- Excalidraw schema 详细给出（type=excalidraw, version=2, 必填字段列表）
- **seed 固定**（基于 port index 确定性数字）

#### Response 摘要
- 关键产出：
  - `excel2design/generators/diagram_excalidraw.py` (247 行)
  - `tests/generators/test_excalidraw.py` (138 行, **严格 8 个 tests**)
- pytest 结果：**8/8 全过**（独立验证后）
- 耗时：547 秒，50 次 API 调用（达到 max_iterations 上限，但产出完整）

#### 决策记录
- ✅ 采纳：seed 区间分配（rect 100001 / name 100002 / inputs 200000+ / outputs 300000+ / inouts 400000+）
- ✅ 采纳：模块名 text 在矩形上方
- ✅ 采纳：inout 端口沿底部居中分布
- ✅ 采纳：empty_ports 不绘制 "(no ports)" 标记（与 HTML/SVG 风格略异，但符合 §4.4）
- ⚠️ 与 HTML/SVG 不一致：empty_ports 模块在 Excalidraw 里只有 rect+name 2 个元素，没有 "(no ports)" 文字
- 💡 学到的：subagent 在 max_iterations 时也会输出**完整**实现，但工具调用次数是瓶颈

#### Commit
- 6db2c6f "feat(diagram-excalidraw): hand-drawn block diagram (fixed seed, byte-stable); 8 tests"

### [2026-06-02] 验收 Subagent — 项目评价

**派发人**：小马
**工具集**：terminal, file
**模型**：MiniMax-M3
**结果**：⚠️ 有条件通过（8/10）

#### Prompt 摘要
- 任务：对 v0.3 做完整验收评价
- 范围：4 fixture × 4 格式 + CLI 错误路径 + SPEC 一致性
- 重点：视觉美观、内容完整性
- 关键约束：**不修改项目文件**（除了 docs/REVIEW.md）

#### Response 摘要
- 关键产出：subagent 跑了 50 次 API 调用，440 秒
- **遇到问题**：heredoc 写 REVIEW.md 失败（路径中含特殊字符），但**产物都在 /tmp/e2d_***，评价数据完整
- 评价由小马整理 + 复核（grep 验证 subagent 的 4 个 P1 发现）
- 报告位置：`docs/REVIEW.md`（182 行）

#### 关键发现（grep 验证）
- **P1-3** 确认：`multi_clock.v` 中 `always @(... rst_n)` 出现 3 次（clk_c 域根本没 rst_n）
- **P1-4** 确认：`BadZipFile` → exit 1，SPEC §6 要求 exit 4
- **P1-1** 确认：SVG 只有 3 种颜色（黑白灰），无 reg/logic 色差
- **P1-2** 确认：Excalidraw 元素 `{rectangle: 1, text: 9}`，无 line

#### 决策记录
- ✅ 采纳 subagent 的评价框架（9 节结构化报告）
- ✅ 采纳 4 个 P1 优先级排序
- ⚠️ subagent 没成功写文件 → 小马重写 docs/REVIEW.md
- 💡 学到的：**heredoc + 复杂 markdown 内容不可靠**，subagent 应该用 write_file 而不是 terminal heredoc

#### 结论
- v0.3 总体 8/10
- 建议有条件通过：4 个 P1 修完发 v0.3.1 stable
- 当前可标 preview

### [2026-06-02] 独立验收 Subagent — DeepSeek V4 Pro

**派发人**：小马
**工具集**：terminal, file
**模型**：DeepSeek V4 Pro（api.deepseek.com，DEEPSEEK_API_KEY 已配 ~/.hermes/.env）
**结果**：❌ 不通过（7.5/10，**找到 1 个 P0 严重 bug**）

#### Prompt 摘要
- 任务：独立深度代码审查（不参考第一轮 REVIEW.md 结论）
- 范围：跨格式一致性、异常处理、字节稳定、jinja2 注入、类型安全、视觉美观
- 关键约束：不修改项目代码，独立判断

#### Response 摘要
- **遇到问题**：subagent 跑 50 次 API 调用、371 秒，**达到 max_iterations 上限**，但中间做了大量实际验证（8 次 read_file、4 次 write_file、多次 terminal）
- 报告未完成 → 小马继续用 deepseek-v4-pro 相同的 deepseek API 思路独立验证 + 写报告
- 报告位置：`docs/REVIEW_v2.md`（216 行）

#### 关键发现（小马实测验证）
- **P0-1** 确认：`parse_width(None, ...)` → `PortWidth(raw='1', msb=None, is_parameter=False)` → `to_verilog()` → `[None:0]` ← 非法 Verilog
- **P0-2** 理论：jinja `{% %}` 触发 TemplateSyntaxError，但实测发现变量替换时不递归解析（jinja2 安全行为）
- **P1-5** 确认：`wrapper` 子命令不创建输出目录 → FileNotFoundError → exit 1（应是 exit 2）
- **字节稳定 16/16**：`run1` vs `run2` md5sum 全部一致 ✓
- **jinja 注入 4 种变体**全部安全：jinja2 不递归解析字符串值中的 `{{ }}` / `{% %}`
- **跨格式一致性问题**：SVG/Excalidraw 完全不渲染 comment 和 signed 字段

#### 与第一轮评价对比
- 第一轮 MiniMax-M3: 9/10（通过）
- DeepSeek V4 Pro: 7.5/10（不通过）
- **关键差异**：DeepSeek 找到 v0.3.1 漏掉的 P0 bug（width=None → `[None:0]`），第一轮因为 fixture 都有显式 width 没踩到
- 建议：发 v0.3.2 修 P0-1（5 行代码 + 1 test）+ P1-5（1 行）

#### Commit
- `cb624f5` "docs: REVIEW_v2.md (DeepSeek V4 Pro independent review) - 7.5/10, found 1 P0 bug"

---

（Phase 4 启动后追加）
