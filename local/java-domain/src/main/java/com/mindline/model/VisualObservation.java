package com.mindline.model;

import java.util.List;

/**
 * 多模态模型对画作图片的客观视觉描述。
 */
public class VisualObservation {

    private String houseDescription;
    private String treeDescription;
    private String personDescription;
    private String overallPlacement;
    private List<String> notableFeatures;

    public VisualObservation() {}

    public String getHouseDescription() { return houseDescription; }
    public void setHouseDescription(String houseDescription) { this.houseDescription = houseDescription; }

    public String getTreeDescription() { return treeDescription; }
    public void setTreeDescription(String treeDescription) { this.treeDescription = treeDescription; }

    public String getPersonDescription() { return personDescription; }
    public void setPersonDescription(String personDescription) { this.personDescription = personDescription; }

    public String getOverallPlacement() { return overallPlacement; }
    public void setOverallPlacement(String overallPlacement) { this.overallPlacement = overallPlacement; }

    public List<String> getNotableFeatures() { return notableFeatures; }
    public void setNotableFeatures(List<String> notableFeatures) { this.notableFeatures = notableFeatures; }
}
