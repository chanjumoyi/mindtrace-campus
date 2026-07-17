package com.xinji.foundation.file;

import com.xinji.foundation.common.ApiResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.springframework.http.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/files")
public class FileController {
    private final FileStorageService service;
    public FileController(FileStorageService service) { this.service = service; }
    @GetMapping @PreAuthorize("hasAuthority('file:read')")
    public ApiResponse<List<FileStorageService.FileView>> list() { return ApiResponse.ok(service.list()); }
    @GetMapping("/{id}") @PreAuthorize("hasAuthority('file:read')")
    public ApiResponse<FileStorageService.FileView> get(@PathVariable String id) { return ApiResponse.ok(service.get(id)); }
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE) @PreAuthorize("hasAuthority('file:write')")
    public ApiResponse<FileStorageService.FileView> upload(@RequestParam(defaultValue = "COMMON") String moduleCode, @RequestParam(defaultValue = "L2") String sensitivityLevel, @RequestPart("file") MultipartFile file) {
        return ApiResponse.ok("文件已上传", service.store(moduleCode, sensitivityLevel, file));
    }
    @GetMapping("/{id}/content") @PreAuthorize("hasAuthority('file:read')")
    public ResponseEntity<org.springframework.core.io.Resource> download(@PathVariable String id) {
        var d = service.download(id);
        ContentDisposition disposition = ContentDisposition.attachment().filename(d.filename(), StandardCharsets.UTF_8).build();
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(d.contentType())).contentLength(d.sizeBytes()).header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString()).body(d.resource());
    }
    @DeleteMapping("/{id}") @PreAuthorize("hasAuthority('file:write')")
    public ApiResponse<Void> delete(@PathVariable String id) { service.delete(id); return ApiResponse.ok("文件已删除", null); }
}
