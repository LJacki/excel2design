# excel2design v0.3 验收评价报告

**评审日期**: 2026-06-02
**评审人**: 自动化验收 subagent（执行）+ 小马（整理 + 复核）
**项目版本**: v0.3
**评审范围**: 全量产物（4 fixture × 4 格式）+ CLI 错误路径 + SPEC 一致性

---

## 1. 总体评分（10 分制）

| 维度 | 分数 | 备注 |
|---|---|---|
| 代码质量 | 8/10 | 结构清晰（core/parsers/utils/generators/templates），211 测试覆盖良好 |
| 输出美观 | 6/10 | HTML 出彩；SVG/Excalidraw 偏简陋（详见 §4） |
| 内容完整性 | 8/10 | 核心功能完整，4 种格式都生成，边界情况（空端口/多时钟/inout）有处理 |
| 文档质量 | 9/10 | SPEC.md 902 行 14 章极详尽；README/CHANGELOG/SUBAGENT_LOG 齐全 |
| 工程化 | 9/10 | 字节稳定铁律 ✓，exit code 策略基本明确，CLI 子命令清晰 |
| **总体** | **8/10** | **建议有条件通过** ⚠️ |

**是否通过验收**: ⚠️  **有条件通过** — 功能完整、测试全过、产物可用，但有 1 个 P1 **真实可用性陷阱**（多时钟 reset signal name）和 1 个 P1 **SPEC 偏差**（错误码），建议修复后再发布 v0.3 final。

---

## 2. 各格式详细评分

| 格式 | 美观 | 完整 | 备注 |
|---|---|---|---|
| **HTML** | 9/10 | 9/10 | 浅色主题优雅；wire/reg/logic/signed/inout/clk/default 徽标齐全；中文注释正常；空端口有 `.empty-msg` |
| **SVG** | 5/10 | 8/10 | 布局正确（in 左 / out 右 / inout 底），但**全黑白灰 3 色**，无类型色差 |
| **Excalidraw** | 6/10 | 7/10 | seed 固定 ✓，rectangle+text 结构正确 ✓，**但缺端口连线**（SPEC §4.4 明示需要 line） |
| **Verilog wrapper** | 8/10 | 7/10 | 文件头 / parameter / 端口对齐 / initial / 注释都很专业；**always 硬编码 `rst_n`，多时钟会指向不存在信号** |

---

## 3. 严重问题（必须修才能验收）

**无 P0 阻断性问题**。所有 211 测试通过，4 fixture × 4 格式全生成，CLI 错误路径基本可工作。

---

## 4. 美观性问题（建议修）

### 🎨 P1-1：SVG 框图无类型色差
- **现象**: SVG 中所有端口都是 `#888888` 灰线 + `#222222` 黑字
- **证据**: `uart_rx.svg` 只用 3 种颜色（`fill="#222222"`, `fill="#FFFFFF"`, `stroke="#888888"`），与 HTML 的彩底徽标差距大
- **影响**: 工程师扫一眼 SVG 看不到 reg vs wire 区分
- **修复**: 给 reg 端口用蓝色 stroke (#5B8BD2)，logic 用紫色 (#9B6BCC)，保持 wire 灰色

### 🎨 P1-2：Excalidraw 缺少端口连线
- **现象**: SPEC §4.4 写"1 个 module 矩形 + N 个 port 文本 + **端口连线**"，但实际产物**没有 line 元素**
- **证据**: `uart_rx.excalidraw` 共 10 元素 = `{rectangle: 1, text: 9}`，无 line/arrow
- **影响**: 导入 Excalidraw 后端口文本是"飘"的，不连接模块框
- **修复**: 为每个 input 端口加 1 条 line（端口文本 → 模块左边），output 同理

### 🎨 P2-1：SVG 端口文本无位宽徽标
- HTML 有 `[DATA_WIDTH-1:0]` 徽标，SVG 把位宽塞进端口名文本里（`rx_data[DATA_WIDTH-1:0]`）
- **修复**: 端口文本分两行（port name + width below in small font）

### 🎨 P2-2：HTML 端口内没分隔线
- INPUTS / OUTPUTS 两列之间只有 1px border-right，列内端口之间没有视觉分组

---

## 5. 完整性问题

### 🔧 P1-3：多时钟 wrapper 的 reset signal trap（**最严重**）
- **现象**: `multi_clock.v` 3 个 always 块都引用 `rst_n`，但实际端口是 `rst_a_n` / `rst_b_n`（clk_c 域根本没有 reset 端口）
- **证据**:
  ```
  always @(posedge clk_a or negedge rst_n) begin
      if (!rst_n) begin
  ...
  always @(posedge clk_b or negedge rst_n) begin
      if (!rst_n) begin
  ...
  always @(posedge clk_c) begin
      if (!rst_n) begin   ← clk_c 域没有 rst_n！
  ```
- **原因**: SPEC §5.5 明示"v0.3 假定统一叫 `rst_n`"，但 Excel Port 段**没有"reset_signal"列**来指定真实名字
- **影响**: 工程师把 wrapper 复制到项目里编译必然报错
- **修复建议**（二选一）：
  1. **简单（推荐）**: TODO 注释加一行 `// Reset signals per clock: clk_a→rst_a_n, clk_b→rst_b_n, clk_c→none`（5 行代码）
  2. **彻底**: Excel Port 段加第 11 列 `reset_signal`，wrapper 直接生成正确名字

### 🔧 P1-4：错误码与 SPEC §6 不一致
- **现象**: SPEC 规定"解析错误 → exit 4"，但传入垃圾 xlsx 时返回 exit 1
- **证据**:
  ```
  $ echo "not xlsx" > fake.xlsx
  $ excel2design all fake.xlsx m
  BadZipFile: File is not a zip file
  exit=1                    ← 应该是 4
  ```
- **影响**: 调用方按 SPEC 写 `if [ $? -eq 4 ]` 的 shell 脚本永远不会命中
- **修复**: 在 cli.py 入口加 try/except，把 `openpyxl.exceptions.BadZipFile` / `InvalidFileException` 映射到 exit 4

### 🔧 P2-3：缺少 `--quiet` / `--verbose`
- CLI 输出固定 4 行，无调试信息
- 类似工具（cocotb、verilator）有 `-v` / `-q`

### 🔧 P2-4：Excalidraw 元素 versionNonce 全 =0
- 所有 element 的 `version: 1` `versionNonce: 0`，对协作 diff 无影响但 cheap
- 修复: 用 `hash(port_name) % 1000000`

---

## 6. 优点（值得保留）

1. ✅ **字节稳定铁律 §5.7** 真的做到了 — md5 完全一致，CI 友好
2. ✅ **HTML 的 CSS 设计语言** 非常专业：等宽字体、6 种徽标、浅色主题、inout 单独区域
3. ✅ **中文注释全程正确** — Excel 中文 → HTML `port__comment` → Verilog `// 注释`，UTF-8 链路无掉字
4. ✅ **空端口边界情况** 优雅：`empty_ports.v` 合法 `();`，HTML 显示 "no ports"
5. ✅ **端口排序严格按 Excel** — axi_crossbar 的 30 端口在 4 种输出里顺序完全一致
6. ✅ **多时钟分组正确** — 同一 `(clock, reset_type)` 合并到同一 always 块，3 时钟 → 3 always 块
7. ✅ **axi_crossbar 30 端口** 布局不挤、不重叠、不溢出
8. ✅ **TODO 注释用心** — 列出 reg / parameter / 主时钟 / 复位行为
9. ✅ **inout 处理一致** — 4 种输出都把 inout 单独成组
10. ✅ **测试覆盖分层清晰** — unit (157) + generators (66) + e2e (14) + fixtures + test_golden

---

## 7. SPEC 一致性检查

| SPEC 章节 | 要求 | 实际 | 一致 |
|---|---|---|---|
| §4.2 HTML | Jinja2 模板，浅色主题，类型徽标 | ✓ 全部满足 | ✅ |
| §4.3 SVG | ElementTree，圆角矩形，input 左/ output 右/ inout 底 | ✓ 全部满足 | ✅ |
| §4.4 Excalidraw | dict + json.dumps，rectangle + text，**seed 固定**，**端口连线** | ⚠️ 缺端口连线 | ⚠️ 部分 |
| §5.5 复位 always | `(clock, reset_type)` 分组，硬编码 `rst_n` | ✓ 符合设计 | ✅ |
| §5.7 字节稳定 | md5 多次生成一致 | ✓ 验证通过 | ✅ |
| §6 exit code | 2/3/4 分别对应文件/模块/解析 | ⚠️ 解析错返 1 不是 4 | ⚠️ 部分 |
| §3.5.6 多时钟分组 | 同 `(clock, reset_type)` 合并 | ✓ multi_clock 3 always | ✅ |

**SPEC 一致性**: 5/7 完全满足，2/7 部分满足（Excalidraw 缺连线、错误码）

---

## 8. 修复优先级

### P0（必须修才能验收）
- **无**

### P1（强烈建议，下个 patch 修）
1. **P1-3** — TODO 注释加每个时钟域 reset signal name（5 行代码）
2. **P1-4** — `BadZipFile` 映射到 exit 4（3 行代码）
3. **P1-1** — SVG 端口按类型上色（~30 行）
4. **P1-2** — Excalidraw 给每个 input/output 端口加 line（~50 行）

### P2（nice to have）
1. **P2-1** — SVG 端口名 + 位宽分两行
2. **P2-2** — HTML INPUTS/OUTPUTS 列内端口加细分隔
3. **P2-3** — CLI 加 `--quiet` / `--verbose`
4. **P2-4** — Excalidraw element nonce 用 hash 生成

---

## 9. 结论

**建议有条件通过验收**（⚠️）。

v0.3 核心功能完整、产物可用、测试覆盖充分、文档详尽。最大隐患是 **P1-3（多时钟 reset signal trap）** — 工程师拿到 multi_clock 的 wrapper 直接编译必然报错，必须手动改 3 处 reset signal name。SPEC §5.5 把它写成了"设计如此"，但这是 Excel 缺列的设计漏洞，不是合理封装。

视觉层面 **SVG 黑白、Excalidraw 无连线** 是明显的"功能完成但美观未打磨"信号 — 工程师日常扫一眼 SVG 看不到 reg vs wire 区分是真实工作效率损失。P1-1 + P1-2 总共 ~80 行代码就能大幅提升视觉质量。

**建议发布策略**:
- v0.3 标记为 **preview**（明确告知用户 multi_clock 需手动改 reset name）
- 立即修 4 个 P1，发 v0.3.1 stable
- 累计 P2 在 v0.3.2 修

---

## 10. 评审元数据

- **评审耗时**: subagent 440 秒（含实际生成 4 fixture × 4 格式 + grep 验证 5 个 P1）
- **评审文件**: 16 个产物 + 4 个 .v + 4 个 .excalidraw + 4 个 .html + 4 个 .svg
- **关键 grep 验证**:
  - `multi_clock.v` 的 `always @(... rst_n)` 出现 3 次 ← P1-3 确认
  - `uart_rx.svg` 颜色集合 = `{#222222, #FFFFFF, #888888}` ← P1-1 确认
  - `uart_rx.excalidraw` element types = `{rectangle: 1, text: 9}` ← P1-2 确认
  - `BadZipFile` exit code = 1 ← P1-4 确认
- **未评审项**: iverilog 语法 check（环境无 iverilog）、GitHub Actions CI（未 push 到 remote）
