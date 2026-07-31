package com.xinji.foundation.plan;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.OffsetDateTime;

@Entity
@Table(name = "action_plan_item")
public class ActionPlanItemEntity {
    @Id private String id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "plan_id", nullable = false)
    private ActionPlanEntity plan;
    @Column(nullable = false) private String title;
    @Column(name = "scheduled_on") private LocalDate scheduledOn;
    @Column(nullable = false) private String status;
    @Column private String feedback;
    @Column(name = "completed_at") private OffsetDateTime completedAt;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public ActionPlanEntity getPlan() { return plan; }
    public void setPlan(ActionPlanEntity plan) { this.plan = plan; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public LocalDate getScheduledOn() { return scheduledOn; }
    public void setScheduledOn(LocalDate scheduledOn) { this.scheduledOn = scheduledOn; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getFeedback() { return feedback; }
    public void setFeedback(String feedback) { this.feedback = feedback; }
    public OffsetDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(OffsetDateTime completedAt) { this.completedAt = completedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
