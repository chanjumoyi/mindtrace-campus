# 研究资产

此目录只保存与立项报告直接相关、可公开和可复现的实验资料：

- `ai/`：房树人、沙盘、笔迹 Prompt、工作流、工具 Schema 和安全评测集；
- `handwriting/`：设备验证、公开参考资料、数据处理和基线训练脚本；
- `knowledge/`：经过来源标注的笔迹研究假设与 RAG 清单；
- `data/`：沙盘字典与合成示例。

真实参与者数据必须放在被 Git 忽略的 `private/` 目录中，并遵循伦理审查、知情同意、最小化采集和可撤回要求。

## 离线脚本依赖

研究脚本需要 `numpy` 和 `pypdf`，它们不属于后端运行时依赖，需要单独安装：

```powershell
uv pip install --python .venv\Scripts\python.exe -r research/requirements.txt
```

## 笔迹脚本用法

所有脚本都必须在仓库根目录执行，默认路径都是相对仓库根目录的。

```powershell
# 1. 把采集器导出的单个轨迹 JSON 导入私有数据集（自动拒绝越界路径）
.\.venv\Scripts\python research\handwriting\scripts\import_handwriting_json.py <trace.json>...

# 2. 或导入采集器批量导出的轨迹/预览图压缩包
.\.venv\Scripts\python research\handwriting\scripts\import_handwriting_bundle.py <trajectory.zip> <images.zip>

# 3. 批量提取特征并生成建模表
.\.venv\Scripts\python research\handwriting\scripts\build_handwriting_dataset.py

# 4. 训练并审计基线，产出 research/handwriting/models/handwriting_ridge_v0.1.json
.\.venv\Scripts\python research\handwriting\scripts\train_handwriting_baseline.py

# 5. 只查看单条轨迹的特征（不写文件）
.\.venv\Scripts\python research\handwriting\scripts\inspect_handwriting_trace.py <trace.json>
```

第 3、4 步依赖 `private/` 下的真实数据；没有数据时脚本会给出明确提示并以退出码 2 结束，
而不是抛出 traceback。生成的模型文件被 `.gitignore` 忽略，不进入仓库；缺失时
`/api/v1/handwriting/analyze` 会自动降级为只输出客观特征。

## 知识库脚本

```powershell
# 直接从 PDF 抽取（需要 pypdf）
.\.venv\Scripts\python research\handwriting\scripts\build_handwriting_book_kb.py <book.pdf>

# 或先做 OCR，再从 OCR 结果构建
.\.venv\Scripts\python research\handwriting\scripts\build_handwriting_book_kb_from_ocr.py --ocr <ocr_raw.jsonl>

# 检索本地知识库
.\.venv\Scripts\python research\handwriting\scripts\search_handwriting_book.py "书写速度 下笔重"
```

知识库产物一律写入 `private/knowledge/`，不得提交。
