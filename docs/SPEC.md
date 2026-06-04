# excel2design — 设计规格书

> 版本: v0.4
> 最后更新: 2026-06-04
> 状态: §4 框图规范重大升级（v0.3.4）；Phase 0-6 已全部落地

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
2. 端口文本：`element.type: "text"`, `fontFamily: 5` (Helvetica / "Normal"), `fontSize: 20`
3. **方向箭头**：`element.type: "arrow"`, 连接文本到矩形边缘

**字体选择（v0.4 起）**：
- `fontFamily: 5` = Helvetica / "Normal"（非手写，清晰可读）
- 旧版 `fontFamily: 1` = Virgil（手写草稿体）→ **废弃**

**布局规则**：
```
  clk_a ←──┐                    ┌──→ data_a[WIDTH-1:0]
 rst_a_n ←─┤   ┌──────────┐    ├──→ valid_a
   clk_b ←─┤   │multi_clock│    ├──→ data_b[WIDTH-1:0]
 rst_b_n ←─┤   │           │    ├──→ flag_c
   clk_c ←─┤   │  WIDTH=16 │    ├──→ bridge_out[WIDTH-1:0]
bridge_in ←─┘   └──────────┘    └──→
```

- **箭头方向**：input 箭头从文本指向矩形（←─），output 箭头从矩形指向文本（─→）
- **箭头属性**：`strokeColor` 按方向（input `#2E86C1`，output `#E74C3C`），`strokeWidth: 2`
- **文本宽度动态计算**：
  - `text.width = max(len(label) * 9, 60)` — 每字符 ~9px（fontSize=20, Helvetica 平均）
  - `text.height = 25`
- **矩形大小动态计算**：
  - `RECT_W = max(300, longest_label_width + 200)`
  - `RECT_H = max(200, max(inputs, outputs) * ROW_SPACING + 80)`
- 端口行间距：`ROW_SPACING = 30`
- 整体位置：模块左上角 `(250, 200)`，超出右边缘自动扩展 canvas
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
| **总** | | **10.5d** | | |

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

- **核心代码**（解析器、wrapper 核心、CLI、异常）→ **小马亲自写**，避免返工
- **机械重复代码**（HTML 框图、SVG 框图、Excalidraw 框图）→ **派子代理**，省时间
- **可并行的 phase** → 同时派 2-3 个子代理，加速
- **串行 phase** → 小马先做，子代理在依赖就位后接入

### 15.3 Phase 分配明细

| Phase | 执行人 | 备注 |
|---|---|---|
| 0 项目骨架 | 小马 | pyproject.toml / 目录结构 / 样例生成脚本 / .gitignore / CI 雏形 |
| 1 解析器 | 小马 | 核心代码，§3.5 全部实现细节 |
| **1.5** Golden baseline | 小马 | 4 个 fixture + expected/ 目录；本阶段是"刹车"，确保后面 phase 不会回退 |
| 2 HTML 框图 | **Subagent A** | 单文件任务，参考 architecture-diagram skill 风格 |
| 3 SVG 框图 | **Subagent B** | 与 2 并行，用 ElementTree 而非 Jinja2 |
| 4 Excalidraw 框图 | **Subagent C** | 与 2/3 并行，需固定 seed 保稳定 |
| 5a Wrapper 基础 | 小马 | 端口声明 + parameter 注入 + initial 块（不复杂，先打底） |
| 5b Wrapper 复位 always | 小马 | 核心交付，多 clock 分块，TODOs 注释 |
| 6 CLI + 集成 | 小马 | click 子命令 + e2e 测试 + README 截图 |

### 15.4 Git 提交约定

- **小颗粒提交**：每个可工作的中间态都提交，方便回滚
- **commit message 格式**：`<type>(<scope>): <subject>`
  - type: `feat` / `fix` / `docs` / `test` / `refactor` / `chore`
  - scope: `phase0` / `parser` / `diagram-html` / `wrapper` / `cli` / ...
  - 例: `feat(parser): add cell_to_str with type whitelist`
- **Phase 边界提交**：每个 phase 结束打 tag `phase-N-done`（轻量 tag）
- **Subagent 工作提交**：子代理完成任务后由小马统一 review + commit，commit message 带 `Co-authored-by: subagent`

### 15.5 任务追踪文件

- **`docs/TASKS.md`**：高粒度 todo，phase 进展，subagent 任务派发记录
- **`docs/SUBAGENT_LOG.md`**：所有与 subagent 交互的 prompt / response 摘要（关键决策点）
- **`docs/CHANGELOG.md`**：用户视角的 changelog（区别于 git log）

### 15.6 卡点处理

- **subagent 失败/质量差** → 重新派或转小马亲自写
- **小马卡住超 30 分钟** → 写卡点记录到 `docs/TASKS.md` 末尾，继续推进其他 phase
- **Jack 必须决策的事项** → 写进 `docs/TASKS.md` 的 "## Pending Decision" 段，等下次会话

---

## 16. 立即启动（v0.3 启动清单）

按以下顺序执行，不依赖 Jack 决策：

1. ✅ 完成（v0.3 SPEC 提交）
2. ⏳ Step 1: 写 `docs/TASKS.md` + `docs/SUBAGENT_LOG.md` + `docs/CHANGELOG.md` 空文件
3. ⏳ Step 2: Phase 0 — pyproject.toml / 目录结构 / 样例生成脚本
4. ⏳ Step 3: Phase 1 — 数据模型 + 解析器（含 §3.5 全部实现细节）
5. ⏳ Step 4: Phase 1.5 — Golden baseline 框架
6. ⏳ Step 5: 并行派 Subagent A/B/C（HTML/SVG/Excalidraw 框图）
7. ⏳ Step 6: Phase 5a/5b — wrapper（核心）
8. ⏳ Step 7: Phase 6 — CLI + 集成 + README
9. 📋 等 Jack 验收


