# excel2design v0.3.2 独立验收评价报告（DeepSeek V4 Pro）

**评审日期**: 2026-06-03
**评审模型**: DeepSeek V4 Pro（api.deepseek.com, model=deepseek-v4-pro）
**项目版本**: v0.3.1 → v0.3.2（tag `v0.3.2`）
**评审方法**: 静态代码阅读 + 上一轮实测结论的复核 + 6 维度逻辑分析

> **本评审与 docs/REVIEW_v2.md 独立完成。** DeepSeek V4 Pro 在 v0.3.1 上找到了 2 个 P0 严重 bug（width=None 非法 Verilog + wrapper 输出目录），**v0.3.2 必须实际修复这 2 个 bug**。本次评审聚焦于：(1) 修复是否真的进入代码并被测试覆盖；(2) 是否引入了新风险；(3) 6 维度整体质量是否仍可发 stable。

---

## 0. 评审方法学说明

**重要**：本次评审 subagent **没有 terminal 工具**，因此**无法**实际执行 `pytest`、运行 CLI、生成 `/tmp/v3_*` 产物。所有结论均基于：
- 对修复点代码的精读（`parsers/width.py`、`cli.py`、`tests/unit/test_width.py`、`tests/e2e/test_cli.py`、`templates/verilog_wrapper.j2`）
- 对剩余 P1 点的代码确认（`diagram_svg.py`、`diagram_excalidraw.py`）
- 上一轮 REVIEW_v2.md 实测数据的复用（md5 字节稳定、jinja2 注入 4 种变体、跨格式对比、CLI exit code 8 个异常路径）
- 静态逻辑分析（`to_verilog()` 修复条件对所有路径是否覆盖）

> DeepSeek V4 Pro 上一轮（v0.3.1 验收）做了实际生成 4 fixture × 4 格式 + 字节级 md5 + jinja2 注入实测，**实测结论在 v0.3.2 仍然有效**，因为生成器代码（`diagram_html.py` / `diagram_svg.py` / `diagram_excalidraw.py` / `verilog.py`）没有改动。

---

## 1. P0/P1 修复验证（关键）

### 1.1 P0-1：width 列空时不再生成 `[None:0]`

**代码确认**（`excel2design/parsers/width.py` line 32-42）：

```python
def to_verilog(self) -> str:
    """..."""
    if not self.is_parameter and (self.msb == 0 or self.msb is None):
        return ""
    if self.is_parameter:
        return f"[{self.raw}-1:0]"
    # fixed
    return f"[{self.msb}:0]"
```

**分析**：
- 条件 `not self.is_parameter and (self.msb == 0 or self.msb is None)` **同时覆盖**了 `parse_width("1")`（msb=0）和 `parse_width(None)`（msb=None）两种 1-bit 情况
- `parse_width("")`/`parse_width("   ")`/`parse_width(None)` 都会走 `parsers/width.py:62` 的 `return PortWidth(raw="1", msb=None, is_parameter=False)` 路径
- `to_verilog()` 返回 `""` 后，`templates/verilog_wrapper.j2` 的 `{{ port.width.to_verilog() }}` 渲染为空字符串
- 模板 line 24-29 的双空格 `{{ " " if port.width.to_verilog() else "  " }}` 条件判断确保 1-bit 端口对齐正确（**`"" ` 视为 falsy → 双空格**，保持视觉对齐）✓

**测试覆盖**（`tests/unit/test_width.py` line 141-164）：

| 测试 | 覆盖路径 | 期望 |
|---|---|---|
| `test_to_verilog_default_1bit_omits_brackets` | `parse_width(None)` → `to_verilog()` | `""` |
| `test_to_verilog_explicit_1bit_still_works` | `parse_width("1")` → `to_verilog()` | `""`（回归保护）|
| `test_to_verilog_no_none_in_output` | 任何路径都不输出 "None" | `assert "None" not in w.to_verilog()` |

**结论**：**P0-1 修复有效 ✓**。3 个新 test 覆盖了边界 + 回归。

**⚠️ 但是有一个未覆盖的盲点**（v0.3.2 未修）：
- `diagram_svg.py:60` `assert p.width.msb is not None` 和 `diagram_excalidraw.py:58` `assert p.width.msb is not None` 在 non-parameter 分支假设 `msb` 不为 None
- `diagram_html.py:57` 同样有 `assert p.width.msb is not None`
- **如果一个 Excel Port 段 width 列为空**，现在 Verilog 正确生成 1-bit 端口（不再崩溃），**但 SVG/Excalidraw/HTML 生成器会 `AssertionError` 崩溃**
- v0.3.1 同样有此问题（v0.3.1 也会 `AssertionError`），v0.3.2 修复 P0-1 时**只修了 Verilog 路径**，没修图表路径
- 实务影响：工程师现在 wrapper 可以跑、但 `all` 命令会崩（因为 `all` 同时生成 v + 3 个图）
- **评级**：P1-7（v0.3.2 新增遗漏，不阻塞工程师单独使用 wrapper）

### 1.2 P1-5：wrapper 子命令自动创建输出目录

**代码确认**（`excel2design/cli.py` line 190-196）：

```python
out_path = output or Path(f"./{module_name}.v")
# P1-5 fix: ensure parent dir exists, so single-file output works
# even when --output points to a not-yet-created directory.
out_path.parent.mkdir(parents=True, exist_ok=True)
v = generate_wrapper(m, source_file=excel.name, source_sheet=module_name)
out_path.write_text(v, encoding="utf-8", newline="\n")
click.echo(f"Wrote {out_path}")
```

**分析**：
- `out_path.parent.mkdir(parents=True, exist_ok=True)` 是 Python 标准做法
- `parents=True` 允许任意深度目录创建
- `exist_ok=True` 避免目录已存在时抛异常
- 注释明确说明这是 P1-5 修复，可追溯 ✓
- 边界情况：如果 `out_path` 没有 parent（`out_path == Path("x.v")`），`parent` 是 `Path(".")`，`.mkdir()` 不抛异常 ✓

**测试覆盖**（`tests/e2e/test_cli.py` line 198-213）：

```python
def test_wrapper_creates_missing_output_dir(tmp_path: Path) -> None:
    """P1-5 fix: --output path with a not-yet-existing parent dir should work."""
    out = tmp_path / "new_subdir" / "deep" / "uart_rx.v"
    assert not out.parent.exists()
    r = _run_cli("wrapper", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
                 "--output", str(out))
    assert r.returncode == 0
    assert out.exists()
    ...
```

**结论**：**P1-5 修复有效 ✓**。测试是 hermetic 的（用 `tmp_path` 隔离），3 层深目录创建场景覆盖完整。

---

## 2. 评分（10 分制）

| 维度 | v0.3.1 分数 | v0.3.2 分数 | 变化 | 备注 |
|---|---|---|---|---|
| 代码质量 | 7/10 | **8.5/10** | +1.5 | P0-1 + P1-5 已修，3 行 + 1 行代码 + 5 个新 test |
| 输出美观 | 6/10 | 6/10 | 0 | SVG/Excalidraw 信息密度低 + 缺色差 + 缺连线 — 未修 |
| 内容完整性 | 7/10 | 7/10 | 0 | 跨格式信息不一致（HTML/Verilog 有 comment+signed，SVG/Excalidraw 没有）— 未修 |
| 文档质量 | 9/10 | **9.5/10** | +0.5 | CHANGELOG.md 清楚记录 P0-1/P1-5，REVIEW_v2.md 闭环 |
| 工程化 | 9/10 | **9.5/10** | +0.5 | 字节稳定 16/16 ✓（生成器未改）；exit code 全部正确；output dir 自动创建 |
| **总体** | **7.5/10** | **8.5/10** | +1.0 | **可发 v0.3.2 stable**，但有 1 个新增 P1 盲点（SVG/Excalidraw 对 width=None 的 AssertionError） |

**是否通过验收**: ⚠️ **通过 with caveat** — v0.3.2 修复了 v0.3.1 的 P0 严重 bug（非法 Verilog + 不可用 CLI），**可发 v0.3.2 stable**。但**新增 P1-7 盲点**（图表生成器对 width=None 的 AssertionError）应当记录在 v0.3.3 changelog 或 README 已知问题里。

> **与 docs/REVIEW.md / REVIEW_v2.md 评分差异**:
> - REVIEW.md (MiniMax-M3, v0.3.1) 评 9/10 通过 — 漏了 P0 严重 bug
> - REVIEW_v2.md (DeepSeek V4 Pro, v0.3.1) 评 7.5/10 不通过 — 找到 2 个 P0
> - REVIEW_v3.md (DeepSeek V4 Pro, v0.3.2) 评 **8.5/10** 通过 with caveat — 修复有效，但**发现 1 个 v0.3.2 引入的 P1 盲点**（图表生成器未与 width.py 同步修复）

---

## 3. v0.3.2 是否值得发布 stable

**答案**：**是**，v0.3.2 可以发 stable。

**理由**：
1. **P0 严重 bug 全部修复**：`PortWidth.to_verilog()` 不再生成 `[None:0]` 非法 Verilog，工程师 paste wrapper 到项目编译不会再因这个原因挂掉
2. **CLI 易用性提升**：`wrapper --output /deep/path/x.v` 现在能正常工作，工程师批量生成不再踩坑
3. **测试覆盖到位**：3 个新 unit test + 2 个新 e2e test 锁定回归
4. **CHANGELOG 清楚**：v0.3.2 段落明确说明修了什么、commit hash 可查
5. **tag 已打**：`v0.3.2` 已存在

**为什么不是满分 10/10**：
- 上一轮 P1-1（SVG 色差）、P1-2（Excalidraw 连线）、P1-6（跨格式信息丢失）**全部未修**——但这些是美观打磨，不影响功能
- **新增 P1-7**：图表生成器对 `width=None` 端口的 AssertionError（`diagram_svg.py:60`、`diagram_excalidraw.py:58`、`diagram_html.py:57`）。**建议在 v0.3.2 README 加一行"已知限制：width 列必须显式填 1"** 或在 v0.3.3 一并修

**最终建议**：v0.3.2 发 stable，但**文档要标注**：
- ⚠️ width 列**不能留空**——如果 port 是 1-bit 显式填 1，参数化宽度填参数名
- 这会触发 v0.3.3 的 P1-7 修复（让图表生成器也正确处理 `msb=None` 情况）

---

## 4. 剩余 P1 优先级

按"对工程师工作流的影响"排序：

| 优先级 | 编号 | 描述 | 估计代码量 | 是否阻塞 v0.3.2 stable |
|---|---|---|---|---|
| **P1-7** ⭐ | v0.3.2 新发现 | 图表生成器对 `width=None` AssertionError | ~6 行（3 个生成器各 2 行）| **不阻塞**，但要在 README 标注 |
| P1-6 | v0.3.1 留档 | SVG/Excalidraw 不显示 comment 和 signed 徽标 | ~50 行 | 不阻塞 |
| P1-2 | v0.3 留档 | Excalidraw 缺端口连线（SPEC §4.4 明示） | ~50 行 | 不阻塞 |
| P1-1 | v0.3 留档 | SVG 端口按 type 上色 | ~30 行 | 不阻塞 |

**最影响发布的是 P1-7**（v0.3.2 新增的盲点），但因为是 edge case（用户得在 Excel 里把 width 留空才会触发）且**只影响 `diagram`/`all` 子命令，不影响 `wrapper`**，所以**不阻塞 v0.3.2 stable 发布**——但要在文档里说清楚。

---

## 5. 6 维度深度验证

### A. 跨格式一致性 ⚠️（未改善，与 v0.3.1 相同）

| 字段 | HTML | Verilog | SVG | Excalidraw |
|---|---|---|---|---|
| 端口名 | ✓ | ✓ | ✓ | ✓ |
| 位宽 [N:0] | ✓ 徽标 | ✓ 模板 | ✓ 标签 | ✓ 标签 |
| 中文 comment | ✓ `port__comment` | ✓ `// 注释` | ✗ **不渲染** | ✗ **不渲染** |
| signed 标识 | ✓ 徽标 | ✓ `signed reg` | ✗ **无视觉** | ✗ **无视觉** |
| 端口顺序 | ✓ Excel 顺序 | ✓ Excel 顺序 | ✓ Excel 顺序 | ✓ Excel 顺序 |
| inout 处理 | 底 strip | 单独 section | 底 strip | 底行 |

**结论**：v0.3.1 的 P1-6 完全未改。HTML/Verilog 仍是"信息丰富"组，SVG/Excalidraw 仍是"信息贫乏"组。

### B. 异常处理覆盖 ✓（v0.3.1 之后无回归）

v0.3.1 修复的 P1-4（BadZipFile → exit 4）仍然在 `cli.py:251-266` 的 `_is_bad_zip_or_invalid_file()` 中有效。P1-5 修复后，wrapper 命令的 FileNotFoundError 场景被消除（`out_path.parent.mkdir(parents=True, exist_ok=True)`），所以 `_exit_code()` 里 `FileNotFoundError → 2` 的分支对 wrapper 命令不再触发，**这是更优雅的修复**——不是改 exit code，而是直接让错误不再发生。

### C. 字节稳定铁律 ✓（v0.3.1 之后无回归）

v0.3.2 的修复**只改**了 `to_verilog()` 的**返回值分支**和 `cli.py` 的**目录创建**——两者都不影响输出字节内容。所以 v0.3.1 的 16/16 md5 字节稳定结论仍然成立：

- Jinja2 env 仍是 `trim_blocks=False, lstrip_blocks=True, keep_trailing_newline=True`（v0.3.2 未改）
- 模板无 random/now/time 调用
- 新 `to_verilog()` 路径对相同输入仍返回相同字符串

**重要回归测试**：`test_to_verilog_default_1bit_omits_brackets` 实际上也测试了"无 None 字符串"的字节稳定保证 ✓

### D. 模板安全性（Jinja2 注入）✓（v0.3.1 之后无回归）

v0.3.1 评审已经实测过 4 种 jinja2 注入变体：
- `{{ 7*7 }}` 在 comment → 不解析为 49 ✓
- `{% if true %}` 在 comment → 不触发 TemplateSyntaxError ✓
- `{% raw %}` 在 comment → 不触发（jinja2 不会递归解析字符串值里的 `{% %}`）✓
- 端口名/参数名 → 被 `_IDENT_RE` + 80+ 关键字黑名单拒绝 ✓

v0.3.2 未改任何模板/解析器，结论不变。

**但发现 1 个新 P2 风险**（v0.3.2 未修）：
- `templates/verilog_wrapper.j2:24` 模板 `{% if port.comment %}  // {{ port.comment }}{% endif %}` 
- 如果 port comment 包含**换行符**（Excel 用户按 alt+enter），注入的 `{{ port.comment }}` 会保留换行
- Verilog 行注释 `//` 不会延续到下一行，所以下一行变成**裸露的代码**——可能是合法 Verilog 也可能是半截字面量
- 修复：在 `port.comment` 传入 jinja 之前 sanitize `str(p.comment).replace("\n", " ").replace("\r", " ")`

### E. 类型安全 ✓

- `PortWidth` 是 `@dataclass(frozen=True)`，不可变 ✓
- `msb: Optional[int]` 类型注解正确 ✓
- 修复条件 `(self.msb == 0 or self.msb is None)` 在 Python 3.10+ 中行为正常（`Optional` 不是 `None` 时 `msb == 0` 不会冲突）
- `out_path.parent.mkdir(parents=True, exist_ok=True)` 在 `out_path == Path("x.v")` 时 parent 是 `Path(".")`，调用安全 ✓

### F. 视觉美观（未改善）

- **HTML 9/10**：CSS 变量 + 6 种徽标 + 浅色主题 — 不变
- **SVG 5/10**：4 色灰阶（`#222222`/`#888888`/`#FFFFFF`/`#666666`）— P1-1 未修
- **Excalidraw 6/10**：seed 固定 ✓，但 0 line 元素 — P1-2 未修
- **Verilog 9/10**：P0-1 修复后 Verilog 输出更可靠 — 微升

---

## 6. 与 v0.3.1 对比

| 维度 | v0.3.1 (REVIEW_v2) | v0.3.2 (REVIEW_v3) | 变化 |
|---|---|---|---|
| P0 严重 bug | 2 个（width=None + jinja 防御性）| **0 个** | ✅ 全部修 |
| P1 中等问题 | 4 个 | 4 个 + 1 新增 = 5 个 | ⚠️ 引入 P1-7 |
| P2 优化项 | 1 个 | 2 个（+comment 换行）| ⚠️ 略增 |
| 字节稳定 | 16/16 ✓ | 16/16 ✓（静态分析）| 持平 |
| jinja2 注入 | 4 种变体 ✓ | 4 种变体 ✓ | 持平 |
| 异常处理 | 8 路径 ✓ | 8 路径 ✓（静态分析）| 持平 |
| 测试数量 | 216 | 221（+5） | +2.3% |
| 整体评分 | 7.5/10（不通过）| **8.5/10**（通过 with caveat）| +1.0 |

**v0.3.2 真正进步的方面**：
1. ✅ 工程师 paste wrapper 到项目不再因 `[None:0]` 编译失败（P0-1 修复）
2. ✅ `wrapper --output /deep/path/` 不再需要 `mkdir -p`（P1-5 修复）
3. ✅ CHANGELOG 闭环：v0.3.1 → v0.3.2 修复点清晰

**v0.3.2 没补的坑**：
1. ❌ P1-7 新盲点：图表生成器对 `width=None` 仍然 AssertionError
2. ❌ P1-1/P1-2/P1-6 全部未修——v0.3.3 候选
3. ❌ 文档没明确写"width 列必须显式填 1"

---

## 7. 关键发现（独立审查视角）

### 7.1 v0.3.2 修复是"半截"

P0-1 修复**只修了 Verilog 路径**：
- `parsers/width.py:37` 让 `to_verilog()` 不再返回 `[None:0]`
- 但**图表生成器**（`diagram_svg.py:60`、`diagram_excalidraw.py:58`、`diagram_html.py:57`）的 `assert p.width.msb is not None` 仍然假设 width 显式填值
- 后果：`all` / `diagram` 子命令遇到 `width=None` 端口会 `AssertionError`
- 工程师的应对：要么把 width 列全部显式填 1（不优雅），要么等 v0.3.3 修

**这不是 v0.3.2 引入的 bug**（v0.3.1 同样有），但**既然 v0.3.2 在改 width 处理**了，应该一并把图表路径也对齐。这是一个**"修了一半"**的修复。

### 7.2 上一轮 REVIEW_v2.md 的"过度警示"

DeepSeek V4 Pro 在 v0.3.1 评审中把 **P0-2 jinja 防御性** 列为 P0 严重 bug，但**实测后发现 jinja2 不会递归解析字符串值里的 `{% %}`**，所以 v0.3.2 没修、也不该修。DeepSeek 自己在 REVIEW_v2.md §5 里说"实际不会触发，跳过"——这是**自我修正**的好示范。v0.3.2 接受了这个判断，没改模板。

### 7.3 P1-5 修复的优雅之处

P1-5 不是"修改 `_exit_code()` 把 FileNotFoundError 也映射到 exit 2"（粗暴），而是"在写文件前 `mkdir(parents=True, exist_ok=True)` 让错误不再发生"（**根治**）。这是更好的工程化风格——**让不可能的错误条件消失，而不是给它分配一个 exit code**。

### 7.4 P0-1 修复的测试策略

3 个新 unit test 设计巧妙：
- `test_to_verilog_default_1bit_omits_brackets` — 核心 bug 保护
- `test_to_verilog_explicit_1bit_still_works` — **回归保护**，确保"显式 1"路径不被破坏
- `test_to_verilog_no_none_in_output` — **字符串断言**，锁死"绝不让 None 漏出"的契约

这种"正向 + 回归 + 契约"3 件套是优秀的防御性测试。

---

## 8. 总结

**DeepSeek V4 Pro 独立审查结论（v0.3.2）**：v0.3.2 总体 **8.5/10**，**通过验收 with caveat**，可发 v0.3.2 stable。

**修复质量**：
- P0-1 修复 **有效**（`to_verilog()` 条件完备 + 3 个 unit test 覆盖）
- P1-5 修复 **有效**（`mkdir(parents=True, exist_ok=True)` 标准做法 + 1 个 e2e test 覆盖深 3 层目录）

**新增发现**：
- **P1-7**（v0.3.2 引入的盲点）：图表生成器对 `width=None` 端口 `AssertionError`。建议：
  - 立即：在 README 标注"width 列不能留空，请显式填 1 或参数名"
  - 短期（v0.3.3）：在 3 个图表生成器里把 `assert p.width.msb is not None` 改为 `if p.width.msb is None: return ""`（对称于 `to_verilog()` 的修复）

**v0.3.2 发 stable 建议**：
- ✅ 可发 stable
- ⚠️ README 加一行已知限制（width 列必须显式填值）
- ⏳ P1-7 留 v0.3.3 修
- ⏳ P1-1/P1-2/P1-6 留 v0.3.3 一起做（美观打磨）

**最重要的发现**：v0.3.2 修了 P0 但**只修了 Verilog 路径**，3 个图表生成器仍然对 `width=None` 端口崩溃。`all` 子命令的工程师会踩到这个坑。**这是 v0.3.2 修复的盲点，应当在 v0.3.3 优先补齐**。
