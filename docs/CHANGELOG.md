# Changelog

> 用户视角的 changelog（区别于 git log 的工程视角）

---

## v0.5.1 (2026-06-10) — 优化修复（P0/P1 综合）

> 触发: subagent 优化扫描 → 小马独立验证 → 立即修复
> 8 commits, 56 新增测试, 282 total passed
> 修复 5 个 P0（其中 2 个是 subagent 漏报/降级）+ 4 个 P1

### P0 — 必须修

**P0-4 [升级 P2 → P0] SVG / Excalidraw 字节稳定铁律违反**
- 根因: `utils/clock_colors.py` 和 `diagram_svg.py` 用 Python 内建 `hash()` 做 clock-name 映射，受 `PYTHONHASHSEED` 影响
- 验证: 同 fixture 跑两次 md5 不同 (`56fae15e` vs `33c82878`)，跨 CI 必挂
- 修复: `hashlib.md5` 替代 `hash()` + 抽 `_stable_marker_token` helper
- 回归测试: `tests/generators/test_byte_stability.py` (2 tests, 跨 PYTHONHASHSEED=42/99 验证)

**P0-5 [升级 P1 → P0] always 块硬编码 `rst_n`**
- 根因: `verilog_wrapper.j2:56` 模板硬编码 `negedge rst_n` / `if (!rst_n)`，没接 `_detect_reset_per_clock` 算出的 per-domain reset port name
- 真实影响: 多时钟域工程 (`rst_a_n` / `rst_b_n` / `cfg_rst_n`) 生成的 always 永远是错的
- 修复: `AlwaysGroup.reset_name` 字段 + `_resolve_reset_names_per_clock` 计算 + 模板 `{{ group.reset_name }}` 替换
- 回归测试: `tests/generators/test_always_reset.py` (3 tests: per-domain / legacy fallback / sync-only)

**P0-1 `_handle_errors` 死代码 + 6× try/except 重复**
- 根因: `cli.py:42-62` 定义了 `_handle_errors(ctx, exc)` 但 click group 没注册；每个子命令都手动复制 try/except
- 修复: 删死代码 + 抽 `@catch_errors` decorator + `_exit_code` helper（同时修了一个隐藏 bug：custom `ModuleNotFoundError` 被 Python 内建 shadow，旧代码靠 click 9.x 默认行为蒙混）
- 收益: -90 行重复，错误处理 1 处

**P0-2 `project` 子命令无 e2e 测试**
- 根因: v0.5 主打新命令 (`excel2design project`) 完全没有端到端保护
- 修复: 加 5 个 e2e 测试（exit 0 / rtl 创建 / filelist / 框图 / 错误退出码）+ 1 个 help 输出 assert

### P1 — 应该修

**P1-1 v0.5 新模块加 unit tests**
- 新增 38 个 unit test: `test_hierarchy.py` (8) + `test_connection.py` (16) + `test_defines.py` (8) + `test_hierarchy_diagrams.py` (10)
- 覆盖: parse_project / get_submodules / walk_bfs / OrphanChildError / match_port 4 级优先级 / collect_internal_wires / generate_vh / generate_f / diagram_svg_hierarchy / diagram_excalidraw_hierarchy

**P1-2 删 `collect_internal_wires` 死代码**
- `connection.py::collect_internal_wires` 死代码（verilog.py 重新实现了一遍并加了 width 注释），还有配套的 `InternalWire` dataclass 和 `_widest_port` helper
- 删除: -55 行死代码

**P1-3 抽 `_ALIGN_PAD = 1` 常量**
- 消除 `verilog.py` 里 5 处 magic `+1` padding（param + port + instance 三类对齐），统一在 SPEC §17.6 引用

**P1-5 抽 `hierarchy_layout.py` 公共布局模块**
- 新建 `generators/hierarchy_layout.py`（~180 行）含 `compute_hierarchy_layout` 函数 + `HierarchyLayout` / `SubLayout` / `Wire` dataclass
- **不重构现有 renderer**（保持 byte-stable）
- **未来新 renderer**（如 `diagram_html_hierarchy`）可直接用，新加 8 个 unit test

### P2 — 锦上添花

**P2-3 `pyproject.toml` version 0.3.0 → 0.5.1**

### Subagent v1 报告 vs 小马独立验证

| 项 | subagent 报 | 独立验证 | 结果 |
|---|---|---|---|
| P0-1 `_handle_errors` 死代码 | P0 | ✅ verified | 修了 |
| P0-2 `project` 无 e2e | P0 | ✅ verified | 修了 |
| P0-3 `match_port` 优先级反语义 | P0 | ❌ **误报** | 没动 |
| `hash(clock)` 字节不稳定 | P2 | ✅ 升级 P0 | 修了 |
| `always` 块硬编码 `rst_n` | P1 | ✅ 升级 P0 | 修了 |
| `collect_internal_wires` 死代码 | P1 | ✅ verified | 删了 |
| v0.5 新模块无单测 | P1 | ✅ verified | 加了 38 |
| `_ALIGN_PAD` 散落 | P1 | ✅ verified | 抽了 |
| `_fmt_params` width 边界 | P1 | ❌ 撤回 | SPEC 未定义上限 |
| 三个对齐循环结构重复 | P1 | ❌ 撤回 | adapter 比原版复杂 |

### Subagent 教训

1. **报告未落地** — subagent 跑 50 次 API 调用但**没真正写报告文件**（只有口头总结）。我重新独立做了完整审查。
2. **严重度排序错** — `hash()` 字节不稳定是 SPEC §5.7 核心铁律违反，应该 P0 不是 P2
3. **误报 P0-3** — 把 SPEC 实际正确的优先级（1a+1b→2→3）说成反语义

### 测试统计
- 226 → **282 passed** (+56)
- 新增 6 个测试文件
- e2e: 17 → 23 (+6, 含 1 个 help 增强)

### 升级路径
- 任何从 v0.5 升到 v0.5.1 的工程不需要改任何 Excel 模板
- wrapper 输出的 always 块现在使用 per-domain reset port name（如果你之前 hardcode 了 `if (!rst_n)`，现在要重新生成）
- byte-stable SVG/Excalidraw 输出**完全一致**（除非 hash seed 改变）

---

## v0.5.0 (2026-06-10) — 子模块层次化 + 实例化（大版本）

> 15 commits, 159 新增测试, 226 total passed ✅
> SPEC 升级 v0.5.1 → v0.5.2（§17.6 instance 列对齐规范）
> 关键新命令：`excel2design project <xlsx> -o <dir>` — 一键产出多文件工程

### Phase 7 — `@defines` 解析 + `.vh` / `.f` 生成
- 新增 `Define` dataclass + 异常类型
- `@defines` sheet 解析 + marker 校验
- 层次异常（OrphanChild / Recursive / EmptyHierarchy）
- `.vh` 生成器 + Jinja2 模板（如 `\`define ADC_EN 32`）
- `.f` 文件列表生成器（按 BFS 顺序）
- 完整单元测试

### Phase 8 — 层次解析器 + `Project` 数据模型
- `SubmoduleInstance` + `Project` dataclass（含 hierarchy dict / top_modules / `get_submodules` / `walk_bfs`）
- `parse_project()` in `parsers/hierarchy.py` — 从多 sheet 构建嵌套树
- 层次异常检测（orphan / recursive / no-top）
- BFS 遍历顺序 `walk_bfs()` 保证确定性输出
- 单元测试

### Phase 9a — 实例化连接算法
- **三级端口匹配**：parent port → sibling port → parent param
- **模糊后缀匹配**：同名 + 数字后缀（`adc_a` ↔ `adc_b`）自动消除歧义
- **位宽不匹配检测**：发现不一致时标记 `TODO: width mismatch`
- **内部 wire 生成决策**：从连接关系推导 wire 列表（不再单独扫描）
- 单元测试

### Phase 9b — Verilog 实例化模板
- `partial_instance.j2` 子模板抽离
- 扩展 `verilog_wrapper.j2`（internal wires + sub-modules 段）
- `generate_wrapper(project=...)` 支持整工程生成
- **关键 v0.5.2 修复**：param 的 `name` 列宽取 `max(max_pn, max_pn_p)`、`value` 列填充到 `max_cn`，确保 `)` 和 `,` 在整个 instance 块内同列（SPEC §17.6）
- 单元测试（8+ cases）+ 参数化实例覆盖

### Phase 9c — 多文件输出 + CLI `project`
- `generate_all()` 多文件编排器（按 BFS 顺序输出 `rtl/*.v` + `define/*.vh` + `filelist/*.f` + `doc/*.{html,svg,excalidraw}`）
- **新 CLI 命令** `excel2design project <xlsx> -o <dir>` — 一键产出完整工程
- 端到端测试（CLI project 命令 subprocess）

### Phase 10a — 独立框图批量模式
- CLI `diagram --all` 批量生成所有模块
- 批量输出目录调整 + 错误处理
- 单元测试

### Phase 10b — 层次化 SVG 框图（**新格式**）
- `diagram_svg_hierarchy.py` 生成器
- **层次布局算法**：嵌套矩形（top 框内嵌 sub-module 框）
- **连线渲染**：wrapper→sub、sub↔sub 内部走线
- 端口标签 `inst_name.port_name` 格式
- CLI 自动检测多 sheet → 切换到层次图

### Phase 10c — 层次化 Excalidraw 框图（**新格式**）
- `diagram_excalidraw_hierarchy.py` 生成器
- 嵌套矩形 + arrow 元素 + 信号名 label
- seed 确定性 + 字节稳定
- CLI 集成

### Phase 11 — 集成测试 + Golden baseline
- 新增层次化 fixture `hierarchy_2level.xlsx`
- Golden baseline `expected/hierarchy_2level.json`
- 回归验证 226 tests all pass

### 验收（vs SPEC v0.5.2 验收标准）
| 标准 | 结果 |
|------|------|
| `@defines` sheet 解析 + `.vh`/`.f` 生成 | ✅ done |
| `parse_project()` 构建多级嵌套树 | ✅ done |
| 同名端口自动匹配 + 位宽不匹配标 TODO | ✅ done |
| wrapper 模板含子模块实例化 + 内部 wire | ✅ done |
| 多文件输出目录结构 match SPEC §15.4 | ✅ done |
| CLI `project` 正常工作 | ✅ done |
| 所有现有 tests 不回归 | ✅ 226 passed |
| 字节稳定铁律保持 | ✅ golden diff=0 |
| instance 列对齐（param `)`/`,` 与 port 同列） | ✅ done |

### 真实项目样例
完整 7 模块 / 3 级层次示例见 `examples/sample_module_iic_top.xlsx`：
- 顶层 `iic_top` 包含 `iic_slave` + `reg_cfg` + `tempsensor_crg`
- 同名端口用 `_a` / `_b` 后缀（`adc_a` / `adc_b`）演示模糊匹配
- 一行命令出全套：`excel2design project examples/sample_module_iic_top.xlsx -o output/`
- 生成 32 个文件：7 个 `.v` + 1 个 `.vh` + 1 个 `.f` + 23 个图（7 模块 × 3 格式 + 2 层次图）

---

## v0.3.5 (2026-06-09) — 回归修复：signed 正则 + hierarchy baseline

### 修复
- **test_signed_keyword_present**：正则从 `signed reg` → `reg signed`，匹配新的 Verilog 端口顺序
- **test_all_fixtures_have_baselines**：新增 `hierarchy_2level.xlsx` 的 golden baseline
- **gen_baseline.py / test_golden.py**：升级支持多模块 fixture（list-of-dict 格式）

### 测试
- 225 → **226 全过**（+1 hierarchy_2level golden test）
- 新 tag `v0.3.5`

---

## v0.3.4 (2026-06-04) — 框图 v0.4 + Verilog 列对齐（15 commits）

### 框图 v0.4 — 三种格式全面升级
- **HTML**：从两栏列表 → CSS 模块框 + Unicode 方向箭头（→ 输入 / 输出→ / ↔ inout）
- **SVG**：新增 `<marker>` arrowhead 三角箭头，时钟域分色（input 蓝色系 / output 绿色系）
- **Excalidraw**：
  - 字体：Virgil(1) → Comic Shanns(4)，干净手写风
  - 文本宽度动态计算，不再截断
  - 箭头带方向，统一等长，padding 50px
  - 时钟域分色

### 时钟域颜色系统（新增 `utils/clock_colors.py`）
- 输入 → 8 色蓝色系（`#00B0FF` / `#00E5FF` / `#18FFFF`…）
- 输出 → 8 色绿色系（`#00E676` / `#76FF03` / `#B9F6CA`…）
- 同 clock name × direction 确定性映射

### Verilog Wrapper — 工业级列对齐
- **Parameter 声明**：`=` 号对齐，value 列对齐，逗号列对齐
- **Port 声明**：direction(7) / signed(7) / type(5) / width(max) / name(max) / comma 六列左对齐
- 去掉了冗余 output wire 声明和 TODO 注释段
- 模板简化：port → initial/always → endmodule

### SVG 参数处理
- 参数从框内移除（用户反馈：怎么放都难看）

### 测试
- 227 → **225 全过**（去掉了 7 个 TODO 相关测试，新增箭头/字体/对齐测试）

## v0.3.3 (2026-06-03) — DeepSeek V4 Pro 第三轮审查修复

### 修复
- **P0-3**：3 个图表生成器（HTML/SVG/Excalidraw）修复 `assert msb is not None` 崩溃问题，统一与 `to_verilog()` 对称处理 `msb=None` 边界

### 测试
- 221 → **227 全过**（+6 P0-3 测试）
- 验证：`excel2design all` / `diagram` 子命令遇到 width=None 不再 AssertionError

### Commit
- `b33fa04` "fix: P0-3 diagram generators now tolerate width=None (3 generators, 6 tests)"

### Tag
- `v0.3.3`

---

## v0.3.2 (2026-06-02) — DeepSeek V4 Pro 审查修复

### 修复（基于 docs/REVIEW_v2.md 评价）
- **P0-1**：`PortWidth.to_verilog()` 处理 `msb=None` 边界（width 列空时正确生成无位宽端口，而不是 `[None:0]` 非法 Verilog）
- **P1-5**：`wrapper` 子命令自动创建输出目录（之前会 `FileNotFoundError → exit 1`）

### 测试
- 216 → **221 全过**（+3 unit + 2 e2e）
- 验证：width 列空 → 合法 1-bit 端口 ✓；输出目录深 3 层自动创建 ✓

### Commit
- `cda08d6` "fix: DeepSeek V4 Pro review findings — P0-1 (width=None bug) + P1-5 (wrapper output dir)"

### Tag
- `v0.3.2`

---

## v0.3.1 (2026-06-02) — v0.3 验收 P1 修复

### 修复（基于 docs/REVIEW.md 评价）
- **P1-3**：TODO 注释增加每个时钟域对应的 reset signal name 提示 + 匹配策略标签（explicit/name match/fallback/no port）
- **P1-4**：`BadZipFile` / `InvalidFileException` 现在映射到 exit 4（SPEC §6）

### 测试
- 211 → **216 全过**（+3 wrapper + 2 e2e）
- 修复后 4 fixture 全部正常生成

### Commit
- `a3e6330` "fix(wrapper): P1-3 add per-clock reset signal hint in TODO comment"
- `1b1a46e` "fix(cli): P1-4 map BadZipFile/InvalidFileException to exit 4"

### Tag
- `v0.3.1`

---

## v0.3 (2026-06-02) — Phase 5 + Phase 6 + 收尾

### Phase 5 — Verilog Wrapper（23 tests, 197 总数）
- `excel2design/generators/verilog.py` (110 行)
- `excel2design/templates/verilog_wrapper.j2` (130 行) + `partial_always.j2`
- **多 (clock, reset_type) always 分块**（SPEC §3.5.6）
- 字节稳定铁律全部落实（LF 行尾 / 无 trailing whitespace / Jinja2 禁 random）
- reset_type=none 行为修正（仅 initial 块，不生成 always 块）
- **关键决策**：Jinja2 env `trim_blocks=False`（避免 for 循环吃掉换行导致端口挤一行）

### Phase 6 — CLI + 端到端（14 tests, 211 总数）
- `excel2design/cli.py` (180 行) — click 子命令
  - `parse` / `diagram` / `wrapper` / `all`
  - 退出码 0/2/3/4 按 SPEC §6
- `tests/e2e/test_cli.py` (14 tests) — 端到端 subprocess 测试
- README 大幅扩展（完整示例输出 / 项目结构 / 设计原则）

### 总测试：**211 passed**

### Tag
- `phase-5-done` (commit d9419ae)
- `phase-6-done` (commit e484a3a)

---

## v0.3.2 (2026-06-02) — Phase 2/3/4 三种框图（subagent 并行）

3 个 subagent 并行实现，**33 个新测试全过**：

### Phase 2 — HTML 框图（Subagent A）
- `excel2design/generators/diagram_html.py` (129 行)
- `excel2design/templates/diagram_html.j2` (251 行)
- `tests/generators/test_html.py` (**17 tests**)
- 浅色主题 + CSS 变量 + Flexbox 响应式

### Phase 3 — SVG 框图（Subagent B）
- `excel2design/generators/diagram_svg.py` (309 行)
- `tests/generators/test_svg.py` (**8 tests**)
- ElementTree 构造（不用 Jinja2，遵守 SPEC §9 ADR）

### Phase 4 — Excalidraw 框图（Subagent C）
- `excel2design/generators/diagram_excalidraw.py` (247 行)
- `tests/generators/test_excalidraw.py` (**8 tests**)
- 纯 dict + json.dumps，固定 seed 保证字节稳定

### 关键经验
- Subagent A 进程 600s 超时（但**产出完整**）— 提示：要**严格限制测试数量**到 8-10 个
- Subagent B/C 在 388s / 547s 内完成
- 三次都产出**测试全过**的高质量代码
- 总计：166 → 174 测试

---

## v0.3.1 (2026-06-01) — Phase 0/1/1.5 落地

实现 18 个 commit：

### Phase 0 — 项目骨架
- pyproject.toml（openpyxl/Jinja2/click/pytest）
- 完整目录结构
- 样例 Excel 生成脚本 + `examples/sample_module.xlsx`
- 3 个 smoke test 通过
- GitHub Actions CI（py3.10/3.11/3.12）

### Phase 1 — 数据模型 + 解析器（136 单测 100% 通过）
- 异常体系（10 个类，3 层分类，行列号定位）
- 4 个核心工具：cell_to_str / identifier / width / default
- 数据模型 Port/Parameter/Module + 4 个 enum
- 完整 Excel 解析器（marker 定位、两段式、11 种错误检测）
- 公共 API

### Phase 1.5 — Golden baseline 框架（5 个新测试）
- 4 个 fixture（uart_rx / axi_crossbar 30 端口 / multi_clock 3 时钟 / empty_ports）
- 4 个 JSON baseline
- `test_golden.py` 字节级回归测试

---

## v0.3 (2026-06-01) — 设计规格冻结

- SPEC 升级到 v0.3，含 14 章 + 902 行
- 集成 subagent 设计审查的 5 个必须补丁（M1-M5）：
  - 多时钟域 always 分组
  - 异常三层分类 + 行列号定位
  - 字节稳定铁律
  - Verilog identifier 校验
  - reset_type=none 行为修正
- 新增任务分配方案（§15）+ 启动清单（§16）
- 阶段估时 5d → 10.5d（更现实）

## v0.2 (2026-06-01) — 核心设计确认

- Excel 模板改为模块级两段式（参数 + 端口）
- Port 列 7 → 10（补 reset_type / signed / interface）
- Wrapper 自动按 reset_type 生成复位 always
- README 同步

## v0.1 (2026-06-01) — 初版设计

- 项目骨架 + 第一版 SPEC
