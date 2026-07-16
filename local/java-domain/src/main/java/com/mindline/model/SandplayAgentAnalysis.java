package com.mindline.model;

import java.util.List;

/**
 * 沙盘Agent分析结果。
 */
public class SandplayAgentAnalysis {

    private String themeSummary;
    private List<String> explorationQuestions;
    private String disclaimer;
    private List<Citation> citations;

    public SandplayAgentAnalysis() {}

    public String getThemeSummary() { return themeSummary; }
    public void setThemeSummary(String themeSummary) { this.themeSummary = themeSummary; }

    public List<String> getExplorationQuestions() { return explorationQuestions; }
    public void setExplorationQuestions(List<String> explorationQuestions) { this.explorationQuestions = explorationQuestions; }

    public String getDisclaimer() { return disclaimer; }
    public void setDisclaimer(String disclaimer) { this.disclaimer = disclaimer; }

    public List<Citation> getCitations() { return citations; }
    public void setCitations(List<Citation> citations) { this.citations = citations; }
}
