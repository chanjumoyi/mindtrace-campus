package com.mindline.sandplay;

import com.mindline.model.SandplayAnalysisRequest;
import com.mindline.model.SandplayElement;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * SandplayGeometryService 单元测试。
 * 所有测试数据为人工构造的模拟数据。
 */
@DisplayName("沙盘几何特征提取服务测试")
class SandplayGeometryServiceTest {

    private SandplayGeometryService service;

    @BeforeEach
    void setUp() {
        service = new SandplayGeometryService();
    }

    // ================================================================
    // 坐标校验
    // ================================================================

    @Nested
    @DisplayName("坐标校验")
    class CoordinateValidation {

        @Test
        @DisplayName("有效范围内的元素应通过校验")
        void shouldAcceptValidCoordinates() {
            List<SandplayElement> elements = List.of(
                    elem("inst-001", "人物", 0, 0),
                    elem("inst-002", "植物", 800, 600),
                    elem("inst-003", "建筑", 400, 300)
            );
            assertDoesNotThrow(() -> service.validateCoordinates(elements));
        }

        @Test
        @DisplayName("X坐标超出范围应抛出异常")
        void shouldRejectXOutOfRange() {
            List<SandplayElement> elements = List.of(
                    elem("inst-001", "人物", -1, 300)
            );
            assertThrows(IllegalArgumentException.class,
                    () -> service.validateCoordinates(elements));
        }

        @Test
        @DisplayName("X坐标超过800应抛出异常")
        void shouldRejectXExceedsMax() {
            List<SandplayElement> elements = List.of(
                    elem("inst-001", "人物", 801, 300)
            );
            assertThrows(IllegalArgumentException.class,
                    () -> service.validateCoordinates(elements));
        }

        @Test
        @DisplayName("Y坐标超出范围应抛出异常")
        void shouldRejectYOutOfRange() {
            List<SandplayElement> elements = List.of(
                    elem("inst-001", "人物", 400, 601)
            );
            assertThrows(IllegalArgumentException.class,
                    () -> service.validateCoordinates(elements));
        }

        @Test
        @DisplayName("空列表应通过校验")
        void shouldAcceptEmptyList() {
            assertDoesNotThrow(() -> service.validateCoordinates(Collections.emptyList()));
        }
    }

    // ================================================================
    // 类别分布
    // ================================================================

    @Nested
    @DisplayName("类别分布统计")
    class CategoryDistribution {

        @Test
        @DisplayName("应正确统计各类别数量")
        void shouldCountCategories() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 100, 100),
                    elem("i2", "人物", 200, 200),
                    elem("i3", "植物", 300, 300)
            );
            Map<String, SandplayAnalysisRequest.CategoryStat> dist = service.calculateCategoryDistribution(elements);

            assertEquals(2, dist.size());
            assertEquals(2, dist.get("人物").getCount());
            assertEquals(1, dist.get("植物").getCount());
        }

        @Test
        @DisplayName("应正确计算占比")
        void shouldCalculateProportions() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 100, 100),
                    elem("i2", "人物", 200, 200),
                    elem("i3", "植物", 300, 300),
                    elem("i4", "建筑", 400, 300)
            );
            Map<String, SandplayAnalysisRequest.CategoryStat> dist = service.calculateCategoryDistribution(elements);

            assertEquals(0.5, dist.get("人物").getProportion(), 0.001);
            assertEquals(0.25, dist.get("植物").getProportion(), 0.001);
            assertEquals(0.25, dist.get("建筑").getProportion(), 0.001);
        }

        @Test
        @DisplayName("空列表应返回空Map")
        void shouldReturnEmptyForEmptyList() {
            Map<String, SandplayAnalysisRequest.CategoryStat> dist =
                    service.calculateCategoryDistribution(Collections.emptyList());
            assertTrue(dist.isEmpty());
        }
    }

    // ================================================================
    // 象限分析
    // ================================================================

    @Nested
    @DisplayName("象限分析")
    class QuadrantAnalysis {

        @Test
        @DisplayName("元素应被正确分配到四个象限")
        void shouldAssignToCorrectQuadrants() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("ul", "人物", 100, 100),   // 左上
                    elem("ur", "植物", 500, 100),   // 右上
                    elem("ll", "建筑", 100, 500),   // 左下
                    elem("lr", "动物", 500, 500)    // 右下
            );
            SandplayAnalysisRequest.QuadrantAnalysis qa = service.calculateQuadrantAnalysis(elements);

            assertEquals(1, qa.getUpperLeft().getElementCount());
            assertEquals(1, qa.getUpperRight().getElementCount());
            assertEquals(1, qa.getLowerLeft().getElementCount());
            assertEquals(1, qa.getLowerRight().getElementCount());
        }

        @Test
        @DisplayName("中心线上的元素应归入左上/右下")
        void shouldHandleCenterLine() {
            List<SandplayElement> elements = List.of(
                    elem("center", "人物", 400, 300)  // 中心 = 左上象限 (x≤400, y≤300)
            );
            SandplayAnalysisRequest.QuadrantAnalysis qa = service.calculateQuadrantAnalysis(elements);

            assertEquals(1, qa.getUpperLeft().getElementCount());
            assertEquals(0, qa.getUpperRight().getElementCount());
            assertEquals(0, qa.getLowerLeft().getElementCount());
            assertEquals(0, qa.getLowerRight().getElementCount());
        }

        @Test
        @DisplayName("应统计类别多样性")
        void shouldCountCategoryDiversity() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 100, 100),
                    elem("i2", "植物", 150, 150),
                    elem("i3", "建筑", 120, 180)
            );
            SandplayAnalysisRequest.QuadrantAnalysis qa = service.calculateQuadrantAnalysis(elements);

            assertEquals(3, qa.getUpperLeft().getCategoryDiversity());
            assertEquals(3, qa.getUpperLeft().getCategories().size());
        }
    }

    // ================================================================
    // DBSCAN 聚类
    // ================================================================

    @Nested
    @DisplayName("DBSCAN聚类")
    class DBSCAN {

        @Test
        @DisplayName("紧密聚集的元素应形成一个聚类")
        void shouldClusterDensePoints() {
            // 5个点在(200,200)周围密集聚集
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 200, 200),
                    elem("i2", "植物", 210, 205),
                    elem("i3", "建筑", 195, 198),
                    elem("i4", "动物", 205, 195),
                    elem("i5", "自然", 200, 210)
            );
            List<SandplayAnalysisRequest.ClusterInfo> clusters = service.performDBSCAN(elements);

            assertFalse(clusters.isEmpty(), "应有至少一个聚类");
            SandplayAnalysisRequest.ClusterInfo c = clusters.get(0);
            assertTrue(c.getElementCount() >= 3, "核心聚类应至少有3个点");
        }

        @Test
        @DisplayName("远距离的孤立点应被标记为噪声")
        void shouldMarkIsolatedPointsAsNoise() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 100, 100),  // 孤立
                    elem("i2", "植物", 700, 500)   // 孤立
            );
            List<SandplayAnalysisRequest.ClusterInfo> clusters = service.performDBSCAN(elements);

            assertTrue(clusters.isEmpty(), "两个孤立点不应形成聚类");
        }

        @Test
        @DisplayName("空列表应返回空聚类列表")
        void shouldReturnEmptyForEmptyList() {
            List<SandplayAnalysisRequest.ClusterInfo> clusters =
                    service.performDBSCAN(Collections.emptyList());
            assertTrue(clusters.isEmpty());
        }

        @Test
        @DisplayName("两个分离的密集群应形成两个聚类")
        void shouldDetectTwoSeparateClusters() {
            List<SandplayElement> elements = new ArrayList<>();
            // 聚类1：左上角
            for (int i = 0; i < 5; i++) {
                elements.add(elem("c1-" + i, "人物", 100 + i * 10, 100 + i * 8));
            }
            // 聚类2：右下角（距离>300，远超ε=100）
            for (int i = 0; i < 5; i++) {
                elements.add(elem("c2-" + i, "植物", 600 + i * 10, 450 + i * 8));
            }
            List<SandplayAnalysisRequest.ClusterInfo> clusters = service.performDBSCAN(elements);

            assertTrue(clusters.size() >= 2, "应有至少2个聚类，实际: " + clusters.size());
        }
    }

    // ================================================================
    // 邻接矩阵
    // ================================================================

    @Nested
    @DisplayName("邻接矩阵")
    class Adjacency {

        @Test
        @DisplayName("距离≤100的元素应判定为邻接")
        void shouldDetectAdjacentElements() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 100, 100),
                    elem("i2", "植物", 150, 120)  // 距离≈53.85 ≤ 100
            );
            List<SandplayAnalysisRequest.AdjacencyEdge> edges = service.calculateAdjacency(elements);

            assertEquals(1, edges.size());
            assertEquals("i1", edges.get(0).getElementA());
            assertEquals("i2", edges.get(0).getElementB());
        }

        @Test
        @DisplayName("距离>100的元素不应判定为邻接")
        void shouldNotDetectFarElements() {
            List<SandplayElement> elements = Arrays.asList(
                    elem("i1", "人物", 0, 0),
                    elem("i2", "植物", 200, 200)  // 距离≈282.8 > 100
            );
            List<SandplayAnalysisRequest.AdjacencyEdge> edges = service.calculateAdjacency(elements);

            assertTrue(edges.isEmpty());
        }

        @Test
        @DisplayName("空列表应返回空边列表")
        void shouldReturnEmptyEdgesForEmptyList() {
            List<SandplayAnalysisRequest.AdjacencyEdge> edges =
                    service.calculateAdjacency(Collections.emptyList());
            assertTrue(edges.isEmpty());
        }
    }

    // ================================================================
    // 欧几里得距离
    // ================================================================

    @Nested
    @DisplayName("距离计算")
    class Distance {

        @Test
        @DisplayName("相同点距离为0")
        void shouldReturnZeroForSamePoint() {
            SandplayElement a = elem("i1", "人物", 100, 100);
            SandplayElement b = elem("i2", "植物", 100, 100);
            assertEquals(0.0, service.euclideanDistance(a, b), 0.001);
        }

        @Test
        @DisplayName("3-4-5三角形距离")
        void shouldCalculate345Triangle() {
            SandplayElement a = elem("i1", "人物", 0, 0);
            SandplayElement b = elem("i2", "植物", 3, 4);
            assertEquals(5.0, service.euclideanDistance(a, b), 0.001);
        }
    }

    // ---- 辅助方法 ----

    private SandplayElement elem(String instanceId, String category, double x, double y) {
        return new SandplayElement(instanceId, "elem-" + category, category, x, y, 0.0, 1.0, 0);
    }
}
