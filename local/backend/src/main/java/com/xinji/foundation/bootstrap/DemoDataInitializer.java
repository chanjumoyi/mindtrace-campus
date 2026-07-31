package com.xinji.foundation.bootstrap;

import com.xinji.foundation.auth.*;
import com.xinji.foundation.config.XinjiProperties;
import com.xinji.foundation.module.ModuleRegistrationEntity;
import com.xinji.foundation.module.ModuleRegistrationRepository;
import java.time.OffsetDateTime;
import java.util.*;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class DemoDataInitializer implements ApplicationRunner {
    private final PermissionRepository permissions;
    private final RoleRepository roles;
    private final UserRepository users;
    private final ModuleRegistrationRepository modules;
    private final PasswordEncoder encoder;
    private final XinjiProperties properties;

    public DemoDataInitializer(PermissionRepository permissions, RoleRepository roles, UserRepository users, ModuleRegistrationRepository modules, PasswordEncoder encoder, XinjiProperties properties) {
        this.permissions = permissions; this.roles = roles; this.users = users; this.modules = modules; this.encoder = encoder; this.properties = properties;
    }

    @Override @Transactional
    public void run(ApplicationArguments args) {
        Map<String, PermissionEntity> p = new LinkedHashMap<>();
        for (String[] item : PERMISSIONS) p.put(item[0], permission(item[0], item[1]));
        RoleEntity student = role("STUDENT", "学生", p, Set.of("profile:read","profile:write","task:read","task:write","file:read","file:write","ai:invoke","ai:log:read","module:read","mood:read","mood:write"));
        RoleEntity counselor = role("COUNSELOR", "咨询师/辅导员", p, Set.of("profile:read","profile:write","task:read","task:write","task:read:all","task:write:all","file:read","file:write","ai:invoke","ai:log:read","module:read","mood:read","mood:read:all"));
        RoleEntity sysAdmin = role("SYS_ADMIN", "系统管理员", p, p.keySet());
        if (properties.getDemo().isEnabled()) {
            user("student_demo", properties.getDemo().getStudentPassword(), "模拟学生", "student@example.invalid", student);
            user("counselor_demo", properties.getDemo().getCounselorPassword(), "模拟咨询师", "counselor@example.invalid", counselor);
            user("admin_demo", properties.getDemo().getAdminPassword(), "系统管理员", "admin@example.invalid", sysAdmin);
        }
        module("COMMON", "公共基础与苍穹集成", "C", null, null, "ACTIVE");
        module("HANDWRITING", "笔迹模块（A负责）", "A", null, "/health", "UNCONFIGURED");
        module("MULTIMODAL_AGENT", "房树人/沙盘/Agent模块（B负责）", "B", null, "/health", "UNCONFIGURED");
    }

    private PermissionEntity permission(String code, String name) {
        return permissions.findByCode(code).orElseGet(() -> {
            PermissionEntity e = new PermissionEntity(); e.setId(UUID.randomUUID().toString()); e.setCode(code); e.setName(name); e.setCreatedAt(OffsetDateTime.now()); return permissions.save(e);
        });
    }
    private RoleEntity role(String code, String name, Map<String, PermissionEntity> all, Set<String> codes) {
        RoleEntity e = roles.findByCode(code).orElseGet(() -> { RoleEntity r = new RoleEntity(); r.setId(UUID.randomUUID().toString()); r.setCode(code); r.setName(name); r.setCreatedAt(OffsetDateTime.now()); return r; });
        LinkedHashSet<PermissionEntity> assigned = new LinkedHashSet<>(); codes.forEach(c -> assigned.add(all.get(c))); e.setPermissions(assigned); return roles.save(e);
    }
    private void user(String username, String password, String displayName, String email, RoleEntity role) {
        if (users.findByUsername(username).isPresent()) return;
        UserEntity e = new UserEntity(); OffsetDateTime now = OffsetDateTime.now();
        e.setId(UUID.randomUUID().toString()); e.setUsername(username); e.setPasswordHash(encoder.encode(password)); e.setDisplayName(displayName); e.setEmail(email); e.setStatus("ACTIVE"); e.setCreatedAt(now); e.setUpdatedAt(now); e.setRoles(new LinkedHashSet<>(Set.of(role))); users.save(e);
    }
    private void module(String code, String name, String owner, String baseUrl, String healthPath, String status) {
        if (modules.findByModuleCode(code).isPresent()) return;
        ModuleRegistrationEntity e = new ModuleRegistrationEntity(); e.setId(UUID.randomUUID().toString()); e.setModuleCode(code); e.setModuleName(name); e.setOwnerCode(owner); e.setBaseUrl(baseUrl); e.setHealthPath(healthPath); e.setEnabled(true); e.setStatus(status); e.setContractVersion("1.0.0"); e.setUpdatedAt(OffsetDateTime.now()); modules.save(e);
    }

    private static final String[][] PERMISSIONS = {
        {"profile:read","读取个人资料"},{"profile:write","修改个人资料"},
        {"task:read","读取自己的任务"},{"task:write","管理自己的任务"},{"task:read:all","读取全部任务"},{"task:write:all","管理全部任务"},
        {"file:read","读取自己的文件"},{"file:write","管理自己的文件"},{"file:read:all","读取全部文件"},{"file:write:all","管理全部文件"},
        {"ai:invoke","调用AI统一网关"},{"ai:log:read","读取自己的AI调用日志"},{"ai:log:read:all","读取全部AI调用日志"},
        {"module:read","读取模块注册信息"},{"module:write","维护模块注册信息"},{"audit:read","读取审计日志"},
        {"mood:read","读取自己的情绪打卡"},{"mood:write","创建自己的情绪打卡"},{"mood:read:all","按授权读取全部情绪打卡"}
    };
}
