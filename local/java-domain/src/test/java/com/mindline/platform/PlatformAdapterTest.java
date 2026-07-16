package com.mindline.platform;

import com.mindline.model.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * PlatformAdapter接口契约测试 —— 验证LocalMockAdapter行为符合规范。
 *
 * <p>所有测试使用Mock数据，零真实学生信息。
 */
@DisplayName("PlatformAdapter 契约测试")
class PlatformAdapterTest {

    private PlatformAdapter adapter;

    @BeforeEach
    void setUp() {
        adapter = new LocalMockAdapter();
    }

    // ================================================================
    // 适配器元信息
    // ================================================================

    @Test
    @DisplayName("应返回local模式")
    void shouldReturnLocalMode() {
        assertEquals("local", adapter.getMode());
    }

    // ================================================================
    // 沙盘分析
    // ================================================================

    @Nested
    @DisplayName("沙盘分析")
    class SandplayAnalysis {

        @Test
        @DisplayName("应返回包含主题摘要的分析结果")
        void shouldReturnAnalysisWithThemeSummary() {
            SandplayAnalysisRequest req = createBasicRequest();
            SandplayAgentAnalysis result = adapter.analyzeSandplay(req);

            assertNotNull(result);
            assertNotNull(result.getThemeSummary());
            assertFalse(result.getThemeSummary().isEmpty());
        }

        @Test
        @DisplayName("应包含2-4个探索问题")
        void shouldReturn2To4ExplorationQuestions() {
            SandplayAnalysisRequest req = createBasicRequest();
            SandplayAgentAnalysis result = adapter.analyzeSandplay(req);

            assertNotNull(result.getExplorationQuestions());
            assertTrue(result.getExplorationQuestions().size() >= 2,
                    "应有至少2个问题，实际: " + result.getExplorationQuestions().size());
            assertTrue(result.getExplorationQuestions().size() <= 4,
                    "应最多4个问题，实际: " + result.getExplorationQuestions().size());
        }

        @Test
        @DisplayName("应包含非空免责声明")
        void shouldContainDisclaimer() {
            SandplayAnalysisRequest req = createBasicRequest();
            SandplayAgentAnalysis result = adapter.analyzeSandplay(req);

            assertNotNull(result.getDisclaimer());
            assertFalse(result.getDisclaimer().isEmpty());
            assertTrue(result.getDisclaimer().contains("不构成心理诊断"),
                    "免责声明应明确'不构成心理诊断'");
        }

        @Test
        @DisplayName("应包含RAG引用来源")
        void shouldContainCitations() {
            SandplayAnalysisRequest req = createBasicRequest();
            SandplayAgentAnalysis result = adapter.analyzeSandplay(req);

            assertNotNull(result.getCitations());
            assertFalse(result.getCitations().isEmpty(), "应至少有1条引用");
            assertNotNull(result.getCitations().get(0).getDocId());
            assertNotNull(result.getCitations().get(0).getTitle());
        }

        @Test
        @DisplayName("空画布应正常返回结果")
        void shouldHandleEmptyCanvas() {
            SandplayAnalysisRequest req = new SandplayAnalysisRequest();
            req.setSessionId("test-empty");
            req.setElements(Collections.emptyList());
            req.setUserDescription("我只写了描述，没有放元素");

            SandplayAgentAnalysis result = adapter.analyzeSandplay(req);
            assertNotNull(result);
            assertNotNull(result.getThemeSummary());
        }
    }

    // ================================================================
    // 房树人分析
    // ================================================================

    @Nested
    @DisplayName("房树人分析")
    class HTPAnalysis {

        @Test
        @DisplayName("应包含三个输出分区：观察/用户解释/探索提示")
        void shouldHaveThreeSections() {
            HTPAnalysisRequest req = createBasicHTPRequest();
            HTPAgentAnalysis result = adapter.analyzeHTP(req);

            assertNotNull(result.getObservations());
            assertNotNull(result.getUserInterpretation());
            assertNotNull(result.getExplorationPrompts());
            assertTrue(result.getExplorationPrompts().size() >= 2);
        }

        @Test
        @DisplayName("应包含免责声明和AI推测标注")
        void shouldContainDisclaimerAndAINote() {
            HTPAnalysisRequest req = createBasicHTPRequest();
            HTPAgentAnalysis result = adapter.analyzeHTP(req);

            assertNotNull(result.getDisclaimer());
            assertTrue(result.getDisclaimer().contains("不具有诊断意义"));
            assertNotNull(result.getAiInferenceNote());
            assertTrue(result.getAiInferenceNote().contains("辅助推测"));
        }

        @Test
        @DisplayName("无视觉观察时应降级为仅问卷分析")
        void shouldDegradeWithoutVisualObservation() {
            HTPAnalysisRequest req = createBasicHTPRequest();
            req.setVisualObservation(null);
            req.setImageRef(null);

            HTPAgentAnalysis result = adapter.analyzeHTP(req);
            assertNotNull(result);
            assertTrue(result.getObservations().contains("图像分析暂不可用"));
        }

        @Test
        @DisplayName("有视觉观察时应包含画面描述")
        void shouldIncludeVisualDescriptionWhenAvailable() {
            HTPAnalysisRequest req = createBasicHTPRequest();
            VisualObservation obs = new VisualObservation();
            obs.setHouseDescription("一栋红色屋顶的小房子");
            obs.setOverallPlacement("位于画面中央");
            req.setVisualObservation(obs);

            HTPAgentAnalysis result = adapter.analyzeHTP(req);
            assertNotNull(result);
            assertTrue(result.getObservations().contains("红色屋顶"));
        }
    }

    // ================================================================
    // 多模态模型
    // ================================================================

    @Nested
    @DisplayName("多模态视觉描述")
    class Multimodal {

        @Test
        @DisplayName("有效图片引用应返回视觉观察")
        void shouldReturnVisualObservationForValidImage() {
            VisualObservation result = adapter.describeImage("img/test.png");

            assertNotNull(result);
            assertNotNull(result.getHouseDescription());
            assertNotNull(result.getTreeDescription());
            assertNotNull(result.getPersonDescription());
            assertNotNull(result.getOverallPlacement());
            assertNotNull(result.getNotableFeatures());
            assertFalse(result.getNotableFeatures().isEmpty());
        }

        @Test
        @DisplayName("null图片引用应返回null")
        void shouldReturnNullForNullImageRef() {
            VisualObservation result = adapter.describeImage(null);
            assertNull(result);
        }

        @Test
        @DisplayName("空字符串图片引用应返回null")
        void shouldReturnNullForEmptyImageRef() {
            VisualObservation result = adapter.describeImage("");
            assertNull(result);
        }
    }

    // ================================================================
    // RAG检索
    // ================================================================

    @Nested
    @DisplayName("RAG知识检索")
    class KnowledgeRetrieval {

        @Test
        @DisplayName("沙盘主题应返回沙盘相关引用")
        void shouldReturnSandplayCitations() {
            List<Citation> results = adapter.retrieveKnowledge("sandplay", "沙盘分析", 5);
            assertNotNull(results);
            assertFalse(results.isEmpty());
            assertTrue(results.get(0).getTitle().contains("沙盘"),
                    "引用标题应包含'沙盘'");
        }

        @Test
        @DisplayName("房树人主题应返回HTP相关引用")
        void shouldReturnHTPCitations() {
            List<Citation> results = adapter.retrieveKnowledge("htp", "房树人", 5);
            assertNotNull(results);
            assertFalse(results.isEmpty());
            assertTrue(results.get(0).getTitle().contains("房树人"),
                    "引用标题应包含'房树人'");
        }

        @Test
        @DisplayName("未知主题应返回空列表")
        void shouldReturnEmptyForUnknownTopic() {
            List<Citation> results = adapter.retrieveKnowledge("unknown", "test", 5);
            assertNotNull(results);
            assertTrue(results.isEmpty());
        }
    }

    // ================================================================
    // 工具执行
    // ================================================================

    @Nested
    @DisplayName("工具执行")
    class ToolExecution {

        @Test
        @DisplayName("save_sandbox_record应返回记录ID")
        void shouldSaveSandboxRecord() {
            Map<String, Object> params = new HashMap<>();
            params.put("elementCount", 5);

            Map<String, Object> result = adapter.executeTool("save_sandbox_record", params);
            assertNotNull(result);
            assertEquals("saved", result.get("status"));
            assertNotNull(result.get("recordId"));
        }

        @Test
        @DisplayName("同一幂等键重复调用应返回相同结果")
        void shouldBeIdempotent() {
            String idempKey = "test-idempotent-" + UUID.randomUUID();
            Map<String, Object> params = new HashMap<>();
            params.put("idempotencyKey", idempKey);
            params.put("elementCount", 3);

            Map<String, Object> first = adapter.executeTool("save_sandbox_record", params);
            Map<String, Object> second = adapter.executeTool("save_sandbox_record", params);

            assertEquals(first.get("recordId"), second.get("recordId"),
                    "相同幂等键应返回相同recordId");
        }

        @Test
        @DisplayName("未知工具应抛出异常")
        void shouldThrowForUnknownTool() {
            assertThrows(ToolExecutionException.class, () ->
                    adapter.executeTool("unknown_tool", Collections.emptyMap()));
        }
    }

    // ================================================================
    // 工厂方法
    // ================================================================

    @Nested
    @DisplayName("适配器工厂")
    class Factory {

        @Test
        @DisplayName("create('local')应返回LocalMockAdapter")
        void shouldCreateLocalMockAdapter() {
            PlatformAdapter adapter = PlatformAdapterFactory.create("local");
            assertInstanceOf(LocalMockAdapter.class, adapter);
        }

        @Test
        @DisplayName("create('kingdee')当前应抛出UnsupportedOperationException")
        void shouldThrowForKingdeeCurrently() {
            assertThrows(UnsupportedOperationException.class, () ->
                    PlatformAdapterFactory.create("kingdee"));
        }

        @Test
        @DisplayName("未知模式应抛出IllegalArgumentException")
        void shouldThrowForUnknownMode() {
            assertThrows(IllegalArgumentException.class, () ->
                    PlatformAdapterFactory.create("production"));
        }
    }

    // ---- 辅助方法 ----

    private SandplayAnalysisRequest createBasicRequest() {
        SandplayAnalysisRequest req = new SandplayAnalysisRequest();
        req.setSessionId("test-session-" + UUID.randomUUID().toString().substring(0, 8));

        SandplayElement elem1 = new SandplayElement("inst-001", "tree-oak", "植物",
                150.0, 300.0, 0.0, 1.0, 0);
        SandplayElement elem2 = new SandplayElement("inst-002", "person-adult", "人物",
                400.0, 250.0, 0.0, 1.2, 1);
        req.setElements(Arrays.asList(elem1, elem2));
        req.setUserDescription("测试沙盘：一棵树旁边站了一个人");

        return req;
    }

    private HTPAnalysisRequest createBasicHTPRequest() {
        HTPAnalysisRequest req = new HTPAnalysisRequest();
        req.setSessionId("test-htp-" + UUID.randomUUID().toString().substring(0, 8));
        req.setImageRef("img/test-drawing.png");
        req.setDrawingOrder("house-first");
        req.setCompleteness("mostly-complete");
        req.setHouseDescription("一栋有烟囱的房子");
        req.setTreeDescription("一棵茂盛的大树");
        req.setPersonDescription("一个站立的年轻人");

        VisualObservation obs = new VisualObservation();
        obs.setHouseDescription("方形房屋，有三角形屋顶");
        obs.setTreeDescription("圆形树冠的大树");
        obs.setPersonDescription("小型人物，双臂下垂");
        obs.setOverallPlacement("元素集中在画面中下部");
        obs.setNotableFeatures(Arrays.asList("上方留白较多"));
        req.setVisualObservation(obs);

        return req;
    }
}
