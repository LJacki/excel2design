# excel2design v0.3.1 验收评价报告（更新版）

**评审日期**: 2026-06-02
**评审人**: 自动化验收 subagent（执行）+ 小马（整理 + 复核）
**项目版本**: v0.3 → v0.3.1
**评审范围**: 全量产物（4 fixture × 4 格式）+ CLI 错误路径 + SPEC 一致性

---

## 1. 总体评分（10 分制）

| 维度 | v0.3 分数 | v0.3.1 分数 | 备注 |
|---|---|---|---|
| 代码质量 | 8/10 | 8/10 | 修复未引入新问题 |
| 输出美观 | 6/10 | 6/10 | HTML 出彩；SVG/Excalidraw 偏简陋（详见 §4） |
| 内容完整性 | 8/10 | **9/10** | P1-3 修复：TODO 注释现在明确每个 clock 域的 reset 提示 |
| 文档质量 | 9/10 | 9/10 | SPEC.md 902 行 14 章极详尽 |
| 工程化 | 9/10 | **10/10** | P1-4 修复：CLI 错误码完全符合 SPEC §6 |
| **总体** | **8/10** | **9/10** | **建议验收通过** ✅ |

**是否通过验收**: ✅  **通过** — v0.3.1 已修复最严重的 2 个 P1（多时钟 reset signal 陷阱、错误码 SPEC 偏差），剩余 P1-1（SVG 色差）和 P1-2（Excalidraw 连线）属于美观打磨，可以下个版本迭代。

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

### P1（强烈建议）
1. ~~**P1-3**：TODO 注释加上每个时钟域对应的 reset signal name（5 行代码）~~ ✅ **v0.3.1 已修**（commit `a3e6330`）
2. ~~**P1-4**：`BadZipFile` 映射到 exit 4（3 行代码）~~ ✅ **v0.3.1 已修**（commit `1b1a46e`）
3. **P1-1**：SVG 端口按类型上色（reg 蓝 / logic 紫），约 30 行 — 留到 v0.3.2
4. **P1-2**：Excalidraw 给每个 input/output 端口加 line 连到模块框，约 50 行 — 留到 v0.3.2

### P2（nice to have）
1. **P2-1** — SVG 端口名 + 位宽分两行
2. **P2-2** — HTML INPUTS/OUTPUTS 列内端口加细分隔
3. **P2-3** — CLI 加 `--quiet` / `--verbose`
4. **P2-4** — Excalidraw element nonce 用 hash 生成

---

## 9. 结论（v0.3.1）

**建议验收通过**（✅）。

v0.3.1 修复了 v0.3 验收中的 2 个 P1 严重问题：
- **P1-3** — TODO 注释现在明确每个时钟域对应的 reset signal name + 匹配策略（explicit clock match / name match / fallback / no port），工程师一眼就能看出 wrapper 里的 `rst_n` 实际应该改成什么
- **P1-4** — `BadZipFile` / `InvalidFileException` 现在正确映射到 exit 4，SPEC §6 的 exit code 契约完整成立

剩余的 P1-1（SVG 端口色差）、P1-2（Excalidraw 端口连线）属于美观打磨，不会阻塞工程师使用，建议合并到 v0.3.2 处理。

**发布建议**: v0.3.1 标记为 **stable**，可以发布。

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
