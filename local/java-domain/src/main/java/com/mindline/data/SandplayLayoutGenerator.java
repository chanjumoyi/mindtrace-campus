package com.mindline.data;

import com.mindline.model.SandplayElement;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * 沙盘布局随机生成器 —— 生成可配置的模拟沙盘布局数据。
 *
 * <p>支持不同的分布模式（均匀/聚类/散点），用于测试数据生成和批量验证。
 * 生成的数据均标注为模拟，零真实学生信息。
 *
 * <p>使用示例：
 * <pre>{@code
 * SandplayLayoutGenerator gen = new SandplayLayoutGenerator(42L);
 * List<SandplayElement> layout = gen.generate(12, Distribution.CLUSTERED);
 * }</pre>
 */
public class SandplayLayoutGenerator {

    /** 画布宽度（逻辑单位） */
    public static final double CANVAS_WIDTH = 800.0;

    /** 画布高度（逻辑单位） */
    public static final double CANVAS_HEIGHT = 600.0;

    /** 预定义元素模板 */
    private static final List<ElementTemplate> TEMPLATES = List.of(
            new ElementTemplate("person-adult-male", "人物"),
            new ElementTemplate("person-adult-female", "人物"),
            new ElementTemplate("person-child", "人物"),
            new ElementTemplate("person-elder", "人物"),
            new ElementTemplate("animal-dog", "动物"),
            new ElementTemplate("animal-cat", "动物"),
            new ElementTemplate("animal-bird", "动物"),
            new ElementTemplate("animal-fish", "动物"),
            new ElementTemplate("building-house", "建筑"),
            new ElementTemplate("building-school", "建筑"),
            new ElementTemplate("building-fence", "建筑"),
            new ElementTemplate("plant-tree-oak", "植物"),
            new ElementTemplate("plant-tree-pine", "植物"),
            new ElementTemplate("plant-flower", "植物"),
            new ElementTemplate("plant-bush", "植物"),
            new ElementTemplate("nature-sun", "自然"),
            new ElementTemplate("nature-moon", "自然"),
            new ElementTemplate("nature-cloud", "自然"),
            new ElementTemplate("nature-mountain", "自然"),
            new ElementTemplate("nature-rock", "自然"),
            new ElementTemplate("vehicle-car", "交通工具"),
            new ElementTemplate("vehicle-bicycle", "交通工具"),
            new ElementTemplate("abstract-star", "抽象符号"),
            new ElementTemplate("abstract-heart", "抽象符号"),
            new ElementTemplate("abstract-circle", "抽象符号")
    );

    private final Random random;

    /**
     * 分布模式
     */
    public enum Distribution {
        /** 均匀分布 —— 元素在整个画布均匀散布 */
        UNIFORM,
        /** 聚类分布 —— 元素围绕1-3个中心聚集 */
        CLUSTERED,
        /** 散点分布 —— 元素沿四边和角落分布 */
        SCATTERED,
        /** 象限分布 —— 元素集中在某一象限 */
        QUADRANT
    }

    public SandplayLayoutGenerator() {
        this.random = ThreadLocalRandom.current();
    }

    public SandplayLayoutGenerator(long seed) {
        this.random = new Random(seed);
    }

    /**
     * 生成指定数量和分布模式的沙盘布局。
     *
     * @param count        元素数量（1-200）
     * @param distribution 分布模式
     * @return 生成的沙盘元素列表
     */
    public List<SandplayElement> generate(int count, Distribution distribution) {
        if (count < 0 || count > 200) {
            throw new IllegalArgumentException("元素数量必须在0-200之间，当前: " + count);
        }

        List<SandplayElement> elements = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            ElementTemplate template = pickRandomTemplate();
            double[] pos = generatePosition(distribution);
            SandplayElement elem = new SandplayElement(
                    "gen-inst-" + String.format("%03d", i + 1),
                    template.elementId,
                    template.category,
                    pos[0], pos[1],
                    random.nextDouble() * 360.0,
                    0.3 + random.nextDouble() * 2.0,
                    i
            );
            elements.add(elem);
        }
        return elements;
    }

    /**
     * 生成便捷方法：12个元素的聚类分布。
     */
    public List<SandplayElement> generateDefault() {
        return generate(12, Distribution.CLUSTERED);
    }

    /**
     * 生成便捷方法：指定数量的均匀分布。
     */
    public List<SandplayElement> generateUniform(int count) {
        return generate(count, Distribution.UNIFORM);
    }

    // ---- 内部方法 ----

    private ElementTemplate pickRandomTemplate() {
        return TEMPLATES.get(random.nextInt(TEMPLATES.size()));
    }

    private double[] generatePosition(Distribution distribution) {
        return switch (distribution) {
            case UNIFORM -> new double[]{
                    random.nextDouble() * CANVAS_WIDTH,
                    random.nextDouble() * CANVAS_HEIGHT
            };
            case CLUSTERED -> {
                // 选择1-3个聚类中心
                double[][] centers = {
                        {200 + random.nextDouble() * 400, 150 + random.nextDouble() * 300},
                        {200 + random.nextDouble() * 400, 150 + random.nextDouble() * 300},
                        {200 + random.nextDouble() * 400, 150 + random.nextDouble() * 300}
                };
                double[] center = centers[random.nextInt(3)];
                // 在中心周围80单位内散布
                double cx = center[0] + (random.nextGaussian() * 80);
                double cy = center[1] + (random.nextGaussian() * 80);
                yield new double[]{
                        clamp(cx, 0, CANVAS_WIDTH),
                        clamp(cy, 0, CANVAS_HEIGHT)
                };
            }
            case SCATTERED -> {
                // 倾向于边缘
                double x = random.nextBoolean()
                        ? random.nextDouble() * 150
                        : CANVAS_WIDTH - random.nextDouble() * 150;
                double y = random.nextDouble() * CANVAS_HEIGHT;
                yield new double[]{x, y};
            }
            case QUADRANT -> {
                // 集中在左上象限
                double x = random.nextDouble() * 350;
                double y = random.nextDouble() * 250;
                yield new double[]{x, y};
            }
        };
    }

    private double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }

    /** 元素模板 */
    private record ElementTemplate(String elementId, String category) {}
}
