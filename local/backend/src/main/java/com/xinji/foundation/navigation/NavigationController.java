package com.xinji.foundation.navigation;

import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.ApiResponse;
import java.util.ArrayList;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/navigation")
public class NavigationController {
    @GetMapping
    public ApiResponse<List<NavItem>> navigation() {
        var p = SecurityUtils.current();
        List<NavItem> items = new ArrayList<>();
        items.add(new NavItem("handwriting", "笔迹观察", "/handwriting", "pen"));
        items.add(new NavItem("home", "首页", "/", "home"));
        if (p.permissions().contains("mood:read")) items.add(new NavItem("mood", "情绪打卡", "/mood", "heart"));
        if (p.permissions().contains("task:read")) items.add(new NavItem("tasks", "任务状态", "/tasks", "tasks"));
        if (p.permissions().contains("file:read")) items.add(new NavItem("files", "文件中心", "/files", "folder"));
        items.add(new NavItem("profile", "个人中心", "/profile", "user"));
        if (p.permissions().contains("module:read")) items.add(new NavItem("integration", "模块集成", "/integration", "plug"));
        if (p.permissions().contains("audit:read")) items.add(new NavItem("audit", "审计日志", "/audit", "shield"));
        return ApiResponse.ok(items);
    }
    public record NavItem(String id, String label, String path, String icon) {}
}
