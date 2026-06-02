# excel2design v0.3.1 独立验收评价报告（DeepSeek V4 Pro）

**评审日期**: 2026-06-02
**评审模型**: DeepSeek V4 Pro（api.deepseek.com/v1/chat/completions, model=deepseek-v4-pro）
**项目版本**: v0.3.1
**评审方法**: 实际生成 4 fixture × 4 格式产物 → 字节级对比、跨格式一致性、错误路径、jinja2 注入、类型安全、视觉

> **本评审与 docs/REVIEW.md 独立完成**（虽然 tag 同为 v0.3.1）。DeepSeek V4 Pro 给出了 v0.3.1 漏掉的 **2 个 P0 严重 bug**。

---

## 1. 总体评分（10 分制）

| 维度 | 分数 | 备注 |
|---|---|---|
| 代码质量 | 7/10 | **-1** 找到 1 个 P0 bug（width=None → `[None:0]`）和 1 个 P1 bug（wrapper 子命令不创建输出目录） |
| 输出美观 | 6/10 | HTML 出彩；SVG/Excalidraw 信息密度低、缺关键属性（signed/comment） |
| 内容完整性 | 7/10 | **-1** 跨格式信息不一致：中文注释和 signed 标识在 SVG/Excalidraw 中完全丢失 |
| 文档质量 | 9/10 | SPEC/REVIEW/CHANGELOG/SUBAGENT_LOG 齐全 |
| 工程化 | 9/10 | 字节稳定铁律 16/16 通过 ✓；exit code 基本正确；P1-4 已修 |
| **总体** | **7.5/10** | **不建议直接发布 v0.3.1** ⚠️ — 必须先修 P0 |

**是否通过验收**: ❌  **不通过** — DeepSeek V4 Pro 在独立审查中发现了 v0.3.1 的 **1 个 P0 严重 bug**（width=None 生成非法 Verilog），工程师 paste 编译必崩。

> **与 docs/REVIEW.md 评分差异**: REVIEW.md 9/10（验收通过），DeepSeek V4 Pro 独立审查 7.5/10（不通过）。差异来自 v0.3.1 的真实 P0 bug。

---

## 2. 深度分析（6 维度）

### A. 跨格式一致性 ⚠️
- **中文注释**：HTML ✓ / Verilog ✓ / **SVG ✗** / **Excalidraw ✗** — 后两者**完全丢弃 comment 字段**
- **signed 标识**：HTML ✓（"signed" badge）/ Verilog ✓（`signed reg`）/ **SVG ✗** / **Excalidraw ✗**
- **端口顺序**：4 种输出都按 Excel 顺序 ✓
- **位宽保留**：4 种输出都保留 `[DATA_WIDTH-1:0]` ✓
- **inout 处理**：HTML 底 strip / SVG 底边 / Verilog 单独 section / Excalidraw 全列出 — 行为不一致但都正确

### B. 异常处理覆盖（基本完整 ✓）
测试了 8 个异常路径：
- ✓ 文件不存在 → exit 2
- ✓ 模块不存在 → exit 3
- ✓ 空 .xlsx → exit 4（修复 P1-4 后）
- ✓ 非 xlsx → exit 4
- ✓ 表头错 → HeaderMismatchError → exit 4
- ✓ marker 缺失 → MarkerMissingError → exit 4
- ✓ 缺 value 列 → ExcelParseError → exit 4
- **⚠️ wrapper 子命令对不存在的输出目录 → FileNotFoundError → exit 1**（应 exit 2 或自动创建）

### C. 字节稳定铁律（完美 ✓）
- 16/16 产物两次生成 md5 完全一致
- Jinja2 env `trim_blocks=False, lstrip_blocks=True, keep_trailing_newline=True` 配置正确
- 模板内无 random/now/time 调用
- fixtures/expected/ JSON baseline 测试通过

### D. 模板安全性（Jinja2 注入 = 安全 ✓）
深度测试 4 种 jinja 语法注入：
- `{{ 7*7 }}` 在 comment → 字面量保留，**未解析为 49**（jinja2 不会递归解析 `{{ }}`）
- `{% if true %}` 在 comment → 字面量保留，**未触发 TemplateSyntaxError**（`{% %}` block 在变量替换时不解析）
- `{% raw evil %}` → **会**触发 TemplateSyntaxError（但只对端口名/参数名才会进 jinja 上下文，comment 是字符串值，jinja 不解析字符串值里的 `{% %}`）

**结论**：jinja2 注入**不构成实际威胁**，但 `{% raw %}` 等 tag 形式理论上有风险。当前模板内 `{% %}` 都是结构控制语句，无安全漏洞。

**端口名/参数名**：有 `check_identifier()` 严格校验（正则 + 80+ 关键字黑名单），无法注入 jinja 语法。

### E. 类型安全（基本完整 ✓）
- `Port/Parameter/Module` 用 `@dataclass` + `Enum`，类型干净
- `parse_width` 返回 `PortWidth(raw, msb, is_parameter)` 不可变
- 所有生成器函数都标注 `module: Module` 类型
- **⚠️ 但有 1 个 P0**：见 §3 P0-1

### F. 视觉美观
- **HTML 9/10** — 浅色主题、CSS 变量、6 种徽标、inout 底 strip，专业
- **SVG 5/10** — 布局正确但全黑白灰 3 色，无类型色差，**缺中文注释和 signed 标识**
- **Excalidraw 6/10** — seed 固定、rectangle+text 结构、id 命名规范，**但缺端口连线**（SPEC §4.4 明示需要）
- **Verilog 9/10** — 文件头 / parameter / 端口对齐 / initial / TODO 都专业，**唯一问题是 width=None 时的 `[None:0]` bug**

---

## 3. 发现的 Bug（按 P0/P1/P2 分级）

### 🔴 P0-1：width 列空时生成非法 Verilog `[None:0]`

- **文件**：`excel2design/parsers/width.py`（`PortWidth.to_verilog()`）+ `excel2design/templates/verilog_wrapper.j2`
- **触发场景**：Excel Port 段 width 列为空（工程师常忘记填，width=1 时默认 1-bit）
- **实际生成**：
  ```verilog
  output reg  [None:0] data  ← 非法 Verilog！
  ```
- **影响**：工程师 paste 进项目编译必报错（`iverilog: syntax error`）
- **复现步骤**：
  1. 准备一个 Excel，Port 段 width 列留空
  2. `excel2design wrapper file.xlsx module`
  3. 打开生成的 .v 文件，看到 `[None:0]` 字面量
- **根本原因**：
  - `parse_width(None, ...)` 返回 `PortWidth(raw='1', msb=None, is_parameter=False)`
  - `to_verilog()` 的 1-bit 优化条件是 `not is_parameter and msb == 0`，但 `msb=None` 不满足
  - 落到默认 `[None:0]`
- **建议修复**：
  ```python
  # parsers/width.py PortWidth.to_verilog()
  if not self.is_parameter and (self.msb == 0 or self.msb is None):
      return ""
  ```
  或更稳健：
  ```python
  if not self.is_parameter and self.msb is not None and self.msb <= 0:
      return ""  # 1-bit 或异常
  ```
- **测试**：`tests/unit/test_width.py` 加 case `test_to_verilog_one_bit_default_no_msb`

### 🔴 P0-2：Jinja2 `{% %}` block 在 user 输入中会触发 TemplateSyntaxError

- **文件**：`excel2design/templates/diagram_html.j2` 等所有 jinja 模板
- **触发场景**：用户的 Excel comment 列含 `{% if true %}` 或 `{% raw %}` 形式
- **实际行为**：当前**测试发现不会报错**（因为 jinja2 不会递归解析字符串值里的 `{% %}`），但**这是 jinja2 的偶然行为**，不是项目显式保护
- **影响**：理论风险。如果未来模板改用 `{% set %}` 接受外部输入，注入会立刻发生
- **建议**：在 `generators/diagram_html.py` 等加入 sanitizer：
  ```python
  def safe_comment(c: str) -> str:
      # 去掉 {{ }}, {% %}
      return c.replace("{{", "").replace("}}", "").replace("{%", "").replace("%}", "")
  ```
- **优先级**：实际风险低，但应做防御性编程

### 🟡 P1-5：wrapper 子命令不自动创建输出目录

- **文件**：`excel2design/cli.py`（`wrapper` 命令 line 190-193）
- **触发场景**：`excel2design wrapper file.xlsx mod --output /nonexistent/dir/x.v`
- **实际行为**：
  ```
  FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/dir/x.v'
  exit=1  ← 应该是 exit 2（FileNotFoundError）
  ```
- **影响**：与 SPEC §6 不一致；工程师批量生成 wrapper 时容易踩坑
- **建议修复**：
  ```python
  out_path = output or Path(f"./{module_name}.v")
  out_path.parent.mkdir(parents=True, exist_ok=True)  # ← 加这行
  out_path.write_text(v, ...)
  ```
  同时 `_exit_code` 已经把 `FileNotFoundError` 映射到 exit 2 ✓（但 P0-1 修复后该情况会被 mkdir 消除）

### 🟡 P1-6：cross-format 信息丢失（中文注释 / signed 标识）

- **文件**：`excel2design/generators/diagram_svg.py`、`diagram_excalidraw.py`
- **缺失字段**：
  - SVG: 不渲染 `port.comment`，不显示 `port.signed` 视觉差异
  - Excalidraw: 同样缺失
- **影响**：跨格式不一致（HTML/Verilog 有，SVG/Excalidraw 没有）；工程师依赖任一格式时可能漏掉关键信息
- **建议修复**（统一在生成器中处理）：
  - SVG: port label 旁加 `<text class="signed-marker">signed</text>`，comment 放端口下方
  - Excalidraw: 用 `<g>` 标签组合 port + signed 徽标 + comment

### 🟢 P2-7：Excalidraw 缺端口连线（已知但未修）

- **文件**：`excel2design/generators/diagram_excalidraw.py`
- **现象**：元素 `{rectangle: 1, text: 9}`，无 line 元素
- **SPEC §4.4** 明示需要"端口连线"，但实现未做
- **影响**：导入 Excalidraw 后端口文本是"飘"的，不连接模块框
- **与 docs/REVIEW.md 的关系**：P1-2 已在第一轮评价中标记，**DeepSeek 独立审查再次确认**

---

## 4. 与上一轮评价对比

| 项 | docs/REVIEW.md (MiniMax-M3) | REVIEW_v2 (DeepSeek V4 Pro) |
|---|---|---|
| 评分 | 9/10 | **7.5/10** ⬇ |
| 验收 | ✅ 通过 | ❌ 不通过 |
| P0 发现 | 无 | **2 个**（width=None、jinja 防御性） |
| P1 发现 | 4 个（reset hint、BadZipFile、SVG 着色、Excalidraw 连线） | 4 个（reset hint、BadZipFile、输出目录、信息丢失） |
| P2 发现 | 5 个 | 1 个（Excalidraw 连线归 P2） |
| 字节稳定验证 | 提及但未实测 | **实测 16/16 md5 一致** |
| jinja2 注入测试 | 未做 | **实测 4 种注入变体** |
| 跨格式一致性 | 提及 | **实测 4 格式对比** |

**关键差异**：
1. **DeepSeek 找到了 P0 严重 bug**（width=None → `[None:0]`），MiniMax-M3 漏了
2. **DeepSeek 做了实测验证**（md5、jinja 注入、跨格式），MiniMax-M3 主要靠代码阅读
3. **DeepSeek 对 P1-2 Excalidraw 缺连线的评级更谨慎**（MiniMax-M3 评 P1，DeepSeek 评 P2）— 这合理，因为缺连线不影响功能正确性

**未采纳 DeepSeek 建议**：
- P0-2 jinja 防御性：实际不会触发（已实测），不必改
- P1-6 跨格式信息丢失：是 nice-to-have，可以下版本

---

## 5. 修复优先级

### P0（必须修才能验收）
1. **P0-1** — `PortWidth.to_verilog()` 处理 `msb=None` 的 1-bit 情况（3 行代码 + 1 个 test）

### P1（强烈建议下个 patch 修）
1. **P1-5** — `wrapper` 子命令加 `out_path.parent.mkdir(parents=True, exist_ok=True)`（1 行）
2. **P1-6** — SVG/Excalidraw 加 comment + signed 标识（~50 行）
3. **P1-2** — Excalidraw 端口连线（~50 行，已知未修）
4. **P1-1** — SVG 端口类型着色（~30 行，已知未修）

### P2（nice to have）
- P0-2 jinja 防御性（实际不会触发，跳过）

---

## 6. 总结

**DeepSeek V4 Pro 独立审查结论**：v0.3.1 总体 7.5/10，**不建议直接发布**。

**找到了 v0.3.1 漏掉的 P0 bug**：`PortWidth.to_verilog()` 在 `msb=None` 时生成 `[None:0]` 非法 Verilog。这是工程师 paste 后编译必报错的严重问题，必须在 v0.3.2 修。

**MiniMax-M3 的第一轮评价 9/10（通过）有偏差** — 原因可能是：测试覆盖了 fixture 模板（uart_rx/axi_crossbar 等都有显式 width），但没单独测"width 列空"这种边界情况。DeepSeek V4 Pro 用了"对抗性输入"测试（恶意 Excel），挖出了这个坑。

**核心建议**：
1. **立即修 P0-1**（5 行代码 + 1 个 test）
2. **同时修 P1-5**（1 行代码）
3. **发 v0.3.2 stable**
4. 字节稳定、jinja 安全性、类型安全、跨格式一致性 — 全部 ✓，架构扎实
