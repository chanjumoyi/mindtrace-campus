package com.mindline.embedded;

import java.util.*;

/**
 * 本地 Mock 嵌入式控件服务 —— 所有方法返回模拟数据或打印日志。
 * 迁移到 cosmic 后删除，替换为 EmbeddedControlService 真实调用。
 */
public class LocalMockEmbeddedService implements EmbeddedAgentService {

    private final Map<String, List<String>> chatHistory = new HashMap<>();
    private final Map<String, Map<String, Object>> contexts = new HashMap<>();

    @Override
    public void show(AgentParam agentParam, ShowStyle showStyle, String fastQuestion) {
        String agentName = agentParam.getAgents() != null && !agentParam.getAgents().isEmpty()
                ? agentParam.getAgents().get(0).getName() : "unknown";
        System.out.printf("[Mock] 打开AI控件: agent=%s, location=%s, mounting=%s%n",
                agentName,
                showStyle.getLocation(),
                agentParam.getAgents() != null ? agentParam.getAgents().get(0).getMountingMethod() : "default");
        if (fastQuestion != null) {
            System.out.printf("[Mock] 自动发送问题: %s%n", fastQuestion);
        }
    }

    @Override
    public void chat(String chatSessionId, long skillId, String userInput, Map<String, Object> userParams) {
        System.out.printf("[Mock] Chat: session=%s, skill=%d, input=%s, params=%s%n",
                chatSessionId, skillId, userInput, userParams);
        chatHistory.computeIfAbsent(chatSessionId, k -> new ArrayList<>())
                .add("user: " + userInput);

        // 模拟 Agent 回复
        String mockResponse = "这是Mock Agent的回复。"
                + (userParams != null && !userParams.isEmpty()
                    ? " 已接收页面上下文: " + userParams.keySet() : "");
        chatHistory.get(chatSessionId).add("agent: " + mockResponse);
    }

    @Override
    public String newChat() {
        String id = "mock-session-" + UUID.randomUUID().toString().substring(0, 8);
        chatHistory.put(id, new ArrayList<>());
        System.out.printf("[Mock] 新建会话: %s%n", id);
        return id;
    }

    @Override
    public void sendUserChat(String chatSessionId, long skillId, String message) {
        System.out.printf("[Mock] 系统消息→前端: session=%s, skill=%d, msg=%s%n",
                chatSessionId, skillId, message);
    }

    @Override
    public void stop(String chatSessionId, String taskId, String flowId) {
        System.out.printf("[Mock] 停止生成: session=%s, task=%s, flow=%s%n",
                chatSessionId, taskId, flowId);
    }

    @Override
    public Map<String, Object> getChatContext(String chatSessionId) {
        Map<String, Object> ctx = contexts.getOrDefault(chatSessionId, new HashMap<>());
        ctx.put("messageCount", chatHistory.getOrDefault(chatSessionId, List.of()).size());
        return ctx;
    }

    @Override
    public void sendMessage(String chatSessionId, String message, boolean isThink, boolean end, int index) {
        System.out.printf("[Mock] 流式消息: session=%s, think=%b, end=%b, idx=%d, msg=%s...%n",
                chatSessionId, isThink, end, index,
                message.length() > 40 ? message.substring(0, 40) : message);
    }

    @Override
    public String getChatData(String chatTraceId) {
        return "{\"mock\": true, \"traceId\": \"" + chatTraceId + "\"}";
    }
}
