# 测试

在仓库根目录执行（必须先激活项目虚拟环境）：

```powershell
.\.venv\Scripts\python -m pytest tests
node tests/test_pointer_normalization.cjs
npm run build --prefix frontend
```

- `python -m pytest tests`：FastAPI、安全分流和笔迹算法测试。必须用 `python -m pytest` 而不是裸 `pytest`，
  因为 `tests/test_api.py` 通过 `backend.app.main` 导入应用，依赖当前目录在 `sys.path` 上。
- `node tests/test_pointer_normalization.cjs`：浏览器手写笔采样归一化测试。
- `npm run build --prefix frontend`：Vue 3 生产构建验证。

测试数据必须是合成数据，不得包含参与者身份、真实笔迹、量表或私人对话。
