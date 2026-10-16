import { expect, test } from "@playwright/test";

test("the collector keeps identity read-only and pen-safe actions outside scroll dragging", async ({ page }) => {
  test.setTimeout(30_000);
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();

  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await expect(currentScreen).toContainText(/MT-\d{8}-[A-HJ-NP-Z2-9]{6}/);
  await expect(currentScreen).toContainText("第 1 次");
  await expect(currentScreen.locator("#participant")).toHaveCount(0);

  await currentScreen.getByRole("checkbox").check();
  await currentScreen.getByRole("button", { name: "继续" }).click();

  for (let itemIndex = 0; itemIndex < 18; itemIndex += 1) {
    await currentScreen.getByRole("radio", { name: "从未 0 天" }).click();
    await currentScreen.getByRole("button", { name: itemIndex === 17 ? "进入书写采集" : "下一题" }).click();
  }

  await expect(currentScreen.getByText("压力热身")).toBeVisible();
  await expect(currentScreen.locator(".writing-actions")).toHaveAttribute("data-scroll-drag", "ignore");
  await expect(currentScreen.getByRole("button", { name: "确认本页书写" })).toHaveAttribute("type", "button");
});
