# 离线笔迹研究工作区

Python 3.10.20，独立环境 `ml/.venv`。所有原始轨迹、清单、哈希、参与者划分、图表、检查点和逐人结果均留在 Git 忽略目录。不要移动、重命名或修改原始下载；备份应保存在研究负责人指定的受控位置。

从任意目录使用脚本绝对路径执行（下列示例从仓库根目录执行）：

```powershell
uv python install 3.10.20
uv venv --python 3.10.20 --managed-python ml/.venv
uv pip install --python ml/.venv/Scripts/python.exe --index-strategy unsafe-best-match -r ml/requirements.txt
ml/.venv/Scripts/python ml/scripts/verify_environment.py
ml/.venv/Scripts/python -m unittest discover -s ml/tests -v
ml/.venv/Scripts/python ml/scripts/00_inventory.py
ml/.venv/Scripts/python ml/scripts/01_prepare_data.py --cpu-affinity 0xffff0000
# 全量检查并抽样保存每个集合的一个窗口，验证无 pickle 加载：
ml/.venv/Scripts/python ml/scripts/01_prepare_data.py --sample-arrays --cpu-affinity 0xffff0000
# 同时保存全部派生时间窗（占用额外本地磁盘）：
ml/.venv/Scripts/python ml/scripts/01_prepare_data.py --write-arrays --cpu-affinity 0xffff0000
```

数据配置位于 `configs/data.json`，路径相对于 ml，CASIA 入口显式为空。OUHD-L 官方 train/val/test manifest 是唯一划分来源，以 writer_id 检查集合互斥。读取原始测量通道，不使用包中预计算速度。EMOTHAW 配置仅指定 canonical 镜像，当前不启动监督训练；MindTrace 尚无样例。

上述 CPU affinity 是**本次机器专用**的进程设置，不修改系统配置；该机器默认调度下的长数据读取出现底层异常，因此单独记录此执行条件。其他机器应去掉该选项，或提供其有效 CPU 位掩码；程序会验证设置结果，输出记录实际 mask。该观察不足以诊断硬件故障。

`00_inventory.py` 只读核验所有已配置下载，完整文件路径/哈希清单写入 `data/inventory/`；`01_prepare_data.py` 对 OUHD-L 全量检查并输出 `data/processed/ouhd_l-v1/<run_id>/`。每次运行创建独立目录，避免旧窗口混入新运行；后续训练必须指定一个 `summary.json` 中 status=passed 的完整运行，不能跨运行 glob 读取。可公开的汇总经人工确认后记录到 `docs/acceptance.md`，不得复制逐人清单或图表到受跟踪目录。

五通道为 dx、dy、dt_seconds、pressure、pen_state，含独立 feature_mask、measurement_missing、augmentation_mask、padding_mask、stroke_boundary。augmentation mask 默认为 false，留给后续遮盖训练。首点增量无前驱，标记不可用；状态转换保留，dt=0 的速度无效。同刻同状态只聚合连续点，保存原索引半开区间；倒序直接隔离，不排序。原始时间和聚合后测量保留，无 epoch 明确 NaN。

归一化坐标使用**训练集合坐标范围**，保存 origin/scale，可逆；这只是统计尺度映射，不是已验证的设备物理校准，不报告毫米或物理速度。测试集超出训练范围时不裁剪。OUHD-L 压力按来源量程 4095 缩放，不能解释为与浏览器压力已校准。`browser_pressure_mask` 单独实现 MindTrace pen 且落笔动态范围 ≥0.01 的有效性规则，待真实样例适配时接入读取器。

步骤 2 的 v1 时间窗保留作源数据审计。正式协议已由步骤 3 在训练/验证集验证后冻结到 `configs/preprocessing-frozen.json`：125 Hz、2 秒窗口、2 秒步长、至少 500 ms 尾窗、按批 padding，不截断。状态事件保留，抬笔与长空隙不插值。后续正式预训练须使用 `windowing.py` 的 v2 处理与对应私有运行的训练集标准化参数，不能直接使用 v1 产物或原始 256 点作为跨域窗口。

统计特征 v1.1 为 28 维，速度使用归一化坐标/秒，压力统计限落笔有效点，形状不连接跨笔画跳跃；停顿按完整抬笔片段或连续落笔采样间隔计算，并保存 200/500/1000ms 敏感性。缺失统计输出有限零值加 false mask；不能将占位零解释为测量结果。图表仅留本地。

PR #3 复核后，轨迹与特征版本更新为 v1.1。`summary.json`、`normalization.json` 与 NPZ 都记录实际版本和窗口/步长；归一化文件另列四个连续通道的顺序。`--window-ms` 和 `--stride-ms` 可改变审计窗口，实际调用与元数据使用同一组参数，不代表正式实验选参。

压力量程仅由 `configs/data.json` 注入，其他设备可显式传入自己的范围；变换、有效性检查和统计共享同一 offset/scale。实际量程、offset、scale 写入每次运行的元数据，旧产物不会被重写或补标版本。

`pad()` 统一补齐所有逐点数组：模型值补 0、有效性/缺失/遮盖标志补 false、来源索引补 -1、辅助浮点测量补 NaN；只有 padding_mask 补 true。标量和压力量程/时间边界元数据保持原样，支持 NPZ 回读后的表示。使用辅助测量时仍须排除 padding。

验收门禁为显式异常，在 `python -O` 下也有效。`.github/workflows/ml-synthetic-tests.yml` 在 Windows/Python 3.10 中运行普通与优化模式的合成测试，不读取私有数据、不安装 CUDA。

复现步骤 3（`--input-run` 指向步骤 2 的完整 passed 运行；从其他目录启动时传绝对路径）：

```powershell
ml/.venv/Scripts/python ml/scripts/03_select_windows.py --input-run ml/data/processed/ouhd_l-v1/20261025T141625Z-e16afa82 --cpu-affinity 0xffff0000
# 新 run 的目录在输出中显示，随后可生成本地验收图：
ml/.venv/Scripts/python ml/scripts/plot_window_study.py ml/experiments/window-study/<run_id>
```

默认只写私有运行；`--freeze` 仅用于首次生成公共冻结契约，已有契约时拒绝覆盖。更改协议需要显式新版本及新的训练/验证实验，不能悄悄重选。正式训练尚未开始，冒烟权重不视作正式编码器。

步骤 1、2 的证据见 `docs/acceptance.md`，步骤 3 的完整规则、结果和限制见 `docs/window-selection.md`。tasks.md 中监督基线、EMOTHAW 专门适配、MindTrace 样例适配属于另外分支，未完成前不会勾选。
