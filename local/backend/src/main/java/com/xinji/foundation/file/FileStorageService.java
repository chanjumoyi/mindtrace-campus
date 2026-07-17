package com.xinji.foundation.file;

import com.xinji.foundation.audit.AuditService;
import com.xinji.foundation.auth.SecurityUtils;
import com.xinji.foundation.common.BusinessException;
import com.xinji.foundation.common.ErrorCode;
import com.xinji.foundation.common.Hashes;
import com.xinji.foundation.common.Jsons;
import com.xinji.foundation.config.XinjiProperties;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class FileStorageService {
    private final FileObjectRepository repository;
    private final XinjiProperties properties;
    private final AuditService audit;
    private final Jsons jsons;
    private final Path root;

    public FileStorageService(FileObjectRepository repository, XinjiProperties properties, AuditService audit, Jsons jsons) throws IOException {
        this.repository = repository; this.properties = properties; this.audit = audit; this.jsons = jsons;
        this.root = Path.of(properties.getStorage().getRoot()).toAbsolutePath().normalize();
        Files.createDirectories(this.root);
    }

    @Transactional
    public FileView store(String moduleCode, String sensitivityLevel, MultipartFile file) {
        var actor = SecurityUtils.current();
        if (file.isEmpty()) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "文件不能为空");
        String contentType = file.getContentType() == null ? "application/octet-stream" : file.getContentType().toLowerCase();
        if (!properties.getStorage().getAllowedContentTypes().contains(contentType)) {
            throw new BusinessException(ErrorCode.FILE_TYPE_NOT_ALLOWED, "不允许的文件类型: " + contentType);
        }
        String original = sanitizeName(file.getOriginalFilename());
        String storageName = UUID.randomUUID() + extension(original);
        Path target = root.resolve(storageName).normalize();
        if (!target.startsWith(root)) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "非法文件路径");
        try {
            byte[] bytes = file.getBytes();
            Files.write(target, bytes, StandardOpenOption.CREATE_NEW);
            FileObjectEntity e = new FileObjectEntity();
            e.setId(UUID.randomUUID().toString());
            e.setOwnerUserId(actor.id());
            e.setModuleCode(normalizeModule(moduleCode));
            e.setOriginalName(original);
            e.setStorageName(storageName);
            e.setContentType(contentType);
            e.setSizeBytes(bytes.length);
            e.setSha256(Hashes.sha256(bytes));
            e.setSensitivityLevel(normalizeSensitivity(sensitivityLevel));
            e.setMetadataJson(jsons.write(Map.of("scanStatus", "DEMO_SKIPPED", "note", "比赛模拟数据；生产环境需接入恶意文件扫描")));
            e.setCreatedAt(OffsetDateTime.now());
            repository.save(e);
            audit.record(actor.id(), actor.getUsername(), "FILE_UPLOAD", "FILE", e.getId(), "SUCCESS", null,
                    jsons.write(Map.of("module", e.getModuleCode(), "sha256", e.getSha256())));
            return FileView.from(e);
        } catch (IOException ex) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "文件保存失败");
        }
    }

    @Transactional(readOnly = true)
    public List<FileView> list() {
        var actor = SecurityUtils.current();
        var rows = actor.permissions().contains("file:read:all")
                ? repository.findTop100ByDeletedAtIsNullOrderByCreatedAtDesc()
                : repository.findTop100ByOwnerUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(actor.id());
        return rows.stream().map(FileView::from).toList();
    }

    @Transactional(readOnly = true)
    public FileView get(String id) {
        var actor = SecurityUtils.current();
        FileObjectEntity e = repository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "文件不存在"));
        if (!actor.permissions().contains("file:read:all") && !actor.id().equals(e.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权读取该文件");
        }
        return FileView.from(e);
    }

    @Transactional(readOnly = true)
    public Download download(String id) {
        var actor = SecurityUtils.current();
        FileObjectEntity e = repository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "文件不存在"));
        if (!actor.permissions().contains("file:read:all") && !actor.id().equals(e.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权读取该文件");
        }
        Path target = root.resolve(e.getStorageName()).normalize();
        if (!target.startsWith(root) || !Files.exists(target)) throw new BusinessException(ErrorCode.NOT_FOUND, "文件内容不存在");
        try {
            Resource resource = new UrlResource(target.toUri());
            return new Download(e.getOriginalName(), e.getContentType(), e.getSizeBytes(), resource);
        } catch (Exception ex) {
            throw new BusinessException(ErrorCode.INTERNAL_ERROR, "文件读取失败");
        }
    }

    @Transactional
    public void delete(String id) {
        var actor = SecurityUtils.current();
        FileObjectEntity e = repository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "文件不存在"));
        if (!actor.permissions().contains("file:write:all") && !actor.id().equals(e.getOwnerUserId())) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权删除该文件");
        }
        e.setDeletedAt(OffsetDateTime.now());
        repository.save(e);
        audit.record(actor.id(), actor.getUsername(), "FILE_DELETE", "FILE", e.getId(), "SUCCESS", null, null);
    }

    private static String sanitizeName(String value) {
        String name = value == null ? "unnamed" : Path.of(value).getFileName().toString();
        name = name.replaceAll("[\\r\\n\\t]", "_");
        return name.length() > 240 ? name.substring(name.length() - 240) : name;
    }
    private static String extension(String name) {
        int i = name.lastIndexOf('.');
        if (i < 0 || name.length() - i > 12) return "";
        String ext = name.substring(i).toLowerCase();
        return ext.matches("\\.[a-z0-9]{1,10}") ? ext : "";
    }
    private static String normalizeModule(String value) {
        String v = value == null || value.isBlank() ? "COMMON" : value.trim().toUpperCase();
        if (!v.matches("[A-Z0-9_-]{2,50}")) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "moduleCode 格式不正确");
        return v;
    }
    private static String normalizeSensitivity(String value) {
        String v = value == null ? "L2" : value.toUpperCase();
        if (!List.of("L1", "L2", "L3", "L4").contains(v)) throw new BusinessException(ErrorCode.INVALID_ARGUMENT, "sensitivityLevel 只能是 L1-L4");
        return v;
    }

    public record FileView(String id, String ownerUserId, String moduleCode, String originalName, String contentType, long sizeBytes, String sha256, String sensitivityLevel, OffsetDateTime createdAt) {
        static FileView from(FileObjectEntity e) {
            return new FileView(e.getId(), e.getOwnerUserId(), e.getModuleCode(), e.getOriginalName(), e.getContentType(), e.getSizeBytes(), e.getSha256(), e.getSensitivityLevel(), e.getCreatedAt());
        }
    }
    public record Download(String filename, String contentType, long sizeBytes, Resource resource) {}
}
