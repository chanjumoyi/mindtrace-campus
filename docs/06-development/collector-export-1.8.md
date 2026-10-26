# 采集导出格式 1.8.0

`schemaVersion` 为 `1.8.0`，`appVersion` 为 `handwriting-collector-mobile/1.8.0`。Android 安装包版本为 1.0.2（versionCode 3）；安装包版本与 JSON 格式版本分别管理。

完成页仅显示采集完成、保存和上传状态，不展示 WHO-5 评分卡、分数、评定或建议。量表答案、计分规则及 `questionnaire.derived` 仍完整写入本地导出和上传的 JSON。

自由书写提示为“轨迹会上传用于研究，请不要写姓名、联系方式、学校等个人信息”。导出的 `points` 可以重绘书写内容，不能将其解释为不含内容的统计摘要。

## 输入有效性与设备档案

每个 `attempt` 增加以下字段；原始点中的压力和倾角字段继续保留。

| 字段 | 当前含义 | 消费方式 |
| --- | --- | --- |
| `tiltValid` | 当前始终为 `false`，尚未独立验证设备倾角能力 | 将该 attempt 的倾角特征标记为缺失；常数 0 不代表测得的零倾角 |
| `pressureValid` | 暂与 `pressureDetected` 相同：观察到 pen 输入，且正压力样本范围至少为 0.01 | 仅是动态笔压检测启发式，不代表压力已校准；为 `false` 时屏蔽压力特征 |
| `deviceProfileId` | 与根对象 `device.deviceProfileId` 相同 | 按设备档案关联采集环境，不能据此断言是同一台实体设备 |

触屏或固定压力回退值（例如 0.5）不会因数值非零而成为有效笔压。即使动态笔压通过检测，数值也不是经过物理标定的力单位。倾角不因存在原始字段、值非零或笔压有效而自动变为有效。

构建时可通过 `VITE_DEVICE_PROFILE_ID` 指定已登记的研究设备档案。未配置时生成 `unverified-web-v1-` 加 16 位十六进制环境哈希：使用报告的 user agent、platform、maxTouchPoints、devicePixelRatio，以及按大小排序后的屏幕宽高，采用 64 位 FNV-1a。屏幕旋转不会单独改变该宽高签名；浏览器或系统升级等环境变化可能改变档案 ID，相同环境的多台设备也可能共享 ID。

根对象 `device` 同时记录 `profileSource`（`study_configuration` 或 `reported_environment`）、`profileVersion`、`calibrationStatus: "unverified"` 和 `physicalDeviceVerified: false`。配置档案名称本身不执行硬件识别或传感器校准。每轮使用同一个设备档案，attempt 通过 ID 与其关联。

## 停顿、抬手和未观测时间

新指标位于 `attempt.metrics`，按导出中保留的点序列计算，不改写原始时间戳。时间单位为毫秒，距离单位为 CSS 像素。根对象 `metricDefinitions.strokeTiming` 导出算法版本和阈值，当前版本为 `1.0.0`。

| 字段 | 定义 |
| --- | --- |
| `pauseInStrokeMs` | 笔画内连续、可观测低速片段达到 500 ms 时，累计整个片段时长 |
| `pauseInStrokeCount` | 满足上述条件的连续片段数 |
| `betweenStrokeMs` | 明确的相邻 `up` → 下一 `down` 边界之间的非负时间间隔之和 |
| `betweenStrokeCount` | 上述明确边界数，包括时差为 0 的边界 |
| `unobservedIntervalMs` | 无法归入明确抬手间隔或可观测笔画内采样的正相邻时差之和 |

笔画内相邻两点必须有相同 `strokeId` 和 `pointerId`，前点不能为 `up`，后点不能为 `down`，坐标有限且时差满足 `0 < dt <= 100 ms`。用相邻点距离除以时差计算速度；速度 `<= 5 CSS px/s` 的连续区间累计 `>= 500 ms` 才计入停顿。正常移动会结束低速片段；不足 500 ms 的低速片段不计为停顿，但不因此成为未观测时间。

抬手间隔只接受明确的前点 `up`、后点 `down`，且二者不属于相同 `strokeId`/`pointerId` 组合。无论长短，只要时差非负就单独计入，不加入 `pauseInStrokeMs`。取消事件导致缺失 `up` 时，不能从下一次落笔推断整段都是抬手或思考。

超过 100 ms 的笔画内采样空缺、缺少明确边界或坐标无效的正时差计入 `unobservedIntervalMs`，并截断连续低速片段。单个 600 ms 间隔即使两端坐标相同，也不能建立一次笔画内停顿；12 个连续的 50 ms 静止采样间隔可以。重复、倒序和非法时间戳会截断低速片段；非法或负时差不增加任何时长。首点之前没有相邻采样区间，也不计入上述指标。

这些指标是采样轨迹的操作性定义，不能直接证明参与者在思考。撤回和恢复后按最终保留轨迹重算，不把删除的点重新计入。

## 旧字段与数据迁移

`pauseDurationMs` 和 `pauseCount` 保留为 legacy 字段，避免破坏旧消费者：前者仍为 `max(0, durationMs - activeDurationMs)`，后者仍统计旧计算中不同 stroke 间达到 500 ms 的间隔。它们不表示新版笔画内停顿，不应作为 `pauseInStrokeMs` 的别名。`activeDurationMs` 的历史定义也保持不变，不能用它与新字段直接构造时长恒等式。

训练适配器应分别提供数值和缺失 mask：`tiltValid !== true` 时屏蔽倾角，`pressureValid !== true` 时屏蔽压力，保留原始 JSON 供审计。旧记录没有这些有效性字段时按 missing 处理，不能默认有效或将缺失填成真实零。旧数据未测得的新停顿字段也按 missing；如需重算，必须有足够的原始 `points`，并记录所用算法版本。已知缺失与可观测条件下计算得到的 0 应保持区别。

`deviceProfileId` 缺失时保持未知档案，不能用新版本默认哈希替旧记录编造设备身份。量表版本及旧 18 题数据的兼容规则继续遵循 [WHO-5 说明](who5-questionnaire.md)。

## 接收服务

仓库根目录的 [upload-server.ps1](../../upload-server.ps1) 校验 `schemaVersion` 和 `sessionId` 等基础请求条件后保存 UTF-8 JSON 请求原文，不剥离 attempt、新设备档案或指标定义。因此新增字段不需要修改此次接收协议；下游分析及训练适配器需要按本说明读取版本和有效性标记。

请求地址、鉴权配置、网页/Android 上传路径及重试方式继续沿用现有实现。根目录 [update-upload-server.ps1](../../update-upload-server.ps1) 用于更新接收脚本并保留部署配置，不能因为 JSON 版本递增而清理或改写已有采集文件。
