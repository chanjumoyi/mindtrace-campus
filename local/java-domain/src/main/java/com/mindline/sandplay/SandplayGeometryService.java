package com.mindline.sandplay;

import com.mindline.model.SandplayAnalysisRequest;
import com.mindline.model.SandplayElement;

import java.util.*;
import java.util.stream.Collectors;

/**
 * 沙盘几何特征提取服务 —— 纯Java实现，不依赖任何外部空间分析库。
 *
 * <p>所有算法手动实现以保证本地与苍穹环境的一致性。
 * 沙盘元素数量通常&lt;100，O(n²)算法完全可接受。
 *
 * <p>提取的特征包括：
 * <ul>
 *   <li>类别分布统计（每个类别的元素数量和占比）</li>
 *   <li>象限分析（以画布中心(400,300)分四象限）</li>
 *   <li>DBSCAN空间聚类</li>
 *   <li>邻接矩阵（距离&lt;100逻辑单位判定为邻接）</li>
 *   <li>坐标范围校验</li>
 * </ul>
 */
public class SandplayGeometryService {

    /** 画布宽度（逻辑单位） */
    public static final double CANVAS_WIDTH = 800.0;

    /** 画布高度（逻辑单位） */
    public static final double CANVAS_HEIGHT = 600.0;

    /** 画布中心X */
    public static final double CENTER_X = CANVAS_WIDTH / 2.0;   // 400.0

    /** 画布中心Y */
    public static final double CENTER_Y = CANVAS_HEIGHT / 2.0;  // 300.0

    /** DBSCAN邻域半径（逻辑单位） */
    public static final double DBSCAN_EPS = 100.0;

    /** DBSCAN最小邻域点数 */
    public static final int DBSCAN_MIN_PTS = 3;

    /** 邻接距离阈值（逻辑单位） */
    public static final double ADJACENCY_THRESHOLD = 100.0;

    /**
     * 提取沙盘布局的全部几何特征。
     *
     * @param elements 沙盘元素列表
     * @return 填充了几何特征的请求对象
     * @throws IllegalArgumentException 如果有元素的坐标超出有效范围
     */
    public SandplayAnalysisRequest extractFeatures(List<SandplayElement> elements) {
        validateCoordinates(elements);

        SandplayAnalysisRequest request = new SandplayAnalysisRequest();
        request.setElements(elements);
        request.setCategoryDistribution(calculateCategoryDistribution(elements));
        request.setQuadrantAnalysis(calculateQuadrantAnalysis(elements));
        request.setClusters(performDBSCAN(elements));
        request.setAdjacencyEdges(calculateAdjacency(elements));

        return request;
    }

    // ================================================================
    // 坐标校验
    // ================================================================

    /**
     * 校验所有元素的坐标在有效范围内。
     *
     * @throws IllegalArgumentException 坐标超出范围
     */
    public void validateCoordinates(List<SandplayElement> elements) {
        for (SandplayElement elem : elements) {
            if (elem.getX() < 0 || elem.getX() > CANVAS_WIDTH) {
                throw new IllegalArgumentException(
                        String.format("元素 %s X坐标 %.1f 超出范围 [0, %.0f]",
                                elem.getInstanceId(), elem.getX(), CANVAS_WIDTH));
            }
            if (elem.getY() < 0 || elem.getY() > CANVAS_HEIGHT) {
                throw new IllegalArgumentException(
                        String.format("元素 %s Y坐标 %.1f 超出范围 [0, %.0f]",
                                elem.getInstanceId(), elem.getY(), CANVAS_HEIGHT));
            }
        }
    }

    // ================================================================
    // 类别分布
    // ================================================================

    /**
     * 计算每个类别的元素数量和占比。
     */
    public Map<String, SandplayAnalysisRequest.CategoryStat> calculateCategoryDistribution(
            List<SandplayElement> elements) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (SandplayElement e : elements) {
            counts.merge(e.getCategory(), 1, Integer::sum);
        }

        int total = elements.size();
        Map<String, SandplayAnalysisRequest.CategoryStat> distribution = new LinkedHashMap<>();
        for (Map.Entry<String, Integer> entry : counts.entrySet()) {
            SandplayAnalysisRequest.CategoryStat stat = new SandplayAnalysisRequest.CategoryStat();
            stat.setCount(entry.getValue());
            stat.setProportion(total > 0 ? (double) entry.getValue() / total : 0.0);
            distribution.put(entry.getKey(), stat);
        }
        return distribution;
    }

    // ================================================================
    // 象限分析
    // ================================================================

    /**
     * 以画布中心(400, 300)为原点划分四个象限，统计每个象限的元素分布。
     *
     * <pre>
     *   左上(-x,-y)  |  右上(+x,-y)
     *   -------------+--------------
     *   左下(-x,+y)  |  右下(+x,+y)
     * </pre>
     */
    public SandplayAnalysisRequest.QuadrantAnalysis calculateQuadrantAnalysis(
            List<SandplayElement> elements) {

        List<SandplayElement> upperLeft = new ArrayList<>();
        List<SandplayElement> upperRight = new ArrayList<>();
        List<SandplayElement> lowerLeft = new ArrayList<>();
        List<SandplayElement> lowerRight = new ArrayList<>();

        for (SandplayElement e : elements) {
            if (e.getX() <= CENTER_X && e.getY() <= CENTER_Y) {
                upperLeft.add(e);
            } else if (e.getX() > CENTER_X && e.getY() <= CENTER_Y) {
                upperRight.add(e);
            } else if (e.getX() <= CENTER_X && e.getY() > CENTER_Y) {
                lowerLeft.add(e);
            } else {
                lowerRight.add(e);
            }
        }

        SandplayAnalysisRequest.QuadrantAnalysis analysis = new SandplayAnalysisRequest.QuadrantAnalysis();
        analysis.setUpperLeft(toQuadrantStat(upperLeft));
        analysis.setUpperRight(toQuadrantStat(upperRight));
        analysis.setLowerLeft(toQuadrantStat(lowerLeft));
        analysis.setLowerRight(toQuadrantStat(lowerRight));
        return analysis;
    }

    private SandplayAnalysisRequest.QuadrantStat toQuadrantStat(List<SandplayElement> elements) {
        SandplayAnalysisRequest.QuadrantStat stat = new SandplayAnalysisRequest.QuadrantStat();
        stat.setElementCount(elements.size());
        stat.setCategories(elements.stream()
                .map(SandplayElement::getCategory)
                .distinct()
                .sorted()
                .collect(Collectors.toList()));
        stat.setCategoryDiversity((int) elements.stream()
                .map(SandplayElement::getCategory)
                .distinct()
                .count());
        return stat;
    }

    // ================================================================
    // DBSCAN 聚类
    // ================================================================

    /**
     * DBSCAN密度聚类算法实现。
     *
     * <p>参数：ε=100逻辑单位，minPts=3。
     * 时间复杂度 O(n²)，空间复杂度 O(n)。
     *
     * @param elements 沙盘元素列表
     * @return 聚类列表（-1表示噪声点，不包含在返回结果中）
     */
    public List<SandplayAnalysisRequest.ClusterInfo> performDBSCAN(List<SandplayElement> elements) {
        if (elements.isEmpty()) {
            return Collections.emptyList();
        }

        int n = elements.size();
        int[] labels = new int[n];
        Arrays.fill(labels, -1); // -1 = 未分类（噪声）

        int clusterId = 0;
        for (int i = 0; i < n; i++) {
            if (labels[i] != -1) continue; // 已分类

            List<Integer> neighbors = rangeQuery(elements, i);
            if (neighbors.size() < DBSCAN_MIN_PTS) {
                labels[i] = -1; // 标记为噪声
                continue;
            }

            // 新聚类
            clusterId++;
            labels[i] = clusterId;
            expandCluster(elements, labels, neighbors, clusterId);
        }

        // 聚合聚类结果
        Map<Integer, List<Integer>> clusterMembers = new LinkedHashMap<>();
        for (int i = 0; i < n; i++) {
            if (labels[i] > 0) {
                clusterMembers.computeIfAbsent(labels[i], k -> new ArrayList<>()).add(i);
            }
        }

        List<SandplayAnalysisRequest.ClusterInfo> result = new ArrayList<>();
        for (Map.Entry<Integer, List<Integer>> entry : clusterMembers.entrySet()) {
            List<Integer> memberIndices = entry.getValue();
            double sumX = 0, sumY = 0;
            List<String> ids = new ArrayList<>();
            for (int idx : memberIndices) {
                SandplayElement e = elements.get(idx);
                sumX += e.getX();
                sumY += e.getY();
                ids.add(e.getInstanceId());
            }
            SandplayAnalysisRequest.ClusterInfo info = new SandplayAnalysisRequest.ClusterInfo();
            info.setClusterId(entry.getKey());
            info.setElementCount(memberIndices.size());
            info.setCenterX(sumX / memberIndices.size());
            info.setCenterY(sumY / memberIndices.size());
            info.setMemberInstanceIds(ids);
            result.add(info);
        }
        return result;
    }

    /**
     * ε-邻域查询：返回与元素i距离≤ε的所有点的索引。
     */
    private List<Integer> rangeQuery(List<SandplayElement> elements, int i) {
        List<Integer> neighbors = new ArrayList<>();
        SandplayElement ei = elements.get(i);
        for (int j = 0; j < elements.size(); j++) {
            if (i == j) continue;
            if (euclideanDistance(ei, elements.get(j)) <= DBSCAN_EPS) {
                neighbors.add(j);
            }
        }
        return neighbors;
    }

    /** 从核心点扩展聚类 */
    private void expandCluster(List<SandplayElement> elements, int[] labels,
                                List<Integer> seedNeighbors, int clusterId) {
        // 使用队列进行BFS扩展
        Deque<Integer> queue = new ArrayDeque<>(seedNeighbors);
        while (!queue.isEmpty()) {
            int idx = queue.poll();
            if (labels[idx] == -1) {
                // 噪声点加入聚类但不作为核心点扩展
                labels[idx] = clusterId;
                continue;
            }
            if (labels[idx] > 0) continue; // 已经属于某个聚类

            labels[idx] = clusterId;
            List<Integer> neighbors = rangeQuery(elements, idx);
            if (neighbors.size() >= DBSCAN_MIN_PTS) {
                queue.addAll(neighbors);
            }
        }
    }

    // ================================================================
    // 邻接矩阵
    // ================================================================

    /**
     * 计算元素间的邻接关系。
     * 两元素距离 ≤ 100 逻辑单位判定为"邻接"。
     */
    public List<SandplayAnalysisRequest.AdjacencyEdge> calculateAdjacency(
            List<SandplayElement> elements) {
        List<SandplayAnalysisRequest.AdjacencyEdge> edges = new ArrayList<>();
        int n = elements.size();
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                double dist = euclideanDistance(elements.get(i), elements.get(j));
                if (dist <= ADJACENCY_THRESHOLD) {
                    SandplayAnalysisRequest.AdjacencyEdge edge = new SandplayAnalysisRequest.AdjacencyEdge();
                    edge.setElementA(elements.get(i).getInstanceId());
                    edge.setElementB(elements.get(j).getInstanceId());
                    edge.setDistance(Math.round(dist * 100.0) / 100.0);
                    edges.add(edge);
                }
            }
        }
        return edges;
    }

    // ================================================================
    // 距离计算
    // ================================================================

    /**
     * 计算两个元素之间的欧几里得距离。
     */
    public double euclideanDistance(SandplayElement a, SandplayElement b) {
        double dx = a.getX() - b.getX();
        double dy = a.getY() - b.getY();
        return Math.sqrt(dx * dx + dy * dy);
    }
}
