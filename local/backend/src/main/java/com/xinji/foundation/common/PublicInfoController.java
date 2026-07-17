package com.xinji.foundation.common;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/public")
public class PublicInfoController {
    @GetMapping("/info")
    public ApiResponse<Map<String,Object>> info() {
        return ApiResponse.ok(Map.of(
            "name", "心迹AI公共基础服务",
            "version", "1.0.0",
            "owner", "C",
            "scope", "公共框架、数据底座、苍穹适配、系统集成",
            "medicalDisclaimer", "本系统不提供医学诊断，演示数据均为模拟数据"
        ));
    }
}
