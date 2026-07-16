package com.mindline.model;

import java.util.List;

/**
 * 沙盘元素 —— 画布上的单个元素实例。
 */
public class SandplayElement {

    private String instanceId;
    private String elementId;
    private String category;
    private double x;
    private double y;
    private double rotation;
    private double scale;
    private int zIndex;

    public SandplayElement() {}

    public SandplayElement(String instanceId, String elementId, String category,
                           double x, double y, double rotation, double scale, int zIndex) {
        this.instanceId = instanceId;
        this.elementId = elementId;
        this.category = category;
        this.x = x;
        this.y = y;
        this.rotation = rotation;
        this.scale = scale;
        this.zIndex = zIndex;
    }

    public String getInstanceId() { return instanceId; }
    public void setInstanceId(String instanceId) { this.instanceId = instanceId; }

    public String getElementId() { return elementId; }
    public void setElementId(String elementId) { this.elementId = elementId; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public double getX() { return x; }
    public void setX(double x) { this.x = x; }

    public double getY() { return y; }
    public void setY(double y) { this.y = y; }

    public double getRotation() { return rotation; }
    public void setRotation(double rotation) { this.rotation = rotation; }

    public double getScale() { return scale; }
    public void setScale(double scale) { this.scale = scale; }

    public int getZIndex() { return zIndex; }
    public void setZIndex(int zIndex) { this.zIndex = zIndex; }
}
