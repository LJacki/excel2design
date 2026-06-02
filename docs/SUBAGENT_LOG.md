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

---

（Phase 4 启动后追加）
