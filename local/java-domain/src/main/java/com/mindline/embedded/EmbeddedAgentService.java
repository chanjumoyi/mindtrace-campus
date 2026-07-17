package com.mindline.embedded;

import java.util.*;

/**
 * 嵌入式AI控件服务 —— 封装金蝶苍穹 {@code EmbeddedControlService} SDK 调用。
 *
 * <p>迁移到 cosmic 环境后，将此接口的实现替换为对
 * {@code kd.bos.gptas.api.embedctrl.EmbeddedControlService} 的直接调用。
 * 当前本地 Mock 实现用于开发调试。
 *
 * <p>对应苍穹文档 SDK 方法：
 * <ul>
 *   <li>show() — 打开AI控件</li>
 *   <li>chat() — 对话</li>
 *   <li>newChat() — 新建对话</li>
 *   <li>sendUserChat() — 系统发送用户消息到前端</li>
 *   <li>sendButtonCard() — 发送按钮卡片</li>
 *   <li>getChatContext() — 获取上下文</li>
 *   <li>stop() — 停止生成</li>
 *   <li>sendMessage() — 发送流式消息到前端</li>
 *   <li>getChatData() — 获取当前会话消息内容</li>
 * </ul>
 *
 * @see kd.bos.gptas.api.embedctrl.EmbeddedControlService
 */
public interface EmbeddedAgentService {

    /**
     * 打开嵌入式AI控件。
     *
     * @param agentParam 智能体配置（assistantId/agents/mountingMethod/avatar等）
     * @param showStyle  展示配置（showKey/location/clickHideCtrl/small）
     * @param fastQuestion 打开后立即发送的问题（可选）
     */
    void show(AgentParam agentParam, ShowStyle showStyle, String fastQuestion);

    /**
     * 发送对话消息。
     *
     * @param chatSessionId 会话ID
     * @param skillId      智能体ID
     * @param userInput    用户输入
     * @param userParams   用户自定义参数（如页面上下文）
     */
    void chat(String chatSessionId, long skillId, String userInput, Map<String, Object> userParams);

    /**
     * 新建会话。
     */
    String newChat();

    /**
     * 系统主动发送消息到前端（非用户输入）。
     */
    void sendUserChat(String chatSessionId, long skillId, String message);

    /**
     * 停止生成。
     */
    void stop(String chatSessionId, String taskId, String flowId);

    /**
     * 获取上下文信息。
     */
    Map<String, Object> getChatContext(String chatSessionId);

    /**
     * 发送流式消息到前端。
     */
    void sendMessage(String chatSessionId, String message, boolean isThink, boolean end, int index);

    /**
     * 获取当前会话生成的消息内容。
     */
    String getChatData(String chatTraceId);

    // ---- 参数 DTO ----

    class AgentParam {
        private Long assistantId;
        private List<AgentInfo> agents;
        private String avatar;
        private String name;
        public Long getAssistantId() { return assistantId; }
        public void setAssistantId(Long assistantId) { this.assistantId = assistantId; }
        public List<AgentInfo> getAgents() { return agents; }
        public void setAgents(List<AgentInfo> agents) { this.agents = agents; }
        public String getAvatar() { return avatar; }
        public void setAvatar(String avatar) { this.avatar = avatar; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    class AgentInfo {
        private int order;
        private String name;
        private String number;
        private String picture;
        private String suggestedAsks;
        private String mountingMethod; // floatAboveTheContainer / embeddedToTheContainer / smallPopupWindow
        public int getOrder() { return order; }
        public void setOrder(int order) { this.order = order; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getNumber() { return number; }
        public void setNumber(String number) { this.number = number; }
        public String getPicture() { return picture; }
        public void setPicture(String picture) { this.picture = picture; }
        public String getSuggestedAsks() { return suggestedAsks; }
        public void setSuggestedAsks(String suggestedAsks) { this.suggestedAsks = suggestedAsks; }
        public String getMountingMethod() { return mountingMethod; }
        public void setMountingMethod(String mountingMethod) { this.mountingMethod = mountingMethod; }
    }

    class ShowStyle {
        private String showKey;
        private String ctrlKey;
        private String location;   // TOP/BOTTOM/LEFT/RIGHT
        private boolean clickHideCtrl = true;
        private boolean small;
        public String getShowKey() { return showKey; }
        public void setShowKey(String showKey) { this.showKey = showKey; }
        public String getCtrlKey() { return ctrlKey; }
        public void setCtrlKey(String ctrlKey) { this.ctrlKey = ctrlKey; }
        public String getLocation() { return location; }
        public void setLocation(String location) { this.location = location; }
        public boolean isClickHideCtrl() { return clickHideCtrl; }
        public void setClickHideCtrl(boolean clickHideCtrl) { this.clickHideCtrl = clickHideCtrl; }
        public boolean isSmall() { return small; }
        public void setSmall(boolean small) { this.small = small; }
    }
}
