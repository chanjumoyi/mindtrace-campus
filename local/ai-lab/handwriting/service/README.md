# A 模块本地笔迹分析服务

该服务把现有采集器导出的轨迹 JSON 接入特征提取脚本，并返回可解释的客观观察、数据质量、行为指标与书籍证据引用。

## 启动

在项目根目录执行：

```powershell
python local\ai-lab\handwriting\service\server.py --port 8091
```

然后在电脑浏览器打开 `http://127.0.0.1:8091/`，选择采集器导出的 JSON 文件。

接口同时支持：

- `GET /api/v1/health`
- `POST /api/v1/handwriting/analyze`
- `POST /handwriting/analyze`（兼容路径）

请求体：

```json
{
  "requestId": "可选",
  "trace": {}
}
```

`trace` 必须是 `local/ai-lab/handwriting/collector` 导出的完整 JSON，而不是旧版 `strokes` 数组。

## 当前边界

- 这是可解释特征与个人纵向研究原型，不是心理诊断模型。
- 没有个人基线时，不输出“变化”结论。
- 书籍内容作为待验证假设来源，不能充当监督学习真值标签。
- 当前少量自采数据只适合验证采集、清洗、特征和接口闭环，不足以训练通用“大模型”。
