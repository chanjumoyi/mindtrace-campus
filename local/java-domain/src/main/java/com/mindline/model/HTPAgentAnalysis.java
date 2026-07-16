package com.mindline.model;

import java.util.List;

/**
 * 房树人Agent分析结果。
 */
public class HTPAgentAnalysis {

    private String observations;
    private String userInterpretation;
    private List<String> explorationPrompts;
    private String disclaimer;
    private String aiInferenceNote;
    private List<Citation> citations;

    public HTPAgentAnalysis() {}

    public String getObservations() { return observations; }
    public void setObservations(String observations) { this.observations = observations; }

    public String getUserInterpretation() { return userInterpretation; }
    public void setUserInterpretation(String userInterpretation) { this.userInterpretation = userInterpretation; }

    public List<String> getExplorationPrompts() { return explorationPrompts; }
    public void setExplorationPrompts(List<String> explorationPrompts) { this.explorationPrompts = explorationPrompts; }

    public String getDisclaimer() { return disclaimer; }
    public void setDisclaimer(String disclaimer) { this.disclaimer = disclaimer; }

    public String getAiInferenceNote() { return aiInferenceNote; }
    public void setAiInferenceNote(String aiInferenceNote) { this.aiInferenceNote = aiInferenceNote; }

    public List<Citation> getCitations() { return citations; }
    public void setCitations(List<Citation> citations) { this.citations = citations; }
}
