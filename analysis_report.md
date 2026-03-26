# cloc 与 scc 代码行分析差异报告

针对 `nanogui` 和 `userver` 两个项目的 C/C++ 代码分析显示，[cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 和 [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 两个工具在默认配置下会产生显著的统计差异。通过对比实验，我们将差异原因归纳为以下四类：

## 1. 文件识别与排除策略差异
这是导致**总行数 (Total Lines)** 不一致的首要原因。

- **问题描述**: 
  - [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 默认不识别 `.ipp` 后缀（C++ 内联文件），即使手动指定 `--include-ext` 有时也会失效。而 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 默认将其识别为 C++。
  - `userver` 项目中包含多个 `.ipp` 文件，导致 [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 的初始统计丢失了约 1,390 行数据。
- **解决方法**: 在 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 中使用 `--exclude-ext=ipp` 统一排除该后缀，或在 [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 中确保其被正确识别。

## 2. 重复文件与符号链接处理
- **问题描述**: 
  - [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 默认具有“去重”机制（Uniqueness match），如果两个文件内容完全相同（如硬链接、符号链接或副本），它只计算其中一个。
  - [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 默认会扫描路径下的所有物理文件。
- **解决方法**: 使用 `cloc --skip-uniqueness` 禁用去重，使两者在文件采集阶段保持一致。

## 3. 正则表达式超时导致的误判 (关键)
这是导致 `userver` 项目中 **代码行数 (Code)** 严重偏低的核心原因。

- **问题描述**: 
  - [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 使用正则表达式识别注释和字符串。对于包含巨大 C++11 `R"(...)"` 原始字符串的文件（如包含数千行 JSON 数据的文件），正则表达式会触发内部超时保护。
  - 一旦超时，[cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 会放弃解析，并倾向于将大部分内容归类为 **Comment** (甚至将代码行记为 0)。
  - [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) (Go 语言编写) 的解析引擎在处理这类复杂大型文件时表现更稳定。
- **典型案例**: `userver` 的 `serialize_benchmark.cpp` 在 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 默认下显示为 0 行代码，实际有 1,208 行。
- **解决方法**: 为 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 添加 `--timeout=0` 以完全禁用超时限制。

## 4. 空行归属分类标准
即使总行数完全一致，两工具对“空行”的定义也不同。

- **差异逻辑**:
  - **cloc (物理主义)**: 只要行内没有任何字符，统一计为 **Blank**，无论该行是否处于 `/* ... */` 注释块或多行字符串内部。
  - **scc (语境主义)**: 如果空行处于注释块内部，则计为 **Comment**；如果处于代码逻辑中，则计为 **Blank**。
- **表现**: `nanogui` 中 [scc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#62-92) 的注释行通常比 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 多，而空行相应减少。

---

## 最终结论与建议
在应用了 `--skip-uniqueness`、`--exclude-ext=ipp` 和 `--timeout=0` 后，两个工具在 `userver` 上的总行数统计已达到 **100% 一致** (529,557 行)。

| 工具 | 优势 | 适用场景 |
|---|---|---|
| **cloc** | 计数严谨、历史悠久、支持去重。 | 需要精确物理行分布统计时。 |
| **scc** | 速度极快、对复杂语法（如 C++11 R-string）处理更稳健。 | 大型项目快速扫描、逻辑代码行评估。 |

**建议**: 对复杂 C++ 项目使用 [cloc](file:///Volumes/code/prjs/loc_test/analyze_loc.py#24-58) 时，务必开启 `--timeout=0`。
