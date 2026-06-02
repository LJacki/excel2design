# 任务追踪（Tasks）

> 实时更新。每完成一个 todo 改状态；卡点写到末尾的 "## Stuck" 段。
> Jack 必须决策的事项写到 "## Pending Decision" 段。

---

## Phase 0 — 项目骨架（0.5d）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 0.1 | pyproject.toml（openpyxl/jinja2/click/pytest） | ✅ | Phase 0 | 65d16e6 |
| 0.2 | 目录结构（core/parsers/generators/templates） | ✅ | Phase 0 | 65d16e6 |
| 0.3 | tools/gen_sample.py — 样例 Excel 生成脚本 | ✅ | Phase 0 | 0922854 |
| 0.4 | 样例 Excel examples/sample_module.xlsx | ✅ | Phase 0 | 0922854 |
| 0.5 | conftest.py + pytest 跑通空测试 | ✅ | Phase 0 | ebd0054 |
| 0.6 | .github/workflows/ci.yml 雏形 | ✅ | Phase 0 | ebd0054 |

## Phase 1 — 数据模型 + Excel 解析器（2.5d）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 1.1 | core/exceptions.py — §3.4 异常体系 | ✅ | Phase 1 | 16b93ea |
| 1.2 | core/port.py + core/parameter.py + core/module.py | ✅ | Phase 1 | 97500ab |
| 1.3 | utils/identifier.py — VERILOG_KEYWORDS + check_identifier | ✅ | Phase 1 | 0ae884e |
| 1.4 | utils/cell.py — cell_to_str + 类型白名单 | ✅ | Phase 1 | d998139 |
| 1.5 | parsers/excel.py — marker 解析 + 两段式布局 | ✅ | Phase 1 | 766f087 |
| 1.6 | parsers/width.py — parse_width | ✅ | Phase 1 | 8953170 |
| 1.7 | parsers/default.py — default 字面量规则 | ✅ | Phase 1 | 4536124 |
| 1.8 | tests/unit/test_parser_* | ✅ | Phase 1 | 766f087 |
| 1.9 | tests/unit/test_identifier.py + test_cell.py + test_width.py + test_models.py + test_default.py | ✅ | Phase 1 | multiple |

## Phase 1.5 — Golden baseline（0.5d）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 1.5.1 | tests/fixtures/uart_rx.xlsx | ✅ | Phase 1.5 | e392f8b |
| 1.5.2 | tests/fixtures/axi_crossbar.xlsx | ✅ | Phase 1.5 | e392f8b |
| 1.5.3 | tests/fixtures/multi_clock.xlsx | ✅ | Phase 1.5 | e392f8b |
| 1.5.4 | tests/fixtures/empty_ports.xlsx | ✅ | Phase 1.5 | e392f8b |
| 1.5.5 | tests/fixtures/expected/ 目录 + JSON baseline | ✅ | Phase 1.5 | e392f8b |
| 1.5.6 | tests/test_golden.py | ✅ | Phase 1.5 | e392f8b |

## Phase 2/3/4 — 三种框图（并行派 subagent）

| Phase | 任务 | 执行人 | 状态 | subagent_log |
|---|---|---|---|---|
| 2 | HTML 框图 | Subagent A | ⏳ | 见 SUBAGENT_LOG.md |
| 3 | SVG 框图 | Subagent B | ⏳ | 见 SUBAGENT_LOG.md |
| 4 | Excalidraw 框图 | Subagent C | ⏳ | 见 SUBAGENT_LOG.md |

## Phase 5a/5b — Verilog wrapper（小马亲自）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 5a.1 | templates/verilog_wrapper.j2 + Jinja2 env | ⏳ | | |
| 5a.2 | generators/verilog.py — 端口 + parameter 注入 | ⏳ | | |
| 5a.3 | generators/verilog.py — initial 块 | ⏳ | | |
| 5a.4 | tests/unit/test_verilog.py 基础 case | ⏳ | | |
| 5b.1 | 多 (clock, reset_type) 分组算法 | ⏳ | | |
| 5b.2 | 异步/同步 always 块生成 | ⏳ | | |
| 5b.3 | TODO 注释 + 字节稳定铁律落实 | ⏳ | | |
| 5b.4 | tests/unit/test_verilog.py 高级 case（混合/多 clock/none） | ⏳ | | |
| 5b.5 | iverilog -t null 语法 check | ⏳ | | |

## Phase 6 — CLI + 集成（1.5d）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 6.1 | cli.py — click 子命令（parse/diagram/wrapper/all） | ⏳ | | |
| 6.2 | tests/e2e/test_cli.py | ⏳ | | |
| 6.3 | README 截图 + 完善文档 | ⏳ | | |
| 6.4 | pyproject 入口点 + pip install -e . 验证 | ⏳ | | |

---

## Pending Decision（等 Jack 决策）

（暂无）

## Stuck（卡点记录）

（暂无）
