package com.xinji.foundation.task;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "common_task")
public class TaskEntity {
    @Id private String id;
    @Column(name = "owner_user_id") private String ownerUserId;
    @Column(name = "module_code", nullable = false) private String moduleCode;
    @Column(name = "task_type", nullable = false) private String taskType;
    @Column(nullable = false) private String title;
    @Enumerated(EnumType.STRING) @Column(nullable = false) private TaskStatus status;
    @Column(nullable = false) private int progress;
    @Column(name = "request_ref") private String requestRef;
    @Column(name = "result_ref") private String resultRef;
    @Column(name = "error_code") private String errorCode;
    @Column(name = "error_message") private String errorMessage;
    @Version private long version;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;
    @Column(name = "updated_at", nullable = false) private OffsetDateTime updatedAt;
    public String getId() { return id; } public void setId(String id) { this.id = id; }
    public String getOwnerUserId() { return ownerUserId; } public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }
    public String getModuleCode() { return moduleCode; } public void setModuleCode(String moduleCode) { this.moduleCode = moduleCode; }
    public String getTaskType() { return taskType; } public void setTaskType(String taskType) { this.taskType = taskType; }
    public String getTitle() { return title; } public void setTitle(String title) { this.title = title; }
    public TaskStatus getStatus() { return status; } public void setStatus(TaskStatus status) { this.status = status; }
    public int getProgress() { return progress; } public void setProgress(int progress) { this.progress = progress; }
    public String getRequestRef() { return requestRef; } public void setRequestRef(String requestRef) { this.requestRef = requestRef; }
    public String getResultRef() { return resultRef; } public void setResultRef(String resultRef) { this.resultRef = resultRef; }
    public String getErrorCode() { return errorCode; } public void setErrorCode(String errorCode) { this.errorCode = errorCode; }
    public String getErrorMessage() { return errorMessage; } public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public long getVersion() { return version; } public void setVersion(long version) { this.version = version; }
    public OffsetDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; } public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
}
