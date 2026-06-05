# excel2design v0.5 — Phase 10/11 + 文档 细粒度任务分解

> 生成日期: 2026-06-05
> 前置: Phase 7-9（`@defines` 解析、层次解析器、实例化连接算法、Verilog 实例化模板、多文件输出）
> SPEC 参考: §18（层次化框图）§19（异常与容错）§20（路线图）

---

## Phase 10a — 独立框图批量模式（0.2d）

**目标**: `excel2design diagram --all` 为 Excel 中每个 sheet 独立生成三种框图，放入 `output/doc/` 目录。

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|---|---|---|---|---|
| 10a.1 | CLI `diagram` 子命令新增 `--all` 标志（与现有 `<module>` 参数互斥），当 `--all` 时遍历 `parse_workbook()` 返回的所有模块，为每个模块生成 HTML/SVG/Excalidraw | `excel2design/cli.py` | 45min | `excel2design diagram sample.xlsx --all` 输出全部模块的三种框图；`--all` 与指定 module 名互斥（click 参数冲突检测） |
| 10a.2 | 批量输出目录结构调整：`diagram --all` 时输出到 `output/doc/{module_name}.{html,svg,excalidraw}`（与 §15.4 多文件输出模板一致）；单模块 `diagram` 保持原有 `--output <dir>` 行为不变 | `excel2design/cli.py` | 15min | 批量输出目录 `output/doc/` 包含所有模块的图；单模块调用不受影响 |
| 10a.3 | 批量模式错误处理：对每个模块独立生成，一个模块的解析/生成异常不阻断其它模块（collect errors, report at end）；遇到 `OrphanChildError` / `RecursiveHierarchyError` 时跳过并发 warning | `excel2design/cli.py`, `excel2design/core/exceptions.py` | 20min | 3 模块工作簿中 1 个 bad sheet → 2 个正常输出 + 1 个 error log；exit code 仍为 0（只 report，不 abort） |
| 10a.4 | 单元测试：`tests/e2e/test_cli.py` 新增 `test_diagram_all`（用 3-sheet fixture 验证输出文件数 + 校验 SVG/JSON 合法） | `tests/e2e/test_cli.py` | 15min | 3 个模块 → 9 个输出文件；`xml.etree` parse SVG 通过；`json.loads` parse excalidraw 通过 |
| 10a.5 | 回归验证：现有单模块 `diagram` 命令行为不变（不引入任何 breaking change） | `tests/e2e/test_cli.py` | 10min | 全部 225 现有测试持续通过 |

---

## Phase 10b — 层次化 SVG 框图（0.5d）

**目标**: 生成嵌套矩形 + 子模块间连线的 SVG，按 §18.1-18.2 规范。Wrapper 外框内嵌套子模块矩形框，端口连线区分 wrapper→submodule 和 submodule↔submodule。

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|---|---|---|---|---|
| 10b.1 | 新增 `generators/diagram_svg_hierarchy.py`，导出 `generate_svg_hierarchy(project: Project, top_module: str) -> str`。读取 `Project.hierarchy` 构建子模块列表（`SubmoduleInstance`），确定嵌套深度 | `excel2design/generators/diagram_svg_hierarchy.py` (新建) | 30min | 函数签名正确；对 `sram_wrapper` + 3 个子模块能构建正确的 instance 列表 |
| 10b.2 | 层次布局算法 `_HierarchySVGLayout`：Wrapper 外框包裹所有子模块；子模块按深度层叠排列（depth=1 一行，depth=2 在对应父模块内缩进一行）；动态计算 Canvas 尺寸 | `excel2design/generators/diagram_svg_hierarchy.py` | 1h | `sram_wrapper`（2 子模块 depth=1 + 1 子模块 depth=2）→ 4 个矩形正确嵌套；Canvas 不裁剪元素 |
| 10b.3 | 连线渲染：wrapper port → submodule port（从 wrapper 边缘穿过到子模块边缘）；submodule A → submodule B（子模块间直接 `<line>`）。连线颜色按 clock domain（复用 `clock_colors`）。添加 arrow marker | `excel2design/generators/diagram_svg_hierarchy.py` | 45min | `sram_wrapper.clk → u_ctrl.clk` 连线可见；`u_ctrl.data_bus → u_datapath.data_bus` 子模块间连线可见；箭头方向正确（input→框、框→output） |
| 10b.4 | 端口标签：子模块端口标签为 `{inst_name}.{port_name}[{width}]`（如 `u_ctrl.clk`）；wrapper 顶层端口标签为 `{port_name}[{width}]`。字体 10px 子模块标签（比顶层 12px 小一档） | `excel2design/generators/diagram_svg_hierarchy.py` | 20min | 标签格式正确；嵌套子模块标签用 `instance_name.port_name` 格式 |
| 10b.5 | 集成到 CLI：`diagram` 命令检测 Excel 含多个 sheet + 层次关系 → 自动切换为层次化 SVG 生成；单模块 Excel 仍用原有 `generate_svg()` | `excel2design/cli.py`, `excel2design/generators/__init__.py` | 20min | 单 sheet Excel → 旧 SVG；多 sheet 层次 Excel → 层次化 SVG；`diagram --all` 同时生成独立框图 + 层次总图 |
| 10b.6 | 单元测试：`tests/generators/test_svg_hierarchy.py` — 3 个 case：（1）2 层 `wrapper → u_a, u_b` 连线正确，（2）空子模块不崩溃，（3）`OrphanChildError` sheet 触发 error | `tests/generators/test_svg_hierarchy.py` (新建) | 25min | 3 个测试通过；`xml.etree` parse 输出合法；元素数量 >= 预期（矩形 + 连线 + 标签） |

---

## Phase 10c — 层次化 Excalidraw 框图（0.5d）

**目标**: 与 10b 对等的 Excalidraw 版本，嵌套矩形 + 带标签箭头，符合 §4.4 手绘风格。

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|---|---|---|---|---|
| 10c.1 | 新增 `generators/diagram_excalidraw_hierarchy.py`，导出 `generate_excalidraw_hierarchy(project, top_module) -> str`。复用 `Project.hierarchy` + `SubmoduleInstance` | `excel2design/generators/diagram_excalidraw_hierarchy.py` (新建) | 15min | 函数签名同 10b.1；对 `sram_wrapper` 构建正确 instance 列表 |
| 10c.2 | 层次布局算法 `_HierarchyExcalidrawLayout`：Wrapper 矩形 + 各子模块矩形堆叠；坐标全部为整数；子模块大小按端口数动态缩放（最小 200×120）；动态计算 scene canvas 尺寸 | `excel2design/generators/diagram_excalidraw_hierarchy.py` | 1h | 4 个矩形（1 wrapper + 3 submodule）正确嵌套；所有坐标整数；`appState.viewBackgroundColor="#ffffff"`；无坐标碰撞 |
| 10c.3 | 连线 + 箭头元素：使用 `.type: "arrow"` 元素连接端口。wrapper→submodule 用 `arrow.text` 字段承载信号名；submodule↔submodule 同样方式。箭头颜色按 clock domain（复用 `clock_colors`）。统一用 `fontFamily: 4`（Comic Shanns） | `excel2design/generators/diagram_excalidraw_hierarchy.py` | 45min | 连线箭头数量 >= 端口数；`arrow.text` 含正确的信号名 label；`strokeColor` 按方向/时钟域正确；`json.loads` 解析通过 |
| 10c.4 | 元素 seed 确定性：所有 element seed 从元素 ID 字符串的 hash 派生（`hash(eid) & 0x7FFFFFFF`），确保相同输入 → 相同 JSON 输出（字节稳定） | `excel2design/generators/diagram_excalidraw_hierarchy.py` | 15min | 同一 Project 生成两次 → `json.dumps` 输出字节完全一致 |
| 10c.5 | CLI 集成：多 sheet 层次 Excel → `diagram --format excalidraw` 或 `--format all` 自动调用层次化版本 | `excel2design/cli.py` | 15min | `excel2design diagram hierarchy.xlsx --all --format all` → `doc/sram_wrapper.excalidraw` 为层次总图 |
| 10c.6 | 单元测试：`tests/generators/test_excalidraw_hierarchy.py` — 3 个 case：（1）2 层 wrapper+2 子模块，（2）3 层深度嵌套，（3）字节稳定重复生成 | `tests/generators/test_excalidraw_hierarchy.py` (新建) | 20min | 3 个测试通过；`json.loads` 合法；所有坐标整数；`fontFamily` 均为 4 |

---

## Phase 11 — 集成测试 + 多 sheet fixture（0.5d）

**目标**: 构建层次化测试 fixture，端到端覆盖 §19 全部异常路径（层次异常 + 连线异常）。

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|---|---|---|---|---|
| 11.1 | 创建 `tests/fixtures/hierarchy/` 目录，包含 3 个 Excel fixture：`sram_wrapper_flat.xlsx`（2 层: top + 2 子模块）、`sram_wrapper_deep.xlsx`（3 层: top→u_ctrl→u_fifo）、`bad_orphan.xlsx`（sheet `A.B` 但 `A` 不存在 → 触发 `OrphanChildError`） | `tests/fixtures/hierarchy/*.xlsx`, `tools/gen_fixtures.py` (更新) | 30min | 3 个 .xlsx 文件可用 `openpyxl` 打开；sheet 名符合 `A.B` 约定；`bad_orphan.xlsx` 的 `parse_project()` 抛 `OrphanChildError` |
| 11.2 | Golden baseline：为每个 fixture 生成 `expected/v0.5/{fixture_name}/` 目录，存放 SVG/Excalidraw/HTML/Verilog golden 文件。更新 `tests/test_golden.py` 含层次化 baseline 对比 | `tests/fixtures/expected/v0.5/*/`, `tests/test_golden.py` | 30min | 4 格式 × 3 fixtures = 12 golden 文件；`test_golden.py` 对比通过 |
| 11.3 | 端到端测试：`tests/e2e/test_cli_hierarchy.py` — CLI `diagram --all` / `wrapper --all` / `all --all` 三个子命令全链路验证，含 exit code、输出文件数、SVG 解析、JSON 解析、iverilog 语法 check | `tests/e2e/test_cli_hierarchy.py` (新建) | 20min | 3 个 CLI 路径全部 exit 0；输出文件结构与 §15.4 一致；`diagram --all` 含层次总图 |
| 11.4 | 异常路径测试（§19）：`test_hierarchy_errors.py` — OrphanChildError（exit 4）、RecursiveHierarchyError（sheet 环检测）、EmptyHierarchyError（全是子模块无顶层 → 警告）、WidthMismatchWarning（同名端口位宽不同 → 注释不阻断） | `tests/unit/test_hierarchy_errors.py` (新建) | 25min | 4 个异常 case 全部覆盖；error message 含精确 location；non-fatal warning 不改变 exit code |
| 11.5 | 端到端层次连线验证：`test_connection_algorithm.py` — 检查生成的 Verilog 包含正确的 `.port(signal)` 实例化、兄弟模块间 wire 声明、位宽不匹配 TODO 注释 | `tests/unit/test_connection_algorithm.py` (新建) | 20min | `u_ctrl` 和 `u_datapath` 间 `data_bus` wire 生成正确；`// TODO: width mismatch` 在宽度不一致时出现 |
| 11.6 | 全量回归：运行 `pytest -v` 确保全部现有 225 测试 + 新增测试全部通过；不引入任何回归 | 全项目 | 15min | `pytest` 0 failures；所有新测试在 CI 中可运行 |

---

## 文档更新（0.3d）

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|---|---|---|---|---|
| DOC.1 | `docs/SPEC.md` §18-§20 更新：补充 10a/10b/10c 实现细节（含布局算法伪代码、元素坐标计算公式）；§19 补全异常类型枚举 + 处理策略；§20 路线图状态标记 Phase 7-11 完成 | `docs/SPEC.md` | 30min | §18 含 SVG/Excalidraw 层次布局的完整描述；§19 所有异常类型有触发条件 + 行为说明 |
| DOC.2 | `docs/TASKS.md` 新增 v0.5 章节：Phase 7-11 + 文档任务清单，每项含 ID/描述/状态/commit | `docs/TASKS.md` | 15min | v0.5 任务表格格式与现有 Phase 0-6 一致，状态列初始为 ⬜ / ✅ |
| DOC.3 | `README.md` 补充：（1）层次化 Excel 样例截图/ASCII art；（2）`diagram --all` 使用示例；（3）v0.5 新增 CLI flags 文档 | `README.md` | 15min | README 含层次化样例的 sheet 命名约定说明 + 命令行示例 |
| DOC.4 | `docs/CHANGELOG.md` 追加 v0.5 条目：新增特性（层次解析、连接算法、层次化框图、多文件输出）、breaking changes（API 变化） | `docs/CHANGELOG.md` | 10min | changelog 格式与现有 v0.3/v0.4 条目一致 |

---

## 依赖关系

```
Phase 7 (@defines + .vh + .f)
  │
Phase 8 (层次解析器 + Project 数据模型)
  │
Phase 9a (实例化连接算法)
  │
Phase 9b (Verilog 实例化模板)
  │
Phase 9c (多文件输出 + CLI --all)
  │
  ├── Phase 10a (独立框图批量模式) ← 可并行
  │
  ├── Phase 10b (层次化 SVG 框图) ─┐
  │                                  ├── 可并行（10b/10c 互不依赖）
  └── Phase 10c (层次化 Excalidraw) ─┘
       │
  Phase 11 (集成测试 + fixture) ← 依赖 10a + 10b + 10c
       │
  Docs 更新 ← 可与 11 并行
```

## 估时汇总

| Phase | 内容 | 估时 |
|---|---|---|
| 10a | 独立框图批量模式 | 0.2d (1.75h) |
| 10b | 层次化 SVG 框图 | 0.5d (4.0h) |
| 10c | 层次化 Excalidraw 框图 | 0.5d (3.83h) |
| 11 | 集成测试 + 多 sheet fixture | 0.5d (3.5h) |
| DOC | 文档更新 | 0.3d (2.0h) |
| **总计** | | **~2.0d (15.1h)** |

> **注**: 原 SPEC §20 估时 Phase 10+11+文档 = 2.3d，细化后约 2.0d（接近一致）。10b/10c 可并行派 subagent，实际 wall-clock 更短。
