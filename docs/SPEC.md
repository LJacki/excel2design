# excel2design — 设计规格书

> 版本: v0.2
> 最后更新: 2026-06-01
> 状态: Jack 已确认核心设计，进入实现阶段

---

## 1. 概述

### 1.1 目标
提供一个从 Excel 模块端口表 → (标准/手绘) 框图 + Verilog wrapper 的自动化工具集。

### 1.2 核心价值
- 数字IC工程师在 Excel 中维护模块端口表（已是主流工作流）
- 一键生成三种框图（HTML/SVG/Excalidraw）+ Verilog wrapper 骨架
- 减少手工编写 wrapper 的机械工作和出错可能
- 框图与代码保持单一事实源（Excel）

### 1.3 不在范围（Non-goals）
- ❌ 不生成任何功能性 RTL 逻辑
- ❌ 不解析已有 Verilog 文件反向生成 Excel
- ❌ 不支持 Excel 公式、合并单元格、跨 sheet 引用
- ❌ 不做 lint、CDC 检查、综合 — 这些是 EDA 工具的活
- ❌ v0 不支持 SystemVerilog interface/class（只到 module + port 级别）

---

## 2. Excel 模板规范

### 2.1 文件格式
- `.xlsx`（openpyxl 默认）
- 单个文件 = 一个项目（可包含多个模块）
- 每个模块独立 sheet，sheet 名 = 模块名

### 2.2 Sheet 命名规则
- **模块 sheet**：`{module_name}` — 例 `uart_rx`, `axi_crossbar`
- 每个 sheet 是**两段式**布局：顶部 parameter 段 + 端口段，中间用 marker 行分隔

**约定**：
- 一个 sheet 一个模块
- sheet 名即为模块名，必须是合法 Verilog identifier
- 不再使用 `@parameters` 这种文件级共享 sheet（v0.2 起参数归各模块所有）

### 2.3 两段式布局

每个模块 sheet 的行结构：

```
# === PARAMETERS ===          ← marker 行（# 开头，注释）
name | value | width | param_type | comment
...parameters...

# === PORTS ===               ← marker 行
name | direction | width | type | default | clock | reset_type | signed | interface | comment
...ports...
```

**Marker 行**：
- `# === PARAMETERS ===` / `# === PORTS ===`
- 以 `#` 开头，表示段分隔
- 解析器看到这个 marker 切到对应段
- 两个 marker 都必须存在（即使其中一个为空段）
- 两段之间可空任意行

### 2.4 Parameter 段列定义（5 列）

| 列 | 字段 | 必填 | 缺省 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | — | parameter 名，合法 Verilog identifier |
| B | `value` | ✅ | — | 默认值（int 或表达式，如 `ADDR_WIDTH-1`） |
| C | `width` | ❌ | 空 | 位宽（int），空=无位宽（局部参数风格） |
| D | `param_type` | ❌ | `parameter` | `parameter` / `localparam` |
| E | `comment` | ❌ | 空 | 说明 |

### 2.5 Port 段列定义（10 列）

| 列 | 字段 | 必填 | 缺省 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | — | 端口名，合法 Verilog identifier |
| B | `direction` | ✅ | — | `input` / `output` / `inout`（大小写不敏感） |
| C | `width` | ❌ | `1` | 位宽，int 或表达式（如 `DATA_WIDTH`、`DATA_WIDTH*2`） |
| D | `type` | ❌ | 见下 | `wire` / `reg` / `logic` |
| E | `default` | ❌ | 空 | reg 的 reset 默认值（`1'b0`、`8'hFF`、`{DATA_WIDTH{1'b0}}`） |
| F | `clock` | ❌ | 空 | 关联时钟名（仅 reg 用） |
| G | `reset_type` | ❌ | `sync` | reg 复位行为：`sync` / `async` / `none` |
| H | `signed` | ❌ | `0` | `1` = signed 端口，wrapper 会加 `signed` 关键字 |
| I | `interface` | ❌ | `0` | `1` = interface 风格端口（v0 仅记录，不做特殊处理） |
| J | `comment` | ❌ | 空 | 端口说明 |

**`type` 字段缺省推断规则**（不变）：
- `output` + 无 type → `reg`
- `input` + 无 type → `wire`
- `inout` + 无 type → `wire`

**`reset_type` 语义**：
- `sync` — 同步复位（always 块中 `if(rst_n)` 风格）
- `async` — 异步复位（敏感列表含 `posedge clk or negedge rst_n`）
- `none` — 无复位行为（不需要 reset 块）

**特殊行约定**：
- 第一行（紧跟 marker）是表头
- 之后每行一条记录
- 整行空白 → 跳过
- `#` 开头 → 注释行，跳过
- `reset_type` 不适用 wire/inout，填什么值都会被忽略

### 2.6 完整样例 Excel（v0.2）

**Sheet: `uart_rx`**（单 sheet 示例）
```
# === PARAMETERS ===
name            | value | width | param_type | comment
DATA_WIDTH      | 8     | 32    | parameter  | 数据位宽
FIFO_DEPTH      | 16    | 32    | parameter  | FIFO 深度
CLK_FREQ_MHZ    | 100   | 32    | parameter  | 时钟频率(MHz)

# === PORTS ===
name        | direction | width      | type | default                     | clock | reset_type | signed | interface | comment
clk         | input     | 1          | wire |                             |       |            | 0      | 0         | 系统时钟
rst_n       | input     | 1          | wire |                             |       |            | 0      | 0         | 异步低有效复位
rx_pad      | input     | 1          | wire |                             |       |            | 0      | 0         | 串行输入
baud_tick   | input     | 1          | wire |                             |       |            | 0      | 0         | 波特率 tick
rx_data     | output    | DATA_WIDTH | reg  | {DATA_WIDTH{1'b0}}          | clk   | async      | 0      | 0         | 接收数据
rx_valid    | output    | 1          | reg  | 1'b0                        | clk   | async      | 0      | 0         | 接收有效
fifo_full   | output    | 1          | reg  | 1'b0                        | clk   | async      | 0      | 0         | FIFO 满
fifo_data   | output    | DATA_WIDTH | reg  | {DATA_WIDTH{1'b0}}          | clk   | async      | 1      | 0         | FIFO 数据 (signed)
```

---

## 3. 数据结构（核心模型）

### 3.1 Port
```python
class Direction(Enum):
    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"

class SignalType(Enum):
    WIRE = "wire"
    REG = "reg"
    LOGIC = "logic"

class ResetType(Enum):
    SYNC = "sync"
    ASYNC = "async"
    NONE = "none"

@dataclass
class Port:
    name: str                    # "rx_data"
    direction: Direction
    width: str                   # "8" 或 "DATA_WIDTH" (保留原始表达式)
    type: SignalType
    default: Optional[str]       # "{DATA_WIDTH{1'b0}}"
    clock: Optional[str]         # "clk"
    reset_type: ResetType        # 默认 SYNC
    signed: bool                 # False
    is_interface: bool           # False
    comment: Optional[str]
    msb: Optional[int]           # 解析后的 MSB（width=8 → 7）；参数化宽度时为 None
    is_parameter_width: bool     # width 是否含 parameter 名
```

### 3.2 Parameter
```python
class ParamType(Enum):
    PARAMETER = "parameter"
    LOCALPARAM = "localparam"

@dataclass
class Parameter:
    name: str
    value: str                   # "8" / "ADDR_WIDTH-1"
    width: Optional[str]         # "32" 或 None
    param_type: ParamType
    comment: Optional[str]
```

### 3.3 Module
```python
@dataclass
class Module:
    name: str                                    # "uart_rx"
    ports: list[Port]
    parameters: list[Parameter]                  # 本模块私有的 parameter
    source_file: Path                            # Excel 路径（用于 wrapper 注释）
    source_sheet: str                            # 源 sheet 名

    def inputs(self) -> list[Port]: ...
    def outputs(self) -> list[Port]: ...
    def inouts(self) -> list[Port]: ...
    def regs(self) -> list[Port]: ...
    def wires(self) -> list[Port]: ...
    def async_regs(self) -> list[Port]: ...      # reset_type=async
    def sync_regs(self) -> list[Port]: ...       # reset_type=sync
    def no_reset_regs(self) -> list[Port]: ...   # reset_type=none
    def primary_clock(self) -> Optional[str]: ...# 出现次数最多的 clock 名
```

### 3.4 异常
- `ExcelParseError` — Excel 格式/列缺失/marker 缺失
- `PortValidationError` — 端口名非法/方向非法/位宽非法
- `DuplicatePortError` — 同名端口
- `ModuleNotFoundError` — sheet 不存在
- `MarkerMissingError` — `# === PARAMETERS ===` / `# === PORTS ===` 缺失

---

## 4. 框图规范

### 4.1 三种格式对照

| 格式 | 载体 | 主题 | 编辑性 | 用途 |
|---|---|---|---|---|
| HTML | `.html` | 浅色（白底） | 可在浏览器缩放/打印 | 设计文档、Confluence |
| SVG | `.svg` | 浅色 | 矢量，可嵌入 PPT/Word | 文档、PPT |
| Excalidraw | `.excalidraw` | 手绘风 | app.excalidraw.com 可继续编辑 | 早期设计评审 |

### 4.2 HTML 框图规范

**布局**：
```
┌─────────────────────────────────┐
│         uart_rx                 │
├─────────────────────────────────┤
│ INPUTS           │  OUTPUTS     │
│ ─────────        │  ─────────   │
│ clk              │  rx_data     │
│ [1:0] wire       │  [7:0] reg   │
│                  │  8'h00 clk   │
│ rst_n            │              │
│ ...              │  rx_valid    │
└─────────────────────────────────┘
```

**视觉**：
- 整体宽度自适应，最小 480px
- 模块名：粗体，居中
- input 列左对齐，output 列右对齐
- 位宽格式：`[MSB:0]`（width=1 时省略）
- 类型徽标：`wire` 灰底，`reg` 蓝底，`logic` 紫底
- 注释：斜体小字，紧贴端口名下方
- 时钟标签：`clk` 小字灰底跟在 reg 端口
- 字体：等宽（monospace）
- 颜色：白底 #FFFFFF，灰边 #DDDDDD，主文字 #333333

### 4.3 SVG 框图规范

- 画布大小：根据端口数动态计算
- 模块：圆角矩形（rx=8）
- input 端口：左侧 + 短横线（小方块）
- output 端口：右侧 + 短横线（小方块）
- inout 端口：底部
- 端口标签：端口名 + 位宽
- 字体：sans-serif

### 4.4 Excalidraw 框图规范

- 场景：Excalidraw JSON object
- 元素：1 个 module 矩形 + N 个 port 文本 + 端口连线
- 矩形：位置居中 (250, 200)，大小根据端口数自适应
- 端口文本：等距分布在矩形左右
- 风格：手绘（roughness=1, strokeStyle=solid）

---

## 5. Verilog Wrapper 规范

### 5.1 生成内容

| 部分 | 自动？ | 说明 |
|---|---|---|
| 文件头注释 | ✅ | 模块名、源 Excel、时间戳、生成器版本 |
| `module ... endmodule` | ✅ | — |
| 端口声明 | ✅ | 按 input/output/inout 分组 |
| `parameter` / `localparam` | ✅ | 从本模块 parameter 段读 |
| 内部 signal 声明 | ✅ | input 端 wire，output 端 reg |
| `initial` 块 | ✅ | 只为带 `default` 的 reg 生成 |
| `always` 块（复位模板） | ✅ | **为每个有 default 的 reg 生成** 复位 always（按 reset_type 风格） |
| TODO 注释 | ✅ | 标出"用户实现区"+ 复位行为清单 |
| 时间戳注释 | ✅ | `// Generated: <time> by excel2design v0.x` |
| 功能逻辑（非复位 always） | ❌ | **不生成**，留给工程师 |
| 时钟产生 | ❌ | **不生成** |

### 5.2 输出示例（基于 v0.2 样例 Excel）

```verilog
// =====================================================
// Module:    uart_rx
// Source:    examples/sample_module.xlsx / sheet: uart_rx
// Generated: 2026-06-01 14:30:00 by excel2design v0.2
// =====================================================
// Company Confidential
// =====================================================

module uart_rx #(
    parameter DATA_WIDTH   = 8,
    parameter FIFO_DEPTH   = 16,
    parameter CLK_FREQ_MHZ = 100
) (
    // ---------- INPUTS ----------
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       rx_pad,
    input  wire                       baud_tick,

    // ---------- OUTPUTS ----------
    output reg  [DATA_WIDTH-1:0]      rx_data,    // async reset
    output reg                        rx_valid,   // async reset
    output reg                        fifo_full,  // async reset
    output reg  signed [DATA_WIDTH-1:0] fifo_data // async reset
);

    // ---------- INTERNAL WIRES ----------
    // (none)

    // ---------- INTERNAL REGS ----------
    // rx_data, rx_valid, fifo_full, fifo_data already declared in port list

    // ---------- INITIAL ----------
    initial begin
        rx_data   = {DATA_WIDTH{1'b0}};
        rx_valid  = 1'b0;
        fifo_full = 1'b0;
        fifo_data = {DATA_WIDTH{1'b0}};
    end

    // ---------- ASYNC RESET ALWAYS ----------
    // Generated for: rx_data, rx_valid, fifo_full, fifo_data
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_data   <= {DATA_WIDTH{1'b0}};
            rx_valid  <= 1'b0;
            fifo_full <= 1'b0;
            fifo_data <= {DATA_WIDTH{1'b0}};
        end else begin
            // TODO: drive these regs
        end
    end

    // =================================================
    // TODO: Implement uart_rx logic above (in the else branch)
    // 
    // Module: uart_rx
    // Clock: clk
    // Reset: rst_n (active low, async)
    // Parameters: DATA_WIDTH, FIFO_DEPTH, CLK_FREQ_MHZ
    //
    // Registers and reset behavior:
    //   rx_data   : async reset to {DATA_WIDTH{1'b0}}
    //   rx_valid  : async reset to 1'b0
    //   fifo_full : async reset to 1'b0
    //   fifo_data : async reset to {DATA_WIDTH{1'b0}}  (signed)
    // =================================================

endmodule
```

### 5.3 端口声明顺序规则
1. `input` 按 Excel 顺序
2. `output` 按 Excel 顺序
3. `inout` 按 Excel 顺序
4. 每组前一行注释 `// ---------- INPUTS ----------`

### 5.4 端口格式规则
- `width=1`：省略位宽（`input wire clk`）
- `width>1`：位宽用表达式（`[DATA_WIDTH-1:0]`）
- `signed=1`：在位宽前加 `signed` 关键字
- 同组同 type 连续时 v0 简化为每行都带类型（更清晰，便于行内注释）

### 5.5 复位 always 块生成规则

**触发条件**：模块中存在带 `default` 的 reg。

**分块规则**（按 reset_type 分）：
- 所有 `async` 的 reg → 一个 `always @(posedge clk or negedge rst_n)` 块
- 所有 `sync` 的 reg → 一个 `always @(posedge clk)` 块
- 所有 `none` 的 reg → **不生成 always 块**，但 TODO 注释里列出
- 混合 reset_type → 多个 always 块（按类型分组）

**块内结构**（async 为例）：
```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        <每个 reg 用其 default 值复位>
    end else begin
        // TODO: drive these regs
    end
end
```

**块内结构**（sync 为例）：
```verilog
always @(posedge clk) begin
    if (!rst_n) begin
        <每个 reg 用其 default 值复位>
    end else begin
        // TODO: drive these regs
    end
end
```

### 5.6 TODO 注释规则
- 列出所有 reg 及其 reset 行为
- 列出模块的主时钟和复位信号
- 列出该模块涉及的所有 parameter 名
- 注明哪些 reg 暂未生成 always（`reset_type=none` 的）

---

## 6. CLI 规范

```bash
excel2design parse <excel> [--json]
    # 解析并打印所有模块/参数概览，--json 输出 JSON

excel2design diagram <excel> <module>
    [--format {html,svg,excalidraw,all}]   # 默认 all
    [--output <dir>]                        # 默认 ./output

excel2design wrapper <excel> <module>
    [--output <file>]                       # 默认 ./<module>.v

excel2design all <excel> <module>
    # = diagram + wrapper 一起生成
    [--output <dir>]                        # 默认 ./output
```

**错误处理**：
- Excel 不存在 → exit 2
- sheet 不存在 → exit 3
- 解析错误 → exit 4，打印具体行列号

---

## 7. 库 API 规范

```python
from excel2design import parse_excel, generate_diagram, generate_wrapper
from pathlib import Path

# 解析
project = parse_excel(Path("sample_module.xlsx"))
module = project.get_module("uart_rx")

# 框图
generate_diagram(module, format="html",     output=Path("out/uart_rx.html"))
generate_diagram(module, format="svg",      output=Path("out/uart_rx.svg"))
generate_diagram(module, format="excalidraw", output=Path("out/uart_rx.excalidraw"))

# Wrapper
generate_wrapper(module, output=Path("out/uart_rx.v"))
```

---

## 8. 阶段路线图

| Phase | 目标 | 验收标准 | 估时 |
|---|---|---|---|
| 0 | 项目骨架 + Excel 样例 + 依赖 | `pip install -e .` 成功；`examples/sample_module.xlsx` 可被 openpyxl 读 | 0.5d |
| 1 | 数据模型 + Excel 解析器 | `parse_excel()` 正确解析样例；7 种边界情况有单元测试（缺列、空行、注释、参数表达式宽度、重复端口名、非法方向、inout 端口） | 1d |
| 2 | HTML 框图生成器 | 视觉符合 §4.2；3 种端口（input/output/inout）渲染正确；位宽表达式保留原样 | 0.5d |
| 3 | SVG 框图生成器 | 视觉符合 §4.3；在浏览器/Inkscape 打开正常；端口数自适应 | 0.5d |
| 4 | Excalidraw 框图生成器 | 在 app.excalidraw.com 打开正常；端口可读 | 0.5d |
| 5 | Verilog wrapper 生成器 | 输出符合 §5；用 iverilog/verilator 语法 check 通过；TODO 注释完整 | 1d |
| 6 | CLI + 集成测试 + README | `excel2design all examples/sample_module.xlsx uart_rx` 一键跑通；README 有安装/使用/样例截图 | 1d |

**总估时**：~5 个工作日

---

## 9. 技术决策记录（ADR 摘要）

| 决策 | 选择 | 替代方案 | 理由 |
|---|---|---|---|
| Excel 库 | openpyxl | pandas | openpyxl 读写 .xlsx 性能更好，pandas 过度 |
| 模板引擎 | Jinja2 | 字符串拼接 | wrapper 和 HTML 框图都需要模板，可维护性高 |
| CLI 框架 | click | argparse | 装饰器风格、子命令更优雅、自动生成 --help |
| Excalidraw | 手写 JSON 生成 | 调用 Excalidraw API | Excalidraw 没有官方的 headless 库；JSON 格式稳定 |
| 测试 | pytest | unittest | 社区标准、fixture 强大 |
| 打包 | pyproject.toml | setup.py | 现代标准，PEP 517/518 |

---

## 10. 开放问题（v0.2 暂缓）

- [ ] 是否需要支持 .xls（旧格式）？v0.2 只做 .xlsx
- [ ] 是否需要支持从 wrapper 反向生成 Excel？v0.2 不做
- [ ] Excalidraw 是否需要带 PNG 导出？v0.2 只输出 .excalidraw JSON
- [ ] HTML 框图是否需要交互（hover 显示 comment）？v0.2 先做静态
- [ ] `interface=1` 端口是否需要特殊处理（生成 `mod_port`）？v0.2 仅记录，后续版本实现
- [ ] 是否需要支持 Excel 模板文件（用户自定义列名/列序）？v0.2 固定 5/10 列
- [ ] 多 module 共享 parameter（如多个 AXI 模块共用 `ADDR_WIDTH`）？v0.2 改为模块级后，跨模块共享需手动复制

---

## 11. v0.1 → v0.2 变更日志

| 项 | v0.1 | v0.2 | 原因 |
|---|---|---|---|
| Parameter 位置 | 独立 `@parameters` sheet | 每个模块 sheet 顶部 | 参数属于模块，跨 sheet 找不便 |
| Port 列数 | 7 列 | 10 列 | 补 reset_type / signed / interface |
| reset_type | 无 | 新增 sync/async/none | 支持自动生成复位 always |
| signed | 无 | 新增 | 数字信号经常需要 signed |
| interface 标记 | 无 | 新增（v0 仅记录） | 后续扩展 SV interface 留口子 |
| 复位 always | 不生成 | 自动按 reset_type 分块生成 | 减少工程师样板代码 |
| TODO 注释 | 简单 | 完整（含 reset 行为、parameter 清单） | 上下文更全 |
| initial 块 | `DATA_WIDTH'(8'h00)` | `{DATA_WIDTH{1'b0}}` | 真正的参数化写法 |
| 样例 Excel | 2 sheet（@parameters + uart_rx） | 1 sheet（uart_rx 内分两段） | 与新结构对齐 |

---

**确认后我会**：
1. 提交 SPEC v0.2 到 git
2. 写 README.md
3. 开始 Phase 0（项目骨架 + 样例 Excel）
