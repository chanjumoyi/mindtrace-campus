package com.xinji.foundation.wellbeing;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "mood_checkin")
public class MoodCheckinEntity {
    @Id private String id;
    @Column(name = "owner_user_id", nullable = false) private String ownerUserId;
    @Column(nullable = false) private int mood;
    @Column(nullable = false) private int stress;
    @Column(name = "sleep_hours", nullable = false) private double sleepHours;
    @Column(name = "tags_json", nullable = false, columnDefinition = "TEXT") private String tagsJson;
    @Column(name = "occurred_at", nullable = false) private OffsetDateTime occurredAt;
    @Column(name = "created_at", nullable = false) private OffsetDateTime createdAt;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getOwnerUserId() { return ownerUserId; }
    public void setOwnerUserId(String ownerUserId) { this.ownerUserId = ownerUserId; }
    public int getMood() { return mood; }
    public void setMood(int mood) { this.mood = mood; }
    public int getStress() { return stress; }
    public void setStress(int stress) { this.stress = stress; }
    public double getSleepHours() { return sleepHours; }
    public void setSleepHours(double sleepHours) { this.sleepHours = sleepHours; }
    public String getTagsJson() { return tagsJson; }
    public void setTagsJson(String tagsJson) { this.tagsJson = tagsJson; }
    public OffsetDateTime getOccurredAt() { return occurredAt; }
    public void setOccurredAt(OffsetDateTime occurredAt) { this.occurredAt = occurredAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
