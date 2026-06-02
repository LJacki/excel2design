# excel2design

> 从 Excel 模块端口表 → 标准/手绘框图 + Verilog wrapper 的自动化工具集

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

---

## 这是什么

数字IC工程师通常在 Excel 里维护模块端口表（端口名、方向、位宽、寄存器类型等）。
`excel2design` 读取这份 Excel，一键生成：

1. **3 种框图**
   - HTML（浅色主题，可在浏览器缩放/打印）
   - SVG（矢量，可嵌入 PPT/Word）
   - Excalidraw（手绘风，可在 [app.excalidraw.com](https://app.excalidraw.com) 继续编辑）
2. **Verilog wrapper 骨架**（含端口声明、parameter、内部信号、initial 块、复位 always 块、TODO 注释）

所有产出以 Excel 为单一事实源 — 改 Excel 重跑即可，框图和 wrapper 永远对齐。

---

## 安装

```bash
git clone <repo-url>
cd excel2design
pip install -e .
```

需要 Python 3.10+。

---

## 快速开始

### 1. 准备 Excel

每个 sheet = 一个模块。sheet 顶部 `# === PARAMETERS ===` 段是模块私有 parameter，底部 `# === PORTS ===` 段是端口列表。

样例见 `examples/sample_module.xlsx`。

### 2. 查看项目

```bash
excel2design parse examples/sample_module.xlsx
```

### 3. 生成框图（3 种格式）

```bash
excel2design diagram examples/sample_module.xlsx uart_rx
# 默认生成 .html / .svg / .excalidraw 三种到 ./output/
```

只生成一种：

```bash
excel2design diagram examples/sample_module.xlsx uart_rx --format html
```

### 4. 生成 Verilog wrapper

```bash
excel2design wrapper examples/sample_module.xlsx uart_rx
# 输出到 ./output/uart_rx.v
```

### 5. 一次全做

```bash
excel2design all examples/sample_module.xlsx uart_rx
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
| C | `width` | ❌ | 空 | 位宽 |
| D | `param_type` | ❌ | `parameter` | `parameter` / `localparam` |
| E | `comment` | ❌ | 空 | 说明 |

### Port 段（10 列）

| 列 | 字段 | 必填 | 缺省 | 说明 |
|---|---|---|---|---|
| A | `name` | ✅ | — | 端口名 |
| B | `direction` | ✅ | — | `input` / `output` / `inout` |
| C | `width` | ❌ | `1` | 位宽或表达式 |
| D | `type` | ❌ | 见下 | `wire` / `reg` / `logic` |
| E | `default` | ❌ | 空 | reg reset 默认值 |
| F | `clock` | ❌ | 空 | 关联时钟 |
| G | `reset_type` | ❌ | `sync` | `sync` / `async` / `none` |
| H | `signed` | ❌ | `0` | `1` = signed 端口 |
| I | `interface` | ❌ | `0` | `1` = interface 风格端口（v0.2 仅记录） |
| J | `comment` | ❌ | 空 | 端口说明 |

**`type` 缺省推断**：
- `output` + 无 type → `reg`
- `input` + 无 type → `wire`
- `inout` + 无 type → `wire`

**`reset_type` 语义**：
- `sync` — 同步复位
- `async` — 异步复位（敏感列表含 posedge clk or negedge rst_n）
- `none` — 无复位

详细规范见 [`docs/SPEC.md`](docs/SPEC.md)。

---

## 作为 Python 库使用

```python
from pathlib import Path
from excel2design import parse_excel, generate_diagram, generate_wrapper

# 解析
project = parse_excel(Path("examples/sample_module.xlsx"))
module = project.get_module("uart_rx")

# 框图
generate_diagram(module, format="html",      output=Path("out/uart_rx.html"))
generate_diagram(module, format="svg",       output=Path("out/uart_rx.svg"))
generate_diagram(module, format="excalidraw", output=Path("out/uart_rx.excalidraw"))

# Wrapper
generate_wrapper(module, output=Path("out/uart_rx.v"))
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

---

## 路线图

| Phase | 目标 | 状态 |
|---|---|---|
| 0 | 项目骨架 + Excel 样例 + 依赖 | ⏳ 进行中 |
| 1 | 数据模型 + Excel 解析器 | 📋 待开始 |
| 2 | HTML 框图生成器 | 📋 待开始 |
| 3 | SVG 框图生成器 | 📋 待开始 |
| 4 | Excalidraw 框图生成器 | 📋 待开始 |
| 5 | Verilog wrapper 生成器 | 📋 待开始 |
| 6 | CLI + 集成测试 + README | 📋 待开始 |

详细见 [docs/SPEC.md §8](docs/SPEC.md)。

---

## 技术栈

- **Excel 解析**：[openpyxl](https://openpyxl.readthedocs.io/)
- **模板引擎**：[Jinja2](https://jinja.palletsprojects.com/)
- **CLI**：[click](https://click.palletsprojects.com/)
- **测试**：[pytest](https://docs.pytest.org/)

---

## 项目结构

```
excel2design/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
│   └── SPEC.md                ← 详细设计规格书
├── excel2design/              ← 源码
│   ├── core/                  # 数据模型
│   ├── parsers/               # Excel 解析
│   ├── generators/            # 输出生成（HTML/SVG/Excalidraw/Verilog）
│   ├── templates/             # Jinja2 模板
│   └── cli.py
├── examples/
│   └── sample_module.xlsx     ← 样例 Excel
├── tests/
└── output/                    ← 默认输出目录（git ignored）
```

---

## 不在范围（v0.2）

- ❌ 不生成任何功能性 RTL 逻辑（只生成复位 always 块）
- ❌ 不解析已有 Verilog 文件反向生成 Excel
- ❌ 不支持 Excel 公式、合并单元格、跨 sheet 引用
- ❌ 不做 lint、CDC 检查、综合
- ❌ 不支持 SystemVerilog interface/class
- ❌ `interface=1` 标记仅记录，不做特殊处理（后续版本）

---

## 贡献

待补充。

---

## License

MIT
