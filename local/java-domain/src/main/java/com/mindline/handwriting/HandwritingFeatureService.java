package com.mindline.handwriting;

import java.util.*;

/**
 * 笔迹特征提取服务 —— 从手写轨迹坐标序列提取结构化特征。
 *
 * <p>提取的特征包括：
 * <ul>
 *   <li>笔划数（stroke count）</li>
 *   <li>总点数（total points）</li>
 *   <li>平均书写速度（average writing speed, px/s）</li>
 *   <li>停顿次数（pauses: >500ms inter-stroke gap）</li>
 *   <li>边界框（bounding box: width × height）</li>
 *   <li>书写密度（point density per 10000 px²）</li>
 * </ul>
 *
 * <p>纯Java实现，无外部依赖。可直接编译为苍穹 Java 插件。
 */
public class HandwritingFeatureService {

    /** 500ms 以上的笔划间隔视为停顿 */
    public static final long PAUSE_THRESHOLD_MS = 500;

    /**
     * 从笔划数据中提取特征。
     *
     * @param strokes 笔划列表，每个笔划包含带时间戳的坐标点
     * @return 笔迹特征
     */
    public HandwritingFeatures extract(List<Stroke> strokes) {
        if (strokes == null || strokes.isEmpty()) {
            return HandwritingFeatures.empty();
        }

        HandwritingFeatures features = new HandwritingFeatures();
        features.strokeCount = strokes.size();

        // 展开所有点
        List<Point> allPoints = new ArrayList<>();
        for (Stroke s : strokes) {
            allPoints.addAll(s.getPoints());
        }
        features.totalPoints = allPoints.size();

        // 速度计算
        double[] speedResult = calculateSpeed(strokes);
        features.totalDistance = speedResult[0];
        features.totalTimeMs = (long) speedResult[1];
        features.avgSpeedPxPerSec = speedResult[2];

        // 停顿检测
        features.pauseCount = countPauses(strokes);

        // 边界框
        double[] bounds = calculateBounds(allPoints);
        features.boundX = bounds[0];
        features.boundY = bounds[1];
        features.boundWidth = bounds[2];
        features.boundHeight = bounds[3];

        // 密度
        double area = features.boundWidth * features.boundHeight;
        features.densityPer10kPx = area > 0
                ? Math.round(features.totalPoints / (area / 10000.0) * 10.0) / 10.0
                : 0;

        return features;
    }

    /**
     * 计算总距离、总时间和平均速度。
     * @return [totalDistance, totalTimeMs, avgSpeedPxPerSec]
     */
    private double[] calculateSpeed(List<Stroke> strokes) {
        double totalDist = 0;
        long totalTimeMs = 0;

        for (Stroke stroke : strokes) {
            List<Point> pts = stroke.getPoints();
            for (int i = 1; i < pts.size(); i++) {
                Point a = pts.get(i - 1);
                Point b = pts.get(i);
                double dx = b.getX() - a.getX();
                double dy = b.getY() - a.getY();
                totalDist += Math.sqrt(dx * dx + dy * dy);
                totalTimeMs += (b.getTimestamp() - a.getTimestamp());
            }
        }

        double avgSpeed = totalTimeMs > 0
                ? Math.round(totalDist / (totalTimeMs / 1000.0))
                : 0;

        return new double[]{totalDist, totalTimeMs, avgSpeed};
    }

    /**
     * 计算笔划间的停顿次数（>500ms 间隔）。
     */
    private int countPauses(List<Stroke> strokes) {
        int pauses = 0;
        for (int i = 1; i < strokes.size(); i++) {
            List<Point> prevPoints = strokes.get(i - 1).getPoints();
            List<Point> currPoints = strokes.get(i).getPoints();
            if (!prevPoints.isEmpty() && !currPoints.isEmpty()) {
                long gap = currPoints.get(0).getTimestamp()
                        - prevPoints.get(prevPoints.size() - 1).getTimestamp();
                if (gap > PAUSE_THRESHOLD_MS) {
                    pauses++;
                }
            }
        }
        // 笔划内部的长时间停顿
        for (Stroke stroke : strokes) {
            List<Point> pts = stroke.getPoints();
            for (int i = 1; i < pts.size(); i++) {
                long gap = pts.get(i).getTimestamp() - pts.get(i - 1).getTimestamp();
                if (gap > PAUSE_THRESHOLD_MS) {
                    pauses++;
                }
            }
        }
        return pauses;
    }

    /**
     * 计算所有点的边界框。
     * @return [minX, minY, width, height]
     */
    private double[] calculateBounds(List<Point> points) {
        double minX = Double.MAX_VALUE, minY = Double.MAX_VALUE;
        double maxX = Double.MIN_VALUE, maxY = Double.MIN_VALUE;

        for (Point p : points) {
            if (p.getX() < minX) minX = p.getX();
            if (p.getY() < minY) minY = p.getY();
            if (p.getX() > maxX) maxX = p.getX();
            if (p.getY() > maxY) maxY = p.getY();
        }

        return new double[]{
                minX, minY,
                Math.round((maxX - minX) * 10.0) / 10.0,
                Math.round((maxY - minY) * 10.0) / 10.0
        };
    }

    // ---- 数据类 ----

    /** 坐标点 */
    public static class Point {
        private double x;
        private double y;
        private long timestamp;

        public Point() {}
        public Point(double x, double y, long timestamp) {
            this.x = x; this.y = y; this.timestamp = timestamp;
        }

        public double getX() { return x; }
        public void setX(double x) { this.x = x; }
        public double getY() { return y; }
        public void setY(double y) { this.y = y; }
        public long getTimestamp() { return timestamp; }
        public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    }

    /** 笔划 */
    public static class Stroke {
        private List<Point> points;
        private String color;
        private double width;

        public Stroke() { this.points = new ArrayList<>(); }
        public Stroke(List<Point> points) { this.points = points; }

        public List<Point> getPoints() { return points; }
        public void setPoints(List<Point> points) { this.points = points; }
        public String getColor() { return color; }
        public void setColor(String color) { this.color = color; }
        public double getWidth() { return width; }
        public void setWidth(double width) { this.width = width; }
    }

    /** 笔迹特征结果 */
    public static class HandwritingFeatures {
        public int strokeCount;
        public int totalPoints;
        public long totalTimeMs;
        public double totalDistance;
        public double avgSpeedPxPerSec;
        public int pauseCount;
        public double boundX, boundY;
        public double boundWidth, boundHeight;
        public double densityPer10kPx;

        public static HandwritingFeatures empty() {
            return new HandwritingFeatures();
        }

        // getters
        public int getStrokeCount() { return strokeCount; }
        public int getTotalPoints() { return totalPoints; }
        public long getTotalTimeMs() { return totalTimeMs; }
        public double getTotalDistance() { return totalDistance; }
        public double getAvgSpeedPxPerSec() { return avgSpeedPxPerSec; }
        public int getPauseCount() { return pauseCount; }
        public double getBoundX() { return boundX; }
        public double getBoundY() { return boundY; }
        public double getBoundWidth() { return boundWidth; }
        public double getBoundHeight() { return boundHeight; }
        public double getDensityPer10kPx() { return densityPer10kPx; }
    }
}
