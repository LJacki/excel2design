# excel2design

> 从 Excel 模块端口表 → (HTML / SVG / Excalidraw) 框图 + Verilog wrapper 的自动化工具集

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Tests](https://img.shields.io/badge/tests-211%20passing-brightgreen)](#)
[![Phase](https://img.shields.io/badge/phase-0--6%20done-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

---

## 这是什么

数字IC工程师通常在 Excel 里维护模块端口表（端口名、方向、位宽、寄存器类型、复位行为等）。
`excel2design` 读取这份 Excel，一键生成：

1. **3 种框图**
   - **HTML**（浅色主题，CSS 变量 + Flexbox 响应式，可在浏览器缩放/打印）
   - **SVG**（矢量，ElementTree 构造，可嵌入 PPT/Word）
   - **Excalidraw**（手绘风，固定 seed 字节稳定，可在 [app.excalidraw.com](https://app.excalidraw.com) 继续编辑）
2. **Verilog wrapper 骨架**
   - 端口声明（按 input/output/inout 分组，严格按 Excel 顺序）
   - parameter 注入（带位宽）
   - 内部 signal 声明
   - `initial` 块（带 default 的 reg）
   - 多 (clock, reset_type) always 块（按二元组分块）
   - 完整 TODO 注释

所有产出以 Excel 为单一事实源 — 改 Excel 重跑即可，框图和 wrapper 永远对齐。

---

## 安装

```bash
git clone <repo-url>
cd excel2design
python -m venv .venv
.venv/bin/pip install -e .
```

需要 Python 3.10+。可选 dev 依赖：

```bash
.venv/bin/pip install -e ".[dev]"
```

---

## 快速开始

### 1. 准备 Excel

每个 sheet = 一个模块。sheet 顶部 `# === PARAMETERS ===` 段是模块私有 parameter，底部 `# === PORTS ===` 段是端口列表。

样例见 `examples/sample_module.xlsx`（运行 `python tools/gen_sample.py` 重新生成）。

### 2. 查看项目

```bash
$ excel2design parse examples/sample_module.xlsx
Module: uart_rx  (sheet: uart_rx)
  Parameters: 3
    DATA_WIDTH = 8
    FIFO_DEPTH = 16
    CLK_FREQ_MHZ = 100
  Ports:      8
    inputs:   4
    outputs:  4
    inouts:   0
```

或 JSON：

```bash
$ excel2design parse examples/sample_module.xlsx --json
{
  "modules": [
    {
      "name": "uart_rx",
      "source_sheet": "uart_rx",
      "parameter_count": 3,
      "port_count": 8,
      "input_count": 4,
      "output_count": 4,
      "inout_count": 0
    }
  ]
}
```

### 3. 生成框图（3 种格式）

```bash
$ excel2design diagram examples/sample_module.xlsx uart_rx
Wrote output/uart_rx.html
Wrote output/uart_rx.svg
Wrote output/uart_rx.excalidraw
```

只生成一种：

```bash
$ excel2design diagram examples/sample_module.xlsx uart_rx --format html
```

### 4. 生成 Verilog wrapper

```bash
$ excel2design wrapper examples/sample_module.xlsx uart_rx
Wrote uart_rx.v
```

### 5. 一次全做

```bash
$ excel2design all examples/sample_module.xlsx uart_rx
Wrote output/uart_rx.html
Wrote output/uart_rx.svg
Wrote output/uart_rx.excalidraw
Wrote output/uart_rx.v
```

---

## Excel 模板规范

### 两段式布局

```
# === PARAMETERS ===
name            | value | width | param_type | comment
DATA_WIDTH      | 8     | 32    | parameter  | 数据位宽
FIFO_DEPTH      | 16    | 32    | parameter  | FIFO 深度

# === PORTS ===
name        | direction | width      | type | default                     | clock | reset_type | signed | interface | comment
clk         | input     | 1          | wire |                             |       |            | 0      | 0         | 系统时钟
rst_n       | input     | 1          | wire |                             |       |            | 0      | 0         | 异步低有效复位
rx_data     | output    | DATA_WIDTH | reg  | {DATA_WIDTH{1'b0}}          | clk   | async      | 0      | 0         | 接收数据
rx_valid    | output    | 1          | reg  | 1'b0                        | clk   | async      | 0      | 0         | 接收有效
```

### Parameter 段（5 列）

| 列 | 字段 | 必填 | 缺省 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | — | parameter 名 |
| B | `value` | ✅ | — | 默认值 |
| C | `width` | ❌ | 空 | 位宽（整数，如 `32`） |
| D | `param_type` | ❌ | `parameter` | `parameter` / `localparam` |
| E | `comment` | ❌ | 空 | 说明 |

### Port 段（10 列）

| 列 | 字段 | 必填 | 缺省 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | — | 端口名 |
| B | `direction` | ✅ | — | `input` / `output` / `inout` |
| C | `width` | ❌ | `1` | 位宽或表达式（`DATA_WIDTH` / `DATA_WIDTH*2`） |
| D | `type` | ❌ | 见下 | `wire` / `reg` / `logic` |
| E | `default` | ❌ | 空 | reg reset 默认值（`1'b0` / `8'hFF` / `{N{1'b0}}`） |
| F | `clock` | ❌ | 空 | 关联时钟 |
| G | `reset_type` | ❌ | `sync` | `sync` / `async` / `none` |
| H | `signed` | ❌ | `0` | `1` = signed 端口 |
| I | `interface` | ❌ | `0` | `1` = interface 风格（v0.3 仅记录） |
| J | `comment` | ❌ | 空 | 端口说明 |

**`type` 缺省推断**：
- `output` + 无 type → `reg`
- `input` + 无 type → `wire`
- `inout` + 无 type → `wire`

**`reset_type` 语义**：
- `sync` — 同步复位（`always @(posedge clk)`）
- `async` — 异步复位（`always @(posedge clk or negedge rst_n)`）
- `none` — 无复位（不生成 always 块，但仍生成 initial 块如有 default）

详细规范见 [`docs/SPEC.md`](docs/SPEC.md)。

---

## 作为 Python 库使用

```python
from pathlib import Path
from excel2design import parse_workbook, get_module
from excel2design.generators.diagram_html import generate_html
from excel2design.generators.diagram_svg import generate_svg
from excel2design.generators.diagram_excalidraw import generate_excalidraw
from excel2design.generators.verilog import generate_wrapper

# 解析
project = parse_workbook(Path("examples/sample_module.xlsx"))
module = get_module(project, "uart_rx")

# 框图
Path("out/uart_rx.html").write_text(generate_html(module), encoding="utf-8", newline="\n")
Path("out/uart_rx.svg").write_text(generate_svg(module), encoding="utf-8", newline="\n")
Path("out/uart_rx.excalidraw").write_text(generate_excalidraw(module), encoding="utf-8", newline="\n")

# Wrapper
Path("out/uart_rx.v").write_text(
    generate_wrapper(module, source_file="examples/sample_module.xlsx", source_sheet="uart_rx"),
    encoding="utf-8", newline="\n",
)
```

---

## CLI 命令

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

**退出码**（SPEC §6）：
- `0` — 成功
- `2` — Excel 文件不存在
- `3` — 模块（sheet）不存在
- `4` — 解析错误（marker 缺失 / 表头错 / 端口重名等）

---

## 路线图（全部完成 ✅）

| Phase | 目标 | 状态 | commit |
|---|---|---|---|
| 0 | 项目骨架 + Excel 样例 + CI | ✅ | `ebd0054` |
| 1 | 数据模型 + Excel 解析器（136 tests） | ✅ | `c152dd7` |
| 1.5 | Golden baseline 框架（4 fixture + 5 tests） | ✅ | `e392f8b` |
| 2 | HTML 框图（17 tests via subagent） | ✅ | `435503d` |
| 3 | SVG 框图（8 tests via subagent） | ✅ | `fd29900` |
| 4 | Excalidraw 框图（8 tests via subagent） | ✅ | `6db2c6f` |
| 5 | Verilog wrapper（23 tests） | ✅ | `d9419ae` |
| 6 | CLI + e2e tests（14 tests） | ✅ | `e484a3a` |

**总计：211 个测试 100% 通过**

详细见 [docs/SPEC.md §8](docs/SPEC.md)。

---

## 技术栈

- **Excel 解析**：[openpyxl](https://openpyxl.readthedocs.io/) ≥ 3.1
- **模板引擎**：[Jinja2](https://jinja.palletsprojects.com/) ≥ 3.1
- **CLI**：[click](https://click.palletsprojects.com/) ≥ 8.1
- **测试**：[pytest](https://docs.pytest.org/) ≥ 7.4

---

## 项目结构

```
excel2design/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── SPEC.md                ← 详细设计规格书（v0.3, 14 章, 902 行）
│   ├── TASKS.md               ← 实时任务追踪
│   ├── CHANGELOG.md           ← 用户视角 changelog
│   └── SUBAGENT_LOG.md        ← 3 个 subagent 详细记录
├── excel2design/              ← 源码
│   ├── core/                  # 数据模型 + 异常
│   │   ├── models.py          # Port/Parameter/Module + 4 enums
│   │   └── exceptions.py      # 10 个异常类（3 层分类）
│   ├── parsers/               # Excel 解析
│   │   ├── excel.py           # 完整解析器（marker + 两段式 + 11 种错误检测）
│   │   ├── width.py           # 位宽解析（固定/参数/表达式）
│   │   └── default.py         # default 字面量规则
│   ├── utils/                 # 核心工具
│   │   ├── cell.py            # cell_to_str（类型白名单）
│   │   └── identifier.py      # VERILOG_KEYWORDS（80+ 保留字）
│   ├── generators/            # 输出生成
│   │   ├── diagram_html.py    # HTML 框图（Jinja2 + CSS 变量）
│   │   ├── diagram_svg.py     # SVG 框图（ElementTree）
│   │   ├── diagram_excalidraw.py  # Excalidraw（dict + json.dumps）
│   │   └── verilog.py         # Verilog wrapper（多 clock always 分块）
│   ├── templates/             # Jinja2 模板
│   │   ├── diagram_html.j2
│   │   ├── partial_port.j2
│   │   ├── verilog_wrapper.j2
│   │   └── partial_always.j2
│   ├── cli.py                 # click CLI（parse/diagram/wrapper/all）
│   └── __init__.py            # 公共 API
├── tools/                     # 生成脚本
│   ├── gen_sample.py          # examples/sample_module.xlsx
│   ├── gen_fixtures.py        # 4 个测试 fixture
│   └── gen_baseline.py        # JSON baseline
├── examples/
│   └── sample_module.xlsx     # 样例 Excel
├── tests/                     # 6 层测试
│   ├── unit/                  # 解析器/工具单测
│   ├── generators/            # 生成器单测
│   ├── e2e/                   # CLI 端到端
│   ├── fixtures/              # 4 fixture + 4 JSON baseline
│   └── test_golden.py         # 字节级回归
└── .github/workflows/ci.yml   # GitHub Actions（py3.10/3.11/3.12）
```

---

## 关键设计原则

### 字节稳定（SPEC §5.7）
- **时间戳可控**（默认不写，开启时支持 `SOURCE_DATE_EPOCH`）
- **行尾固定 LF**，无 trailing whitespace
- **端口严格按 Excel 顺序**
- **Jinja2 模板禁用 random / timestamp**
- **多次生成输出字节完全一致**

### 异常三层分类（SPEC §3.4）
- `ExcelParseError` — 物理层：cell 类型、列缺失、marker 缺失
- `SemanticError` — 逻辑层：端口重名、identifier 非法、width 表达式含未声明 param
- `RenderError` — 生成层：模板失败、坐标越界

每个异常带 `row, col, sheet, suggestion` 字段，CLI 渲染为：
```
ERROR [sheet: uart_rx, row 8, col 3] 位宽 "8 bits" 既不是数字也不是表达式
       ↳ 建议：width 列应填纯数字（如 8）或 parameter 名（如 DATA_WIDTH）
```

### 多时钟域 always 分组（SPEC §3.5.6）
- 分块键：`(clock, reset_type)` 二元组
- 同 (clock, reset_type) → 1 个 always 块
- 块间顺序：先按 clock 名 ASCII，再按 reset_type（async → none → sync）

---

## 不在范围（v0.3）

- ❌ 不生成任何功能性 RTL 逻辑（只生成复位 always 块）
- ❌ 不解析已有 Verilog 文件反向生成 Excel
- ❌ 不支持 Excel 公式、合并单元格、跨 sheet 引用
- ❌ 不做 lint、CDC 检查、综合
- ❌ 不支持 SystemVerilog interface/class
- ❌ `interface=1` 标记仅记录，不做特殊处理（v0.4+）

---

## 贡献

待补充。

---

## License

MIT

