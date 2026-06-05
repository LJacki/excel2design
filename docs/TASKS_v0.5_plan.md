# excel2design v0.5 — 子模块层次化任务分解

> 版本: v0.5-plan-draft
> 最后更新: 2026-06-05
> 依据: SPEC.md §15-§20
> 当前代码基线: v0.3.0 + v0.4 补丁（225 tests passed）

---

## 概述

v0.5 新增四大能力：
1. **`@defines` sheet** → `.vh` 通用头文件 + `.f` 文件列表
2. **层次化 sheet 名**（`top.u_sub.u_subsub`）→ `Project` 树形数据模型
3. **实例化连接算法** → 自动匹配端口/生成内部 wire/标记位宽不匹配
4. **多文件输出** → 按 `rtl/` / `define/` / `filelist/` / `doc/` 目录结构输出

总估时：~4.3d（含 Phase 10/11 框图部分，本计划仅覆盖 Phase 7-9c，约 2.3d）

---

## Phase 7: `@defines` 解析 + `.vh` + `.f` 生成（0.5d）

### 前置条件
- `parsers/excel.py` 当前 `parse_workbook()` 遍历所有 sheet，跳过空 sheet 和 `@defines`（如果存在会被当作模块解析并失败）
- 需要识别 `@defines` sheet 并特殊处理

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|----|---------|---------|------|---------|
| **7.1** | **新增 `Define` dataclass** — 在 `core/models.py` 中添加 `Define` 数据类（`name: str, value: str, comment: Optional[str]`），同时在 `excel2design/__init__.py` 中导出 | `core/models.py`, `__init__.py` | 0.05d | `Define("SRM_DW", "256", "SRAM 数据通路位宽")` 可实例化；`from excel2design import Define` 可用 |
| **7.2** | **新增 `@defines` sheet 解析** — 修改 `parsers/excel.py`，在 `parse_workbook()` 中识别 sheet 名 `@defines`（大小写不敏感？SPEC 固定为 `@defines`），调用新函数 `_parse_defines(ws)` 解析 `# === DEFINES ===` marker + 三列表头（name/value/comment），返回 `list[Define]`。空 value → `Define.value=""` 表示无值宏。不校验 Verilog identifier（`define 允许特殊字符）。跳过 `@defines` 的模块解析 | `parsers/excel.py` | 0.1d | `parse_workbook("hierarchy.xlsx")` 正确返回 defines 列表；`@defines` 不出现在 modules 列表中；三列表头校验失败抛 `HeaderMismatchError`；marker 缺失抛 `MarkerMissingError` |
| **7.3** | **新增层次相关异常** — 在 `core/exceptions.py` 中添加 `OrphanChildError(sheet, parent)`、`RecursiveHierarchyError(sheet)`、`EmptyHierarchyError`（SPEC §19.1）；同时在 `__init__.py` 导出 | `core/exceptions.py`, `__init__.py` | 0.05d | 各异常可独立实例化；`__str__` 输出含 sheet 名和修复建议 |
| **7.4** | **`.vh` 生成器** — 新建 `generators/defines.py` + `templates/defines_vh.j2`，Jinja2 模板输出 `define FOO VAL` 格式（左对齐）；生成函数签名 `generate_vh(defines: list[Define], module_name: str) -> str` | `generators/defines.py`, `templates/defines_vh.j2` | 0.1d | `generate_vh([Define("SRM_DW","256")], "sram_wrapper")` 输出 `define SRM_DW 256`；空 value → `define FOO`（无值）；文件头含生成注释；字节稳定（两次调用 diff 为空） |
| **7.5** | **`.f` 文件列表生成器** — 在 `generators/defines.py` 中添加 `generate_f(filelist: list[str], module_name: str) -> str`，按层次遍历顺序列出 `rtl/<module>.v` 路径 | `generators/defines.py` | 0.05d | `generate_f(["sram_wrapper", "u_ctrl", "u_datapath"], "sram_wrapper")` 输出三行带 `//` 注释头的文件列表 |
| **7.6** | **单元测试** — 新建 `tests/unit/test_defines.py`，覆盖：正常解析、空 value 宏、@defines 缺失 marker、空 @defines sheet、.vh 格式验证、.f 格式验证 | `tests/unit/test_defines.py` | 0.1d | 8+ test cases 全部通过；覆盖 §16.1-16.3 所有规则 |
| **7.7** | **集成到 parse_workbook 返回值** — 修改 `parse_workbook()` 返回类型为 `tuple[list[Module], list[Define]]` 或新建包装 dataclass；确保向后兼容现有 `get_module()` 调用 | `parsers/excel.py`, `cli.py` | 0.05d | 现有 225 tests 不回归；CLI `parse` 命令能显示 defines 信息 |

---

## Phase 8: 层次解析器 + Project 数据模型（0.5d）

### 前置条件
- 当前 `Module` 无层级概念；`parse_workbook` 只返回扁平的 `list[Module]`
- SPEC §15.1 定义 sheet 名用 `.` 表示层级：`sram_wrapper.u_ctrl.u_fifo`

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|----|---------|---------|------|---------|
| **8.1** | **新增 `SubmoduleInstance` 和 `Project` dataclass** — 在 `core/models.py` 中添加 SPEC §15.2 定义的两个数据类。`Project.modules: dict[str, Module]`（key=sheet_name）、`Project.hierarchy: dict[str, list[str]]`（parent_sheet→children）、`Project.defines: list[Define]`、`Project.top_modules: list[str]`（无 `.` 的 sheet）。添加 `Project.get_submodules(parent: str) -> list[SubmoduleInstance]` 方法 | `core/models.py`, `__init__.py` | 0.1d | `Project` 可实例化；`top_modules` 正确识别顶层；`get_submodules()` 返回带深度信息的子模块列表 |
| **8.2** | **实现 `parse_project()` — 新建 `parsers/hierarchy.py`** — 核心函数签名 `parse_project(xlsx_path: Path) -> Project`。流程：1) 调用 `parse_workbook()` 获取 modules + defines；2) 按 sheet 名中的 `.` 构建 hierarchy tree；3) 验证层次完整性（父模块存在、无循环）；4) 返回 `Project` | `parsers/hierarchy.py` | 0.15d | `parse_project("hierarchy.xlsx")` 正确构建三级嵌套树；顶层模块 `sram_wrapper` 的 children 包含 `sram_wrapper.u_ctrl` 和 `sram_wrapper.u_datapath` |
| **8.3** | **层次异常检测** — 在 `parsers/hierarchy.py` 中实现三项检测：1) orphan child（`A.B` 存在但 `A` 不存在 → `OrphanChildError`）；2) 循环引用（sheet 名自引用或有向图环 → `RecursiveHierarchyError`）；3) 无顶层模块（全是子模块 sheet → `EmptyHierarchyError` 警告但不阻断）| `parsers/hierarchy.py` | 0.1d | `OrphanChildError` 在父模块缺失时触发；`RecursiveHierarchyError` 在 `a.b.a` 或 `a.b.c.a` 时触发；`EmptyHierarchyError` 所有 sheet 都含 `.` 时警告 |
| **8.4** | **层次遍历顺序** — 在 `Project` 中添加 `walk_bfs() -> list[str]`（广度优先，先顶层后子模块，同层按 sheet 名字典序）。此顺序用于 `.f` 文件生成和实例化顺序 | `core/models.py` | 0.05d | `walk_bfs()` 输出 `["sram_wrapper", "sram_wrapper.u_ctrl", "sram_wrapper.u_datapath", "sram_wrapper.u_ctrl.u_fifo"]` 的正确顺序 |
| **8.5** | **单元测试** — 新建 `tests/unit/test_hierarchy.py`，覆盖：单模块无层级、二级嵌套、三级嵌套、多顶层模块、orphan child、循环引用、无顶层模块警告 | `tests/unit/test_hierarchy.py` | 0.1d | 10+ test cases 通过，覆盖 §15.1、§15.3、§19.1 所有规则 |

---

## Phase 9a: 实例化连接算法（0.5d）

### 前置条件
- 需要 `Project` 数据模型和 `Module` 端口/参数查询能力
- SPEC §17 定义三级优先级连接策略

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|----|---------|---------|------|---------|
| **9a.1** | **端口匹配算法** — 新建 `core/connection.py`，实现 `match_port(port: Port, parent_module: Module, sibling_modules: list[Module]) -> ConnectionResult`。按 SPEC §17.1 三级优先级：1) 父模块有同名端口 → `ConnectionResult(kind="parent_port", target=...)`；2) 兄弟模块有同名端口 → `ConnectionResult(kind="sibling_port", target=...)`（多个兄弟有同名端口时按 SPEC §19.2 选第一个并生成 `AmbiguousConnectionWarning`）；3) 父模块有同名 parameter → `ConnectionResult(kind="parent_param", target=...)`；未匹配 → `ConnectionResult(kind="unconnected")` | `core/connection.py` | 0.15d | 三级优先级正确；同名端口匹配不区分大小写（暂定区分）；多个兄弟同名端口取 alphabetically 第一个并附 warning |
| **9a.2** | **位宽不匹配检测** — 在 `core/connection.py` 中实现 `check_width_match(port_a: Port, port_b: Port) -> WidthMatch`（返回 Match/PartialMismatch/FullMismatch + 描述）。v0.5 仅比较固定宽度（有 msb 的）；参数化宽度默认不比较（视为潜在匹配） | `core/connection.py` | 0.1d | 固定宽度 `[7:0]` vs `[7:0]` → Match；`[7:0]` vs `[15:0]` → Mismatch 带注释 `// TODO: width mismatch — a:[7:0] vs b:[15:0]`；参数化宽度 `[DATA_WIDTH-1:0]` vs `[DATA_WIDTH-1:0]` → Match；参数化 vs 固定 → Potential（不标 mismatch，留注释） |
| **9a.3** | **内部 wire 生成决策** — 在 `core/connection.py` 中实现 `collect_internal_wires(project: Project, top_sheet: str) -> list[InternalWire]`。遍历顶层模块的所有子模块端口，将所有 sibling 连接归类为内部 wire（去重：同信号名只生成一根 wire）。wire 宽度取涉及的端口位宽中最大的（保守策略） | `core/connection.py` | 0.1d | `data_bus` 连接 `u_ctrl` ↔ `u_datapath` → 生成一根 `wire [SRM_DW-1:0] data_bus;` 声明 + `// connects u_ctrl ↔ u_datapath` 注释 |
| **9a.4** | **单元测试** — 新建 `tests/unit/test_connection.py`，覆盖：父端口匹配、兄弟端口匹配、parameter 匹配、未匹配、位宽匹配/不匹配、多个兄弟同名端口、去重内部 wire、所有三个优先级联合测试 | `tests/unit/test_connection.py` | 0.15d | 12+ test cases 通过；覆盖 §17.1-17.2 和 §19.2 所有规则 |

---

## Phase 9b: Verilog 实例化模板（0.5d）

### 前置条件
- 依赖 Phase 9a 的 `ConnectionResult` 和 `InternalWire` 数据结构
- 基于目前的 `generators/verilog.py` + `templates/verilog_wrapper.j2` 扩展

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|----|---------|---------|------|---------|
| **9b.1** | **实例化子模板** — 新建 `templates/partial_instance.j2`，Jinja2 宏/片段：为单个子模块生成 `module_name instance_name ( .port(signal), ... );` 的实例化代码。端口按 Excel 顺序排列；连接信号名来自 `ConnectionResult.target`；未连接端口生成悬空 `()` + TODO 注释 | `templates/partial_instance.j2` | 0.1d | 模板渲染输出符合 SPEC §17.3 格式：`.port_name (signal_name), // 可选注释` |
| **9b.2** | **扩展 wrapper 主模板** — 修改 `templates/verilog_wrapper.j2`，在 `endmodule` 前加入三段（条件渲染）：1) `// ---------- INTERNAL WIRES ----------` 段（仅当有内部 wire）；2) `// ---------- SUB-MODULES ----------` 段（仅当有子模块）。复用现有端口声明、参数声明、initial/always 块逻辑 | `templates/verilog_wrapper.j2` | 0.1d | 无子模块的模块生成与原模板完全一致（字节稳定）；有子模块的模块额外生成 internal wires + sub-modules 段 |
| **9b.3** | **扩展 `generate_wrapper()`** — 修改 `generators/verilog.py`，新增可选参数 `project: Optional[Project] = None`。若传入 project 且有子模块，调用 Phase 9a 算法获取连接结果和内部 wire，传入模板；否则行为与现有一致 | `generators/verilog.py` | 0.1d | `generate_wrapper(module)` 不传 project → 原行为不变；`generate_wrapper(module, project=project)` → 生成含子模块实例化的 wrapper |
| **9b.4** | **单元测试** — 扩展 `tests/generators/test_verilog.py`，新增：单子模块实例化、多子模块实例化、内部 wire 生成、未连接端口悬空标记、位宽不匹配注释、无子模块模块不回归验证 | `tests/generators/test_verilog.py` | 0.15d | 8+ 新 test cases；原有 20+ verilog tests 不回归；生成 Verilog 可被 `iverilog -t null` 语法 check（非强制） |
| **9b.5** | **参数化实例覆盖** — 在 `generators/verilog.py` 中实现：若子模块有 parameter，生成 `#(.PARAM(value))` 参数覆盖连接。v0.5 仅支持同名 parameter 直通（父模块 parameter → 子模块 parameter），不做 override 值计算 | `generators/verilog.py` | 0.05d | 父模块有 `parameter WIDTH=8`，子模块也有 `parameter WIDTH=8` → 生成 `#(.WIDTH(WIDTH))`；无同名 parameter → 不生成 `#()` 部分 |

---

## Phase 9c: 多文件输出 + CLI `--all`（0.3d）

### 前置条件
- 依赖 Phase 7（.vh/.f）、Phase 8（Project）、Phase 9a（连接算法）、Phase 9b（wrapper 实例化）

| ID | 任务描述 | 涉及文件 | 估时 | 验收标准 |
|----|---------|---------|------|---------|
| **9c.1** | **多文件输出编排器** — 新建 `generators/project_output.py`，实现 `generate_all(project: Project, output_dir: Path) -> list[Path]`。按 SPEC §15.4 目录结构输出所有文件：`output/<top_module>/define/*.vh`、`output/<top_module>/filelist/*.f`、`output/<top_module>/rtl/*.v`、`output/<top_module>/doc/*.html|svg|excalidraw`。按顶层模块分组，若多个顶层模块各自一个目录 | `generators/project_output.py` | 0.15d | 调用后磁盘目录结构完全匹配 SPEC §15.4；返回所有输出文件路径列表；目录不存在时自动创建 |
| **9c.2** | **CLI 新增 `--all` / `--project` 标志** — 修改 `cli.py`：1) `excel2design wrapper <excel> --all` → 批量为所有模块生成 wrapper；2) `excel2design diagram <excel> --all` → 批量为所有模块生成框图（SPEC §18.3）；3) 新增子命令 `excel2design project <excel> [--output <dir>]` → 调用 `generate_all()` 输出完整项目 | `cli.py` | 0.1d | `excel2design project hierarchy.xlsx` 输出完整目录结构；`--all` 标志在 wrapper/diagram 子命令中正常工作；退出码规范不变（2/3/4） |
| **9c.3** | **端到端测试** — 新建 `tests/e2e/test_project.py`，用临时目录验证：1) 完整层次化 fixture（`tests/fixtures/hierarchy/` 下放 `sram_wrapper.xlsx` 含 @defines + 3 层嵌套）；2) CLI `project` 命令输出目录结构正确；3) `.vh` 含所有 define；4) `.f` 文件列表顺序正确；5) wrapper `.v` 含子模块实例化；6) 所有图框文件存在 | `tests/e2e/test_project.py` | 0.05d | 6+ e2e cases 通过；exit code=0；所有文件存在且非空 |
| **9c.4** | **层次化 fixture 准备** — 新建 3 个 fixture（用 `tools/gen_fixtures.py` 或手动）：1) `hierarchy_flat.xlsx` — 单模块无层次；2) `hierarchy_2level.xlsx` — `top + top.u_a + top.u_b`；3) `hierarchy_3level.xlsx` — `top + top.u_a + top.u_a.u_fifo + top.u_b`；每个 fixture 配 `expected/` golden baseline（至少 .v + .vh） | `tests/fixtures/hierarchy/`, `tests/fixtures/hierarchy/expected/` | 0.1d | 3 个 fixture .xlsx 可用 openpyxl 打开；golden baseline 含至少 .v+.vh 预期输出；pytest 可 diff 校验 |

---

## 跨 Phase 依赖关系

```
Phase 7 (defines) ─────────────────────────────────────────┐
                                                            ├──→ Phase 9c (多文件输出)
Phase 8 (hierarchy/Project) ───→ Phase 9a (连接算法) ──→ Phase 9b (实例化模板) ──┘
```

- **Phase 7 和 Phase 8 可并行**（共享 `parsers/excel.py` 但改动区域不同）
- **Phase 9a 必须在 Phase 8 之后**（需要 Project 数据模型）
- **Phase 9b 必须在 Phase 9a 之后**（需要 ConnectionResult）
- **Phase 9c 必须在 Phase 7 + Phase 9b 之后**（需要 .vh/.f + 实例化 wrapper）

---

## 风险与注意点

| 风险 | 影响 Phase | 缓解措施 |
|------|-----------|---------|
| `parse_workbook()` 返回类型变更破坏现有调用 | 7, 8 | 保持向后兼容 `parse_workbook() -> list[Module]`；新 API 走 `parse_project() -> Project` |
| Sheet 名含 `.` 的模块在现有解析器中会被当作普通模块名尝试 identifier 校验（`.` 不合法）| 8 | Phase 8 在 `parse_project()` 中先提取层级名，各子模块 sheet 名的最后一段（实例名）做 identifier 校验 |
| Jinja2 模板复杂度增加，字节稳定难保证 | 9b | 用 `include` + `macro` 拆分模板；严格保持现有模块的 `generate_wrapper()` 输出不变（golden diff） |
| 参数化位宽匹配判断困难 | 9a | v0.5 保守策略：参数化宽度默认视为匹配，仅固定宽度做精确比较；不匹配只注释不阻断 |
| 多顶层模块场景未充分定义 | 8, 9c | SPEC §15.4 暗示每顶层模块一个目录；Phase 9c.1 实现此语义 |

---

## 增量测试策略

| 层次 | Phase 7 | Phase 8 | Phase 9a | Phase 9b | Phase 9c |
|------|---------|---------|---------|---------|---------|
| Unit | `test_defines.py` (8+) | `test_hierarchy.py` (10+) | `test_connection.py` (12+) | `test_verilog.py` 扩展 (8+) | — |
| Generator | `generate_vh()` / `generate_f()` | — | — | `generate_wrapper()` 含子模块 | `generate_all()` |
| E2E | — | — | — | — | `test_project.py` (6+) |
| Golden | `.vh` golden diff | — | — | `.v` golden diff | 多文件 golden diff |
| **不回归** | 225 tests | 225 tests | 225 tests | 225+28 tests | 所有前面 tests |
| **预估新增** | ~10 tests | ~12 tests | ~14 tests | ~10 tests | ~8 tests |
| **总 tests 目标** | 235 | 247 | 261 | 271 | 279 |

---

## 验收总标准（Phase 7-9c 全部完成）

1. ✅ `@defines` sheet 解析正确，`.vh` / `.f` 生成格式匹配 SPEC §16
2. ✅ `parse_project()` 正确构建多级嵌套树，异常情况面面俱到
3. ✅ 同名端口自动匹配（父端口/兄弟端口/parameter），位宽不匹配标记 TODO
4. ✅ wrapper 模板正确生成子模块实例化代码，含内部 wire 声明
5. ✅ 多文件输出目录结构匹配 SPEC §15.4
6. ✅ CLI `--all` / `project` 子命令正常工作
7. ✅ 所有现有 225 tests 不回归
8. ✅ 新增 ~50+ tests 全部通过
9. ✅ 字节稳定铁律保持（golden diff 为空）
