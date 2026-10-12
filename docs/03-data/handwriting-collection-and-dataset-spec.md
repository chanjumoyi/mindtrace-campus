# 笔迹数据集与数位板采集规范

版本：v1.0

状态：程序实现与真人采集的执行基线

最后更新：2026-10-12

## 1. 目的与适用范围

本规范用于统一以下工作：

- 下载、登记和处理公开在线手写数据集；
- 使用项目统一采购的数位板，在 PC 或移动设备上采集真人手写轨迹；
- 设计不超过 10 分钟的人次采集流程；
- 定义原始事件、量表、派生特征、质量标记和数据划分；
- 保证公开数据只扩充手写表示能力，最终心理状态拟合以项目真人数据为主。

本项目只输出压力、情绪和行为变化的辅助观察，不依据笔迹作人格判断、医学诊断、处分或危机判定。

## 2. 数据使用原则

### 2.1 数据分层

| 层级 | 数据 | 主要用途 | 最终监督拟合 |
| --- | --- | --- | --- |
| E0 | Quick, Draw!、CASIA-OLHWDB、IAM-OnDB | 学习通用轨迹、笔画和时序表示 | 不使用其原标签拟合心理状态 |
| E1 | CASIA-onDo、CASIA-OHFC、OUHD-L、OnHW | 学习压力、速度和设备动态特征 | 不直接作为心理标签 |
| E2 | EMOTHAW | 迁移学习和相关特征验证 | 可辅助，DASS 标签须独立保存 |
| H0 | 项目成员设备验证数据 | 验证采集、回放、校准和质量控制 | 不用于心理状态模型 |
| H1 | 经审批和同意的真人研究数据 | 最终训练、校准、验证和测试 | 核心目标域 |

不同数据集的诊断、情绪、量表或识别标签不得互相改名或直接合并。外部数据主要用于预训练轨迹编码器，最终预测头使用 H1 真人数据训练。

### 2.2 真人数据权重

训练采用以下顺序：

1. 使用 E0/E1 数据进行无监督或自监督预训练；
2. 可选使用 E2 数据验证候选特征或迁移学习；
3. 冻结或低学习率调整编码器，使用 H1 数据训练最终预测头；
4. 验证集和测试集必须 100% 来自 H1，并按参与者隔离划分。

如某一阶段必须混合外部数据和 H1，每个训练批次中 H1 的采样比例不得低于 70%，或对 H1 至少按 3:1 过采样。模型选择只依据 H1 验证集，最终报告只以参与者隔离的 H1 测试集为主。

## 3. 数位板与终端基线

### 3.1 统一设备要求

正式采集优先使用同一型号数位板和触控笔。开始编写采集器前，填写并冻结设备档案：

| 字段 | 说明 |
| --- | --- |
| `device_profile_id` | 项目内部设备配置编号 |
| `vendor` / `model` | 品牌与完整型号 |
| `firmware_version` | 固件版本 |
| `driver_name` / `driver_version` | PC 驱动名称与版本；移动端无驱动时记为 `none` |
| `active_width_mm` / `active_height_mm` | 官方有效书写区域物理尺寸 |
| `reported_pressure_levels` | 厂商标称压感级数，只作设备说明 |
| `reported_sample_rate_hz` | 厂商标称采样率，只作设备说明 |
| `connection_mode` | USB、蓝牙或其他方式 |
| `os_name` / `os_version` | 采集终端系统 |
| `browser_name` / `browser_version` | 采集浏览器 |
| `verified_pressure` | 网页实际是否读到变化的压力值 |
| `verified_tilt` | 网页实际是否读到倾角 |

厂商标称能力不能代替网页实测。相同数位板连接不同系统或浏览器，应建立不同的设备档案。

### 3.2 采集技术

- Canvas 2D API：呈现书写区域和实时笔迹；
- Pointer Events API：采集 `pointerdown`、`pointermove`、`pointerup`；
- `getCoalescedEvents()`：支持时读取浏览器合并前的采样点；
- `performance.now()`：产生单调递增的相对时间；
- `setPointerCapture()`：避免笔尖移出画布导致笔划丢失；
- IndexedDB：上传前加密或最小化暂存，上传成功后按策略清理；
- JSON Schema：在客户端和服务端验证轨迹格式及版本。

Canvas 平滑后的显示轨迹不能代替原始事件。保存原始点，平滑、重采样和归一化只能生成新的处理版本。

### 3.3 PC 与移动端准入

每种终端组合先完成 D0 设备验证：

1. 至少 3 名项目成员；
2. 每人完成 5 次固定抄写和 3 次自由书写；
3. 检查压力、时间、坐标、笔划边界、回放和断网恢复；
4. 比较同一数位板在 PC 与移动设备上的字段、取值范围和采样间隔；
5. 只有通过验证的终端组合可以进入真人采集。

如果移动设备只把数位板映射为鼠标，或压力值始终固定，该终端不得进入笔压实验；其数据可单独用于坐标和时间管线测试。

## 4. 真人采集设计

### 4.1 建议规模

- 目标不少于 80 名有效参与者；
- 每人 6 次：T0、W1、W2、W3、W4、T1；
- 目标约 480 个有效人次；
- 每位参与者至少完成 4 次才进入纵向分析；
- 同一个人的不同人次不能跨训练集、验证集和测试集。

在伦理审查、知情同意、隐私方案、撤回流程和专业审核完成前，不采集非项目成员的真实敏感数据。知情同意材料提前阅读，不得为了满足 10 分钟而压缩同意过程。

### 4.2 单次流程

#### T0：目标 7—9 分钟

| 环节 | 时间 |
| --- | ---: |
| 同意状态与参与者编号确认 | 15 秒 |
| 首次基础信息 | 30—45 秒 |
| PHQ-4 | 45—60 秒 |
| PSS-4 | 45—60 秒 |
| 当前状态 4 项 | 30 秒 |
| `PRESS_CHECK` 设备检查 | 15 秒 |
| `BASE` 短句抄写 | 45 秒 |
| `COPY` 标准文本抄写 | 60—90 秒 |
| `FREE` 中性短文本，可选 | 60 秒 |
| `PENTAGON` 五边形临摹 | 30 秒 |
| 页面切换、检查和上传缓冲 | 60—90 秒 |

#### W1—W4：目标 3—4 分钟

- 当前状态 4 项；
- `PRESS_CHECK`；
- `BASE`；
- `COPY`；
- W2、W4 可增加 `PENTAGON`。

#### T1：目标 6—8 分钟

重复 PHQ-4、PSS-4、当前状态题和核心书写任务。

### 4.3 量表与信息

| 项目 | 字段/计分 | 时间点 | 说明 |
| --- | --- | --- | --- |
| PHQ-4 | 4 题，每题 0—3，总分 0—12；另存 PHQ-2、GAD-2 分量表 | T0、T1 | 使用正式中文版和规定计分，不作诊断 |
| PSS-4 | 4 题，每题 0—4，总分 0—16；按正式文件反向计分 | T0、T1 | 不自行设临床等级 |
| 当前压力 | `stress_now`，0—10 整数 | 每次 | 主要即时监督目标 |
| 当前心情 | `mood_valence_now`，0—10 整数 | 每次 | 辅助目标 |
| 当前疲劳 | `fatigue_now`，1—5 整数 | 每次 | 控制变量 |
| 昨夜睡眠 | `sleep_hours_last_night`，0—16，可含 0.5 | 每次 | 控制变量 |

首次基础信息只收集年龄段、惯用手、数位板使用经验和设备配置编号。除非研究假设和审批明确要求，否则不收集姓名、学号、手机号、精确生日、班级、寝室、签名和就诊细节。

PHQ-4 使用条件和正式版本从 [PHQ Screeners](https://www.phqscreeners.com/) 核实；PSS-4 从 [CMU PSS 页面](https://www.cmu.edu/dietrich/psychology/stress-immunity-disease-lab/scales/index.html)和 [ePROVIDE](https://eprovide.mapi-trust.org/)申请或确认中文版使用条件。仓库不得复制未确认授权的完整量表文字。

如果学校的效果评估方案已经明确要求 PHQ-9、GAD-7 和完整版 PSS，应把它们作为 T0/T1 的独立评估环节，经伦理和专业人员审核后执行；不要与每周 3—4 分钟采集混在一起，也不要把不同量表分数直接换算成 PHQ-4 或 PSS-4。

### 4.4 书写任务

| 代码 | 任务 | 频率 | 用途 |
| --- | --- | --- | --- |
| `PRESS_CHECK` | 以自然力度画 3 条短横线 | 每次 | 检查笔压是否真实变化 |
| `BASE` | 抄写约 20 个中性汉字 | 每次 | 建立个人稳定基线 |
| `COPY` | 抄写 35—45 个中性汉字 | 每次 | 比较速度、压力、停顿和空间特征 |
| `PENTAGON` | 临摹两个相交五边形 | T0、W2、W4、T1 | 连接公开心理手写任务 |
| `FREE` | 中性主题 20—30 字 | T0、T1，可选 | 获取自然书写和辅助文本信息 |

固定文本必须内容中性、长度稳定并具有版本号。自由书写提示必须提醒参与者不要填写姓名、联系方式、学校、家庭住址或他人隐私。签名、房树人、钟表和长篇自由写作不进入 v1.0 核心流程。

## 5. 数据实体与字段

### 5.1 `dataset_source`

`source_id`、`source_name`、`source_type`、`official_url`、`license`、`allowed_use`、`modality`、`language`、`label_system`、`version`、`downloaded_at`、`sha256`。

### 5.2 `participant`

`participant_id`、`cohort`、`age_band`、`dominant_hand`、`digitizer_experience`、`consent_version`、`consent_time`、`withdrawn_at`。身份对应表与研究数据隔离保存。

### 5.3 `visit`

`visit_id`、`participant_id`、`timepoint`、`collected_at`、`timezone`、4 项当前状态、PHQ-4/PHQ-2/GAD-2/PSS-4 总分、`completion_status`、`interruption_reason`。

### 5.4 `questionnaire_response`

每题一行：`administration_id`、`visit_id`、`instrument_code`、`instrument_version`、`item_no`、`response_raw`、`response_score`、`total_score`、`missing_reason`、`completed_at`。不能只保存总分。

### 5.5 `task_attempt`

`attempt_id`、`visit_id`、`task_code`、`task_content_id`、`instruction_version`、`attempt_no`、`started_at`、`ended_at`、`duration_ms`、`device_profile_id`、`canvas_width`、`canvas_height`、`pointer_type`、`pressure_supported`、`pressure_valid`、`interruption_count`、`retry_reason`、`quality_status`。

### 5.6 `pointer_event`

每个原始采样点保存：

- `attempt_id`、`sequence_no`、`stroke_id`；
- `phase`：`down`、`move`、`up`；
- `elapsed_ms`、`timestamp_epoch_ms`；
- `x_raw`、`y_raw`、`x_normalized`、`y_normalized`；
- `pressure_raw`、`pressure_normalized`；
- `tilt_x`、`tilt_y`、`altitude_angle`、`azimuth_angle`；
- `twist`、`tangential_pressure`；
- `contact_width`、`contact_height`；
- `pointer_type`、`is_coalesced_event`。

原始坐标、原始压力和归一化值同时保留。跨设备比较必须以设备档案为分组或完成独立校准，不能直接把不同终端返回的压力数值视为同一物理量。

### 5.7 `derived_feature`

至少包含压力均值、标准差、分位数、极差和变化率；速度、加速度、加加速度；落笔和悬空时长；停顿数量和时长；笔画数、轨迹长度、回笔；包围盒、页面利用率、倾斜和曲率；采样间隔及异常点比例。每个特征记录单位、算法版本和输入数据版本。

## 6. 数据质量规则

### 6.1 设备级检查

- 实际检测到触控笔输入和变化的压力值；
- PC 和移动端分别记录兼容性结果；
- 浏览器缩放固定为 100%，页面滚动和手势不会中断书写；
- 同一批实验不随意更换驱动、固件、浏览器大版本或有效书写区域；
- 发生配置变化时创建新的 `device_profile_id`，不得覆盖旧配置。

### 6.2 会话级检查

- 有完整的 `down/move/up` 笔划边界；
- 固定文本基本完成，任务时长处于试采确定的合理区间；
- 笔划内采样间隔 P95 大于 50 ms 时标记警告并检查卡顿；
- 零毫秒间隔点超过 10% 时标记并在重采样时合并；
- 有效落笔压力为空，或极差小于 0.01 时，禁用该会话的压力特征；
- 压力无效但坐标和时间有效的数据，可以进入非压力模型；
- 页面切换、断连、误触、重复提交和人工重试均需记录原因。

阈值先用于 D0 设备验证，不应在没有试采统计前擅自扩大为所有设备的永久淘汰标准。

## 7. 公开数据集获取登记

| 优先级 | 数据集 | 关键内容 | 官方途径 | 使用限制与建议 |
| --- | --- | --- | --- | --- |
| A | CASIA-onDo | 中英文在线文档；x/y、压力、笔状态、时间；200 名书写者 | [官方介绍和下载](https://nlpr.ia.ac.cn/databases/CASIA-onDo/index.html) | 学术研究协议；最适合压力和时序管线预训练 |
| A | Quick, Draw! Raw | 大规模绘图；x/y/时间 | [官方仓库与下载说明](https://github.com/googlecreativelab/quickdraw-dataset) | CC BY 4.0；必须使用 Raw NDJSON，不使用丢失时间信息的简化版 |
| A | OUHD-L | 行级在线手写；压力、时间、倾角及派生运动特征 | [Zenodo DOI](https://doi.org/10.5281/zenodo.20642162) | CC BY 4.0；语言为乌尔都语，适合验证动态特征而非中文内容 |
| A-申请 | EMOTHAW | 7 类书写/绘图任务；压力、时间、笔姿和 DASS 标签 | [论文说明](https://arxiv.org/abs/2202.12245)，通过作者/实验室申请 | 与项目目标最相关；不得将 DASS 直接改成 PHQ/PSS 标签 |
| B-申请 | CASIA-OLHWDB | 约 1020 名书写者的大规模中文在线字符和文本 | [数据说明](https://nlpr.ia.ac.cn/databases/handwriting/Online_database.html)、[申请与下载](https://nlpr.ia.ac.cn/databases/handwriting/Download.html) | 适合中文笔画编码；公开格式重点是坐标轨迹 |
| B | CASIA-OHFC | 在线手绘流程图；x/y、压力、笔状态、时间 | [官方页面](https://nlpr.ia.ac.cn/databases/CASIA-OHFC/) | 适合绘图轨迹、压力和结构任务预训练；下载前核实协议 |
| B-注册 | IAM-OnDB | 英文在线手写文本；x/y/时间及转录 | [官方注册下载](https://fki.tic.heia-fr.ch/databases/download-the-iam-on-line-handwriting-database) | 非商业研究，通常需注册；无可用压力 |
| C | OnHW | 传感器笔的书写力和 IMU 信号 | [Fraunhofer 官方页面](https://www.iis.fraunhofer.de/de/ff/lv/dataanalytics/anwproj/schreibtrainer/onhw-dataset.html) | 模态与数位板不同，只用于运动特征思路和对照 |
| C | DARWIN | 174 名参与者、451 个已提取手写特征 | [UCI 官方页面](https://archive.ics.uci.edu/dataset/732/darwin) | CC BY 4.0；只有特征且标签为阿尔茨海默病，不用于本项目心理标签 |

“可以获取”不等于“可以任意再分发”。下载前保存许可页面、协议、版本、日期和文件校验值；申请表和签字文件保存在受限位置，不进入 Git。

## 8. 目录与安全

真实数据保存在加密或受控存储中，不直接放在仓库工作区。逻辑目录如下：

```text
datasets/
├─ registry/
│  └─ dataset_registry.csv
├─ external/<source_id>/
│  ├─ MANIFEST.md
│  ├─ raw/
│  └─ processed/
├─ own/restricted/
│  ├─ identity_map/
│  ├─ consent/
│  └─ safety/
├─ own/pseudonymized/raw/<participant_id>/<visit_id>/
└─ derived/
   ├─ features_v1/
   └─ splits_v1.json
```

Git 只保存 Schema、脚本、无私人信息的数据登记模板和合成样例。不得提交真实笔迹、量表回答、身份映射、同意书、申请协议、缓存、密钥或训练产物。

原始文件只读保存，清洗和派生数据写入新目录；参与者撤回后，删除必须覆盖身份映射、原始数据、派生特征、待训练集合和可识别备份。

## 9. 编写采集程序前的完成清单

- [ ] 记录数位板完整型号、连接方式、有效区域、驱动和固件；
- [ ] 在目标 PC、Android/iOS 设备和浏览器上完成压力兼容性小测试；
- [ ] 确认正式采集只使用通过 D0 的终端组合；
- [ ] 冻结 `BASE`、`COPY`、`FREE` 提示文本和版本号；
- [ ] 获取或确认 PHQ-4、PSS-4 正式中文版的使用条件；
- [ ] 完成伦理审查、知情同意、撤回和异常情况处理流程；
- [ ] 建立公开数据集登记表并保存许可证据；
- [ ] 冻结轨迹 JSON Schema、设备档案 Schema 和任务编码；
- [ ] 确认参与者隔离的数据划分策略；
- [ ] 使用合成数据和项目成员数据完成采集、断网恢复、上传、回放和特征提取测试。
