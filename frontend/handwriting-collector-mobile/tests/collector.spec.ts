import { expect, test } from "@playwright/test";

test("initial collection creates the requested ID and keeps pen-safe writing actions", async ({ page }) => {
  test.setTimeout(30_000);
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();

  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await currentScreen.getByRole("button", { name: "初次测试" }).click();
  await currentScreen.getByRole("spinbutton", { name: "年龄" }).fill("20");
  await currentScreen.getByLabel("年级").selectOption("24");
  await currentScreen.getByLabel("来自省份").selectOption("440000");
  await currentScreen.getByRole("button", { name: "生成采集编号" }).click();

  await expect(currentScreen).toContainText(/MT-24-[A-HJ-NP-Z2-9]{4}/);
  await expect(currentScreen).toContainText("第 1 次");
  const participantId = await currentScreen.locator(".identity-card strong").innerText();
  const storedProfile = await page.evaluate((id) => localStorage.getItem(`mindtrace.participant-profile.v2.${id}`), participantId);
  expect(JSON.parse(storedProfile ?? "{}")).toMatchObject({ ageYears: 20, grade: "24", provinceCode: "440000", provinceLabel: "广东省" });

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

test("follow-up collection accepts the fixed administrator test ID", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();
  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await currentScreen.getByRole("button", { name: "后续测试" }).click();
  await currentScreen.getByRole("textbox", { name: "前两位" }).fill("ad");
  await currentScreen.getByLabel("年级").selectOption("24");
  await currentScreen.getByRole("textbox", { name: "后四位" }).fill("mast");
  await currentScreen.getByRole("button", { name: "确认采集编号" }).click();
  await expect(currentScreen).toContainText("AD-24-MAST");
});

test("identity actions keep visual spacing and the keyboard dismisses outside fields", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();
  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');

  const modeButton = currentScreen.getByRole("button", { name: "初次测试" });
  const confirmButton = currentScreen.getByRole("button", { name: "确认采集编号" });
  const [modeBox, confirmBox] = await Promise.all([modeButton.boundingBox(), confirmButton.boundingBox()]);
  expect(modeBox).not.toBeNull();
  expect(confirmBox).not.toBeNull();
  expect((confirmBox?.y ?? 0) - ((modeBox?.y ?? 0) + (modeBox?.height ?? 0))).toBeGreaterThanOrEqual(15);

  await modeButton.click();
  await currentScreen.getByRole("spinbutton", { name: "年龄" }).click();
  await expect(page.getByTestId("keyboard-dock")).toHaveAttribute("data-visible", "true");
  await currentScreen.getByRole("heading", { name: "参与者识别" }).click();
  await expect(page.getByTestId("keyboard-dock")).toHaveAttribute("data-visible", "false");
});
