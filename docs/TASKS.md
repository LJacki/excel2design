# 任务追踪（Tasks）

> 实时更新。每完成一个 todo 改状态；卡点写到末尾的 "## Stuck" 段。
> Jack 必须决策的事项写到 "## Pending Decision" 段。

---

## v0.3.4 — 框图 v0.4 + Verilog 列对齐（2026-06-04）

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 0.4.1 | 三种框图方向箭头（HTML/SVG/Excalidraw） | ✅ | 357cea0 |
| 0.4.2 | Excalidraw 文本宽度 + 字体（Comic Shanns） | ✅ | 08b6ba0, 3dd2310 |
| 0.4.3 | Excalidraw 箭头统一等长 + containerId 绑定 | ✅ | 67ab363, b3cb6d4 |
| 0.4.4 | 时钟域颜色系统（蓝/绿系列） | ✅ | 5e30ea6, e6a2698 |
| 0.4.5 | 亮色 palette 调整 + SVG 参数优化 | ✅ | 16ee3b2, 39938c9 |
| 0.4.6 | Verilog 列对齐（param + port 六列） | ✅ | 38a6443, 72ca7a9, ef147a8 |
| 0.4.7 | 测试更新：225 passed | ✅ | — |

## v0.5 — 子模块层次化 + 实例化（2026-06-05 planned）

> SPEC §15-20 完整规格。详情见 `docs/TASKS_v0.5_plan.md`（Phase 7-9c）和 `docs/TASKS_v0.5_diagram_plan.md`（Phase 10-11）。

### Phase 7: @defines 解析 + .vh / .f 生成（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 7.1 | `Define` dataclass | ⏳ | 0.05d |
| 7.2 | `@defines` sheet 解析 | ⏳ | 0.1d |
| 7.3 | 层次异常类型（OrphanChild/Recursive/Empty） | ⏳ | 0.05d |
| 7.4 | `.vh` 生成器 + Jinja2 模板 | ⏳ | 0.1d |
| 7.5 | `.f` 文件列表生成器 | ⏳ | 0.05d |
| 7.6 | 单元测试（8+ cases） | ⏳ | 0.1d |
| 7.7 | 集成到 parse_workbook（向后兼容） | ⏳ | 0.05d |

### Phase 8: 层次解析器 + Project 数据模型（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 8.1 | `SubmoduleInstance` + `Project` dataclass | ⏳ | 0.1d |
| 8.2 | `parse_project()` in `parsers/hierarchy.py` | ⏳ | 0.15d |
| 8.3 | 层次异常检测（orphan/recursive/no-top） | ⏳ | 0.1d |
| 8.4 | BFS 遍历顺序 `walk_bfs()` | ⏳ | 0.05d |
| 8.5 | 单元测试（10+ cases） | ⏳ | 0.1d |

### Phase 9a: 实例化连接算法（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 9a.1 | 三级端口匹配（parent/sibling/param） | ⏳ | 0.15d |
| 9a.2 | 位宽不匹配检测 | ⏳ | 0.1d |
| 9a.3 | 内部 wire 生成决策 | ⏳ | 0.1d |
| 9a.4 | 单元测试（12+ cases） | ⏳ | 0.15d |

### Phase 9b: Verilog 实例化模板（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 9b.1 | `partial_instance.j2` 子模板 | ⏳ | 0.1d |
| 9b.2 | 扩展 `verilog_wrapper.j2`（internal wires + sub-modules） | ⏳ | 0.1d |
| 9b.3 | `generate_wrapper(project=...)` 扩展 | ⏳ | 0.1d |
| 9b.4 | 单元测试（8+ cases） | ⏳ | 0.15d |
| 9b.5 | 参数化实例覆盖 | ⏳ | 0.05d |

### Phase 9c: 多文件输出 + CLI --all（0.3d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 9c.1 | `generate_all()` 多文件编排器 | ⏳ | 0.15d |
| 9c.2 | CLI 新增 `--all` / `project` 子命令 | ⏳ | 0.1d |
| 9c.3 | E2E 测试（6+ cases） | ⏳ | 0.05d |
| 9c.4 | 层次化 fixture 准备（3 个） | ⏳ | 0.1d |

### Phase 10a: 独立框图批量模式（0.2d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 10a.1 | CLI `diagram --all` 批量模式 | ⏳ | 0.1d |
| 10a.2 | 批量输出目录调整 | ⏳ | 0.03d |
| 10a.3 | 批量错误处理（单模块失败不阻断） | ⏳ | 0.04d |
| 10a.4 | 单元测试 | ⏳ | 0.03d |

### Phase 10b: 层次化 SVG 框图（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 10b.1 | `diagram_svg_hierarchy.py` 生成器 | ⏳ | 0.1d |
| 10b.2 | 层次布局算法（嵌套矩形+连线） | ⏳ | 0.15d |
| 10b.3 | 连线渲染（wrapper→sub, sub↔sub） | ⏳ | 0.1d |
| 10b.4 | 单元测试 | ⏳ | 0.15d |

### Phase 10c: 层次化 Excalidraw 框图（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 10c.1 | `diagram_excalidraw_hierarchy.py` 生成器 | ⏳ | 0.1d |
| 10c.2 | 层次布局算法 | ⏳ | 0.15d |
| 10c.3 | 连线渲染 | ⏳ | 0.1d |
| 10c.4 | 单元测试 | ⏳ | 0.15d |

### Phase 11: 集成测试（0.5d）

| ID | 任务 | 状态 | 估时 |
|---|---|---|---|
| 11.1 | 层次化 fixture（3 个：flat/2level/3level） | ⏳ | 0.15d |
| 11.2 | E2E 集成测试（CLI project 命令） | ⏳ | 0.1d |
| 11.3 | 框图层次化集成测试 | ⏳ | 0.1d |
| 11.4 | Golden baseline 更新 | ⏳ | 0.1d |
| 11.5 | 回归验证（现有 225 tests） | ⏳ | 0.05d |

### 依赖关系

```
P7 (defines) ────────────────────────────────────────┐
                                                       ├──→ P9c (多文件输出)
P8 (hierarchy) ──→ P9a (连接) ──→ P9b (实例化) ────┘
                                                       │
P10a (框图批量) ──→ P10b (SVG层次) ──→ P10c (Excalidraw) ──→ P11 (集成)
```

- **P7 ∥ P8** 可并行
- **P10b ∥ P10c** 可并行（各自独立的 diagram 生成器）

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
| 2 | HTML 框图 | Subagent A | ✅ | 见 SUBAGENT_LOG.md (435503d, 17 tests) |
| 3 | SVG 框图 | Subagent B | ✅ | 见 SUBAGENT_LOG.md (fd29900, 8 tests) |
| 4 | Excalidraw 框图 | Subagent C | ✅ | 见 SUBAGENT_LOG.md (6db2c6f, 8 tests) |

## Phase 5a/5b — Verilog wrapper（小马亲自）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 5a.1 | templates/verilog_wrapper.j2 + Jinja2 env | ✅ | Phase 5 | d9419ae |
| 5a.2 | generators/verilog.py — 端口 + parameter 注入 | ✅ | Phase 5 | d9419ae |
| 5a.3 | generators/verilog.py — initial 块 | ✅ | Phase 5 | d9419ae |
| 5a.4 | tests/unit/test_verilog.py 基础 case | ✅ | Phase 5 | d9419ae |
| 5b.1 | 多 (clock, reset_type) 分组算法 | ✅ | Phase 5 | d9419ae |
| 5b.2 | 异步/同步 always 块生成 | ✅ | Phase 5 | d9419ae |
| 5b.3 | TODO 注释 + 字节稳定铁律落实 | ✅ | Phase 5 | d9419ae |
| 5b.4 | tests/unit/test_verilog.py 高级 case（混合/多 clock/none） | ✅ | Phase 5 | d9419ae |
| 5b.5 | iverilog -t null 语法 check | ⏳ | — | iverilog 未装（环境无） |

## Phase 6 — CLI + 集成（1.5d）

| ID | 任务 | 状态 | 完成时间 | commit |
|---|---|---|---|---|
| 6.1 | cli.py — click 子命令（parse/diagram/wrapper/all） | ✅ | Phase 6 | e484a3a |
| 6.2 | tests/e2e/test_cli.py | ✅ | Phase 6 | e484a3a |
| 6.3 | README 截图 + 完善文档 | ✅ | Phase 6 | (待 commit) |
| 6.4 | pyproject 入口点 + pip install -e . 验证 | ✅ | Phase 0 | 65d16e6 |

---

## Pending Decision（等 Jack 决策）

（暂无）

## Stuck（卡点记录）

（暂无）
