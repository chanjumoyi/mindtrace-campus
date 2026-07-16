package com.mindline.platform;

import com.mindline.model.*;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 平台适配器接口 —— 隔离本地开发与金蝶AI苍穹平台的所有外部依赖。
 *
 * <p>每个方法都有两个实现：
 * <ul>
 *   <li>{@code LocalMockAdapter} —— 本地开发，返回预定义的Mock数据</li>
 *   <li>{@code KingdeeAdapter} —— 生产环境，调用苍穹Agent平台/服务模型</li>
 * </ul>
 *
 * <p>切换方式：通过配置属性 {@code app.platform.mode} 选择。
 *
 * @author 角色B - 多模态算法与Agent工程
 * @since 1.0.0
 */
public interface PlatformAdapter {

    // ================================================================
    // Agent分析调用（沙盘 / 房树人）
    // ================================================================

    /**
     * 调用沙盘分析Agent，返回结构化分析结果。
     *
     * @param request 沙盘分析请求（几何特征 + 用户描述）
     * @return Agent分析结果
     * @throws AgentException Agent调用失败时抛出
     */
    SandplayAgentAnalysis analyzeSandplay(SandplayAnalysisRequest request);

    /**
     * 调用房树人分析Agent，返回结构化分析结果。
     *
     * @param request 房树人分析请求（视觉观察 + 问卷）
     * @return Agent分析结果
     * @throws AgentException Agent调用失败时抛出
     */
    HTPAgentAnalysis analyzeHTP(HTPAnalysisRequest request);

    // ================================================================
    // 多模态模型调用
    // ================================================================

    /**
     * 调用多模态模型对画作图片进行客观视觉描述。
     *
     * @param imageRef 图片文件引用路径
     * @return 视觉观察结果，模型不可用时返回 {@code null}
     * @throws MultimodalException 调用异常（超时/不可用等）
     */
    VisualObservation describeImage(String imageRef);

    // ================================================================
    // RAG知识检索
    // ================================================================

    /**
     * 检索RAG知识库。
     *
     * @param topic  知识主题过滤（如 "sandplay", "htp"）
     * @param query  检索查询文本
     * @param maxResults 最大返回条数
     * @return 检索到的文档列表（含来源和片段）
     */
    List<Citation> retrieveKnowledge(String topic, String query, int maxResults);

    // ================================================================
    // 工具执行（Agent Tool Calling）
    // ================================================================

    /**
     * 执行Agent工具调用。
     *
     * @param toolName 工具名称
     * @param params   工具参数（JSON反序列化为Map）
     * @return 工具执行结果
     * @throws ToolExecutionException 工具执行失败
     */
    Map<String, Object> executeTool(String toolName, Map<String, Object> params);

    // ================================================================
    // 审计记录
    // ================================================================

    /**
     * 保存Agent执行审计记录。
     *
     * @param auditRecord 审计记录
     */
    void saveAuditRecord(AgentAuditRecord auditRecord);

    // ================================================================
    // 适配器元信息
    // ================================================================

    /**
     * @return 当前适配器模式（"local" 或 "kingdee"）
     */
    String getMode();
}
