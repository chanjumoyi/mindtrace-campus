package com.mindline.htp;

import com.mindline.model.VisualObservation;
import com.mindline.platform.PlatformAdapter;
import com.mindline.platform.MultimodalException;

/**
 * 房树人视觉观察服务 —— 通过PlatformAdapter调用多模态模型，
 * 处理超时/不可用降级。
 *
 * <p>降级策略：多模态模型不可用时返回null，
 * 上层（HTPAnalysisController）负责在返回中标注降级信息。
 */
public class HTPObservationService {

    private final PlatformAdapter platformAdapter;

    public HTPObservationService(PlatformAdapter platformAdapter) {
        this.platformAdapter = platformAdapter;
    }

    /**
     * 获取画作图片的视觉观察。
     *
     * @param imageRef 图片文件引用路径
     * @return 视觉观察结果；模型不可用或imageRef为null时返回null
     */
    public VisualObservation getVisualObservation(String imageRef) {
        if (imageRef == null || imageRef.isEmpty()) {
            return null;
        }
        try {
            return platformAdapter.describeImage(imageRef);
        } catch (MultimodalException e) {
            // 多模态模型不可用 → 降级为仅问卷分析
            return null;
        }
    }

    /**
     * @return 多模态模型当前是否可用
     */
    public boolean isMultimodalAvailable() {
        try {
            platformAdapter.describeImage("ping");
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
