# Changelog

> 用户视角的 changelog（区别于 git log 的工程视角）

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
