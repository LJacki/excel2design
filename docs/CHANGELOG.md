# Changelog

> 用户视角的 changelog（区别于 git log 的工程视角）

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
