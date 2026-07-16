package com.mindline.model;

import java.util.List;
import java.util.Map;

/**
 * 沙盘分析请求 —— 包含几何特征和用户描述，用于Agent分析。
 */
public class SandplayAnalysisRequest {

    private String sessionId;
    private List<SandplayElement> elements;
    private String userDescription;

    // 几何特征（由SandplayGeometryService预先计算）
    private Map<String, CategoryStat> categoryDistribution;
    private QuadrantAnalysis quadrantAnalysis;
    private List<ClusterInfo> clusters;
    private List<AdjacencyEdge> adjacencyEdges;

    public SandplayAnalysisRequest() {}

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public List<SandplayElement> getElements() { return elements; }
    public void setElements(List<SandplayElement> elements) { this.elements = elements; }

    public String getUserDescription() { return userDescription; }
    public void setUserDescription(String userDescription) { this.userDescription = userDescription; }

    public Map<String, CategoryStat> getCategoryDistribution() { return categoryDistribution; }
    public void setCategoryDistribution(Map<String, CategoryStat> categoryDistribution) { this.categoryDistribution = categoryDistribution; }

    public QuadrantAnalysis getQuadrantAnalysis() { return quadrantAnalysis; }
    public void setQuadrantAnalysis(QuadrantAnalysis quadrantAnalysis) { this.quadrantAnalysis = quadrantAnalysis; }

    public List<ClusterInfo> getClusters() { return clusters; }
    public void setClusters(List<ClusterInfo> clusters) { this.clusters = clusters; }

    public List<AdjacencyEdge> getAdjacencyEdges() { return adjacencyEdges; }
    public void setAdjacencyEdges(List<AdjacencyEdge> adjacencyEdges) { this.adjacencyEdges = adjacencyEdges; }

    /** 类别统计 */
    public static class CategoryStat {
        private int count;
        private double proportion;
        public int getCount() { return count; }
        public void setCount(int count) { this.count = count; }
        public double getProportion() { return proportion; }
        public void setProportion(double proportion) { this.proportion = proportion; }
    }

    /** 象限分析 */
    public static class QuadrantAnalysis {
        private QuadrantStat upperLeft;
        private QuadrantStat upperRight;
        private QuadrantStat lowerLeft;
        private QuadrantStat lowerRight;
        public QuadrantStat getUpperLeft() { return upperLeft; }
        public void setUpperLeft(QuadrantStat upperLeft) { this.upperLeft = upperLeft; }
        public QuadrantStat getUpperRight() { return upperRight; }
        public void setUpperRight(QuadrantStat upperRight) { this.upperRight = upperRight; }
        public QuadrantStat getLowerLeft() { return lowerLeft; }
        public void setLowerLeft(QuadrantStat lowerLeft) { this.lowerLeft = lowerLeft; }
        public QuadrantStat getLowerRight() { return lowerRight; }
        public void setLowerRight(QuadrantStat lowerRight) { this.lowerRight = lowerRight; }
    }

    public static class QuadrantStat {
        private int elementCount;
        private List<String> categories;
        private int categoryDiversity;
        public int getElementCount() { return elementCount; }
        public void setElementCount(int elementCount) { this.elementCount = elementCount; }
        public List<String> getCategories() { return categories; }
        public void setCategories(List<String> categories) { this.categories = categories; }
        public int getCategoryDiversity() { return categoryDiversity; }
        public void setCategoryDiversity(int categoryDiversity) { this.categoryDiversity = categoryDiversity; }
    }

    /** 聚类信息 */
    public static class ClusterInfo {
        private int clusterId;
        private int elementCount;
        private double centerX;
        private double centerY;
        private List<String> memberInstanceIds;
        public int getClusterId() { return clusterId; }
        public void setClusterId(int clusterId) { this.clusterId = clusterId; }
        public int getElementCount() { return elementCount; }
        public void setElementCount(int elementCount) { this.elementCount = elementCount; }
        public double getCenterX() { return centerX; }
        public void setCenterX(double centerX) { this.centerX = centerX; }
        public double getCenterY() { return centerY; }
        public void setCenterY(double centerY) { this.centerY = centerY; }
        public List<String> getMemberInstanceIds() { return memberInstanceIds; }
        public void setMemberInstanceIds(List<String> memberInstanceIds) { this.memberInstanceIds = memberInstanceIds; }
    }

    /** 邻接边 */
    public static class AdjacencyEdge {
        private String elementA;
        private String elementB;
        private double distance;
        public String getElementA() { return elementA; }
        public void setElementA(String elementA) { this.elementA = elementA; }
        public String getElementB() { return elementB; }
        public void setElementB(String elementB) { this.elementB = elementB; }
        public double getDistance() { return distance; }
        public void setDistance(double distance) { this.distance = distance; }
    }
}
