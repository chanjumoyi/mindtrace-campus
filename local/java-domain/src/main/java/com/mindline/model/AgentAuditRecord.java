package com.mindline.model;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Agent执行审计记录。
 */
public class AgentAuditRecord {

    private String agentRunId;
    private String agentName;
    private String promptVersion;
    private String inputSummary;
    private String outputSummary;
    private List<ToolCallRecord> toolCalls;
    private List<String> ragCitations;
    private Instant startTime;
    private Instant endTime;
    private long latencyMs;
    private String errorInfo;

    public AgentAuditRecord() {}

    public String getAgentRunId() { return agentRunId; }
    public void setAgentRunId(String agentRunId) { this.agentRunId = agentRunId; }

    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }

    public String getPromptVersion() { return promptVersion; }
    public void setPromptVersion(String promptVersion) { this.promptVersion = promptVersion; }

    public String getInputSummary() { return inputSummary; }
    public void setInputSummary(String inputSummary) { this.inputSummary = inputSummary; }

    public String getOutputSummary() { return outputSummary; }
    public void setOutputSummary(String outputSummary) { this.outputSummary = outputSummary; }

    public List<ToolCallRecord> getToolCalls() { return toolCalls; }
    public void setToolCalls(List<ToolCallRecord> toolCalls) { this.toolCalls = toolCalls; }

    public List<String> getRagCitations() { return ragCitations; }
    public void setRagCitations(List<String> ragCitations) { this.ragCitations = ragCitations; }

    public Instant getStartTime() { return startTime; }
    public void setStartTime(Instant startTime) { this.startTime = startTime; }

    public Instant getEndTime() { return endTime; }
    public void setEndTime(Instant endTime) { this.endTime = endTime; }

    public long getLatencyMs() { return latencyMs; }
    public void setLatencyMs(long latencyMs) { this.latencyMs = latencyMs; }

    public String getErrorInfo() { return errorInfo; }
    public void setErrorInfo(String errorInfo) { this.errorInfo = errorInfo; }

    /** 单次工具调用记录 */
    public static class ToolCallRecord {
        private String toolName;
        private String paramsDigest;
        private String resultStatus;
        private long durationMs;

        public String getToolName() { return toolName; }
        public void setToolName(String toolName) { this.toolName = toolName; }
        public String getParamsDigest() { return paramsDigest; }
        public void setParamsDigest(String paramsDigest) { this.paramsDigest = paramsDigest; }
        public String getResultStatus() { return resultStatus; }
        public void setResultStatus(String resultStatus) { this.resultStatus = resultStatus; }
        public long getDurationMs() { return durationMs; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
    }
}
