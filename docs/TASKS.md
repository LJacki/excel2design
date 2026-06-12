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

## v0.5 — 子模块层次化 + 实例化（2026-06-05 ~ 06-09 全部完成）

> 15 commits, 159 新增测试，226 total passed ✅
> SPEC v0.5.1 — 模糊匹配 / 方向箭头 / 层次图连线 / 连接算法

### Phase 7: @defines 解析 + .vh / .f 生成

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 7.1 | `Define` dataclass + 异常类型 | ✅ | 11936ed |
| 7.2 | `@defines` sheet 解析 + marker 校验 | ✅ | b8ce209, 11936ed |
| 7.3 | 层次异常（OrphanChild/Recursive/EmptyHierarchy） | ✅ | 11936ed |
| 7.4 | `.vh` 生成器 + Jinja2 模板 | ✅ | 11936ed |
| 7.5 | `.f` 文件列表生成器 | ✅ | 11936ed |
| 7.6 | 单元测试 | ✅ | 11936ed |
| 7.7 | parse_workbook 集成（向后兼容） | ✅ | 11936ed |

### Phase 8: 层次解析器 + Project 数据模型

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 8.1 | `SubmoduleInstance` + `Project` dataclass（含 hierarchy dict / top_modules / get_submodules / walk_bfs） | ✅ | 11936ed, 79764c3 |
| 8.2 | `parse_project()` in `parsers/hierarchy.py` | ✅ | 11936ed |
| 8.3 | 层次异常检测（orphan/recursive/no-top） | ✅ | 11936ed |
| 8.4 | BFS 遍历顺序 `walk_bfs()` | ✅ | 11936ed |
| 8.5 | 单元测试 | ✅ | 11936ed |

### Phase 9a: 实例化连接算法

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 9a.1 | 三级端口匹配（parent/sibling/param）+ 模糊后缀匹配 | ✅ | 11936ed, 6b27d22, 4e4faf0 |
| 9a.2 | 位宽不匹配检测 | ✅ | 11936ed |
| 9a.3 | 内部 wire 生成决策 | ✅ | c97deb6 |
| 9a.4 | 单元测试 | ✅ | 11936ed, c97deb6 |

### Phase 9b: Verilog 实例化模板

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 9b.1 | `partial_instance.j2` 子模板 | ✅ | 11936ed |
| 9b.2 | 扩展 `verilog_wrapper.j2`（internal wires + sub-modules） | ✅ | 7e0f3b2 |
| 9b.3 | `generate_wrapper(project=...)` 扩展 | ✅ | 7e0f3b2 |
| 9b.4 | 单元测试（8+ cases） | ✅ | 11936ed, 7e0f3b2 |
| 9b.5 | 参数化实例覆盖 | ✅ | b8ce209 |

### Phase 9c: 多文件输出 + CLI project

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 9c.1 | `generate_all()` 多文件编排器 | ✅ | d90fdd6 |
| 9c.2 | CLI `project` 子命令 + `--all` 标志 | ✅ | d90fdd6 |
| 9c.3 | E2E 测试（CLI project 命令） | ✅ | d90fdd6 |
| 9c.4 | 层次化 fixture（hierarchy_2level.xlsx） | ✅ | 9eb580a, 7f1ad5f |

### Phase 10a: 独立框图批量模式

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 10a.1 | CLI `diagram --all` 批量模式 | ✅ | d90fdd6 |
| 10a.2 | 批量输出目录调整 | ✅ | d90fdd6 |
| 10a.3 | 批量错误处理 | ✅ | d90fdd6 |
| 10a.4 | 单元测试 | ✅ | d90fdd6 |

### Phase 10b: 层次化 SVG 框图

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 10b.1 | `diagram_svg_hierarchy.py` 生成器 | ✅ | 34c65ea |
| 10b.2 | 层次布局算法（嵌套矩形+连线） | ✅ | 34c65ea |
| 10b.3 | 连线渲染（wrapper→sub, sub↔sub） | ✅ | 4e4faf0 |
| 10b.4 | 端口标签（inst_name.port_name） | ✅ | 34c65ea |
| 10b.5 | CLI 集成（多 sheet 自动切换层次图） | ✅ | 34c65ea |
| 10b.6 | 单元测试 | ✅ | 34c65ea |

### Phase 10c: 层次化 Excalidraw 框图

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 10c.1 | `diagram_excalidraw_hierarchy.py` 生成器 | ✅ | 5cf988c |
| 10c.2 | 层次布局算法 + 嵌套矩形 | ✅ | 5cf988c |
| 10c.3 | 连线 + arrow 元素 + 信号名 label | ✅ | 5cf988c |
| 10c.4 | seed 确定性 + 字节稳定 | ✅ | 5cf988c |
| 10c.5 | CLI 集成 | ✅ | 5cf988c |
| 10c.6 | 单元测试 | ✅ | 5cf988c |

### Phase 11: 集成测试

| ID | 任务 | 状态 | commit |
|----|------|------|--------|
| 11.1 | 层次化 fixture（hierarchy_2level） | ✅ | 9eb580a |
| 11.2 | Golden baseline（expected/hierarchy_2level.json） | ✅ | 7b7e15b |
| 11.3 | 回归验证（226 tests all pass） | ✅ | 7b7e15b |

### 依赖关系

```
P7 (defines) ────────────────────────────────────────┐
                                                       ├──→ P9c (多文件输出)
P8 (hierarchy) ──→ P9a (连接) ──→ P9b (实例化) ────┘
                                                       │
P10a (框图批量) ──→ P10b (SVG层次) ──→ P10c (Excalidraw) ──→ P11 (集成)
```

### 验收标准对比

| 标准 | 结果 |
|------|------|
| @defines sheet 解析 + .vh/.f 生成 | ✅ done |
| `parse_project()` 构建多级嵌套树 | ✅ done |
| 同名端口自动匹配 + 位宽不匹配标记 TODO | ✅ done |
| wrapper 模板含子模块实例化 + 内部 wire | ✅ done |
| 多文件输出目录结构 match SPEC §15.4 | ✅ done |
| CLI `project` / `--all` 正常工作 | ✅ done |
| 所有现有 tests 不回归 | ✅ 226 passed |
| 字节稳定铁律保持 | ✅ golden diff=0 |

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

---

## v0.5.1 — 优化修复（2026-06-10 完成）

> 触发: subagent 优化扫描 → 小马独立验证 → 立即修复 5 P0 + 4 P1
> 282 total passed (56 新增)
> 6 commits

| ID | 任务 | 状态 | 关键 commit |
|---|---|---|---|
| 0.5.1.1 | P0-4 hash(clock) → hashlib.md5 (跨进程字节稳定) | ✅ | (pending commit) |
| 0.5.1.2 | P0-5 always 块 per-domain reset_name 注入 | ✅ | (pending commit) |
| 0.5.1.3 | P0-1 catch_errors decorator + 删 90 行死代码 | ✅ | (pending commit) |
| 0.5.1.4 | P0-2 project e2e 5+1 测试 | ✅ | (pending commit) |
| 0.5.1.5 | P1-1 v0.5 新模块 38 个 unit tests | ✅ | (pending commit) |
| 0.5.1.6 | P1-2 删 collect_internal_wires 死代码 (-55 行) | ✅ | (pending commit) |
| 0.5.1.7 | P1-3 _ALIGN_PAD 常量 (消除 5 处 magic +1) | ✅ | (pending commit) |
| 0.5.1.8 | P1-5 hierarchy_layout 公共模块 + 8 unit tests | ✅ | (pending commit) |
| 0.5.1.9 | P2-3 pyproject version 0.3.0 → 0.5.1 | ✅ | (pending commit) |
| 0.5.1.10 | P1-4 抽 _align_columns — **撤回** | ❌ cancelled | adapter 比原版复杂 |
| 0.5.1.11 | P1-6 _fmt_params width 边界 — **撤回** | ❌ cancelled | SPEC 未定义上限 |

### Subagent 教训

- subagent v1 报告未真正写文件 (50 次 API 调用但 /tmp/e2d_optimize_review.md 不存在)
- subagent v1 严重度排序错: hash 字节稳定 (P2) 实际是 P0
- subagent v1 误报 P0-3: match_port 优先级符合 SPEC §17.1 (1a+1b→2→3)

## v0.6 — 小痛点优先（2026-06-12 路线图）

> SPEC §21 详细 phase 分解
> 总投入 ~1.7d，4 个开发 phase + 1 个文档 phase
> 验收: 282 现有测试 0 回归 + 新增 ≥ 16 unit + ≥ 4 e2e

### Phase 12 — `Port.array_dim` 端口数组

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 12.1 | `Port.array_dim: Optional[List[int]]` 字段 | ⏳ | — |
| 12.2 | Excel 解析: `array_dim` 列 `[7:0]` / `[3:0][1:0]` | ⏳ | — |
| 12.3 | Verilog 生成: `output [3:0] data [7:0]` | ⏳ | — |
| 12.4 | SVG 框图: 端口标签后缀 `[7:0]` | ⏳ | — |
| 12.5 | 实例化连接: 单元素访问 / 整数组 TODO | ⏳ | — |
| 12.6 | 字节稳定铁律验证 | ✅ | — |

### Phase 13 — `interface=1` 真实处理

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 13.1 | `Port.interface: bool` 字段落地 | ⏳ | — |
| 13.2 | Verilog: `interface_name.signal` 引用 | ⏳ | — |
| 13.3 | SVG/Excalidraw: 虚线 group container | ⏳ | — |
| 13.4 | README + 截图 | ✅ | — |

### Phase 14 — 端口/parameter 重名容错

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 14.1 | `NamingConflictWarning` 而非 error | ⏳ | — |
| 14.2 | verilog 加 `_p` 后缀避免编译错误 | ⏳ | — |
| 14.3 | README "Known Limitations" 段 | ✅ | — |

### Phase 15 — 同名端口多驱动方向判断

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 15.1 | `SubmoduleInstance.drivers: List[str]` 字段 | ⏳ | — |
| 15.2 | 多 driver: 全 output→error, 含 inout→wire+assign | ⏳ | — |
| 15.3 | Verilog: inout 双向 `wire ...; assign ...` | ⏳ | — |
| 15.4 | 框图: 多驱动连线粗线 + 警告色 | ✅ | — |

### Phase 16 — 文档收尾

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 16.1 | CHANGELOG.md v0.6 段 | ⏳ | — |
| 16.2 | TASKS.md 更新 | ⏳ | — |
| 16.3 | SPEC changelog patch ID M1-M5 | ⏳ | — |
| 16.4 | pyproject version 0.5.1 → 0.6.0 | ✅ | — |

---

## Pending Decision（等 Jack 决策）

- v0.6 是否要开 git branch `v0.6-dev`？还是直接在 main 上推？
- 4 个 phase 是串行还是并行派 subagent？（array_dim 涉及 3 处改动，建议串行；后 3 个可考虑并行）

## Stuck（卡点记录）

- `.hermes/.env` 4 个 key 仍 `***` 占位符（修复方式待定）
- GitHub Release 页面未创建（依赖 GITHUB_TOKEN 修复）

## v0.6 — 小痛点优先（2026-06-12 路线图）

> SPEC §21 详细 phase 分解
> 总投入 ~1.7d，4 个开发 phase + 1 个文档 phase
> 验收: 282 现有测试 0 回归 + 新增 ≥ 16 unit + ≥ 4 e2e

### Phase 12 — Port.array_dim 端口数组

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 12.1 | Port.array_dim Optional[List[int]] 字段 | ⏳ | — |
| 12.2 | Excel 解析 array_dim 列 [7:0] / [3:0][1:0] | ⏳ | — |
| 12.3 | Verilog output [3:0] data [7:0] | ⏳ | — |
| 12.4 | SVG 端口标签后缀 [7:0] | ⏳ | — |
| 12.5 | 实例化连接 单元素访问 / 整数组 TODO | ⏳ | — |
| 12.6 | 字节稳定铁律验证 | ✅ | — |

### Phase 13 — interface=1 真实处理

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 13.1 | Port.interface bool 字段落地 | ⏳ | — |
| 13.2 | Verilog interface_name.signal 引用 | ⏳ | — |
| 13.3 | SVG/Excalidraw 虚线 group container | ⏳ | — |
| 13.4 | README + 截图 | ✅ | — |

### Phase 14 — 端口/parameter 重名容错

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 14.1 | NamingConflictWarning 而非 error | ⏳ | — |
| 14.2 | verilog 加 _p 后缀避免编译错误 | ⏳ | — |
| 14.3 | README Known Limitations 段 | ✅ | — |

### Phase 15 — 同名端口多驱动方向判断

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 15.1 | SubmoduleInstance.drivers List[str] 字段 | ⏳ | — |
| 15.2 | 多 driver 全 output error / 含 inout wire+assign | ⏳ | — |
| 15.3 | Verilog inout 双向 wire + assign | ⏳ | — |
| 15.4 | 框图 多驱动连线粗线 + 警告色 | ✅ | — |

### Phase 16 — 文档收尾

| ID | 任务 | 状态 | commit |
|---|---|---|---|
| 16.1 | CHANGELOG.md v0.6 段 | ⏳ | — |
| 16.2 | TASKS.md 更新 | ⏳ | — |
| 16.3 | SPEC changelog patch ID M1-M5 | ✅ | — |
| 16.4 | pyproject version 0.5.1 → 0.6.0 | ✅ | — |

---

## Pending Decision（等 Jack 决策）

- v0.6 是否要开 git branch v0.6-dev？还是直接在 main 上推？
- 4 个 phase 是串行还是并行派 subagent？（array_dim 涉及 3 处改动，建议串行；后 3 个可考虑并行）

## Stuck（卡点记录）

- .hermes/.env 4 个 key 仍 *** 占位符（修复方式待定）
- GitHub Release 页面未创建（依赖 GITHUB_TOKEN 修复）
