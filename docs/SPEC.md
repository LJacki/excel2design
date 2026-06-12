# excel2design — 设计规格书

> 版本: v0.5.2
> 最后更新: 2026-06-09
> 状态: §17.6 instance 列对齐规范 + 226 tests

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

### 3.4 异常（三层分类）

```
ExcelParseError       # 物理层：cell 类型、列缺失、marker 缺失、合并单元格
SemanticError         # 逻辑层：端口重名、identifier 非法、width 表达式含未声明 param
RenderError           # 生成层：模板渲染失败、坐标越界
```

所有异常的基类：

```python
@dataclass
class ExcelParseError(Exception):
    message: str
    sheet: Optional[str] = None     # 源 sheet 名
    row: Optional[int] = None       # 1-based；None = 整文件级错误
    col: Optional[int] = None       # 1-based (A=1)；None = 整行级错误
    suggestion: Optional[str] = None  # 修复建议
```

**子类型清单**：
- `MarkerMissingError(sheet, marker_name)` — `# === PARAMETERS ===` / `# === PORTS ===` 缺失
- `HeaderMismatchError(sheet, row, expected, got)` — 表头列名不匹配
- `MergedCellError(sheet, range)` — 检测到合并单元格
- `FormulaCellError(sheet, row, col)` — 检测到 Excel 公式
- `PortValidationError(sheet, row, col, message)` — 端口名非法/方向非法/位宽非法
- `DuplicatePortError(sheet, name, rows)` — 同名端口（列出所有重复行号）
- `ModuleNotFoundError(name)` — sheet 不存在
- `IdentifierError(sheet, row, col, name)` — 非合法 Verilog identifier 或为保留字
- `UnknownParameterError(sheet, port_row, param_name)` — width 表达式引用未声明的 parameter
- `UnsupportedCellTypeError(sheet, row, col, type_name)` — 单元格类型不在白名单

**CLI 渲染格式**：
```
ERROR [sheet: uart_rx, row 8, col 3] 位宽 "8 bits" 既不是数字也不是表达式
       ↳ 建议：width 列应填纯数字（如 8）或 parameter 名（如 DATA_WIDTH）
```

### 3.5 实现细节（强制规范）

#### 3.5.1 单元格类型容错 `cell_to_str`

```python
def cell_to_str(cell) -> str:
    """统一转字符串；None 和空字符串一致处理"""
    v = cell.value
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(int(v)) if isinstance(v, int) else str(v)
    if isinstance(v, str):
        return v.strip()
    raise UnsupportedCellTypeError(
        sheet=cell.parent.title, row=cell.row, col=cell.column,
        type_name=type(v).__name__
    )
```

**白名单**：`str / int / float / bool / None`，其他类型（datetime、formula）必须报错。

**陷阱**：
- openpyxl `data_only=False` 时公式返回 `"=A1+1"` 字符串，要先检测 `cell.data_type == 'f'`
- 数字 0/1 会被 Excel 自动转 bool，需特别处理
- 日期单元格 `datetime.datetime` 必须报错

#### 3.5.2 Verilog Identifier 校验

```python
import re
from keyword import kwlist  # Python 关键字白名单参考

VERILOG_KEYWORDS = {
    "always", "and", "assign", "automatic", "begin", "buf", "bufif0", "bufif1",
    "case", "casex", "casez", "cell", "cmos", "config", "deassign", "default",
    "defparam", "design", "disable", "edge", "else", "end", "endcase",
    "endconfig", "endfunction", "endgenerate", "endmodule", "endprimitive",
    "endspecify", "endtable", "endtask", "event", "for", "force", "forever",
    "fork", "function", "generate", "genvar", "highz0", "highz1", "if",
    "ifnone", "include", "initial", "inout", "input", "integer", "join",
    "large", "liblist", "library", "localparam", "macromodule", "medium",
    "module", "nand", "negedge", "nmos", "nor", "not", "notif0", "notif1",
    "or", "output", "parameter", "pmos", "posedge", "primitive", "pull0",
    "pull1", "pulldown", "pullup", "rcmos", "real", "realtime", "reg",
    "release", "repeat", "rnmos", "rpmos", "rtran", "rtranif0", "rtranif1",
    "scalared", "small", "specify", "specparam", "strong0", "strong1",
    "supply0", "supply1", "table", "task", "time", "tran", "tranif0",
    "tranif1", "tri", "tri0", "tri1", "triand", "trior", "trireg", "unsigned",
    "use", "vectored", "wait", "wand", "weak0", "weak1", "while", "wire",
    "wor", "xnor", "xor",
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def check_identifier(name: str, kind: str, sheet: str, row: int, col: int) -> None:
    if not _IDENT_RE.match(name):
        raise IdentifierError(
            sheet, row, col, name,
            suggestion=f"{kind} 必须是字母/数字/下划线，且以字母或下划线开头"
        )
    if name in VERILOG_KEYWORDS:
        raise IdentifierError(
            sheet, row, col, name,
            suggestion=f"{kind} 不能是 Verilog 保留字"
        )
```

**应用范围**：module 名（从 sheet 名校验）、parameter 名、port 名。

#### 3.5.3 位宽解析 `parse_width`

```python
_PARAM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_EXPR_TOKEN_RE = re.compile(r"[A-Za-z_0-9+\-*/()\s]+")

@dataclass
class PortWidth:
    raw: str                       # 原始字符串
    msb: Optional[int]             # 固定宽度时计算（如 8→7）；参数化时为 None
    is_parameter: bool             # 是否引用 parameter

def parse_width(raw: str, known_params: set[str], sheet: str, row: int, col: int) -> PortWidth:
    s = str(raw).strip() if raw is not None else ""
    if not s:
        return PortWidth(raw="1", msb=None, is_parameter=False)  # 默认 1 位

    # 纯数字
    if s.isdigit():
        n = int(s)
        if n <= 0:
            raise PortValidationError(sheet, row, col, f"位宽必须 > 0，得到 {n}")
        return PortWidth(raw=s, msb=n-1, is_parameter=False)

    # 单个 parameter 名
    if _PARAM_RE.fullmatch(s) and s in known_params:
        return PortWidth(raw=s, msb=None, is_parameter=True)

    # 表达式（必须所有 token 都在 known_params 或为操作符/数字）
    if _EXPR_TOKEN_RE.fullmatch(s):
        tokens = set(_PARAM_RE.findall(s))
        unknown = tokens - known_params - set(s for s in tokens if s.isdigit())
        if not unknown:
            return PortWidth(raw=s, msb=None, is_parameter=True)
        raise UnknownParameterError(sheet, row, col, sorted(unknown)[0])

    raise PortValidationError(
        sheet, row, col, f"位宽 '{s}' 既不是纯数字也不引用已知 parameter"
    )
```

**关键规则**：
- 固定宽度：wrapper 写 `[7:0]`，HTML 写 `[7:0]`
- 参数化宽度：wrapper 写 `[DATA_WIDTH-1:0]`（原样保留），HTML 同样保留
- `width=1`：`msb=0` 但显示时省略位宽

#### 3.5.4 端口排序稳定性

**铁律**：
1. 解析后 `ports` list 严格按 Excel 行的物理顺序（`ws.iter_rows` 顺序 = 行号顺序）
2. 端口按 direction 分组后，**组内顺序仍按 Excel 顺序**，不重排
3. 多次生成同一 Excel，输出字节完全一致（除非有显式变化）

**测试方法**：`test_no_diff_on_repeat` — 同一模块生成两次 wrapper，diff 为空。

#### 3.5.5 Default 值字面量规则

| 用户输入 | 解析后 | wrapper 输出 |
|---|---|---|
| 空 | 无 | 不生成对应 reg 的复位赋值 |
| `0` | `1'b0` | `1'b0` |
| `1` | `1'b1` | `1'b1` |
| `8'hFF` | 原样 | `8'hFF` |
| `{DATA_WIDTH{1'b0}}` | 原样 | `{DATA_WIDTH{1'b0}}` |
| `my_func(x)` | 原样 | `my_func(x)` |

**校验规则**：
- 纯数字 0/1 → 自动加 `1'b` 前缀
- 含 `'` → 视为 Verilog 字面量，原样保留
- 含 `{` → 视为 replication，原样保留
- 含 `( )` 但无 `'` → 视为函数调用，原样保留
- 含中文/特殊字符 → 报错

#### 3.5.6 多时钟域 always 分组键

**分块键**：`{clock, reset_type}` 二元组（注意是 `clock` 不是 `reset`！reset 名字假定是 `rst_n`，详见 §5.7）

**示例**：
- 4 个 reg，`clock` 全是 `clk`，`reset_type` 全是 `async` → 1 个 always 块
- 2 个 reg 用 `clk` async + 1 个 reg 用 `clk2` async → **2 个 always 块**（按 clock 分）
- 1 个 reg 用 `clk` sync + 1 个 reg 用 `clk` async → **2 个 always 块**（按 reset_type 分）

**混合 reset name 处理**：v0.3 假定复位信号统一叫 `rst_n`（见 §5.7）。如果工程师用了 `rst` / `rst_a_n` / `arst_n` 等不同名，v0.3 接受（不报错），但 always 块内统一用 `rst_n`。v0.4 之前不做"按 reset name 二次分组"。

---

## 4. 框图规范

### 4.1 三种格式对照

| 格式 | 载体 | 主题 | 编辑性 | 用途 |
|---|---|---|---|---|
| HTML | `.html` | 浅色（白底） | 可在浏览器缩放/打印 | 设计文档、Confluence |
| SVG | `.svg` | 浅色 | 矢量，可嵌入 PPT/Word | 文档、PPT |
| Excalidraw | `.excalidraw` | 手绘风 | app.excalidraw.com 可继续编辑 | 早期设计评审 |

**三种格式的共同要求**：
- ✅ 必须有模块矩形框（包围所有端口连接点）
- ✅ 必须有方向箭头（→ 输入指向框，← 输出从框指出）
- ✅ 端口标签必须包含端口名 + 位宽（width=1 省略位宽）
- ✅ 字节稳定：相同输入 → 相同输出

### 4.2 HTML 框图规范

**布局（CSS 模块框 + 端口列表）**：
```
         ┌──────────────────────────────────┐
  clk ──→│                                  │──→ rx_data[7:0]  reg
rst_n ──→│            uart_rx               │──→ rx_valid       reg
rx_pad ─→│                                  │──→ fifo_full      reg
          │  parameters: DATA_WIDTH=8, ...   │
          └──────────────────────────────────┘
```

**视觉规范**：
- 模块矩形：CSS `border: 2px solid #888; border-radius: 4px`，最小宽 480px
- 模块名：居中、粗体、16px，在模块框顶部
- parameter 横幅：灰底条在模块名下方，字号 12px 斜体
- **端口行布局**：`[箭头] [端口名] [位宽] [type徽标] [default] [clk]` 的横向流式布局
  - input 行：箭头 → 在端口名左侧（Unicode `→` 或 CSS `::before`）
  - output 行：箭头 → 在端口名右侧
  - inout 行：`↔` 双向箭头
- **箭头颜色**：input `#2E86C1`（蓝），output `#E74C3C`（红），inout `#9B59B6`（紫）
- 位宽徽标：等宽字体灰底 `[7:0]` 风格
- 类型徽标：`wire` 灰底，`reg` 蓝底，`logic` 紫底
- 注释：斜体小字 #888，端口名下方
- 字体：等宽 `Menlo/Consolas/Courier New`，13px
- 颜色：白底 #FFFFFF，主文字 #333333，边框 #DDD

### 4.3 SVG 框图规范

**核心元素**：
1. 模块矩形：圆角 `rx=8`，白底灰边
2. 端口标签：`{name}[{width}]` 格式，12px sans-serif
3. **方向箭头**：SVG `<marker>` arrowhead，用 `<line>` 连接端口标签到模块边缘
4. 箭头大小：6px 三角箭尖

**布局规则**：
```
         ← clk_a                     data_a[WIDTH-1:0] →
         ← rst_a_n    ┌──────────┐   valid_a →
         ← clk_b      │multi_clock│   data_b[WIDTH-1:0] →
         ← rst_b_n    │           │   flag_c →
         ← clk_c      │ WIDTH=16  │   bridge_out[WIDTH-1:0] →
         ← bridge_in  └──────────┘
```

- **input 端口**：箭头从 label 末端指向模块左边缘（direction: left→right）
- **output 端口**：箭头从模块右边缘指向 label（direction: left→right）
- **inout 端口**：底部水平排列，带双向标记
- 箭头颜色：input `#2E86C1`，output `#E74C3C`，inout `#9B59B6`
- **端口标签**：端口名 + 位宽（如 `clk_a`、`bridge_in[WIDTH-1:0]`）
- 画布大小：根据端口数和标签宽度动态计算
- 字体：sans-serif，12px
- 模块名：粗体 14px，模块框上方居中

### 4.4 Excalidraw 框图规范

**核心元素**：
1. 模块矩形：`element.type: "rectangle"`, `roughness: 1`, `strokeStyle: "solid"`
2. 模块名：`element.type: "text"`, `fontFamily: 5`, 矩形上方居中
3. **带标签箭头**：`element.type: "arrow"`，信号名写在 `arrow.text` 字段，一个元素同时承载方向+文字

**字体选择（v0.4 起）**：
- `fontFamily: 4` = Comic Shanns（干净的手写字体，替代 Virgil）
- 旧版 `fontFamily: 1` = Virgil（手写草稿体）→ **废弃**

**布局规则**：
```
  ←── clk_a ──┐                    ┌── data_a[WIDTH-1:0] ──→
  ←─ rst_a_n ─┤   ┌──────────┐    ├─── valid_a ──→
  ←── clk_b ──┤   │multi_clock│    ├── data_b[WIDTH-1:0] ──→
  ←─ rst_b_n ─┤   │           │    ├─── flag_c ──→
  ←── clk_c ──┤   │  WIDTH=16 │    ├ bridge_out[WIDTH-1:0] ─→
  ← bridge_in ┘   └──────────┘    └──
```

- **箭头方向**：input 箭头从左指向模块左边缘（→），output 箭头从模块右边缘指向右（→）
- **箭头属性**：`strokeColor` 按方向（input `#2E86C1`，output `#E74C3C`，inout `#9B59B6`），`strokeWidth: 2`
- **箭头文字**：`arrow.text` = 端口标签（`{name}[{width}]`），沿箭头中点渲染，自然对齐
- **箭头长度动态计算**：
  - `length = max(len(label) * 13 + 30, 100)` — 每字符 ~13px + 30px 余量（fontSize=20, Helvetica）
  - `height = 30` — 足够容纳 fontSize=20 的文字
- **矩形大小动态计算**：
  - `RECT_X = max_input_arrow_len + gap + pad`（为左侧箭头留空间）
  - `RECT_W = max(250, pad * 2)`
  - `RECT_H = max(180, max(inputs, outputs) * ROW_SPACING + 80)`
- 端口行间距：`ROW_SPACING = 32`
- 固定 seed：元素 ID 派生的整数值（非 random），保证字节稳定

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

**分块键**：`(clock, reset_type)` 二元组（详见 §3.5.6）

- 同一 `(clock, reset_type)` 组合的所有 reg → 合并到一个 always 块
- 不同组合 → 多个 always 块
- `reset_type=none` 的 reg → **不生成** always 块（但仍生成 initial 块，若有 default）

**块内结构**（async 为例）：
```verilog
always @(posedge <clock> or negedge <reset>) begin
    if (!<reset>) begin
        <该块内每个 reg 用其 default 值复位>
    end else begin
        // TODO: drive these regs
    end
end
```

**块内结构**（sync 为例）：
```verilog
always @(posedge <clock>) begin
    if (!<reset>) begin
        <该块内每个 reg 用其 default 值复位>
    end else begin
        // TODO: drive these regs
    end
end
```

**`<reset>` 名字**：v0.3 假定统一叫 `rst_n`（用户可在 TODO 注释中改）。always 块内引用 `rst_n`，不复用 Excel 中的 reset signal name（避免不一致）。详见 §5.7。

**示例**：4 个 reg 都用 `clk` async → 1 个 always 块；如果再加 1 个用 `clk2` sync 的 reg → 2 个 always 块。

### 5.6 TODO 注释规则
- 列出所有 reg 及其 reset 行为
- 列出模块的主时钟和复位信号
- 列出该模块涉及的所有 parameter 名
- 注明哪些 reg 暂未生成 always（`reset_type=none` 的）

### 5.7 字节稳定铁律（Byte-Stable Output）

**所有 wrapper / 框图生成必须满足以下铁律**，否则 golden test 失效：

1. **时间戳可控**：文件头 `// Generated:` 默认不写时间戳（`--no-timestamp` 为默认值）。开启时间戳时支持 `SOURCE_DATE_EPOCH` 环境变量。
2. **行尾固定 `'\n'`**（LF），无 `'\r\n'`，无 trailing whitespace。
3. **端口列表严格按 Excel 顺序**：inputs 之间、outputs 之间、inouts 之间不重排。
4. **parameter 列表严格按 parameter 段 Excel 顺序**。
5. **always 块内 reg 顺序**按首次出现在 Excel 中的顺序（去重后）。
6. **always 块之间顺序**按 `(clock, reset_type)` 字典序（先按 clock 名 ASCII 升序，再按 reset_type 字母序：`async` < `none` < `sync`）。
7. **Jinja2 模板禁用 `random` / 时间戳 / 任何非确定性来源**。
8. **不依赖当前 locale / 时区 / 环境变量**（除 `SOURCE_DATE_EPOCH`）。
9. **端口对齐固定宽度**：所有端口声明按 `direction(6) + space + type(8) + space + 端口声明` 格式对齐（`input  wire` / `output reg ` / `inout  wire`，每行右对齐到 `width` 字段）。
10. **同一 Excel 多次生成 → 字节完全一致**（除时间戳外）。

**测试方法**：
```python
def test_no_diff_on_repeat(sample_module):
    a = generate_wrapper(sample_module)
    b = generate_wrapper(sample_module)
    assert a == b

def test_no_diff_on_format_change(sample_module):
    """修改无关字段（如 comment）后重生成，diff 应只包含受影响的行"""
    ...
```

### 5.8 Reset 信号约定

**v0.3 约定**：
- wrapper 中 always 块的复位判断统一引用 `rst_n`（不复用 Excel 的 reset signal name）
- TODO 注释里**同时**列出"假设的复位信号名"（默认 `rst_n`）和"实际引用的 input 端口名"（如果用户 Excel 里有 `rst` / `arst_n` 等）
- 工程师在 Excel 里**可以**有任意 reset input 端口名（`rst_n` / `rst` / `arst_n` / `sys_rst_n` 都可以），但生成的 always 块**永远**用 `rst_n`

**理由**：v0.3 不做 reset name 二次分组，简化 always 块生成；用户只需要把 Excel 里那个真正的 reset port 名字改成 `rst_n` 即可（或在生成的 wrapper 里全文替换）。

**v0.4 计划**：识别 Excel 中"标 reset 用途的 input 端口"（可能需要新列 `reset_signal: bool`），按真实名字生成。

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

## 8. 阶段路线图（v0.3 修订）

| Phase | 目标 | 估时 | 风险 | 验收标准 |
|---|---|---|---|---|
| 0 | 项目骨架 + Excel 样例 + pyproject.toml | 0.5d | 低 | `pip install -e .` 成功；`tools/gen_sample.py` 能生成 `examples/sample_module.xlsx` |
| 1 | 数据模型 + Excel 解析器 | 2.5d | **高** | `parse_excel()` 正确解析样例；§3.5 实现细节全部落地；10+ 边界单测通过（含空行/合并单元格/公式/中文/参数化宽度/多时钟） |
| **1.5** | **Golden baseline 框架 + 4 个 fixture** | **0.5d** | **中** | `tests/fixtures/{uart_rx, axi_crossbar, multi_clock, empty_ports}.xlsx` 配 `expected/` 目录；pytest 跑通 baseline diff |
| 2 | HTML 框图生成器 | 0.5d | 低 | 视觉符合 §4.2；§3.5.4 端口排序铁律验证；3 种端口（in/out/inout）渲染正确 |
| 3 | SVG 框图生成器 | 1d | 中 | 视觉符合 §4.3；`xml.etree` 解析无错；端口数自适应布局（伪代码见 §4.3）；浏览器 + Inkscape 打开正常 |
| 4 | Excalidraw 框图生成器 | 1.5d | **高** | app.excalidraw.com 打开正常；固定 seed 后手绘风格稳定（snapshot test）；元素坐标全为整数 |
| 5a | Wrapper 基础（端口 + parameter） | 0.5d | 中 | 输出符合 §5.3/5.4；端口对齐格式固定（§5.7.9）；`test_no_diff_on_repeat` 通过 |
| 5b | Wrapper 复位 always + TODO 注释 | 1.5d | **高** | 多 (clock, reset_type) 分组正确（§3.5.6 / §5.5）；`test_mixed_reset` 等通过；iverilog `-t null` 语法 check 通过 |
| 6 | CLI + 集成测试 + README 截图 | 1.5d | 中 | `excel2design all` 一键跑通；端到端测试（CLI + iverilog smoke）；README 补三张截图 |
| **总** | | **10.5d + 4.3d = 14.8d** | |
| **v0.3-v0.4 (新增)** | **框图 v0.4 + Verilog 列对齐** | **1d** | **方向箭头 / 时钟域颜色 / 六列对齐** |
| **v0.5 (新增)** | **子模块层次化 + 实例化** | **4.3d** | **多 sheet 层次解析 / 连接算法 / 多文件输出** |

**风险最高的 3 个 Phase**：1（解析器是输入闸）、4（Excalidraw schema 不熟）、5b（wrapper 是核心交付）。

**顺序不变**，但建议在 Phase 1 完成后**先做 1.5 再做 2/3/4/5**。Golden baseline 早建，后续回归压力小。

---

## 9. 技术决策记录（ADR 摘要）

| 决策 | 选择 | 替代方案 | 理由 |
|---|---|---|---|
| Excel 库 | openpyxl | pandas | openpyxl 读写 .xlsx 性能更好，pandas 过度 |
| **Wrapper 模板** | **Jinja2** | **字符串拼接** | **wrapper 和 HTML 框图都需要模板；Jinja2 env 配 `trim_blocks=True, lstrip_blocks=True` 防空行** |
| **SVG / Excalidraw 模板** | **ElementTree / dataclasses.asdict** | **Jinja2** | **结构化数据用代码构造更稳；Jinja2 拼字符串易错** |
| CLI 框架 | click | argparse | 装饰器风格、子命令更优雅、自动生成 --help |
| Excalidraw | 手写 JSON 生成 | 调用 Excalidraw API | Excalidraw 没有官方的 headless 库；JSON 格式稳定；固定 seed 保稳定 |
| 测试 | pytest | unittest | 社区标准、fixture 强大 |
| Golden test | 手写 baseline + 字节稳定铁律 | snapshot | 手写更可控；字节稳定铁律是前置条件 |
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

## 12. v0.2 → v0.3 变更日志（M1-M5 审查补丁）

| ID | 补丁 | 位置 | 关键变更 |
|---|---|---|---|
| **M1** | 多时钟域 always 分组 | §3.5.6, §5.5 | 分块键从 `(reset_type)` 升级到 `(clock, reset_type)` 二元组；同一模块多 clock → 多 always 块 |
| **M2** | 异常三层分类 + 行列号定位 | §3.4 | 新增 `ExcelParseError` 基类带 `row/col/sheet/suggestion` 字段；CLI 渲染 `[sheet: xxx, row N, col M]` 格式 |
| **M2** | 单元格类型容错 | §3.5.1 | `cell_to_str()` 强制函数；白名单 `str/int/float/bool/None`；datetime / formula 必报错 |
| **M3** | 字节稳定铁律 | §5.7 | 10 条铁律（时间戳可控 / LF 行尾 / 端口顺序 / Jinja2 无随机源 / 端口对齐宽度 / 多次生成 diff 空等） |
| **M3** | 复位信号约定 | §5.8 | always 块内统一引用 `rst_n`；TODO 注释里列实际 reset port 名 |
| **M4** | Verilog identifier 校验 | §3.5.2 | 关键字黑名单（VERILOG_KEYWORDS）+ 正则 `^[A-Za-z_][A-Za-z0-9_]*$`；module/param/port 都校验 |
| **M4** | default 值字面量规则 | §3.5.5 | 纯数字 0/1 自动加 `1'b` 前缀；replication/字面量/函数调用原样保留 |
| **M5** | `reset_type=none` 行为 | §5.5 | 不生成 always 块（保留），但仍生成 initial 块（如有 default） |
| **架构** | 增加 §3.5 实现细节章节 | §3.5 | 6 个子节（cell_to_str / identifier / width / 排序 / default / 时钟分组） |
| **架构** | 增加 §1.4 暂未识别风险 | §10 | 增 3 条预留（多模块共享 param / interface modport / generate 实例化） |
| **路线图** | 拆 Phase 5 + 加 Phase 1.5 | §8 | 总估时 5d → 10.5d；新增 Golden baseline 阶段 |
| **路线图** | 增加测试策略章节 | §13 | 4 层测试（unit / generator / e2e / golden fixture） |

**Top-5 投入回报**（已落地）：
- M1 多时钟分块 — 0.5d 投入，规避"真实项目一上来就崩"风险
- M2 cell_to_str + 行列号 — 0.5d 投入，规避 90% 解析 bug
- M3 字节稳定铁律 — 0.5d 投入，确保所有 golden test 可行
- M4 identifier 校验 — 0.2d 投入，规避生成语法错的 .v
- M5 reset_type=none 行为 — 0.1d 投入，规避初始值缺失 bug

**subagent 审查但暂未采纳的建议**（v0.4 之后再议）：
- ❌ entry point 插件化（过早抽象）
- ❌ `Project.shared_parameters` v0 预留 dataclass 字段（YAGNI）
- ✅ 接受：SVG/Excalidraw 别用 Jinja2（v0.3 在 §9 ADR 里更新）
- ✅ 接受：Jinja2 `trim_blocks=True, lstrip_blocks=True`（§9 ADR）
- ✅ 接受：Phase 5 拆 5a/5b（已落地）
- ✅ 接受：4 个 fixture（Phase 1.5 已加入）

---

## 13. 测试策略（v0.3 新增）

### 13.1 四层测试金字塔

```
        /\
       /  \         E2E（CLI 集成 + iverilog smoke）
      /────\        
     /      \       Golden fixture（uart_rx / axi_crossbar / multi_clock / empty_ports）
    /────────\      
   /          \     生成器单测（HTML/SVG/Excalidraw/Verilog 各 1 文件）
  /────────────\    
 /              \   解析器单测（marker / param / port / type / width / identifier）
/________________\  
```

### 13.2 单元测试（pytest）

| 文件 | 测什么 | 关键 case |
|---|---|---|
| `test_models.py` | Port/Parameter/Module dataclass | `inputs()/outputs()/regs()` 分类；`primary_clock()` 多时钟返回第一个/报歧义 |
| `test_parser_markers.py` | 两段 marker 解析 | marker 缺失 / 拼写错误 / 两段间空行 0/5/100 |
| `test_parser_params.py` | parameter 段 | 5 列缺一 / value 含表达式 / param_type 大小写 / width 数字 vs 表达式 |
| `test_parser_ports.py` | port 段 | 缺列 / 空行 / 注释 / 参数化宽度 / 重复端口名 / 非法方向 / inout / signed |
| `test_parser_types.py` | 单元格类型 | 数字 / 字符串 / bool / None / **公式** / **日期** / **合并单元格** |
| `test_width_resolver.py` | 位宽解析 | 固定宽度 / 参数化 / 嵌套表达式 / width=0 / width=-1 / 未声明 param |
| `test_identifier.py` | identifier 校验 | 关键字 / 空字符串 / Unicode / 中文 / 含 `[]` 端口名 |

### 13.3 生成器单测

| 文件 | 必测 case |
|---|---|
| `test_html.py` | 含关键 token / inout 放底部 / 位宽表达式保留 / 端口顺序稳定 |
| `test_svg.py` | `xml.etree` parse 通过 / 画布尺寸正确 / 端口数自适应 |
| `test_excalidraw.py` | `json.loads` 通过 / 固定 seed / 必填字段齐全 / 坐标全为整数 |
| `test_verilog.py` | 见 §13.4 |

### 13.4 Wrapper 测试（最关键）

```python
def test_wrapper_basic(sample_module):
    out = generate_wrapper(sample_module)
    assert "module uart_rx" in out
    assert "endmodule" in out

def test_wrapper_port_order(sample_module):
    out = generate_wrapper(sample_module)
    # inputs 严格按 Excel 顺序
    assert out.index("clk") < out.index("rst_n") < out.index("rx_pad")

def test_wrapper_async_grouped(async_module):
    out = generate_wrapper(async_module)
    assert "always @(posedge clk or negedge rst_n) begin" in out
    assert "if (!rst_n) begin" in out

def test_wrapper_mixed_reset(mixed_module):
    """sync + async + 不同 clock 共存 → 多个 always 块，按 (clock, reset_type) 字典序"""
    out = generate_wrapper(mixed_module)
    assert out.count("always @(") == 3
    # 字典序：async → none → sync（按 reset_type），同 reset_type 内按 clock 名

def test_wrapper_multi_clock(multi_clock_module):
    """2 个 clock (clk / clk2) 各有 async reg → 2 个 always 块"""
    out = generate_wrapper(multi_clock_module)
    assert out.count("always @(") == 2
    assert "posedge clk " in out
    assert "posedge clk2" in out

def test_no_diff_on_repeat(sample_module):
    """字节稳定铁律核心验证：相同输入生成两次必须完全一致"""
    a = generate_wrapper(sample_module)
    b = generate_wrapper(sample_module)
    assert a == b

def test_reset_type_none_with_default(none_module):
    """reset_type=none 但有 default → 仍生成 initial 块，不生成 always 块"""
    out = generate_wrapper(none_module)
    assert "initial" in out
    assert "always @(" not in out
```

### 13.5 端到端测试

`tests/e2e/`：调用 CLI 二进制（`subprocess.run`），断言：
1. exit code = 0
2. 输出文件全部存在
3. 生成的 .v 能跑 `iverilog -t null`（语法 check，**不算**测试，只算 smoke）
4. 生成的 .svg 能被 `xml.etree` parse
5. 生成的 .excalidraw 能被 `json.loads`

### 13.6 Golden Fixture（Phase 1.5）

`tests/fixtures/`：
- `uart_rx.xlsx` — 基本样例
- `axi_crossbar.xlsx` — 大模块（30+ 端口、参数化宽度、inout）
- `multi_clock.xlsx` — 故意多时钟
- `empty_ports.xlsx` — 零端口

每个 fixture 配 `expected/{format}/{module}.{ext}` 存 golden baseline。CI 跑 diff 校验。

---

## 14. 暂未识别风险（v0.3 暂缓 / 架构预留）

- [ ] 多模块共享 parameter（v0.3 → v0.4 解决：加 `Project.shared_parameters`，Excel 顶部加 `@shared` 段）
- [ ] SystemVerilog interface modport（v0.3 → v0.5 解决：补 `Port.interface_name: Optional[str]` 字段；v0.3 暂不加）
- [ ] generate 实例化、参数化模块实例（v0.3 不做；v1.0 之前不考虑）
- [ ] `Port.array_dim`（端口数组如 `output [3:0] data[7:0]`）— v0.3 不支持；v0.4 评估
- [ ] 端口默认值与 parameter 重名（如 parameter `WIDTH` 和端口 `width`）— v0.3 视作不同 identifier，不处理
- [ ] `interface=1` 端口在 Excel 中的真实处理逻辑（v0.3 仅记录，不做特殊处理）

### v0.5 新增风险

- [ ] 同名端口多驱动（子模块间双向连接，需判断方向）
- [ ] 参数化实例覆盖（子模块 parameter override 的合法性检查）
- [ ] 层次化框图布局过密（多模块嵌套时坐标碰撞）
- [ ] 跨文件子模块引用（子模块在另一个 Excel 文件）

---

## 15. 任务分配方案（v0.3 启动版）

### 15.1 角色约定

| 角色 | 责任 |
|---|---|
| **小马（统筹）** | 任务拆解、git 提交节奏、跨 phase 集成、卡点处理、给 Jack 阶段汇报 |
| **小马（执行）** | Phase 0-1 全程（基础设施 + 解析器）、Phase 5 核心、Phase 6 |
| **Subagent** | Phase 2/3/4 框图生成器（互不依赖可并行）、Phase 5a 基础 wrapper 部分 |
| **Jack** | 关键决策 review（Phase 边界）、样例 Excel 拍板、最终验收 |

### 15.2 分配原则

## 15. 子模块层次化（v0.5 新增）

### 15.1 Sheet 命名约定

用 `.` 分隔表示层级关系：

```
Sheet: sram_wrapper              ← 顶层模块
Sheet: sram_wrapper.u_ctrl       ← 实例名 u_ctrl，子模块
Sheet: sram_wrapper.u_ctrl.u_fifo ← 二级嵌套
Sheet: sram_wrapper.u_datapath   ← 实例名 u_datapath
```

**规则**：
- 顶层 sheet 无 `.` → wrapper 模块
- `A.B` → A 的子模块，实例名 = `B`
- `A.B.C` → B 的子模块，实例名 = `C`，三级深度
- 不限制嵌套深度

**不需要 SUBMODULES 段**——层次关系由 sheet 名隐式定义。

### 15.2 数据模型

```python
@dataclass
class Project:
    modules: dict[str, Module]              # sheet_name → Module
    hierarchy: dict[str, list[str]]         # parent_sheet → [child_sheet_names]
    defines: list[Define]                   # @defines sheet 内容

@dataclass
class Define:
    name: str
    value: str
    comment: Optional[str]

@dataclass
class SubmoduleInstance:
    instance_name: str                      # "u_ctrl"
    module: Module                          # 子模块定义
    depth: int                              # 嵌套深度（1 = 直属于 wrapper）
    parent_sheet: str                       # 父模块的 sheet 名
```

### 15.3 层次解析器

```python
def parse_project(xlsx_path: Path) -> Project:
    """解析所有 sheet → 构建层次树 → 返回 Project"""
    # 1. 读 @defines sheet（如果存在）
    # 2. 读所有模块 sheet → {sheet_name: Module}
    # 3. 按 sheet 名构建 hierarchy tree
    #    sram_wrapper.u_ctrl.u_fifo → parent = sram_wrapper.u_ctrl
```

### 15.4 多文件输出

```
output/sram_wrapper/
├── define/
│   └── sram_wrapper.vh
├── doc/
│   ├── sram_wrapper.html
│   ├── sram_wrapper.svg
│   ├── sram_wrapper.excalidraw
│   ├── u_ctrl.html / .svg / .excalidraw
│   ├── u_ctrl_fifo.html / .svg / .excalidraw
│   └── u_datapath.html / .svg / .excalidraw
├── filelist/
│   └── sram_wrapper.f
└── rtl/
    ├── sram_wrapper.v
    ├── u_ctrl.v
    ├── u_ctrl_fifo.v
    └── u_datapath.v
```

---

## 16. Define 文件生成（v0.5 新增）

### 16.1 `@defines` Sheet

独立 sheet，在所有模块 sheet 之前，两列格式：

```
Sheet: @defines

# === DEFINES ===
name              | value | comment
SRM_DW            | 256   | SRAM 数据通路位宽
ENABLE_ECC        | 1     | 开启 ECC 校验
CLK_FREQ_MHZ      | 800   | 时钟频率(MHz)
```

**规则**：
- 与 parameter 段相同格式，但 `value` 是必要字段
- 不检查 Verilog identifier（`define 允许包含特殊字符`）
- 空 value → 视为 `define FOO`（无值宏）

### 16.2 生成 `.vh`

```verilog
// =====================================================
// sram_wrapper.vh — generated by excel2design v0.5
// =====================================================
`define SRM_DW        256
`define ENABLE_ECC    1
`define CLK_FREQ_MHZ  800
```

**格式**：左对齐，`define 名 + 空格 + value`。

### 16.3 `.f` 文件列表

```verilog
// sram_wrapper.f — generated by excel2design v0.5
rtl/sram_wrapper.v
rtl/u_ctrl.v
rtl/u_ctrl_fifo.v
rtl/u_datapath.v
```

按例化顺序（层次遍历），相对路径，可直接喂 iverilog / VCS / xrun。

---

## 17. 实例化连接算法（v0.5 新增）

### 17.1 连接策略

对每个子模块的所有端口，按优先级查找连接目标：

| 优先级 | 规则 | 示例 |
|--------|------|------|
| 1a | 父模块有同名端口 → 直连 | `clk` → `clk` |
| 1b | 父模块有实例后缀匹配端口 → 直连 | `reg_adc_pd`（instance `adc_a`）→ `reg_adc_pd_a` |
| 2 | 兄弟模块有同名端口 → 生成内部 wire | `data_bus` 连接 u_a → u_b |
| 3 | 父模块有同名 parameter → 参数化连接 | `WIDTH` → `#(.WIDTH(WIDTH))` |

### 17.1a 模糊后缀匹配（v0.5.1 新增）

当子模块端口名与父模块端口名不完全相同时，尝试按实例后缀匹配：

- instance `adc_a` 的 `reg_adc_pd` → 匹配父端口 `reg_adc_pd_a`（去掉 `_a` 后相等）
- instance `adc_b` 的 `reg_adc_pd` → 匹配父端口 `reg_adc_pd_b`
- 无实例名时尝试所有后缀（`_a/_b/_c/_0/_1/_2/_3`）

**未匹配**：
- 输出端口 → 悬空 `()` + `// TODO: no matching port`
- 输入端口 → 悬空 + `// TODO: drive this signal`

### 17.2 位宽不匹配

连接时检测位宽不一致，生成注释。**不阻断生成**——只标记，留给工程师处理。

### 17.3 内部 wire 生成

内部 wire 从实际连接结果推导（非独立扫描）。只有被 SIBLING_PORT 匹配使用的信号才生成 wire 声明。注释使用方向箭头：

```verilog
    wire              reg_cfg_wr_en    ;  // iic_slave → reg_cfg
    wire [REG_DW-1:0] reg_cfg_wr_data  ;  // iic_slave → reg_cfg
```

### 17.4 生成示例

```verilog
module sram_wrapper #(...) (
    input  wire clk,
    ...
);
    // ---------- INTERNAL WIRES ----------
    wire [SRM_DW-1:0] data_bus;   // u_ctrl → u_datapath

    // ---------- SUB-MODULES ----------
    u_ctrl u_ctrl (
        .clk      (clk             ) ,
        .rst_n    (rst_n           ) ,
        .data_bus (data_bus        ) ,
        .cfg_in   (cfg_in          )   // 直连 wrapper port
    );

    u_datapath u_datapath (
        .clk      (clk             ) ,
        .data_bus (data_bus        ) ,
        .result   (result          )   // 直连 wrapper port
    );
endmodule
```

### 17.5 多实例连接（v0.5.1）

同一模块的多个实例（如 `adc_a` 和 `adc_b`）各自通过后缀匹配连接到不同的父端口：

```verilog
    adc_a adc_a (
        .reg_adc_pd (reg_adc_pd_a) ,    // ← 模糊匹配 _a 后缀
    );
    adc_b adc_b (
        .reg_adc_pd (reg_adc_pd_b) ,    // ← 模糊匹配 _b 后缀
    );
```

### 17.6 Instance 格式规范（column alignment）

Instance 的 param 行和 port 行必须遵守统一列对齐规则，保证 `)` 和 `,` 竖直对齐：

**规则**：
1. `.name` 列宽取 `pn_pad = max(max_port_name, max_param_name)`，统一 param 和 port 的 name 列起始
2. 左括号 `(` 前统一一个空格
3. value/connection 列统一按 `max_connection_name` 填充，保证 `)` 在同一列
4. `) ` + 逗号 的格式一致（最后一个元素空格代替逗号）

**示例**（带 param 的实例）：
```verilog
iic_slave #(
    .REG_AW            (REG_AW          ) ,
    .REG_DW            (REG_DW          )  
) iic_slave (
    .clk               (clk             ) ,
    .rst_n             (rst_n           ) ,
    .iic_scl_in        (iic_scl_in      ) ,
    .iic_scl_oe        (iic_scl_oe      ) ,
    .iic_slave_busy    (                ) ,  // TODO: no matching port
    .reg_cfg_wr_en     (reg_cfg_wr_en   ) ,
    .reg_cfg_addr      (reg_cfg_addr    ) ,
    .reg_cfg_wr_data   (reg_cfg_wr_data ) ,
    .reg_cfg_rd_en     (reg_cfg_rd_en   ) ,
    .reg_cfg_rd_valid  (reg_cfg_rd_valid) ,
    .reg_cfg_rd_data   (reg_cfg_rd_data )  
);
```

**实现**（verilog.py）：
```python
pn_pad = max(max_pn, max_pn_p)  # max of port-name and param-name widths
f"    .{name:<{pn_pad + 1}} ({value:<{max_cn}}) {comma}"
```

**无 param 的实例**：
```verilog
u_ctrl u_ctrl (
    .clk      (clk      ) ,
    .data_bus (data_bus ) ,
    .cfg_in   (cfg_in   )  
);
```

---

## 18. 层次化框图（v0.5 新增）

### 18.1 总图布局

Wrapper 外框内嵌套子模块内框，端口连线：

```
  ┌─── sram_wrapper ───────────────────────────────┐
  │                                                 │
  │  ← clk                                          │
  │  ← rst_n    ┌── u_ctrl ──┐  ┌─ u_datapath ──┐ │
  │  ← cfg ────→│ cfg_in     │  │               │ │
  │             │    data ───┼──┼→ data_bus     │ │ → result
  │  ← din ────→│ din        │  │               │ │
  │             └────────────┘  └───────────────┘ │
  └─────────────────────────────────────────────────┘
```

### 18.2 连线规则

| 连线类型 | 视觉 | 示例 |
|---------|------|------|
| wrapper port → submodule port | 从 wrapper 边缘穿过到子模块边缘 | `clk` → `u_ctrl.clk` |
| submodule A → submodule B | 子模块间虚线/箭头，带信号名标签 | `u_ctrl.data` → `u_datapath.data_bus` |

### 18.3 子模块间连线（v0.5.1 实现）

SVG：灰色虚线 + 信号名标签在中间点。Excalidraw：灰色箭头。只连接兄弟模块间的内部信号（不由父端口中转的）。

### 18.4 独立框图批量模式

`excel2design diagram --all` → 为每个 sheet 独立生成框图，放入 `doc/` 目录。

### 18.5 层次化图格式

| 格式 | 实现 | 文件 |
|------|------|------|
| SVG | `diagram_svg_hierarchy.py`（嵌套 rect + 虚线连线） | `{top}_hierarchy.svg` |
| Excalidraw | `diagram_excalidraw_hierarchy.py`（矩形 + 箭头连线，Comic Shanns 字体） | `{top}_hierarchy.excalidraw` |

### 18.6 层级深度处理（v0.5.1）

`get_submodules(parent, recursive=False)` 只取直属子模块。每个模块的 wrapper 只实例化自己的直接子模块，孙子模块由子模块自己的 wrapper 实例化：

```
iic_top → iic_slave, reg_cfg, tempsensor_crg, tempsensor
tempsensor → adc_a, adc_b
```

---

## 19. 异常与容错（v0.5 扩展）

### 19.1 层次异常

| 异常类型 | 触发条件 | 行为 |
|---------|---------|------|
| `OrphanChildError` | sheet `A.B` 但 `A` 不存在 | 报错退出 |
| `RecursiveHierarchyError` | 循环引用（检测到重复 . 前缀） | 报错退出 |
| `EmptyHierarchyError` | 没有顶层模块（全是子模块 sheet） | 警告 + 全展开 |

### 19.2 连线异常

| 异常类型 | 触发条件 | 行为 |
|---------|---------|------|
| `WidthMismatchWarning` | 同名端口位宽不同 | 生成 TODO 注释 |
| `UnconnectedPortWarning` | 子模块端口无匹配 | 悬空 + TODO |
| `AmbiguousConnectionWarning` | 多个兄弟模块有同名端口 | 选第一个匹配 + 警告注释 |

---

## 20. v0.5 阶段路线图

| Phase | 目标 | 估时 | 验收标准 |
|---|---|---|---|
| **7** | `@defines` 解析 + `.vh` + `.f` 生成 | 0.5d | `define SRM_DW 256` 输出匹配 |
| **8** | 层次解析器 + Project 数据模型 | 0.5d | `parse_project()` 正确构建多级树 |
| **9a** | 实例化连接算法 | 0.5d | 同名端口匹配、宽度不匹配标记 |
| **9b** | Verilog 实例化模板 | 0.5d | 子模块 `.port(signal)` 连接正确 |
| **9c** | 多文件输出 + CLI `--all` | 0.3d | 目录结构符合 §15.4 |
| **10a** | 独立框图批量模式 | 0.2d | `diagram --all` 全模块出图 |
| **10b** | 层次化 SVG 框图 | 0.5d | 嵌套矩形 + 连线渲染正确 |
| **10c** | 层次化 Excalidraw 框图 | 0.5d | 同上 |
| **11** | 集成测试 + 多 sheet fixture | 0.5d | `tests/fixtures/hierarchy/` 三个层次 |
| **文档** | SPEC + TASKS 更新 | 0.3d | — |
| **总** | | **~4.3d** | |



---

## 21. v0.6 阶段路线图（小痛点优先）

> 触发: v0.5.1 收尾后 Jack 拍板"持续迭代 + 小痛点逐步解决"（2026-06-12）
> 目标: 处理 SPEC §14 列出的 v0.5 阶段未识别风险，按投入产出比排序
> 原则: 4 个 phase + 1 个文档 phase，每个 phase 独立 commit + 独立测试 + 字节稳定

### 选型理由

| 候选 | 选? | 理由 |
|---|---|---|
| `Port.array_dim` 端口数组 | ✅ | §14 评估项，实战常遇（AXI / SRAM），改 3 处（连接算法 / SVG 渲染 / verilog） |
| `interface=1` 端口真实处理 | ✅ | §14 占位代码清理，量小收益清晰 |
| 端口/parameter 重名容错 | ✅ | §14 风险项，用户必踩 |
| 同名端口多驱动方向判断 | ✅ | v0.5 新增风险，真工程必踩 |
| 参数化实例覆盖校验 | ⏸️ 暂缓 | 多数工程用不到 param override |
| 跨文件子模块引用 | ⏸️ 暂缓 | 架构改动大（重写解析层） |
| SystemVerilog modport | ⏸️ 暂缓 | 跟 array_dim 重叠，等 array_dim 落地再评估 |
| CI / PyPI / 覆盖率 | ⏸️ v0.7 集中做 | 不打断痛点修复节奏 |

### Phase 12 — `Port.array_dim` 端口数组（0.5d）

**目标**: 支持 `output [3:0] data[7:0]` 形式的端口数组，Excel 列 `array_dim` 解析为列表（如 `[7:0]`），穿透到 verilog 输出 / SVG 渲染 / 实例化连接。

| ID | 任务 | 验收标准 |
|---|---|---|
| 12.1 | `Port.array_dim: Optional[List[tuple[int,int]]]` 字段（v0.5 **未**留口，v0.6 全新落地） | dataclass 字段新增，存储 `[(hi, lo), ...]` 二维范围列表 |
| 12.2 | Excel 解析: 新列 `array_dim`（可选），格式 `[7:0]` / `[3:0][1:0]` | `uart_rx.xlsx` 加 1 个 array 端口 → 解析通过 |
| 12.3 | Verilog 生成: `output [3:0] data [7:0]` 正确输出（含 `packed`/`unpacked` 区分） | `tests/unit/test_verilog.py::test_array_dim` 通过 |
| 12.4 | SVG 框图: 端口标签后缀 `[7:0]`（不画完整方阵） | `tests/generators/test_diagram_svg.py` 新增 case |
| 12.5 | 实例化连接: `u_ctrl.data[3]` 单元素访问合法，`u_ctrl.data` 整数组留 TODO | `tests/generators/test_connection.py` 扩展 |
| 12.6 | 字节稳定铁律: array_dim 排序/格式不影响输出字节 | `test_byte_stability.py` 加 fixture |

### Phase 13 — `interface=1` 端口真实处理（0.3d）

**目标**: 清理 v0.3 占位代码，实现 interface 端口的真实 verilog 输出和框图渲染。

| ID | 任务 | 验收标准 |
|---|---|---|
| 13.1 | `Port.interface: bool` 字段已在 v0.5.1 加，落地实现 | dataclass 字段已有 |
| 13.2 | Verilog 生成: `interface_name.signal` 引用 + 框图分组（虚线框包围 interface 成员） | `test_verilog.py::test_interface` 通过 |
| 13.3 | SVG / Excalidraw: interface 端口画虚线 group container | `test_diagram_svg.py::test_interface_group` |
| 13.4 | 文档更新: README 加 `interface` 列示例 | `docs/screenshots/interface_port.png` |

### Phase 14 — 端口/parameter 重名容错（0.2d）

**目标**: parameter `WIDTH` 和端口 `width` 共存时不报错（v0.3 视作不同 identifier，v0.6 显式声明）。

| ID | 任务 | 验收标准 |
|---|---|---|
| 14.1 | Excel 解析: 检测 parameter 和 port 名称冲突（case-insensitive），发出 `NamingConflictWarning` 而非 error | `test_parser.py::test_param_port_collision_warning` |
| 14.2 | Verilog 生成: parameter 和 port 重名时加 `_p` 后缀避免编译错误（如 `parameter WIDTH_p`） | `test_verilog.py::test_param_port_collision_suffix` |
| 14.3 | 文档: README "Known Limitations" 段说明此行为 | — |

### Phase 15 — 同名端口多驱动方向判断（0.5d）

**目标**: 多个子模块同名端口连接时，根据 direction 判断 wire 类型（output→input 单向 vs inout 双向）。

| ID | 任务 | 验收标准 |
|---|---|---|
| 15.1 | `SubmoduleInstance.drivers: List[str]` 字段（v0.5 留口已存在），落地实现 | 解析同名 port 收集所有驱动者 |
| 15.2 | 连接算法: 多 driver 全 output → 错误 `MultiDriverError`；多 driver 含 inout → 转为 `wire` + `assign` | `test_connection.py::test_multi_driver_*` 3 个 case |
| 15.3 | Verilog 生成: inout 双向连接用 `wire ...; assign ...` 模式 | `test_verilog.py::test_inout_multi_driver` |
| 15.4 | 框图渲染: 多驱动连线用粗线 + 警告色（黄/红） | `test_diagram_svg.py::test_multi_driver_color` |

### Phase 16 — 文档 + 路线图收尾（0.2d）

| ID | 任务 | 验收标准 |
|---|---|---|
| 16.1 | 更新 `docs/CHANGELOG.md` 加 v0.6 段 | — |
| 16.2 | 更新 `docs/TASKS.md` 加 §Pending Decision / §Stuck 段 | — |
| 16.3 | SPEC changelog: patch ID M1-M5（v0.6 期间每次修改的 review 记录） | — |
| 16.4 | pyproject version: 0.5.1 → 0.6.0 | — |

### 总投入

| 阶段 | 估时 |
|---|---|
| 12 array_dim | 0.5d |
| 13 interface 落地 | 0.3d |
| 14 重名容错 | 0.2d |
| 15 多驱动方向 | 0.5d |
| 16 文档收尾 | 0.2d |
| **总** | **~1.7d** |

### 验收总标准

- 282 现有测试 0 回归
- 4 个新 phase 共新增 ≥ 16 个 unit test + ≥ 4 个 e2e test
- 字节稳定铁律 0 违反（跨 PYTHONHASHSEED=42/99 输出一致）
- 所有警告升级路径清晰（warning → error 的边界条件写进 SPEC）
- pyproject version bump 到 0.6.0

---

## 22. v0.6 之后路线图（v0.7 候选，暂缓评估）

> 留位用，等 v0.6 全部 phase 完成后 Jack 拍板。

- [ ] CI / GitHub Actions（on push 跑 282+ tests）
- [ ] PyPI 发布（`pip install excel2design`）
- [ ] 覆盖率报告（pytest-cov）
- [ ] 跨文件子模块引用（架构级）
- [ ] SystemVerilog modport 完整支持（等 array_dim 落地再评估）
- [ ] 参数化实例覆盖校验
