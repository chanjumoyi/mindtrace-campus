package com.mindline.htp;

import com.mindline.model.VisualObservation;
import com.mindline.platform.LocalMockAdapter;
import com.mindline.platform.PlatformAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("房树人视觉观察服务测试")
class HTPObservationServiceTest {

    private HTPObservationService service;

    @BeforeEach
    void setUp() {
        PlatformAdapter adapter = new LocalMockAdapter();
        service = new HTPObservationService(adapter);
    }

    @Test
    @DisplayName("有效图片引用应返回视觉观察")
    void shouldReturnObservationForValidImage() {
        VisualObservation result = service.getVisualObservation("img/test.png");
        assertNotNull(result);
        assertNotNull(result.getHouseDescription());
        assertNotNull(result.getOverallPlacement());
    }

    @Test
    @DisplayName("null图片引用应返回null")
    void shouldReturnNullForNullImageRef() {
        assertNull(service.getVisualObservation(null));
    }

    @Test
    @DisplayName("空字符串图片引用应返回null")
    void shouldReturnNullForEmptyImageRef() {
        assertNull(service.getVisualObservation(""));
    }

    @Test
    @DisplayName("LocalMockAdapter下多模态应可用")
    void shouldReportMultimodalAvailable() {
        assertTrue(service.isMultimodalAvailable());
    }

    @Test
    @DisplayName("视觉观察应包含所有必要字段")
    void shouldContainAllFields() {
        VisualObservation result = service.getVisualObservation("img/test.png");
        assertNotNull(result.getHouseDescription());
        assertNotNull(result.getTreeDescription());
        assertNotNull(result.getPersonDescription());
        assertNotNull(result.getOverallPlacement());
        assertNotNull(result.getNotableFeatures());
        assertFalse(result.getNotableFeatures().isEmpty());
    }
}
