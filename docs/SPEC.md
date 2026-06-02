# excel2design — 设计规格书

> 版本: v0.1 (draft)
> 最后更新: 2026-06-01
> 状态: 待 Jack 确认

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

### 2.2 Sheet 命名规则
- **普通模块 sheet**：`{module_name}` — 例 `uart_rx`, `axi_crossbar`
- **参数声明 sheet**：`@parameters` — **整个文件唯一**，声明所有模块共享的 parameter

**约定**：
- 以 `@` 开头的 sheet 是元数据 sheet，不当作模块处理
- 其他 sheet 一律当作模块处理
- sheet 名即为模块名，必须是合法 Verilog identifier

### 2.3 模块 Sheet 列定义（7 列固定）

| 列 | 字段 | 必填 | 类型 | 缺省值 | 说明 |
|---|---|---|---|---|---|
| A | `name` | ✅ | str | — | 端口名（信号名），必须是合法 Verilog identifier |
| B | `direction` | ✅ | str | — | `input` / `output` / `inout`（大小写不敏感） |
| C | `width` | ❌ | int/str | `1` | 位宽，整数或表达式（如 `ADDR_WIDTH`、`DATA_WIDTH*2`） |
| D | `type` | ❌ | str | 见下 | `wire` / `reg` / `logic` |
| E | `default` | ❌ | str | 空 | reg 的 reset 默认值（如 `1'b0`、`8'hFF`） |
| F | `clock` | ❌ | str | 空 | 关联时钟名（仅 reg 用，提示给工程师） |
| G | `comment` | ❌ | str | 空 | 端口说明 |

**`type` 字段缺省推断规则**：
- `output` + 无 type → `reg`（最常见的寄存器输出）
- `input` + 无 type → `wire`
- `inout` + 无 type → `wire`

**特殊行约定**：
- 第一行是表头（`name | direction | width | type | default | clock | comment`）
- 之后每行一个端口
- 整行空白 → 跳过
- `#` 开头 → 注释行，跳过

### 2.4 @parameters Sheet 列定义（5 列）

| 列 | 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | str | parameter 名 |
| B | `value` | ✅ | int/str | 默认值 |
| C | `width` | ❌ | int | 位宽，可空（无位宽=局部参数） |
| D | `type` | ❌ | str | `parameter`（默认）/ `localparam` |
| E | `comment` | ❌ | str | 说明 |

### 2.5 样例 Excel（examples/sample_module.xlsx 预期内容）

**Sheet 1: `@parameters`**
| name | value | width | type | comment |
|---|---|---|---|---|
| DATA_WIDTH | 8 | 32 | parameter | 数据位宽 |
| ADDR_WIDTH | 16 | 32 | parameter | 地址位宽 |

**Sheet 2: `uart_rx`**
| name | direction | width | type | default | clock | comment |
|---|---|---|---|---|---|---|
| clk | input | 1 | wire | | | 系统时钟 |
| rst_n | input | 1 | wire | | | 异步低有效复位 |
| rx_data | output | 8 | reg | 8'h00 | clk | 接收数据 |
| rx_valid | output | 1 | reg | 1'b0 | clk | 接收有效 |
| baud_tick | input | 1 | wire | | | 波特率 tick |
| rx_pad | input | 1 | wire | | | 串行输入 |

---

## 3. 数据结构（核心模型）

### 3.1 Port
```python
@dataclass
class Port:
    name: str                    # "rx_data"
    direction: Direction         # enum: INPUT/OUTPUT/INOUT
    width: str                   # "8" 或 "DATA_WIDTH" (保留原始表达式)
    type: SignalType             # enum: WIRE/REG/LOGIC
    default: Optional[str]       # "8'h00"
    clock: Optional[str]         # "clk"
    comment: Optional[str]       # "接收数据"
    msb: int                     # 解析后的 MSB（width=8 → msb=7）
    is_parameter_width: bool     # width 是否含 parameter 名
```

### 3.2 Parameter
```python
@dataclass
class Parameter:
    name: str
    value: str                   # "8" / "ADDR_WIDTH-1"
    width: Optional[str]
    param_type: ParamType        # PARAMETER / LOCALPARAM
    comment: Optional[str]
```

### 3.3 Module
```python
@dataclass
class Module:
    name: str                                    # "uart_rx"
    ports: list[Port]
    parameters: list[Parameter]                  # 来自 @parameters
    source_file: Path                            # Excel 路径（用于 wrapper 注释）
    source_sheet: str                            # 源 sheet 名

    def inputs(self) -> list[Port]: ...
    def outputs(self) -> list[Port]: ...
    def inouts(self) -> list[Port]: ...
    def regs(self) -> list[Port]: ...
    def wires(self) -> list[Port]: ...
```

### 3.4 异常
- `ExcelParseError` — Excel 格式/列缺失
- `PortValidationError` — 端口名非法/方向非法
- `DuplicatePortError` — 同名端口
- `ModuleNotFoundError` — sheet 不存在

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
| 端口声明 | ✅ | 按 input/output 分组，inout 在最后 |
| `parameter` / `localparam` | ✅ | 从 @parameters 读 |
| 内部 signal 声明 | ✅ | input 端 wire，output 端 reg |
| `initial` 块 | ✅ | 只为带 `default` 的 reg 生成 |
| `always` 块 | ❌ | **不生成**，留给工程师 |
| TODO 注释 | ✅ | 标出"用户实现区" |
| 功能逻辑 | ❌ | **绝不生成** |

### 5.2 输出示例（基于样例 Excel）

```verilog
// =====================================================
// Module:    uart_rx
// Source:    sample_module.xlsx / sheet: uart_rx
// Generated: 2026-06-01 14:30:00 by excel2design v0.1
// =====================================================
// Company Confidential
// =====================================================

module uart_rx #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 16
) (
    // ---------- INPUTS ----------
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 baud_tick,
    input  wire                 rx_pad,

    // ---------- OUTPUTS ----------
    output reg  [DATA_WIDTH-1:0] rx_data,
    output reg                   rx_valid
);

    // ---------- INTERNAL WIRES ----------
    // (none)

    // ---------- INTERNAL REGS ----------
    // rx_data, rx_valid already declared in port list

    // ---------- INITIAL ----------
    initial begin
        rx_data  = DATA_WIDTH'(8'h00);
        rx_valid = 1'b0;
    end

    // =================================================
    // TODO: Implement uart_rx logic here
    // Clock: clk
    // Reset: rst_n (active low, async)
    // Register defaults: rx_data=8'h00, rx_valid=1'b0
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
- 同一方向同一类型连续时，类型不重复写（但 v0 简化为每个端口都带类型，更清晰）

### 5.5 TODO 注释规则
- 列出该模块所有 reg 端口及其 default
- 列出时钟和复位信号
- 列出该 module 涉及的所有 parameter 名

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

## 10. 开放问题（v0.1 暂缓）

- [ ] 是否需要支持 .xls（旧格式）？v0 只做 .xlsx
- [ ] 是否需要支持从 wrapper 反向生成 Excel？v0 不做
- [ ] Excalidraw 是否需要带 PNG 导出？v0 只输出 .excalidraw JSON
- [ ] HTML 框图是否需要交互（hover 显示 comment）？v0 先做静态
- [ ] 是否支持多个同名 module（不同实例）？v0 每个 sheet 一个 module 名

---

**确认后我会**：
1. 提交 SPEC.md 到 git
2. 开始 Phase 0（项目骨架 + 样例 Excel）
3. 每个 Phase 结束都汇报进度，等你确认后再进下一个
